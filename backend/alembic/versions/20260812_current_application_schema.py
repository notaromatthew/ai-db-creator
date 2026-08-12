"""Bring the application metadata to the current schema.

Revision ID: 20260812_current
Revises: c25c5721cbb9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_current"
down_revision: Union[str, Sequence[str], None] = "c25c5721cbb9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("user_id", sa.String(255), nullable=True))
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_votes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("benchmark_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("schema_rating", sa.Integer(), nullable=False),
        sa.Column("data_rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_votes_benchmark_id", "user_votes", ["benchmark_id"], unique=False)
    op.create_index("ix_user_votes_project_id", "user_votes", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_votes_project_id", table_name="user_votes")
    op.drop_index("ix_user_votes_benchmark_id", table_name="user_votes")
    op.drop_table("user_votes")
    op.drop_table("benchmark_results")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_column("projects", "user_id")
