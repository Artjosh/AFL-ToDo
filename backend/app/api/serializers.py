"""Serialização de modelos para os schemas de saída (com relações)."""
from __future__ import annotations

from app.models.task import Task
from app.schemas.task import TaskOut, UserBrief


def task_to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        titulo=task.titulo,
        descricao=task.descricao,
        status=task.status,
        position=task.position,
        project_id=task.project_id,
        data_criacao=task.data_criacao,
        updated_at=task.updated_at,
        creator=UserBrief.model_validate(task.owner),
        assignees=[UserBrief.model_validate(a.user) for a in task.assignees],
    )
