"""Store revision-addressable debate claims and their evidence.

Revision ID: 028_debate_claim_records
Revises: 027_transcript_refinement
"""

import sqlalchemy as sa
from alembic import op

revision = "028_debate_claim_records"
down_revision = "027_transcript_refinement"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "debate_claim_records" in existing:
        return
    op.create_table(
        "debate_claim_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id", sa.Uuid(), sa.ForeignKey("sessions.id"), nullable=False
        ),
        sa.Column("claim_id", sa.String(160), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speaker_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("original_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("atomic_claims", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("relations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("feedback", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "session_id",
            "claim_id",
            "revision",
            name="uq_debate_claim_session_claim_revision",
        ),
    )
    op.create_index(
        "ix_debate_claim_records_session_id", "debate_claim_records", ["session_id"]
    )
    op.create_index(
        "ix_debate_claim_records_claim_id", "debate_claim_records", ["claim_id"]
    )


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "debate_claim_records" in existing:
        op.drop_table("debate_claim_records")
