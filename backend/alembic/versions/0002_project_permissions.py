"""project status/position/policy + per-member permissions

Adiciona ao projeto: status, position, removed_member_policy, owner_receives_alerts.
Adiciona ao membro: can_move_project, can_move_tasks, can_manage_tasks, receives_alerts.

Revision ID: 0002_project_permissions
Revises: 0001_initial
Create Date: 2026-05-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_project_permissions"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pendente")
        )
        batch.add_column(
            sa.Column("position", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column(
                "removed_member_policy",
                sa.String(length=16),
                nullable=False,
                server_default="revoke",
            )
        )
        batch.add_column(
            sa.Column(
                "owner_receives_alerts",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    with op.batch_alter_table("project_members") as batch:
        batch.add_column(
            sa.Column("can_move_project", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("can_move_tasks", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column("can_manage_tasks", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column("receives_alerts", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("project_members") as batch:
        batch.drop_column("receives_alerts")
        batch.drop_column("can_manage_tasks")
        batch.drop_column("can_move_tasks")
        batch.drop_column("can_move_project")

    with op.batch_alter_table("projects") as batch:
        batch.drop_column("owner_receives_alerts")
        batch.drop_column("removed_member_policy")
        batch.drop_column("position")
        batch.drop_column("status")
