"""Dependencies de autenticação compartilhadas pelas rotas.

A função ``get_current_user`` é a fonte única de verdade sobre "quem é o usuário".
Ela aceita os dois modos de autenticação a partir do header Authorization:

1. Token JWT local (emitido por /auth/login). O ``sub`` é o id do usuário local.
2. Token JWT da Supabase. Validado via JWKS/segredo; o usuário local é criado ou
   atualizado automaticamente (espelhado) usando o ``sub`` da Supabase.

O backend NUNCA confia em um user_id vindo do corpo/query do frontend — o dono
da requisição é sempre derivado do token validado aqui.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.supabase_auth import SupabaseAuthError, verify_supabase_token
from app.db.session import get_db
from app.models.user import User

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _CREDENTIALS_EXCEPTION
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _CREDENTIALS_EXCEPTION
    return parts[1].strip()


def _get_user_from_local_token(token: str, db: Session) -> User | None:
    payload = decode_access_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def _get_or_create_user_from_supabase(token: str, db: Session) -> User | None:
    """Valida o token da Supabase e espelha o usuário no SQLite local."""
    try:
        payload = verify_supabase_token(token)
    except SupabaseAuthError:
        return None

    supabase_user_id = payload.get("sub")
    email = payload.get("email") or payload.get("user_metadata", {}).get("email")
    if not supabase_user_id:
        return None

    user = (
        db.query(User)
        .filter(User.supabase_user_id == str(supabase_user_id))
        .first()
    )

    if user is None and email:
        # Vincula a um usuário local pré-existente com o mesmo email, se houver.
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            user.supabase_user_id = str(supabase_user_id)

    if user is None:
        # Cria o espelho local do usuário Supabase.
        user = User(
            email=email or f"{supabase_user_id}@supabase.local",
            supabase_user_id=str(supabase_user_id),
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve o usuário autenticado a partir do header Authorization.

    Tenta primeiro o JWT local; se falhar e a Supabase estiver configurada,
    tenta validar como token da Supabase.
    """
    token = _extract_bearer_token(authorization)

    user = _get_user_from_local_token(token, db)
    if user is not None:
        return user

    if settings.supabase_enabled:
        user = _get_or_create_user_from_supabase(token, db)
        if user is not None:
            return user

    raise _CREDENTIALS_EXCEPTION
