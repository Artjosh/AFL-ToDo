"""Armazenamento dos pedidos de login (magic link + OTP) com TTL.

Os pedidos de login são dados EFÊMEROS e VOLÁTEIS (expiram em minutos, são
consultados em polling a cada poucos segundos). Por isso:

- Se houver Redis: ficam no Redis com TTL automático (sem tocar o banco real).
  Isso tira do banco o tráfego intenso do polling multi-device.
- Sem Redis: fallback para a tabela `login_tokens` no SQLite (comportamento atual).

Ambas as implementações expõem a mesma interface, então as rotas não precisam
saber onde os dados moram.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import get_redis
from app.models.login_token import LoginToken, LoginTokenProvider, LoginTokenStatus


@dataclass
class LoginRequest:
    """Representação de um pedido de login, independente do storage."""

    selector: str
    magic_token: str | None
    otp_code: str | None
    otp_attempts: int
    email: str
    provider: str
    status: str
    supabase_access_token: str | None = None
    supabase_refresh_token: str | None = None


def _new_codes(provider: str) -> tuple[str, str | None, str | None]:
    selector = secrets.token_urlsafe(24)
    if provider == LoginTokenProvider.LOCAL:
        magic_token = secrets.token_urlsafe(32)
        otp_code = f"{secrets.randbelow(1_000_000):06d}"
    else:
        magic_token = None
        otp_code = None
    return selector, magic_token, otp_code


# ---------------------------------------------------------------- interface

class LoginTokenStore:
    """Interface comum. Use get_login_store() para obter a implementação ativa."""

    def create(self, email: str, provider: str) -> LoginRequest: ...
    def get_by_selector(self, selector: str) -> LoginRequest | None: ...
    def get_by_magic_token(self, magic_token: str) -> LoginRequest | None: ...
    def approve_local(self, magic_token: str) -> LoginRequest | None: ...
    def approve_supabase(
        self, selector: str, access_token: str, refresh_token: str | None
    ) -> LoginRequest | None: ...
    def approve_supabase_by_email(
        self, email: str, access_token: str, refresh_token: str | None
    ) -> LoginRequest | None: ...
    def increment_otp_attempts(self, selector: str) -> int: ...
    def consume(self, selector: str) -> None: ...
    def invalidate_pending(self, email: str, provider: str) -> None: ...


# ---------------------------------------------------------------- Redis impl

_TTL = None  # calculado a partir de settings


def _ttl_seconds() -> int:
    return settings.MAGIC_LINK_EXPIRE_MINUTES * 60


class RedisLoginTokenStore(LoginTokenStore):
    """Tokens no Redis, com TTL automático. Índices auxiliares por magic_token e email."""

    def __init__(self, client) -> None:
        self.r = client

    @staticmethod
    def _key(selector: str) -> str:
        return f"login:sel:{selector}"

    @staticmethod
    def _mkey(magic_token: str) -> str:
        return f"login:magic:{magic_token}"

    @staticmethod
    def _ekey(email: str, provider: str) -> str:
        return f"login:email:{provider}:{email}"

    def _save(self, req: LoginRequest, ttl: int) -> None:
        self.r.set(self._key(req.selector), json.dumps(asdict(req)), ex=ttl)
        if req.magic_token:
            self.r.set(self._mkey(req.magic_token), req.selector, ex=ttl)

    def create(self, email: str, provider: str) -> LoginRequest:
        self.invalidate_pending(email, provider)
        selector, magic_token, otp_code = _new_codes(provider)
        req = LoginRequest(
            selector=selector,
            magic_token=magic_token,
            otp_code=otp_code,
            otp_attempts=0,
            email=email,
            provider=provider,
            status=LoginTokenStatus.PENDING,
        )
        ttl = _ttl_seconds()
        self._save(req, ttl)
        # registra o selector pendente por email (para invalidação/associação)
        self.r.set(self._ekey(email, provider), selector, ex=ttl)
        return req

    def get_by_selector(self, selector: str) -> LoginRequest | None:
        raw = self.r.get(self._key(selector))
        if not raw:
            return None
        return LoginRequest(**json.loads(raw))

    def get_by_magic_token(self, magic_token: str) -> LoginRequest | None:
        selector = self.r.get(self._mkey(magic_token))
        if not selector:
            return None
        return self.get_by_selector(selector)

    def _ttl_left(self, selector: str) -> int:
        ttl = self.r.ttl(self._key(selector))
        return ttl if ttl and ttl > 0 else _ttl_seconds()

    def approve_local(self, magic_token: str) -> LoginRequest | None:
        req = self.get_by_magic_token(magic_token)
        if req is None:
            return None
        req.status = LoginTokenStatus.APPROVED
        self._save(req, self._ttl_left(req.selector))
        return req

    def approve_supabase(self, selector, access_token, refresh_token):
        req = self.get_by_selector(selector)
        if req is None:
            return None
        req.status = LoginTokenStatus.APPROVED
        req.supabase_access_token = access_token
        req.supabase_refresh_token = refresh_token
        self._save(req, self._ttl_left(selector))
        return req

    def approve_supabase_by_email(self, email, access_token, refresh_token):
        selector = self.r.get(self._ekey(email, LoginTokenProvider.SUPABASE))
        if not selector:
            return None
        return self.approve_supabase(selector, access_token, refresh_token)

    def increment_otp_attempts(self, selector: str) -> int:
        req = self.get_by_selector(selector)
        if req is None:
            return 0
        req.otp_attempts += 1
        self._save(req, self._ttl_left(selector))
        return req.otp_attempts

    def consume(self, selector: str) -> None:
        req = self.get_by_selector(selector)
        if req is None:
            return
        self.r.delete(self._key(selector))
        if req.magic_token:
            self.r.delete(self._mkey(req.magic_token))
        self.r.delete(self._ekey(req.email, req.provider))

    def invalidate_pending(self, email: str, provider: str) -> None:
        selector = self.r.get(self._ekey(email, provider))
        if selector:
            self.consume(selector)


# ---------------------------------------------------------------- DB impl

class DbLoginTokenStore(LoginTokenStore):
    """Fallback: tokens na tabela login_tokens (SQLite)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _expiry(self) -> datetime:
        return datetime.now(UTC) + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)

    @staticmethod
    def _to_req(row: LoginToken) -> LoginRequest:
        return LoginRequest(
            selector=row.selector,
            magic_token=row.magic_token,
            otp_code=row.otp_code,
            otp_attempts=row.otp_attempts,
            email=row.email,
            provider=row.provider,
            status=row.status,
            supabase_access_token=row.supabase_access_token,
            supabase_refresh_token=row.supabase_refresh_token,
        )

    def _row_by_selector(self, selector: str) -> LoginToken | None:
        row = self.db.query(LoginToken).filter(LoginToken.selector == selector).first()
        if row and row.is_expired():
            self.db.delete(row)
            self.db.commit()
            return None
        return row

    def create(self, email: str, provider: str) -> LoginRequest:
        self.invalidate_pending(email, provider)
        selector, magic_token, otp_code = _new_codes(provider)
        row = LoginToken(
            selector=selector,
            magic_token=magic_token,
            otp_code=otp_code,
            otp_attempts=0,
            email=email,
            provider=provider,
            status=LoginTokenStatus.PENDING,
            expires_at=self._expiry(),
        )
        self.db.add(row)
        self.db.commit()
        return self._to_req(row)

    def get_by_selector(self, selector: str) -> LoginRequest | None:
        row = self._row_by_selector(selector)
        return self._to_req(row) if row else None

    def get_by_magic_token(self, magic_token: str) -> LoginRequest | None:
        row = (
            self.db.query(LoginToken)
            .filter(
                LoginToken.magic_token == magic_token,
                LoginToken.provider == LoginTokenProvider.LOCAL,
            )
            .first()
        )
        if row and row.is_expired():
            self.db.delete(row)
            self.db.commit()
            return None
        return self._to_req(row) if row else None

    def approve_local(self, magic_token: str) -> LoginRequest | None:
        row = (
            self.db.query(LoginToken)
            .filter(
                LoginToken.magic_token == magic_token,
                LoginToken.provider == LoginTokenProvider.LOCAL,
            )
            .first()
        )
        if row is None:
            return None
        if row.is_expired():
            self.db.delete(row)
            self.db.commit()
            return None
        row.status = LoginTokenStatus.APPROVED
        self.db.commit()
        return self._to_req(row)

    def approve_supabase(self, selector, access_token, refresh_token):
        row = self._row_by_selector(selector)
        if row is None:
            return None
        row.status = LoginTokenStatus.APPROVED
        row.supabase_access_token = access_token
        row.supabase_refresh_token = refresh_token
        self.db.commit()
        return self._to_req(row)

    def approve_supabase_by_email(self, email, access_token, refresh_token):
        row = (
            self.db.query(LoginToken)
            .filter(
                LoginToken.email == email,
                LoginToken.provider == LoginTokenProvider.SUPABASE,
                LoginToken.status == LoginTokenStatus.PENDING,
            )
            .order_by(LoginToken.created_at.desc())
            .first()
        )
        if row is None or row.is_expired():
            return None
        row.status = LoginTokenStatus.APPROVED
        row.supabase_access_token = access_token
        row.supabase_refresh_token = refresh_token
        self.db.commit()
        return self._to_req(row)

    def increment_otp_attempts(self, selector: str) -> int:
        row = self._row_by_selector(selector)
        if row is None:
            return 0
        row.otp_attempts += 1
        self.db.commit()
        return row.otp_attempts

    def consume(self, selector: str) -> None:
        row = self.db.query(LoginToken).filter(LoginToken.selector == selector).first()
        if row is not None:
            self.db.delete(row)
            self.db.commit()

    def invalidate_pending(self, email: str, provider: str) -> None:
        self.db.query(LoginToken).filter(
            LoginToken.email == email,
            LoginToken.provider == provider,
            LoginToken.status == LoginTokenStatus.PENDING,
        ).delete()
        self.db.commit()


def get_login_store(db: Session) -> LoginTokenStore:
    """Retorna o store ativo: Redis se disponível, senão o banco."""
    client = get_redis()
    if client is not None:
        return RedisLoginTokenStore(client)
    return DbLoginTokenStore(db)
