"""Schemas Pydantic para tarefas, atribuídos e usuários resumidos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.task import TaskStatus


class UserBrief(BaseModel):
    """Representação enxuta de um usuário (para avatares/atribuídos/membros)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


def _validate_status(value: str | None) -> str | None:
    if value is not None and value not in TaskStatus.ALL:
        raise ValueError(f"status inválido. Use um de: {', '.join(TaskStatus.ALL)}")
    return value


def _validate_titulo(value: str | None) -> str | None:
    """Faz strip e rejeita título vazio (evita '   ' passar pelo min_length)."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("O título não pode ser vazio.")
    return stripped


class TaskCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    status: str = Field(default=TaskStatus.PENDENTE)
    project_id: int | None = None

    @field_validator("status")
    @classmethod
    def _vstatus(cls, v: str) -> str:
        return _validate_status(v)  # type: ignore[return-value]

    @field_validator("titulo")
    @classmethod
    def _vtitulo(cls, v: str) -> str:
        return _validate_titulo(v)  # type: ignore[return-value]


class TaskUpdate(BaseModel):
    """Atualização parcial (PATCH). Todos os campos são opcionais."""

    titulo: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    position: int | None = Field(default=None, ge=0)
    # Permite mover a tarefa para dentro/fora de um projeto.
    project_id: int | None = None
    # Sinaliza explicitamente "remover do projeto" (project_id volta a ser nulo).
    clear_project: bool = False

    @field_validator("status")
    @classmethod
    def _vstatus(cls, v: str | None) -> str | None:
        return _validate_status(v)

    @field_validator("titulo")
    @classmethod
    def _vtitulo(cls, v: str | None) -> str | None:
        return _validate_titulo(v)


class AssigneeUpdate(BaseModel):
    """Adiciona ou remove um atribuído por email."""

    email: EmailStr


class ReorderRequest(BaseModel):
    """Reordenação de uma coluna do board (drag-and-drop fino)."""

    task_ids: list[int] = Field(min_length=1)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _vstatus(cls, v: str | None) -> str | None:
        return _validate_status(v)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: str | None
    status: str
    position: int
    project_id: int | None
    data_criacao: datetime
    updated_at: datetime
    creator: UserBrief
    assignees: list[UserBrief] = []
