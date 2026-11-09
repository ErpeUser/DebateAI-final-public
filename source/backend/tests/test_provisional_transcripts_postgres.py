import asyncio
import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, ProvisionalTranscriptRevision, Session
from app.services.provisional_transcripts import persist_provisional_revision


POSTGRES_URL = os.environ.get("BACKCHANNEL_TEST_POSTGRES_URL", "")


@unittest.skipUnless(POSTGRES_URL, "BACKCHANNEL_TEST_POSTGRES_URL is not configured")
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
