"""add project_plans and plan_tasks

Revision ID: 010
Revises: 009
Create Date: 2026-06-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_plans",
        sa.Column("plan_id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("overall_risk_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_plans_project", "project_plans", ["project_id"])
    op.create_index("idx_plans_status", "project_plans", ["status"])

    op.create_table(
        "plan_tasks",
        sa.Column("task_id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("parent_task_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_factors", sa.Text(), nullable=True),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("dependencies", sa.Text(), nullable=True),
        sa.Column("assigned_agent_type", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_plan_tasks_plan", "plan_tasks", ["plan_id"])
    op.create_index("idx_plan_tasks_status", "plan_tasks", ["status"])
    op.create_index("idx_plan_tasks_parent", "plan_tasks", ["parent_task_id"])


def downgrade() -> None:
    op.drop_table("plan_tasks")
    op.drop_table("project_plans")
