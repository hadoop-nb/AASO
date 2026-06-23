"""add agent_skills table

Revision ID: 006
Revises: 005
Create Date: 2026-06-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_skills",
        sa.Column("skill_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("capability", sa.String(100), nullable=False),
        sa.Column("proficiency", sa.Float(), server_default="1.0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_agent_skills_type", "agent_skills", ["agent_type"])
    op.create_index("idx_agent_skills_project", "agent_skills", ["project_id"])


def downgrade() -> None:
    op.drop_table("agent_skills")
