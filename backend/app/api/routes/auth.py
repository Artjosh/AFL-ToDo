"""Rotas de autenticação passwordless (magic link + OTP) com polling cross-device.

Modo local (Backend Python, sem senha):
- POST /auth/magic-link        -> gera link + código OTP, "envia" email, devolve selector
- GET  /auth/confirm           -> alvo do link (qualquer device); aprova o login
- POST /auth/verify-otp        -> valida o código de 6 dígitos (device de origem)
- POST /auth/login-status      -> polling: troca selector por sessão quando aprovado
- GET  /auth/me                -> dados do usuário autenticado (qualquer modo)

Modo Supabase (Backend Python + Supabase Auth):
- O frontend chama signInWithOtp da Supabase (link + OTP no email).
- Link cross-device: o email aponta para GET /auth/supabase/callback?token_hash=...
  O backend troca o token_hash por uma sessão Supabase, guarda no pedido de login
  (selector) e o device de origem busca via /auth/login-status.
- OTP / mesmo-device: o frontend usa supabase.auth.verifyOtp e depois chama
  POST /auth/supabase/sync com o access_token; o backend valida (JWKS) e espelha.

Os pedidos de login (efêmeros) ficam no Redis quando disponível (com TTL), tirando
o tráfego do polling do banco real; sem Redis, caem na tabela login_tokens (ver
app/services/login_tokens.py). Não existe cadastro separado: o primeiro acesso cria a conta.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.email import send_login_email
from app.core.rate_limit import check_rate_limit
from app.core.request_origin import get_backend_origin
from app.core.security import create_access_token, create_ws_ticket
from app.core.supabase_auth import SupabaseAuthError, verify_email_otp_hash
from app.db.session import get_db
from app.models.login_token import LoginTokenProvider, LoginTokenStatus
from app.models.user import User
from app.schemas.auth import (
    LoginStatusResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    OtpVerifyRequest,
    SupabaseSyncResponse,
    UserOut,
)
from app.services.login_tokens import get_login_store

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_or_create_user_by_email(db: Session, email: str) -> User:
    """Busca o usuário pelo email ou cria um novo (primeiro acesso = cadastro)."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ----------------------------------------------------------------------------
# Modo local (magic link + OTP)
# ----------------------------------------------------------------------------


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MagicLinkResponse:
    """Inicia o login passwordless local: cria link + OTP e envia (ou devolve)."""
    email = payload.email.lower().strip()

    # Rate limit anti-spam (por email + por IP) — no-op se Redis indisponível.
    check_rate_limit(f"magiclink:email:{email}")
    check_rate_limit(f"magiclink:ip:{request.client.host if request.client else 'unknown'}")

    store = get_login_store(db)
    req = store.create(email, LoginTokenProvider.LOCAL)

    origin = get_backend_origin(request)
    magic_url = f"{origin}/auth/confirm?token={req.magic_token}"

    # Tenta enviar o email. Uma falha de envio não deve derrubar o request: o
    # pedido de login já foi criado e o usuário pode tentar de novo. Em modo dev,
    # os códigos ainda voltam no corpo (expose_login_codes).
    email_sent = False
    if settings.email_enabled:
        try:
            send_login_email(email, magic_url, req.otp_code or "")
            email_sent = True
        except Exception:
            email_sent = False

    # Devolve link + código na resposta apenas quando permitido. Em produção,
    # expose_login_codes é SEMPRE False (falha fechada) — nada de segredo no corpo.
    expose_codes = settings.expose_login_codes

    if email_sent:
        message = "Enviamos um link e um código de acesso para o seu email."
    elif expose_codes:
        message = "Use o link ou o código abaixo para entrar."
    else:
        message = "Não foi possível enviar o email agora. Tente novamente em instantes."

    return MagicLinkResponse(
        selector=req.selector,
        email=email,
        email_sent=email_sent,
        dev_magic_url=magic_url if expose_codes else None,
        dev_otp_code=req.otp_code if expose_codes else None,
        message=message,
    )


