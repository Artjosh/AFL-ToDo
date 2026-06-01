"""Modelo de tarefa (to-do) com suporte a projeto, posição e atribuídos.

- ``user_id`` é o CRIADOR da tarefa.
- ``project_id`` (opcional) vincula a tarefa a um projeto (board aninhado).
- ``position`` ordena os cards dentro de cada coluna do board.
- atribuídos (TaskAssignee) são as pessoas responsáveis, exibidas no card.

O acesso (ver/editar) é por membership, não só ownership: criador, atribuídos e
membros do projeto têm acesso. A regra é aplicada nas rotas.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus:
    """Valores possíveis para o status de uma tarefa (colunas do board)."""

    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"

    ALL = (PENDENTE, EM_ANDAMENTO, CONCLUIDA)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Criador da tarefa.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Projeto ao qual pertence (nulo = tarefa solta na lista principal).
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=TaskStatus.PENDENTE, nullable=False
    )
    # Ordenação dentro da coluna (board estilo Kanban).
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="tasks", foreign_keys=[user_id]
    )
    project: Mapped["Project | None"] = relationship(  # noqa: F821
        "Project", back_populates="tasks"
    )
    assignees: Mapped[list["TaskAssignee"]] = relationship(
        "TaskAssignee",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskAssignee(Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    task: Mapped["Task"] = relationship("Task", back_populates="assignees")
    user: Mapped["User"] = relationship("User")  # noqa: F821
