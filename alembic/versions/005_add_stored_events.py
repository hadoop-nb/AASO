"""add stored_events table

Revision ID: 005
Revises: 004
Create Date: 2026-06-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stored_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_stored_events_type", "stored_events", ["event_type"])
    op.create_index("idx_stored_events_source", "stored_events", ["source"])


def downgrade() -> None:
    op.drop_table("stored_events")
