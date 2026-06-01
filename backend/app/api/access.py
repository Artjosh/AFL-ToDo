"""Regras de acesso (compartilhamento) para projetos e tarefas.

Centraliza "quem pode ver/editar o quê". O acesso deixou de ser apenas ownership
e passou a ser membership:

- Projeto: acessível pelo dono e pelos membros (project_members).
- Tarefa: acessível pelo criador, pelos atribuídos (task_assignees) e por quem
  tem acesso ao projeto da tarefa.

Nunca confiamos em ids vindos do frontend — o usuário vem sempre do token.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskAssignee
from app.models.user import User

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Não encontrado."
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão."
)


# ---------------------------------------------------------------- projetos

def user_project_ids(db: Session, user: User) -> list[int]:
    """IDs de projetos que o usuário possui ou é membro."""
    owned = db.query(Project.id).filter(Project.owner_id == user.id)
    member = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id)
    return [row[0] for row in owned.union(member).all()]


def is_project_member(db: Session, project: Project, user: User) -> bool:
    if project.owner_id == user.id:
        return True
    return (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
        )
        .first()
        is not None
    )


def get_accessible_project(db: Session, project_id: int, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None or not is_project_member(db, project, user):
        # 404 para não revelar existência de projetos de terceiros.
        raise _NOT_FOUND
    return project


def get_membership(db: Session, project: Project, user: User) -> ProjectMember | None:
    """Retorna o vínculo ProjectMember do usuário (ou None se for dono/sem vínculo)."""
    return (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
        )
        .first()
    )


def ensure_project_owner(db: Session, project: Project, user: User) -> None:
    if project.owner_id != user.id:
        raise _FORBIDDEN


# ---------------------------------------------------------------- permissões por membro

def can_move_project(db: Session, project: Project, user: User) -> bool:
    """Quem pode mover o PRÓPRIO PROJETO entre status: dono, ou membro autorizado."""
    if project.owner_id == user.id:
        return True
    m = get_membership(db, project, user)
    return bool(m and m.can_move_project)


def can_move_tasks(db: Session, project: Project | None, user: User) -> bool:
    """Quem pode mover TAREFAS de status no projeto.

    Tarefas soltas (sem projeto): só o criador (tratado fora). Em projeto: dono
    sempre; membro conforme a flag can_move_tasks.
    """
    if project is None:
        return True
    if project.owner_id == user.id:
        return True
    m = get_membership(db, project, user)
    return bool(m and m.can_move_tasks)


def can_manage_tasks(db: Session, project: Project | None, user: User) -> bool:
    """Quem pode criar/editar/excluir tarefas no escopo.

    Sem projeto: o próprio usuário (criador). Em projeto: dono sempre; membro
    conforme a flag can_manage_tasks.
    """
    if project is None:
        return True
    if project.owner_id == user.id:
        return True
    m = get_membership(db, project, user)
    return bool(m and m.can_manage_tasks)


def ensure_can(condition: bool) -> None:
    """Levanta 403 se a permissão não for satisfeita."""
    if not condition:
        raise _FORBIDDEN


# ---------------------------------------------------------------- tarefas

def task_is_accessible(db: Session, task: Task, user: User) -> bool:
    if task.user_id == user.id:
        return True
    # atribuído?
    assigned = (
        db.query(TaskAssignee)
        .filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user.id)
        .first()
    )
    if assigned is not None:
        return True
    # membro do projeto da tarefa?
    if task.project_id is not None:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project is not None and is_project_member(db, project, user):
            return True
    return False


def get_accessible_task(db: Session, task_id: int, user: User) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None or not task_is_accessible(db, task, user):
        raise _NOT_FOUND
    return task


def accessible_tasks_query(db: Session, user: User):
    """Query base das tarefas que o usuário pode ver (criador/atribuído/projeto)."""
    project_ids = user_project_ids(db, user)
    assigned_task_ids = [
        row[0]
        for row in db.query(TaskAssignee.task_id)
        .filter(TaskAssignee.user_id == user.id)
        .all()
    ]

    conditions = [Task.user_id == user.id]
    if project_ids:
        conditions.append(Task.project_id.in_(project_ids))
    if assigned_task_ids:
        conditions.append(Task.id.in_(assigned_task_ids))

    return db.query(Task).filter(or_(*conditions))
