"""Modelos de projeto e membros (compartilhamento).

Um projeto agrupa tarefas e é a unidade de compartilhamento: usuários adicionados
como membros (ProjectMember) passam a ver e editar as tarefas do projeto.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
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


class ProjectRole:
    OWNER = "owner"
    MEMBER = "member"

    ALL = (OWNER, MEMBER)


class RemovedMemberPolicy:
    """O que acontece com as tarefas de um membro ao ser removido do projeto.

    - REVOKE: perde acesso (tarefas que criou são transferidas ao dono e as
      atribuições dele no projeto são removidas).
    - KEEP: continua "como dono" das tarefas que criou e segue podendo vê-las
      (mantém criação e atribuições), mesmo sem ser mais membro.
    """

    REVOKE = "revoke"
    KEEP = "keep"

    ALL = (REVOKE, KEEP)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # O projeto também é um "card" no board: tem status e posição próprios.
    status: Mapped[str] = mapped_column(String(32), default="pendente", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Política aplicada às tarefas de um membro quando ele é removido.
    removed_member_policy: Mapped[str] = mapped_column(
        String(16), default=RemovedMemberPolicy.REVOKE, nullable=False
    )
    # O dono recebe emails de alerta (criação/mudança de status de tarefa)?
    owner_receives_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), default=ProjectRole.MEMBER, nullable=False)

    # --- Permissões por membro (configuráveis pelo dono) ---
    # Pode mover o PRÓPRIO PROJETO entre status (pendente/em_andamento/concluida).
    can_move_project: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Pode mover as TAREFAS do projeto entre status (drag-and-drop de coluna).
    can_move_tasks: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Pode criar/editar/excluir tarefas do projeto.
    can_manage_tasks: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Recebe emails de alerta (criação / mudança de status de tarefa).
    receives_alerts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")  # noqa: F821
