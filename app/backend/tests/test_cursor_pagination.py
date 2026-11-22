import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.routers.sessions import list_segments, list_sessions
from app.routers.transcripts import list_transcripts
from app.services.cursor_pagination import InvalidCursor, decode_cursor, encode_cursor
from fastapi import HTTPException, Response


class CursorEnvelopeTests(unittest.TestCase):
    def test_cursor_round_trips_as_opaque_value(self):
        value = encode_cursor(
            "sessions", created_at="2026-11-21T10:00:00+00:00", id=str(uuid4())
        )
        decoded = decode_cursor(value, "sessions")
        self.assertEqual("sessions", decoded["kind"])
        self.assertEqual("2026-11-21T10:00:00+00:00", decoded["created_at"])

    def test_cursor_rejects_wrong_endpoint_and_garbage(self):
        value = encode_cursor("sessions", created_at="now", id=str(uuid4()))
        with self.assertRaises(InvalidCursor):
            decode_cursor(value, "transcripts")
        with self.assertRaises(InvalidCursor):
            decode_cursor("not-a-cursor", "sessions")


class SessionCursorRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_route_sets_next_cursor_only_when_page_continues(self):
        rows = [
            SimpleNamespace(
                id=uuid4(),
                created_at=datetime(2026, 11, 21, 10 - index, tzinfo=UTC),
            )
            for index in range(3)
        ]
        result = MagicMock()
        result.scalars.return_value.all.return_value = rows
        db = AsyncMock()
        db.execute.return_value = result
        response = Response()

        page = await list_sessions(limit=2, response=response, db=db)

        self.assertEqual(rows[:2], page)
        self.assertIn("X-Next-Cursor", response.headers)
        marker = decode_cursor(response.headers["X-Next-Cursor"], "sessions")
        self.assertEqual(str(rows[1].id), marker["id"])

    async def test_segment_route_rejects_a_malformed_cursor(self):
        with self.assertRaisesRegex(HTTPException, "Invalid segment cursor"):
            await list_segments(
                uuid4(), response=Response(), cursor="garbage", db=AsyncMock()
            )


class TranscriptCursorRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_provisional_tail_is_not_repeated_after_durable_cursor(self):
        session_id = uuid4()
        first_id, second_id = uuid4(), uuid4()
        first = SimpleNamespace(id=first_id, sequence=1)
        second = SimpleNamespace(id=second_id, sequence=2)
        result = MagicMock()
        db = AsyncMock()
        db.execute.return_value = result
        provisional = SimpleNamespace(id="draft-1")
        with (
            patch(
                "app.routers.transcripts.list_visible_provisional_revisions",
                new=AsyncMock(return_value=[provisional]),
            ),
            patch(
                "app.routers.transcripts.provisional_transcript_payload",
                side_effect=lambda row, sequence: {"id": row.id, "sequence": sequence},
            ),
        ):
            result.scalars.return_value.all.return_value = [first]
            initial = await list_transcripts(
                session_id, response=Response(), limit=2, db=db
            )
            cursor = encode_cursor("transcripts", sequence=1, id=str(first_id))
            result.scalars.return_value.all.return_value = [second]
            continued = await list_transcripts(
                session_id, response=Response(), limit=1, cursor=cursor, db=db
            )

        self.assertEqual([first, {"id": "draft-1", "sequence": 2}], initial)
        self.assertEqual([second], continued)


if __name__ == "__main__":
    unittest.main()
