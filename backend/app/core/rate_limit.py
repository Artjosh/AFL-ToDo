"""Rate limiting simples baseado em Redis (no-op quando Redis indisponível).

Usa contador com janela fixa: incrementa uma chave e a expira após a janela.
Se o número de hits ultrapassar o limite, levanta 429.

Sem Redis configurado, é um no-op (não limita) — adequado para dev/testes, onde
o foco não é proteção contra abuso.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.redis_client import get_redis


def check_rate_limit(
    key: str,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> None:
    """Levanta 429 se a chave exceder `limit` hits dentro de `window_seconds`."""
    client = get_redis()
    if client is None:
        return  # sem Redis: não limita

    limit = limit or settings.RATE_LIMIT_MAX
    window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
    redis_key = f"ratelimit:{key}"

    try:
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_seconds)
    except Exception:
        # Falha no Redis não deve derrubar o endpoint: degrada para "sem limite".
        return

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas solicitações. Aguarde um momento e tente novamente.",
        )