@router.get("/confirm", response_class=HTMLResponse)
def confirm_magic_link(token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Alvo do link do email (modo local). Aprova o login em qualquer device."""
    store = get_login_store(db)
    req = store.approve_local(token)

    if req is None:
        return _confirm_page(
            ok=False,
            message="Link inválido ou expirado. Solicite um novo acesso.",
        )

    _get_or_create_user_by_email(db, req.email)
    return _confirm_page(
        ok=True,
        message="Acesso confirmado! Volte para a aba onde iniciou o login.",
    )


@router.post("/verify-otp", response_model=LoginStatusResponse)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> LoginStatusResponse:
    """Valida o código OTP de 6 dígitos (modo local, device de origem)."""
    store = get_login_store(db)
    req = store.get_by_selector(payload.selector)

    if req is None or req.provider != LoginTokenProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido de login não encontrado ou expirado.",
        )

    if req.otp_attempts >= settings.OTP_MAX_ATTEMPTS:
        store.consume(payload.selector)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Solicite um novo acesso.",
        )

    if not secrets.compare_digest(req.otp_code or "", payload.code):
        store.increment_otp_attempts(payload.selector)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código incorreto.",
        )

    user = _get_or_create_user_by_email(db, req.email)
    access_token = create_access_token(subject=user.id)
    store.consume(payload.selector)

    return LoginStatusResponse(
        status="approved",
        authenticated=True,
        provider="local",
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


# ----------------------------------------------------------------------------
# Modo Supabase (callback cross-device via token_hash)
# ----------------------------------------------------------------------------


@router.post("/supabase/start", response_model=MagicLinkResponse)
def supabase_start(payload: MagicLinkRequest, db: Session = Depends(get_db)) -> MagicLinkResponse:
    """Cria um pedido de login Supabase para polling cross-device."""
    email = payload.email.lower().strip()
    store = get_login_store(db)
    req = store.create(email, LoginTokenProvider.SUPABASE)
    return MagicLinkResponse(
        selector=req.selector,
        email=email,
        email_sent=True,
        message="Pedido de login Supabase criado.",
    )


@router.get("/supabase/callback")
def supabase_callback(
    request: Request,
    token_hash: str,
    selector: str | None = None,
    type: str = "email",
    db: Session = Depends(get_db),
):
    """Callback do link da Supabase (cross-device).

    Troca o token_hash por uma sessão Supabase, guarda no pedido de login
    (selector ou email) e mostra uma página de sucesso. O device de origem pega
    a sessão via polling.
    """
    try:
        session_data = verify_email_otp_hash(token_hash, type)
    except SupabaseAuthError:
        return _confirm_page(
            ok=False,
            message="Link inválido ou expirado. Solicite um novo acesso.",
        )

    access_token = session_data.get("access_token")
    refresh_token = session_data.get("refresh_token")
    user_obj = session_data.get("user") or {}
    email = (user_obj.get("email") or "").lower()

    store = get_login_store(db)
    approved = None
    if selector:
        approved = store.approve_supabase(selector, access_token, refresh_token)
    if approved is None and email:
        approved = store.approve_supabase_by_email(email, access_token, refresh_token)

    if approved is not None:
        return _confirm_page(
            ok=True,
            message="Acesso confirmado! Volte para a aba onde iniciou o login.",
        )

    # Sem pedido pendente (ex.: mesmo device): manda para o frontend processar.
    frontend = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{frontend}/login?supabase=confirmed", status_code=302)


# ----------------------------------------------------------------------------
# Polling comum aos dois modos
# ----------------------------------------------------------------------------


@router.post("/login-status", response_model=LoginStatusResponse)
def login_status(selector: str, db: Session = Depends(get_db)) -> LoginStatusResponse:
    """Polling do device de origem: troca o selector por uma sessão quando aprovado."""
    store = get_login_store(db)
    req = store.get_by_selector(selector)

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido de login não encontrado ou já consumido.",
        )

    if req.status != LoginTokenStatus.APPROVED:
        return LoginStatusResponse(status="pending", authenticated=False, provider=req.provider)

    user = _get_or_create_user_by_email(db, req.email)

    if req.provider == LoginTokenProvider.SUPABASE:
        access_token = req.supabase_access_token
        refresh_token = req.supabase_refresh_token
        store.consume(selector)
        return LoginStatusResponse(
            status="approved",
            authenticated=True,
            provider="supabase",
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )

    access_token = create_access_token(subject=user.id)
    store.consume(selector)
    return LoginStatusResponse(
        status="approved",
        authenticated=True,
        provider="local",
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


# ----------------------------------------------------------------------------
# Espelhamento Supabase + perfil
# ----------------------------------------------------------------------------


@router.post("/supabase/sync", response_model=SupabaseSyncResponse)
def supabase_sync(current_user: User = Depends(get_current_user)) -> SupabaseSyncResponse:
    """Espelha/atualiza o usuário Supabase no SQLite (validação em get_current_user)."""
    return SupabaseSyncResponse(user=UserOut.model_validate(current_user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/ws-ticket")
def ws_ticket(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """Emite um ticket efêmero para autenticar o WebSocket do board.

    Usado pelo padrão BFF: o token de sessão fica num cookie httpOnly e não chega
    ao browser, então o frontend troca o cookie (via proxy) por este ticket de
    curta duração e o usa uma única vez na URL do WebSocket.
    """
    return {"ticket": create_ws_ticket(subject=current_user.id)}


def _confirm_page(ok: bool, message: str) -> HTMLResponse:
    """Página HTML simples mostrada após clicar o link (qualquer device)."""
    color = "#22c55e" if ok else "#ef4444"
    icon = "✓" if ok else "✕"
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{settings.APP_NAME} — Acesso</title>
  <style>
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #0c0e14; color: #e5e4ed;
      font-family: Inter, system-ui, -apple-system, Arial, sans-serif;
    }}
    .card {{
      max-width: 420px; padding: 32px; border-radius: 16px;
      background: #1a1c2e; border: 1px solid #2a2c3e; text-align: center;
    }}
    .badge {{
      width: 56px; height: 56px; border-radius: 999px; margin: 0 auto 16px;
      display: grid; place-items: center; font-size: 28px; font-weight: 700;
      background: {color}22; color: {color};
    }}
    h1 {{ font-size: 20px; margin: 0 0 8px; }}
    p {{ color: #aaaab3; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">{icon}</div>
    <h1>{settings.APP_NAME}</h1>
    <p>{message}</p>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200 if ok else 400)
