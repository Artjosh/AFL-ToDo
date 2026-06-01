"""Funções de segurança do modo local (passwordless).

Não há senha no sistema. O login é por magic link / OTP:
- o backend gera um token de magic link (aleatório) com expiração curta;
- ao confirmar o link/código, o backend emite um JWT de sessão (HS256) próprio.

Usa PyJWT (biblioteca mantida e sem o DeprecationWarning de datetime do python-jose).
A validação do token Supabase fica em app/core/supabase_auth.py.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from app.core.config import settings


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Cria um JWT de sessão assinado com o JWT_SECRET da aplicação.

    O ``subject`` (sub) é o id do usuário local.
    """
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(UTC)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": now + timedelta(minutes=expire_minutes),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica e valida um JWT de sessão local. Retorna o payload ou None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except InvalidTokenError:
        return None


def create_ws_ticket(subject: str | int, expires_seconds: int = 60) -> str:
    """Cria um ticket efêmero (JWT type=ws) para autenticar o WebSocket.

    No padrão BFF, o token de sessão fica num cookie httpOnly e nunca chega ao
    browser. Para o WebSocket (que não usa o cookie httpOnly de forma prática),
    o frontend pede ao BFF um ticket de curtíssima duração e o usa uma vez na URL
    de conexão. Mesmo se vazar, expira em segundos e só serve para abrir o WS.
    """
    now = datetime.now(UTC)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": now + timedelta(seconds=expires_seconds),
        "iat": now,
        "type": "ws",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_ws_ticket(token: str) -> dict[str, Any] | None:
    """Decodifica e valida um ticket de WebSocket. Retorna o payload ou None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "ws":
            return None
        return payload
    except InvalidTokenError:
        return None
