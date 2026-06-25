"""add knowledge graph tables

Revision ID: 007
Revises: 006
Create Date: 2026-06-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("node_id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_knowledge_nodes_project", "knowledge_nodes", ["project_id"])
    op.create_index("idx_knowledge_nodes_type", "knowledge_nodes", ["node_type"])

    op.create_table(
        "knowledge_edges",
        sa.Column("edge_id", sa.String(36), primary_key=True),
        sa.Column(
            "source_node_id",
            sa.String(36),
            sa.ForeignKey("knowledge_nodes.node_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            sa.String(36),
            sa.ForeignKey("knowledge_nodes.node_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_knowledge_edges_source", "knowledge_edges", ["source_node_id"])
    op.create_index("idx_knowledge_edges_target", "knowledge_edges", ["target_node_id"])
    op.create_index(
        "idx_knowledge_edges_relation", "knowledge_edges", ["relationship_type"]
    )


def downgrade() -> None:
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
