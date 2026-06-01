"""Modelo de usuário (passwordless).

Não há senha no sistema. Um único modelo atende aos dois modos:
- Modo local: usuário criado/identificado pelo email ao confirmar o magic link.
- Modo Supabase: ``supabase_user_id`` preenchido (espelho do usuário da Supabase).
"""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # Espelho do id do usuário na Supabase. Único e nulo no modo local.
    supabase_user_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task",
        back_populates="owner",
        foreign_keys="Task.user_id",
        cascade="all, delete-orphan",
    )
