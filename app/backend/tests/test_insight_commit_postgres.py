"""Real PostgreSQL boundaries; requires an explicitly owned temporary cluster."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base, Question, Session, Speaker
from tests.test_insight_commit_retry import (
    MODULE, SPEAKER_A, SPEAKER_B, TEXT, SyntheticSocket, make_orchestrator,
)

POSTGRES_URL = os.environ.get('DEBATEAI_TEST_POSTGRES_URL', '')
DATA_DIRECTORY = os.environ.get('DEBATEAI_TEST_POSTGRES_DATA_DIR', '')
RUN_ID = os.environ.get('DEBATEAI_TEST_POSTGRES_RUN_ID', '')


@unittest.skipUnless(POSTGRES_URL and DATA_DIRECTORY and RUN_ID,
                     'Owned temporary PostgreSQL cluster not configured')
class InsightPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = make_url(POSTGRES_URL)
        if url.host != '127.0.0.1' or url.database != 'debateai_acceptance_' + RUN_ID:
            raise RuntimeError('Refusing non-isolated PostgreSQL target')
        expected = Path(DATA_DIRECTORY).resolve(strict=True)
        marker = json.loads((expected / '.debateai-acceptance-cluster').read_text())
        if marker != {'run_id': RUN_ID, 'database': url.database}:
            raise RuntimeError('Temporary cluster ownership marker does not match')
        self.engine = create_async_engine(url, connect_args={'timeout': 5})
        self.addAsyncCleanup(self.engine.dispose)
        # No schema or data writes until the real server's directory is verified.
        async with self.engine.connect() as connection:
            actual = await connection.scalar(text('SHOW data_directory'))
            if Path(actual).resolve(strict=True) != expected:
                raise RuntimeError('Connected PostgreSQL is not the owned test cluster')
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.socket = SyntheticSocket()
        self.orchestrator = make_orchestrator(self.socket)
        async with self.factory() as database:
            database.add(Session(id=self.orchestrator.session_id, name='Acceptance fixture only'))
            await database.commit()
            database.add_all([
                Speaker(id=UUID(SPEAKER_A), session_id=self.orchestrator.session_id, name='Alex'),
                Speaker(id=UUID(SPEAKER_B), session_id=self.orchestrator.session_id, name='Morgan'),
            ])
            await database.commit()
        self.addAsyncCleanup(self.remove_fixture)
        replacement = patch(MODULE + '.async_session', self.factory)
        replacement.start()
        self.addCleanup(replacement.stop)

    async def remove_fixture(self):
        async with self.factory() as database:
            session = await database.get(Session, self.orchestrator.session_id)
            if session is not None:
                await database.delete(session)
                await database.commit()

    async def rows(self):
        async with self.factory() as database:
            return list((await database.scalars(select(Question).where(
                Question.session_id == self.orchestrator.session_id))).all())

    async def emit(self, **payload):
        return await self.orchestrator._save_and_send_insight(
            {'question': TEXT, **payload}, agent_source='consolidated_analyst')

    async def test_committed_row_survives_refresh_failure_without_duplicate_retry(self):
        # Real commit; only the subsequent read is fault-injected.
        with patch.object(AsyncSession, 'refresh', side_effect=RuntimeError('injected refresh failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected refresh failure'):
                await self.emit()
        original = await self.rows()
        self.assertEqual(1, len(original))
        self.assertFalse(await self.emit())
        repeated = await self.rows()
        self.assertEqual([original[0].id], [row.id for row in repeated])

    async def test_real_constraint_failure_leaves_identical_text_retryable(self):
        # PostgreSQL rejects this VARCHAR(30), so the actual transaction rolls back.
        with self.assertRaises(DBAPIError):
            await self.emit(agent_source='x' * 31)
        self.assertEqual([], await self.rows())
        self.assertTrue(await self.emit())
        self.assertEqual(1, len(await self.rows()))

    async def test_equal_text_from_distinct_validated_speakers_keeps_both_rows(self):
        self.assertTrue(await self.emit(speaker_id=SPEAKER_A))
        self.assertTrue(await self.emit(speaker_id=SPEAKER_B))
        self.assertEqual({UUID(SPEAKER_A), UUID(SPEAKER_B)},
                         {row.speaker_id for row in await self.rows()})
        self.assertFalse(await self.emit(speaker_id=SPEAKER_A))
        self.assertEqual(2, len(await self.rows()))

    async def test_broadcast_failure_does_not_reinsert_committed_row(self):
        self.socket.fail = True
        self.assertTrue(await self.emit())
        self.socket.fail = False
        self.assertFalse(await self.emit())
        self.assertEqual(1, len(await self.rows()))


if __name__ == '__main__':
    unittest.main()
