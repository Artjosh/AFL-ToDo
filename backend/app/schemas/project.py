"""Schemas Pydantic para projetos e membros."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.project import RemovedMemberPolicy
from app.models.task import TaskStatus
from app.schemas.task import TaskOut, UserBrief


def _validate_nome(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("O nome não pode ser vazio.")
    return stripped


class ProjectCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)

    @field_validator("nome")
    @classmethod
    def _vnome(cls, v: str) -> str:
        return _validate_nome(v)  # type: ignore[return-value]


class ProjectUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None)
    removed_member_policy: str | None = Field(default=None)
    owner_receives_alerts: bool | None = None

    @field_validator("nome")
    @classmethod
    def _vnome(cls, v: str | None) -> str | None:
        return _validate_nome(v)

    @field_validator("status")
    @classmethod
    def _vstatus(cls, v: str | None) -> str | None:
        if v is not None and v not in TaskStatus.ALL:
            raise ValueError(f"status inválido. Use um de: {', '.join(TaskStatus.ALL)}")
        return v

    @field_validator("removed_member_policy")
    @classmethod
    def _vpolicy(cls, v: str | None) -> str | None:
        if v is not None and v not in RemovedMemberPolicy.ALL:
            raise ValueError(
                f"política inválida. Use um de: {', '.join(RemovedMemberPolicy.ALL)}"
            )
        return v


class MemberAdd(BaseModel):
    email: EmailStr


class MemberPermissionsUpdate(BaseModel):
    """Atualização das permissões de um membro (todas opcionais)."""

    can_move_project: bool | None = None
    can_move_tasks: bool | None = None
    can_manage_tasks: bool | None = None
    receives_alerts: bool | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    # Permissões (para o dono, vêm como True/defaults de dono).
    can_move_project: bool = False
    can_move_tasks: bool = True
    can_manage_tasks: bool = True
    receives_alerts: bool = False


class ProjectOut(BaseModel):
    """Projeto na listagem (sem as tarefas, mas com contagem e membros)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str | None
    owner_id: int
    status: str
    position: int
    removed_member_policy: str
    owner_receives_alerts: bool
    data_criacao: datetime
    updated_at: datetime
    role: str  # papel do usuário atual neste projeto (owner/member)
    # Permissões efetivas do usuário ATUAL neste projeto (para a UI habilitar ações).
    can_move_project: bool = False
    can_move_tasks: bool = True
    can_manage_tasks: bool = True
    task_count: int
    members: list[MemberOut] = []


class ProjectDetail(ProjectOut):
    """Projeto detalhado, com as tarefas aninhadas (board)."""

    tasks: list[TaskOut] = []


class OwnerBrief(UserBrief):
    pass
