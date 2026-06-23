"""add code_files and task_id to decisions/lessons

Revision ID: 002
Revises: 001
Create Date: 2026-06-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("tasks.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_decisions_task_id", "decisions", ["task_id"]
    )

    op.add_column(
        "lessons",
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("tasks.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_lessons_task_id", "lessons", ["task_id"]
    )

    op.create_table(
        "code_files",
        sa.Column("file_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("tasks.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("language", sa.String(50), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_code_files_project_id", "code_files", ["project_id"]
    )
    op.create_index(
        "idx_code_files_task_id", "code_files", ["task_id"]
    )


def downgrade() -> None:
    op.drop_table("code_files")
    op.drop_index("idx_lessons_task_id", table_name="lessons")
    op.drop_column("lessons", "task_id")
    op.drop_index("idx_decisions_task_id", table_name="decisions")
    op.drop_column("decisions", "task_id")
