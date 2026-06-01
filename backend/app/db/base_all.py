"""Importa a Base e todos os modelos.

Use este módulo onde for necessário ter o metadata completo (ex.: Alembic
autogenerate ou create_all), sem causar import circular nos próprios modelos.
"""
from app.db.base import Base  # noqa: F401
from app.models.login_token import LoginToken  # noqa: F401
from app.models.project import Project, ProjectMember  # noqa: F401
from app.models.task import Task, TaskAssignee  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Task",
    "TaskAssignee",
    "Project",
    "ProjectMember",
    "LoginToken",
]
