"""Helper para descobrir a URL pública do backend a partir do request.

Inspirado no request-origin.ts do projeto gaming-cloud: usa BACKEND_PUBLIC_URL
quando definido; caso contrário, deriva do header Host (respeitando proxies).
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import settings


def get_backend_origin(request: Request) -> str:
    if settings.BACKEND_PUBLIC_URL:
        return settings.BACKEND_PUBLIC_URL.rstrip("/")

    forwarded_proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("host")
    if host:
        proto = forwarded_proto or request.url.scheme or "http"
        return f"{proto}://{host}"

    return str(request.base_url).rstrip("/")
