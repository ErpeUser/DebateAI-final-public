"""Bounded multi-page cursor checks for the core session collections."""

import importlib.util
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from fastapi import Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, CallSegment, Session, TranscriptEntry
from app.routers.sessions import list_segments, list_sessions
from app.routers.transcripts import list_transcripts


@unittest.skipUnless(
    importlib.util.find_spec("aiosqlite"), "optional aiosqlite test dependency"
)
class CoreCursorLoadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_id = uuid4()
        self.count = 1205
        now = datetime(2026, 11, 22, 10, tzinfo=UTC)
        async with self.sessions() as db:
            db.add_all(
                [
                    Session(
                        id=self.session_id,
                        name="Cursor load",
                        created_at=now,
                    ),
                    *(
                        Session(id=uuid4(), name=f"Cursor load {index}", created_at=now)
                        for index in range(1, self.count)
                    ),
                ]
            )
            db.add_all(
                [
                    CallSegment(
                        id=uuid4(),
                        session_id=self.session_id,
                        segment_number=index,
                        started_at=now,
                    )
                    for index in range(self.count)
                ]
            )
            db.add_all(
                [
                    TranscriptEntry(
                        id=uuid4(),
                        session_id=self.session_id,
                        text=f"entry {index}",
                        timestamp=now,
                        sequence=index + 1,
                    )
                    for index in range(self.count)
                ]
            )
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _drain(self, route, args, db, key):
        cursor = None
        rows = []
        page_count = 0
        while True:
            response = Response()
            page = await route(
                *args,
                response=response,
                limit=200,
                cursor=cursor,
                db=db,
            )
            rows.extend(page)
            page_count += 1
            cursor = response.headers.get("X-Next-Cursor")
            if not cursor:
                break
            self.assertLessEqual(page_count, 10, key)
        self.assertEqual(self.count, len(rows), key)
        self.assertEqual(self.count, len({str(row.id) for row in rows}), key)
        return page_count

    async def test_core_routes_drain_over_a_thousand_rows_without_duplicates(self):
        async with self.sessions() as db:
            sessions_page_count = await self._drain(list_sessions, (), db, "sessions")
            segments_page_count = await self._drain(
                list_segments, (self.session_id,), db, "segments"
            )
            with patch(
                "app.routers.transcripts.list_visible_provisional_revisions",
                return_value=[],
            ):
                transcripts_page_count = await self._drain(
                    list_transcripts, (self.session_id,), db, "transcripts"
                )

        self.assertEqual(7, sessions_page_count)
        self.assertEqual(7, segments_page_count)
        self.assertEqual(7, transcripts_page_count)


if __name__ == "__main__":
    unittest.main()
