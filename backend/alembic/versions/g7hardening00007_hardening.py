"""Rafforzamenti: un solo lavoro attivo per progetto e un solo partecipante attivo per account

Revision ID: g7hardening00007
Revises: f6research00006

Idempotente: su un database creato da create_all colonna e indici possono esistere gia'.
"""
from alembic import op
import sqlalchemy as sa

revision = "g7hardening00007"
down_revision = "f6research00006"
branch_labels = None
depends_on = None

JOBS_WHERE = "kind IN ('schema','dati') AND status IN ('queued','running')"
STUDY_WHERE = "account_hash IS NOT NULL AND withdrawn_at IS NULL"


def _indexes(table):
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "account_hash" not in {c["name"] for c in insp.get_columns("study_participants")}:
        op.add_column("study_participants", sa.Column("account_hash", sa.String(64), nullable=True))
    if "uq_jobs_active_project" not in _indexes("jobs"):
        # eventuali duplicati attivi gia' presenti vengono chiusi, tenendo il piu' recente
        bind.execute(sa.text(
            "UPDATE jobs SET status='failed', error='Duplicato chiuso dalla migrazione' "
            f"WHERE {JOBS_WHERE} AND id NOT IN ("
            "SELECT MAX(id) FROM jobs "
            f"WHERE {JOBS_WHERE} GROUP BY project_id)"))
        op.create_index("uq_jobs_active_project", "jobs", ["project_id"], unique=True,
                        sqlite_where=sa.text(JOBS_WHERE), postgresql_where=sa.text(JOBS_WHERE))
    if "uq_study_active_account" not in _indexes("study_participants"):
        op.create_index("uq_study_active_account", "study_participants", ["account_hash"], unique=True,
                        sqlite_where=sa.text(STUDY_WHERE), postgresql_where=sa.text(STUDY_WHERE))


def downgrade() -> None:
    if "uq_study_active_account" in _indexes("study_participants"):
        op.drop_index("uq_study_active_account", table_name="study_participants")
    if "uq_jobs_active_project" in _indexes("jobs"):
        op.drop_index("uq_jobs_active_project", table_name="jobs")
    with op.batch_alter_table("study_participants") as batch:
        batch.drop_column("account_hash")
