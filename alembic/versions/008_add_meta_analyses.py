"""add meta_analyses table

Revision ID: 008
Revises: 007
Create Date: 2026-06-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_analyses",
        sa.Column("analysis_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actionable", sa.Boolean(), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_meta_analyses_project", "meta_analyses", ["project_id"])
    op.create_index("idx_meta_analyses_type", "meta_analyses", ["analysis_type"])


def downgrade() -> None:
    op.drop_table("meta_analyses")
