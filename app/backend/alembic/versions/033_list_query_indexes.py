"""Add composite indexes for bounded list endpoints.

Revision ID: 033_list_query_indexes
Revises: 032_transcript_discard_audits
"""

import sqlalchemy as sa
from alembic import op

revision = "033_list_query_indexes"
down_revision = "032_transcript_discard_audits"
branch_labels = None
depends_on = None


_INDEXES = (
    ("ix_sessions_created_id", "sessions", ("created_at", "id")),
    (
        "ix_call_segments_session_segment_id",
        "call_segments",
        ("session_id", "segment_number", "id"),
    ),
    (
        "ix_transcript_entries_session_sequence_id",
        "transcript_entries",
        ("session_id", "sequence", "id"),
    ),
    (
        "ix_questions_session_created_id",
        "questions",
        ("session_id", "created_at", "id"),
    ),
    (
        "ix_directives_session_created_id",
        "directives",
        ("session_id", "created_at", "id"),
    ),
    (
        "ix_documents_session_uploaded_id",
        "documents",
        ("session_id", "uploaded_at", "id"),
    ),
    ("ix_speakers_session_created_id", "speakers", ("session_id", "created_at", "id")),
    ("ix_knowledge_sources_created_id", "knowledge_sources", ("created_at", "id")),
    (
        "ix_knowledge_records_source_title_created_id",
        "knowledge_records",
        ("source_id", "title", "created_at", "id"),
    ),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table, columns in _INDEXES:
        # A failed startup can leave earlier indexes from this revision in a
        # SQLite database even though Alembic has not advanced its version
        # row.  Skip those on retry so the repaired database can reach head.
        existing = {
            str(item["name"])
            for item in inspector.get_indexes(table)
            if item.get("name")
        }
        if name not in existing:
            op.create_index(name, table, list(columns), unique=False)
            existing.add(name)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
