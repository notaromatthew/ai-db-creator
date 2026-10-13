"""Schema definitivo salvato sul progetto

Revision ID: d4final00004
Revises: d3chat00003
"""
from alembic import op
import sqlalchemy as sa

revision = "d4final00004"
down_revision = "d3chat00003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("schema_finalized_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("schema_finalized_at")
