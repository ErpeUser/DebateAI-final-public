"""Add append-only final transcript correction history.

Revision ID: 031_transcript_entry_revisions
Revises: 030_provisional_transcript_revisions
"""

import sqlalchemy as sa

from alembic import op

revision = "031_transcript_entry_revisions"
down_revision = "030_provisional_transcript_revisions"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    transcript_columns = {
        column["name"] for column in inspector.get_columns("transcript_entries")
    }
    if "manual_corrected_at" not in transcript_columns:
        op.add_column(
            "transcript_entries",
            sa.Column("manual_corrected_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "utterance_id" not in transcript_columns:
        op.add_column(
            "transcript_entries",
            sa.Column("utterance_id", sa.String(length=128), nullable=True),
        )
    if "producer_revision" not in transcript_columns:
        op.add_column(
            "transcript_entries",
            sa.Column("producer_revision", sa.Integer(), nullable=True),
        )
    if "transcript_entry_revisions" in tables:
        return
    op.create_table(
        "transcript_entry_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcript_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_id"], ["speakers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transcript_id", "revision", name="uq_transcript_entry_revision"
        ),
    )
    op.create_index(
        "ix_transcript_entry_revisions_session_id",
        "transcript_entry_revisions",
        ["session_id"],
    )
    op.create_index(
        "ix_transcript_entry_revisions_transcript_id",
        "transcript_entry_revisions",
        ["transcript_id"],
    )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "transcript_entry_revisions" in inspector.get_table_names():
        op.drop_index(
            "ix_transcript_entry_revisions_transcript_id",
            table_name="transcript_entry_revisions",
        )
        op.drop_index(
            "ix_transcript_entry_revisions_session_id",
            table_name="transcript_entry_revisions",
        )
        op.drop_table("transcript_entry_revisions")
    transcript_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("transcript_entries")
    }
    if "producer_revision" in transcript_columns:
        op.drop_column("transcript_entries", "producer_revision")
    if "utterance_id" in transcript_columns:
        op.drop_column("transcript_entries", "utterance_id")
    if "manual_corrected_at" in transcript_columns:
        op.drop_column("transcript_entries", "manual_corrected_at")
