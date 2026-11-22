"""Persist quality-lab rounds and ratings across workers and restarts.

Revision ID: 034_quality_lab_runs
Revises: 033_list_query_indexes
"""

import sqlalchemy as sa
from alembic import op


revision = "034_quality_lab_runs"
down_revision = "033_list_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "quality_lab_runs" not in inspector.get_table_names():
        op.create_table(
            "quality_lab_runs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("dataset_id", sa.String(length=120), nullable=False),
            sa.Column("holdout", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "holdout_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("can_apply", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "can_rollback", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "input_payload", sa.JSON(), nullable=False, server_default="{}"
            ),
            sa.Column("candidates", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("blind_order", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("ratings", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    existing_indexes = {
        str(item["name"])
        for item in inspector.get_indexes("quality_lab_runs")
        if item.get("name")
    }
    if "ix_quality_lab_runs_dataset_created" not in existing_indexes:
        op.create_index(
            "ix_quality_lab_runs_dataset_created",
            "quality_lab_runs",
            ["dataset_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_quality_lab_runs_dataset_created", table_name="quality_lab_runs")
    op.drop_table("quality_lab_runs")
