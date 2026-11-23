"""Persist replay state shared by backend workers.

Revision ID: 035_shared_session_state
Revises: 034_quality_lab_runs
"""

import sqlalchemy as sa
from alembic import op


revision = "035_shared_session_state"
down_revision = "034_quality_lab_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "shared_session_state" not in inspector.get_table_names():
        op.create_table(
            "shared_session_state",
            sa.Column("session_id", sa.Uuid(), nullable=False),
            sa.Column("server_epoch", sa.String(length=64), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "active_connections", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("events", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("state", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("session_id"),
        )


def downgrade() -> None:
    op.drop_table("shared_session_state")
