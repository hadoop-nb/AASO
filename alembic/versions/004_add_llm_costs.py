"""add llm_costs table

Revision ID: 004
Revises: 003
Create Date: 2026-06-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_costs",
        sa.Column("cost_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_type", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_llm_costs_project_id", "llm_costs", ["project_id"])
    op.create_index("idx_llm_costs_agent_type", "llm_costs", ["agent_type"])


def downgrade() -> None:
    op.drop_table("llm_costs")
