"""Lavori in coda, versioni dello schema, cronologia query, dialetto, OCR e tabelle dei benchmark

Revision ID: e5jobs00005
Revises: d4final00004

La migrazione e' idempotente: su un database creato da create_all alcune tabelle
o colonne esistono gia' e vengono saltate.
"""
import json
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "e5jobs00005"
down_revision = "d4final00004"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table):
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "jobs" not in tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("user_id", sa.String(255), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("params", sa.JSON(), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("executor", sa.String(20), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
        op.create_index("ix_jobs_status", "jobs", ["status"])
        op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    if "schema_versions" not in tables:
        op.create_table(
            "schema_versions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("schema_json", sa.JSON(), nullable=False),
            sa.Column("author", sa.String(255), nullable=True),
            sa.Column("origin", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("project_id", "version", name="uq_schema_version"),
        )
        op.create_index("ix_schema_versions_project_id", "schema_versions", ["project_id"])
    if "query_history" not in tables:
        op.create_table(
            "query_history",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("user_id", sa.String(255), nullable=True),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("generated_sql", sa.Text(), nullable=True),
            sa.Column("source", sa.String(20), nullable=False, server_default="query"),
            sa.Column("outcome", sa.String(10), nullable=False),
            sa.Column("rows", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_query_history_project_id", "query_history", ["project_id"])
        op.create_index("ix_query_history_created_at", "query_history", ["created_at"])

    # Tabelle dei benchmark: finora create solo da create_all, mai da una migrazione.
    if "benchmark_results" not in tables:
        op.create_table(
            "benchmark_results",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("scenario_name", sa.String(255), nullable=False),
            sa.Column("provider", sa.String(100), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("norm3_score", sa.Float(), nullable=False),
            sa.Column("relationship_f1", sa.Float(), nullable=False),
            sa.Column("cell_precision", sa.Float(), nullable=False),
            sa.Column("latency_seconds", sa.Float(), nullable=False),
            sa.Column("token_cost_estimate", sa.Float(), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "user_votes" not in tables:
        op.create_table(
            "user_votes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), nullable=True),
            sa.Column("benchmark_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(255), nullable=False),
            sa.Column("schema_rating", sa.Integer(), nullable=False),
            sa.Column("data_rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_user_votes_project_id", "user_votes", ["project_id"])
        op.create_index("ix_user_votes_benchmark_id", "user_votes", ["benchmark_id"])

    project_cols = _columns("projects")
    add_cols = []
    if "schema_version" not in project_cols:
        add_cols.append(sa.Column("schema_version", sa.Integer(), nullable=False, server_default="0"))
    if "target_dialect" not in project_cols:
        add_cols.append(sa.Column("target_dialect", sa.String(20), nullable=True))
    if add_cols:
        with op.batch_alter_table("projects") as batch:
            for col in add_cols:
                batch.add_column(col)
    if "needs_ocr" not in _columns("documents"):
        with op.batch_alter_table("documents") as batch:
            batch.add_column(sa.Column("needs_ocr", sa.Boolean(), nullable=False, server_default=sa.false()))

    _backfill_versions()


def _backfill_versions() -> None:
    """Ai progetti che hanno gia' uno schema si assegna la versione 1."""
    bind = op.get_bind()
    versions = sa.table(
        "schema_versions",
        sa.column("id", sa.String), sa.column("project_id", sa.String), sa.column("version", sa.Integer),
        sa.column("schema_json", sa.JSON), sa.column("author", sa.String), sa.column("origin", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    rows = bind.execute(sa.text(
        "SELECT p.id, p.owner_id, p.schema_json FROM projects p "
        "WHERE p.schema_json IS NOT NULL AND p.schema_version = 0 "
        "AND NOT EXISTS (SELECT 1 FROM schema_versions v WHERE v.project_id = p.id)"
    )).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for project_id, owner_id, raw in rows:
        data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        if not data:
            continue
        bind.execute(versions.insert().values(
            id=str(uuid.uuid4()), project_id=project_id, version=1, schema_json=data,
            author=owner_id, origin="generazione", created_at=now))
        bind.execute(sa.text("UPDATE projects SET schema_version = 1 WHERE id = :pid"), {"pid": project_id})


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("needs_ocr")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("target_dialect")
        batch.drop_column("schema_version")
    op.drop_table("query_history")
    op.drop_table("schema_versions")
    op.drop_table("jobs")
