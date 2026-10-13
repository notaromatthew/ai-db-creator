"""Run di ricerca (benchmark) e studio con partecipanti

Revision ID: f6research00006
Revises: e5jobs00005

Idempotente: su un database creato da create_all le tabelle possono esistere gia'.
"""
from alembic import op
import sqlalchemy as sa

revision = "f6research00006"
down_revision = "e5jobs00005"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "research_runs" not in tables:
        op.create_table(
            "research_runs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("batch_id", sa.String(), nullable=True),
            sa.Column("dataset", sa.String(100), nullable=False),
            sa.Column("condition", sa.String(50), nullable=False),
            sa.Column("provider", sa.String(100), nullable=True),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("run_index", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("precision", sa.Float(), nullable=True),
            sa.Column("recall", sa.Float(), nullable=True),
            sa.Column("f1", sa.Float(), nullable=True),
            sa.Column("value_accuracy", sa.Float(), nullable=True),
            sa.Column("judge_score", sa.Float(), nullable=True),
            sa.Column("tokens_in", sa.Integer(), nullable=True),
            sa.Column("tokens_out", sa.Integer(), nullable=True),
            sa.Column("cost_usd", sa.Float(), nullable=True),
            sa.Column("latency_s", sa.Float(), nullable=True),
            sa.Column("per_table", sa.JSON(), nullable=True),
            sa.Column("schema_json", sa.JSON(), nullable=True),
            sa.Column("manifest", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
        )
        for col in ("batch_id", "dataset", "condition", "model", "temperature", "status", "created_at"):
            op.create_index(f"ix_research_runs_{col}", "research_runs", [col])
    if "study_participants" not in tables:
        op.create_table(
            "study_participants",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("arm", sa.String(20), nullable=False),
            sa.Column("consent_version", sa.String(20), nullable=True),
            sa.Column("consented_at", sa.DateTime(), nullable=True),
            sa.Column("demographics", sa.JSON(), nullable=True),
            sa.Column("step", sa.String(20), nullable=False, server_default="consent"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_study_participants_arm", "study_participants", ["arm"])
    if "study_events" not in tables:
        op.create_table(
            "study_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("participant_id", sa.String(), sa.ForeignKey("study_participants.id"), nullable=False),
            sa.Column("type", sa.String(40), nullable=False),
            sa.Column("data", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_study_events_participant_id", "study_events", ["participant_id"])
        op.create_index("ix_study_events_created_at", "study_events", ["created_at"])
    if "study_responses" not in tables:
        op.create_table(
            "study_responses",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("participant_id", sa.String(), sa.ForeignKey("study_participants.id"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("participant_id", "kind", name="uq_study_response"),
        )
        op.create_index("ix_study_responses_participant_id", "study_responses", ["participant_id"])


def downgrade() -> None:
    op.drop_table("study_responses")
    op.drop_table("study_events")
    op.drop_table("study_participants")
    op.drop_table("research_runs")
