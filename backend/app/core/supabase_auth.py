"""Validação de tokens JWT emitidos pela Supabase (usando PyJWT).

A validação usa chaves **assimétricas (ES256/RS256)** verificadas pelo JWKS
público do projeto (SUPABASE_JWKS_URL) via PyJWKClient, que cacheia as chaves
internamente. Issuer e audience são validados quando configurados.

> O projeto usa o sistema novo de "JWT Signing Keys" da Supabase (chave ECC/ES256).
> A "JWKS" é justamente a publicação pública dessas chaves. O backend não precisa
> de nenhum segredo — valida com a chave pública.
"""
from __future__ import annotations

from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.core.config import settings

# Cache do PyJWKClient (reutiliza conexão e chaves entre chamadas).
_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


class SupabaseAuthError(Exception):
    """Erro de validação de token Supabase."""


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client, _jwk_client_url
    if not settings.SUPABASE_JWKS_URL:
        raise SupabaseAuthError("SUPABASE_JWKS_URL não configurada.")
    # Recria o client se a URL mudou (ex.: testes com monkeypatch).
    if _jwk_client is None or _jwk_client_url != settings.SUPABASE_JWKS_URL:
        _jwk_client = PyJWKClient(settings.SUPABASE_JWKS_URL, cache_keys=True)
        _jwk_client_url = settings.SUPABASE_JWKS_URL
    return _jwk_client


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Valida um access token da Supabase e retorna o payload (claims).

    Levanta SupabaseAuthError se o token for inválido ou se o modo Supabase não
    estiver configurado.
    """
    if not settings.supabase_enabled:
        raise SupabaseAuthError("Modo Supabase não está configurado no backend.")

    audience = settings.SUPABASE_JWT_AUDIENCE or None
    issuer = settings.SUPABASE_JWT_ISSUER or None
    options = {"verify_aud": bool(audience)}

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg", "")
        if not algorithm.startswith(("RS", "ES")):
            raise SupabaseAuthError(
                f"Algoritmo de token não suportado: {algorithm or 'desconhecido'}. "
                "Este projeto valida apenas chaves assimétricas (ES256/RS256) via JWKS."
            )

        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            options=options,
        )
    except SupabaseAuthError:
        raise
    except (InvalidTokenError, Exception) as exc:  # PyJWKClient pode lançar erros próprios
        raise SupabaseAuthError(f"Token Supabase inválido: {exc}") from exc

    return payload


def verify_email_otp_hash(token_hash: str, otp_type: str = "email") -> dict[str, Any]:
    """Troca um token_hash (do link do email) por uma sessão da Supabase.

    Usado no callback cross-device do modo Supabase: o backend recebe o token_hash
    do link, chama o endpoint /auth/v1/verify da Supabase e obtém a sessão
    (access_token + refresh_token + user). Requer SUPABASE_URL e a chave pública.

    Levanta SupabaseAuthError em caso de falha.
    """
    if not settings.supabase_callback_enabled:
        raise SupabaseAuthError(
            "Callback Supabase indisponível: defina SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY."
        )

    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/verify"
    try:
        response = httpx.post(
            url,
            params={"apikey": settings.SUPABASE_PUBLISHABLE_KEY},
            headers={
                "apikey": settings.SUPABASE_PUBLISHABLE_KEY,
                "Content-Type": "application/json",
            },
            json={"type": otp_type, "token_hash": token_hash},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - depende de rede
        raise SupabaseAuthError(f"Falha ao verificar token na Supabase: {exc}") from exc

    if response.status_code != 200:
        raise SupabaseAuthError(
            f"Supabase recusou o token_hash (HTTP {response.status_code})."
        )

    data = response.json()
    if not data.get("access_token"):
        raise SupabaseAuthError("Resposta da Supabase sem access_token.")
    return data
