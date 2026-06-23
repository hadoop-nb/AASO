"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(50), server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_projects_status", "projects", ["status"])
    op.create_index("idx_projects_name", "projects", ["name"])

    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("completion_percentage", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tasks_project_id", "tasks", ["project_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])

    op.create_table(
        "decisions",
        sa.Column("decision_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("alternatives", sa.JSON(), server_default="[]"),
        sa.Column("selected", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_decisions_project_id", "decisions", ["project_id"])

    op.create_table(
        "lessons",
        sa.Column("lesson_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("solution", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_lessons_project_id", "lessons", ["project_id"])


def downgrade() -> None:
    op.drop_table("lessons")
    op.drop_table("decisions")
    op.drop_table("tasks")
    op.drop_table("projects")
