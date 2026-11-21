import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

from app.routers.sessions import delete_session, update_session
from app.schemas import SessionUpdate


def _session(state: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        state=state,
        started_at=None,
        ended_at=None,
    )


class UpdateSessionStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_call_stamps_started_at(self):
        # Regression: v0.3.1-v0.3.3 shipped without the datetime import, so
        # the pre_call -> active transition (Start Call) raised NameError.
        session = _session("pre_call")
        db = AsyncMock()
        db.get.return_value = session

        result = await update_session(session.id, SessionUpdate(state="active"), db=db)

        self.assertIs(result, session)
        self.assertEqual(session.state, "active")
        self.assertIsInstance(session.started_at, datetime)
        self.assertIsNotNone(session.started_at.tzinfo)
        db.commit.assert_awaited_once()

    async def test_end_call_stamps_ended_at(self):
        session = _session("active")
        session.started_at = datetime.now(UTC)
        db = AsyncMock()
        db.get.return_value = session

        await update_session(session.id, SessionUpdate(state="completed"), db=db)

        self.assertEqual(session.state, "completed")
        self.assertIsInstance(session.ended_at, datetime)

    async def test_resume_completed_session_clears_ended_at(self):
        session = _session("completed")
        session.ended_at = datetime.now(UTC)
        db = AsyncMock()
        db.get.return_value = session

        await update_session(session.id, SessionUpdate(state="active"), db=db)

        self.assertEqual(session.state, "active")
        self.assertIsNone(session.ended_at)


class DeleteSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_deleting_session_removes_provider_files_after_local_commit(self):
        session = _session("completed")
        db = AsyncMock()
        db.get.return_value = session
        # SQLAlchemy's AsyncSession.execute is awaitable, while the returned
        # Result exposes synchronous scalars().all(). Model that boundary
        # directly so the test does not accidentally invent an async result.
        document_result = MagicMock()
        document_result.scalars.return_value.all.return_value = [
            "files/one",
            "files/two",
        ]
        db.execute.side_effect = [document_result, MagicMock()]

        with (
            patch(
                "app.routers.sessions.delete_uploaded_file", new_callable=AsyncMock
            ) as delete_file,
            patch("app.routers.sessions.shield.forget_session"),
            patch("app.routers.sessions.run_in_threadpool", new_callable=AsyncMock),
        ):
            await delete_session(session.id, db=db)

        self.assertEqual(1, db.commit.await_count)
        self.assertEqual(
            [call("files/one"), call("files/two")], delete_file.await_args_list
        )


if __name__ == "__main__":
    unittest.main()
