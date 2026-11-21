"""Add durable audit rows for transcript segments discarded before persistence.

Revision ID: 032_transcript_discard_audits
Revises: 031_transcript_entry_revisions
"""

import sqlalchemy as sa
from alembic import op

revision = "032_transcript_discard_audits"
down_revision = "031_transcript_entry_revisions"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "transcript_discard_audits" in inspector.get_table_names():
        return
    op.create_table(
        "transcript_discard_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("speaker_id", sa.Uuid(), nullable=True),
        sa.Column("audio_start_sample", sa.Integer(), nullable=True),
        sa.Column("audio_end_sample", sa.Integer(), nullable=True),
        sa.Column(
            "discard_reason", sa.String(length=160), nullable=False, server_default=""
        ),
        sa.Column("producer", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("segment_revision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_id"], ["speakers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transcript_discard_audits_session_id",
        "transcript_discard_audits",
        ["session_id"],
    )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "transcript_discard_audits" not in inspector.get_table_names():
        return
    op.drop_index(
        "ix_transcript_discard_audits_session_id",
        table_name="transcript_discard_audits",
    )
    op.drop_table("transcript_discard_audits")
