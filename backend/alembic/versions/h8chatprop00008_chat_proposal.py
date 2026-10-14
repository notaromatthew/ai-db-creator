"""Chat: segnala le risposte che contengono una proposta di modifica in attesa di conferma

Revision ID: h8chatprop00008
Revises: g7hardening00007

Idempotente: su un database creato da create_all la colonna puo' esistere gia'.
"""
from alembic import op
import sqlalchemy as sa

revision = "h8chatprop00008"
down_revision = "g7hardening00007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "proposal" not in columns:
        op.add_column("chat_messages", sa.Column("proposal", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_column("proposal")
