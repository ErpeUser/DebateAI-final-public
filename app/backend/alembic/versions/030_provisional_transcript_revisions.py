"""Persist append-only provisional transcript revisions.

Revision ID: 030_provisional_transcript_revisions
Revises: 029_unique_transcript_sequence
"""

import sqlalchemy as sa
from alembic import op

revision = "030_provisional_transcript_revisions"
down_revision = "029_unique_transcript_sequence"
branch_labels = None
depends_on = None


def upgrade():
    if (
        "provisional_transcript_revisions"
        in sa.inspect(op.get_bind()).get_table_names()
    ):
        return
    op.create_table(
        "provisional_transcript_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "mode", sa.String(length=16), nullable=False, server_default="replace"
        ),
        sa.Column(
            "track_id", sa.String(length=32), nullable=False, server_default="mixed"
        ),
        sa.Column("audio_start_sample", sa.Integer(), nullable=True),
        sa.Column("audio_end_sample", sa.Integer(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=False, server_default="16000"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "segment_id",
            "revision",
            name="uq_provisional_transcript_segment_revision",
        ),
    )
    op.create_index(
        "ix_provisional_transcript_revisions_session_id",
        "provisional_transcript_revisions",
        ["session_id"],
    )


def downgrade():
    if (
        "provisional_transcript_revisions"
        not in sa.inspect(op.get_bind()).get_table_names()
    ):
        return
    op.drop_index(
        "ix_provisional_transcript_revisions_session_id",
        table_name="provisional_transcript_revisions",
    )
    op.drop_table("provisional_transcript_revisions")
