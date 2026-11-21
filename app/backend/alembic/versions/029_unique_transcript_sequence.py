"""Serialize transcript identity within each session.

Revision ID: 029_unique_transcript_sequence
Revises: 028_debate_claim_records
"""

import sqlalchemy as sa
from alembic import op

revision = "029_unique_transcript_sequence"
down_revision = "028_debate_claim_records"
branch_labels = None
depends_on = None

_CONSTRAINT = "uq_transcript_entries_session_sequence"


def _unique_constraint_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "transcript_entries" not in inspector.get_table_names():
        return set()
    return {
        str(item.get("name"))
        for item in inspector.get_unique_constraints("transcript_entries")
        if item.get("name")
    }


def upgrade():
    if _CONSTRAINT in _unique_constraint_names():
        return

    # Resequence only affected sessions in their existing conversation order.
    # Moving duplicate rows to the end would corrupt briefing/export chronology.
    op.execute(
        sa.text("""
        WITH affected_sessions AS (
            SELECT session_id
            FROM transcript_entries
            GROUP BY session_id
            HAVING COUNT(*) <> COUNT(DISTINCT sequence)
        ), ordered_rows AS (
            SELECT
                transcript.id,
                ROW_NUMBER() OVER (
                    PARTITION BY transcript.session_id
                    ORDER BY transcript.sequence, transcript.timestamp, transcript.id
                ) AS new_sequence
            FROM transcript_entries AS transcript
            JOIN affected_sessions AS affected
              ON affected.session_id = transcript.session_id
        )
        UPDATE transcript_entries
        SET sequence = ordered_rows.new_sequence
        FROM ordered_rows
        WHERE transcript_entries.id = ordered_rows.id
    """)
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot alter a table to add a named constraint in place.
        # Alembic's batch mode copies the table, preserving the existing rows
        # after the duplicate resequencing above, then recreates it with the
        # same constraint.  This is required for legacy desktop databases,
        # which are adopted on SQLite before the versioned tail is applied.
        # A process interruption can leave the temporary copy behind; it is
        # safe to remove because the original table remains authoritative
        # until the batch rename completes.
        if "_alembic_tmp_transcript_entries" in sa.inspect(bind).get_table_names():
            op.drop_table("_alembic_tmp_transcript_entries")
        with op.batch_alter_table("transcript_entries", recreate="always") as batch:
            batch.create_unique_constraint(
                _CONSTRAINT,
                ["session_id", "sequence"],
            )
    else:
        op.create_unique_constraint(
            _CONSTRAINT,
            "transcript_entries",
            ["session_id", "sequence"],
        )


def downgrade():
    if _CONSTRAINT in _unique_constraint_names():
        op.drop_constraint(_CONSTRAINT, "transcript_entries", type_="unique")
