"""create_memory_tables

Revision ID: 7a5478824875
Revises: 597ad10777b7
Create Date: 2026-08-06 23:07:33.040372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.db.types import GUID, JSONBType, StringList


# revision identifiers, used by Alembic.
revision: str = "7a5478824875"
down_revision: Union[str, Sequence[str], None] = "597ad10777b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("conversation_id", GUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "memory_type",
            sa.Enum(
                "FACT",
                "PREFERENCE",
                "GOAL",
                "TASK",
                "REMINDER",
                "PROJECT",
                "CONVERSATION_SUMMARY",
                "PERSON",
                "PLACE",
                "KNOWLEDGE",
                "DEVICE",
                "AUTOMATION",
                "CUSTOM",
                name="memorytype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("tags", StringList(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_accessed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("metadata", JSONBType, nullable=False),
        sa.Column("future_embedding_id", sa.String(), nullable=True),
        sa.Column("future_graph_node_id", sa.String(), nullable=True),
        sa.Column("origin_conversation_id", GUID(), nullable=True),
        sa.Column("origin_message_id", GUID(), nullable=True),
        sa.Column("created_from", sa.String(length=50), nullable=False),
        sa.Column("confidence_reason", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("times_retrieved", sa.Integer(), nullable=False),
        sa.Column("times_updated", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memories_conversation_id"), "memories", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_memories_deleted"), "memories", ["deleted"], unique=False)
    op.create_index(op.f("ix_memories_memory_type"), "memories", ["memory_type"], unique=False)
    op.create_index(op.f("ix_memories_user_id"), "memories", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memories_user_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_memory_type"), table_name="memories")
    op.drop_index(op.f("ix_memories_deleted"), table_name="memories")
    op.drop_index(op.f("ix_memories_conversation_id"), table_name="memories")
    op.drop_table("memories")
