import asyncio
import uuid
from unittest.mock import patch

from app.models import Base
from app.services import shared_session_state
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_shared_session_state_replays_across_worker_sessions():
    async def exercise():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        session_id = uuid.uuid4()
        with patch.object(shared_session_state, "async_session", sessions):
            first = await shared_session_state.open_generation(
                session_id,
                server_epoch="epoch-1",
                events=[],
                state=[],
                sequence=0,
            )
            assert first.generation == 1
            assert await shared_session_state.save_snapshot(
                session_id,
                first.generation,
                server_epoch="epoch-1",
                events=[{"type": "status", "session_sequence": 1}],
                state=[
                    {
                        "event_type": "status",
                        "state_key": "latest",
                        "event": {"type": "status", "session_sequence": 1},
                    }
                ],
                sequence=1,
            )
            second = await shared_session_state.open_generation(
                session_id,
                server_epoch="ignored",
                events=[],
                state=[],
                sequence=0,
            )
            assert second.generation == 2
            assert second.server_epoch == "epoch-1"
            assert second.sequence == 1
            assert second.events[0]["session_sequence"] == 1
            await shared_session_state.close_generation(session_id, first.generation)
            await shared_session_state.close_generation(session_id, second.generation)
            await shared_session_state.forget_session(session_id)
        await engine.dispose()

    asyncio.run(exercise())
