"""Impostazioni runtime, audit admin e consumi AI

Revision ID: d2adm00002
Revises: d1a0acl00001
"""
from alembic import op
import sqlalchemy as sa

revision = "d2adm00002"
down_revision = "d1a0acl00001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("app_settings",
        sa.Column("key", sa.String(100), primary_key=True), sa.Column("value", sa.JSON()),
        sa.Column("updated_by", sa.String(255)), sa.Column("updated_at", sa.DateTime()))
    op.create_table("admin_audit_log",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False), sa.Column("target", sa.String(255)),
        sa.Column("detail", sa.JSON()), sa.Column("created_at", sa.DateTime()))
    op.create_index("ix_admin_audit_log_created_at", "admin_audit_log", ["created_at"])
    op.create_table("usage_events",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("project_id", sa.String()), sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime()))
    op.create_index("ix_usage_events_user_id", "usage_events", ["user_id"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_table("admin_audit_log")
    op.drop_table("app_settings")
