"""Modelo do pedido de login passwordless (magic link + OTP) com polling.

Cada solicitação de login cria um registro com:
- ``selector``: id público usado no polling (qual device está aguardando);
- ``magic_token``: segredo enviado no link do email (clicável em qualquer device);
- ``otp_code``: código de 6 dígitos, alternativa ao link (digitado no device de origem);
- ``status``: pending -> approved -> consumido pelo polling.

No modo Supabase cross-device, ``provider="supabase"`` e os campos
``supabase_access_token`` / ``supabase_refresh_token`` guardam a sessão obtida
pelo backend no callback (após verificar o token_hash na Supabase), para o
device de origem buscá-la via polling.

Esse fluxo replica o conceito do projeto gaming-cloud (pending-auth +
check-login-status), permitindo clicar o link em um device diferente do que
iniciou o login.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LoginTokenStatus:
    PENDING = "pending"
    APPROVED = "approved"

    ALL = (PENDING, APPROVED)


class LoginTokenProvider:
    LOCAL = "local"
    SUPABASE = "supabase"


class LoginToken(Base):
    __tablename__ = "login_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Identificador público do pedido de login (usado no polling).
    selector: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    # Segredo enviado no link do email (modo local).
    magic_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    # Código OTP de 6 dígitos, alternativa ao link (modo local).
    otp_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(
        String(16), default=LoginTokenProvider.LOCAL, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default=LoginTokenStatus.PENDING, nullable=False
    )

    # Sessão Supabase guardada no callback (modo supabase cross-device).
    supabase_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    supabase_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def is_expired(self) -> bool:
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires
