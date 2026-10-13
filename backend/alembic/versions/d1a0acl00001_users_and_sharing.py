"""Utenti, proprietario dei progetti e condivisione

Revision ID: d1a0acl00001
Revises: c25c5721cbb9
"""
from alembic import op
import sqlalchemy as sa

revision = "d1a0acl00001"
down_revision = "c25c5721cbb9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("daily_ai_quota", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("last_seen_at", sa.DateTime()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    # I progetti esistenti senza proprietario passano a un utente "legacy" per non perderli.
    op.execute("INSERT INTO users (id, display_name, blocked) VALUES ('legacy', 'Progetti precedenti', false)")
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(255), nullable=True))
    op.execute("UPDATE projects SET owner_id = COALESCE(NULLIF(user_id, ''), 'legacy')"
               if _has_user_id() else "UPDATE projects SET owner_id = 'legacy'")
    op.execute("INSERT INTO users (id, blocked) SELECT DISTINCT owner_id, false FROM projects "
               "WHERE owner_id NOT IN (SELECT id FROM users)")
    with op.batch_alter_table("projects") as batch:
        batch.alter_column("owner_id", existing_type=sa.String(255), nullable=False)
        batch.create_foreign_key("fk_projects_owner", "users", ["owner_id"], ["id"])
        batch.create_index("ix_projects_owner_id", ["owner_id"])
        if _has_user_id():
            batch.drop_column("user_id")
    op.create_table(
        "project_members",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("invited_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_table(
        "project_invites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("invited_by", sa.String(255)),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_project_invites_project_id", "project_invites", ["project_id"])
    op.create_index("ix_project_invites_email", "project_invites", ["email"])
    op.create_table(
        "project_links",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_by", sa.String(255)),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_project_links_project_id", "project_links", ["project_id"])


def _has_user_id() -> bool:
    cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")]
    return "user_id" in cols


def downgrade() -> None:
    op.drop_table("project_links")
    op.drop_table("project_invites")
    op.drop_table("project_members")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("owner_id")
    op.drop_table("users")
