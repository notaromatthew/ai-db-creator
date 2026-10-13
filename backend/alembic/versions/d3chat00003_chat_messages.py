"""Cronologia della chat di progettazione

Revision ID: d3chat00003
Revises: d2adm00002
"""
from alembic import op
import sqlalchemy as sa

revision = "d3chat00003"
down_revision = "d2adm00002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("chat_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime()))
    op.create_index("ix_chat_messages_project_id", "chat_messages", ["project_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
