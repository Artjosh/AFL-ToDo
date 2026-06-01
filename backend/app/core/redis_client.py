"""Cliente Redis com fallback gracioso.

Quando REDIS_URL está configurado, fornece um cliente Redis (singleton). Quando
NÃO está, retorna None — e cada chamador faz o fallback apropriado (ex.: tokens
de login vão para o banco; rate limit e realtime são desativados).

Assim o backend funciona com ou sem Redis, sem ramificações espalhadas pelo código.
"""

from __future__ import annotations

import redis

from app.core.config import settings

_client: redis.Redis | None = None
_initialized = False


def get_redis() -> redis.Redis | None:
    """Retorna o cliente Redis (singleton) ou None se indisponível/desconfigurado."""
    global _client, _initialized

    if not settings.redis_enabled:
        return None

    if _initialized:
        return _client

    _initialized = True
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _client = client
    except Exception:
        # Redis configurado mas indisponível: degrada para fallback sem derrubar a app.
        _client = None

    return _client


def reset_redis_cache() -> None:
    """Reseta o singleton (útil em testes que mudam REDIS_URL)."""
    global _client, _initialized
    _client = None
    _initialized = False
