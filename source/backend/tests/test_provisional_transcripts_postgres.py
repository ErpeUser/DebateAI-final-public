import asyncio
import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, ProvisionalTranscriptRevision, Session
from app.services.provisional_transcripts import persist_provisional_revision


POSTGRES_URL = os.environ.get("DEBATEAI_TEST_POSTGRES_URL", "")


@unittest.skipUnless(POSTGRES_URL, "DEBATEAI_TEST_POSTGRES_URL is not configured")
class ProvisionalTranscriptPostgresConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(POSTGRES_URL)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_id = uuid.uuid4()
        async with self.sessions() as db:
            db.add(Session(id=self.session_id, name="Concurrency test"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_invalid_or_non_monotone_revisions_are_rejected(self):
        from app.services.provisional_transcripts import (
            MAX_PROVISIONAL_SEGMENT_CHARS,
        )

        first_data = {
            "segment_id": "segment-1",
            "segment_revision": 1,
            "text": "Erste Hypothese.",
            "mode": "replace",
        }

        with patch(
            "app.services.provisional_transcripts.shield.protect_text",
            AsyncMock(side_effect=lambda _db, _session_id, text: text),
        ):
            async with self.sessions() as db:
                first = await persist_provisional_revision(
                    db, self.session_id, first_data
                )
                await db.commit()

                malformed = await persist_provisional_revision(
                    db,
                    self.session_id,
                    {
                        **first_data,
                        "segment_revision": "not-a-number",
                        "text": "Wird verworfen.",
                    },
                )
                stale = await persist_provisional_revision(
                    db,
                    self.session_id,
                    {
                        **first_data,
                        "text": "Stale replay.",
                    },
                )
                oversized_append = await persist_provisional_revision(
                    db,
                    self.session_id,
                    {
                        **first_data,
                        "segment_revision": 2,
                        "text": "x" * MAX_PROVISIONAL_SEGMENT_CHARS,
                        "mode": "append",
                    },
                )
                await db.commit()

        self.assertTrue(first.created)
        self.assertFalse(malformed.created)
        self.assertIsNone(malformed.row)
        self.assertFalse(stale.created)
        self.assertIsNotNone(stale.row)
        self.assertEqual(1, stale.row.revision)
        self.assertFalse(oversized_append.created)
        self.assertIsNotNone(oversized_append.row)
        self.assertEqual(1, oversized_append.row.revision)

        async with self.sessions() as db:
            count = await db.scalar(
                select(func.count(ProvisionalTranscriptRevision.id)).where(
                    ProvisionalTranscriptRevision.session_id == self.session_id
                )
            )
        self.assertEqual(1, count)

    async def test_identical_concurrent_replay_commits_exactly_one_revision(self):
        data = {
            "segment_id": "segment-1",
            "segment_revision": 1,
            "text": "Derselbe technische Replay.",
            "mode": "replace",
        }

        async def write_once():
            async with self.sessions() as db:
                result = await persist_provisional_revision(db, self.session_id, data)
                await db.commit()
                return result.created

        with patch(
            "app.services.provisional_transcripts.shield.protect_text",
            AsyncMock(side_effect=lambda _db, _session_id, text: text),
        ):
            created = await asyncio.gather(write_once(), write_once())

        async with self.sessions() as db:
            count = await db.scalar(
                select(func.count(ProvisionalTranscriptRevision.id)).where(
                    ProvisionalTranscriptRevision.session_id == self.session_id
                )
            )
        self.assertEqual([False, True], sorted(created))
        self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main()
