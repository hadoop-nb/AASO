"""add prompt_templates and agent_assessments

Revision ID: 009
Revises: 008
Create Date: 2026-06-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("template_id", sa.String(36), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("change_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_prompt_templates_agent", "prompt_templates", ["agent_type"])

    op.create_table(
        "agent_assessments",
        sa.Column("assessment_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("agent_id", sa.String(50), server_default=""),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_assessments_agent_type", "agent_assessments", ["agent_type"])
    op.create_index("idx_assessments_project", "agent_assessments", ["project_id"])
    op.create_index("idx_assessments_task", "agent_assessments", ["task_id"])
    op.create_index("idx_assessments_run", "agent_assessments", ["run_id"])


def downgrade() -> None:
    op.drop_table("agent_assessments")
    op.drop_table("prompt_templates")
