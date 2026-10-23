"""Add expert_evaluations table for RQ1 schema evaluation.

Revision ID: 20261024_expert
Revises: h8chatprop00008
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20261024_expert"
down_revision: Union[str, Sequence[str], None] = "h8chatprop00008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "expert_evaluations" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "expert_evaluations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("evaluator_name", sa.String(255), nullable=False),
        sa.Column("schema_code", sa.String(50), nullable=False),
        sa.Column("d1_3nf", sa.Integer(), nullable=False),
        sa.Column("d2_naming", sa.Integer(), nullable=False),
        sa.Column("d3_constraints", sa.Integer(), nullable=False),
        sa.Column("d4_relationships", sa.Integer(), nullable=False),
        sa.Column("d5_domain", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expert_evaluations_evaluator_name", "expert_evaluations", ["evaluator_name"], unique=False)
    op.create_index("ix_expert_evaluations_schema_code", "expert_evaluations", ["schema_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expert_evaluations_schema_code", table_name="expert_evaluations")
    op.drop_index("ix_expert_evaluations_evaluator_name", table_name="expert_evaluations")
    op.drop_table("expert_evaluations")
