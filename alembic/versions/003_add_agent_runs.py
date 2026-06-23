"""add agent_runs table

Revision ID: 003
Revises: 002
Create Date: 2026-06-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("agent_id", sa.String(50), server_default=""),
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
        sa.Column("success", sa.Boolean(), server_default="1"),
        sa.Column("duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("files_generated", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_agent_runs_project_id", "agent_runs", ["project_id"])
    op.create_index("idx_agent_runs_agent_type", "agent_runs", ["agent_type"])
    op.create_index("idx_agent_runs_task_id", "agent_runs", ["task_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
