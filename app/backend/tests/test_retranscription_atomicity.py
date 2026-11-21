"""Destructive retranscription must preserve existing rows on partial failure."""

import importlib.util
import tempfile
import unittest
import uuid
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.models import Base, CallSegment, Session, TranscriptEntry
from app.routers import imports as import_router
from app.routers import retranscribe
from app.services.batch_transcriber import TranscriptionError
from app.services.speaker_diarizer import DiarizedSegment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@unittest.skipUnless(
    importlib.util.find_spec("aiosqlite"), "optional aiosqlite test dependency"
)
class RetranscriptionAtomicityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="retranscribe-fixture-")
        self.root = Path(self.temp.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.sid = uuid.uuid4()
        self.old_id = uuid.uuid4()
        async with self.sessions() as db:
            db.add(Session(id=self.sid, name="Synthetic replay", state="completed"))
            await db.flush()
            db.add(
                TranscriptEntry(
                    id=self.old_id,
                    session_id=self.sid,
                    sequence=1,
                    text="Keep original transcript",
                )
            )
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.temp.cleanup()

    async def add_segments(self, paths):
        async with self.sessions() as db:
            for number, fields in enumerate(paths, 1):
                db.add(
                    CallSegment(session_id=self.sid, segment_number=number, **fields)
                )
            await db.commit()

    async def run_job(self, responses):
        runtime = SimpleNamespace(
            speaker_similarity_threshold=0.7, effective_live_diarizer="stub"
        )
        transcriber = SimpleNamespace(
            transcribe_segment=AsyncMock(side_effect=responses)
        )
        # One deterministic, unknown-speaker utterance per source, no model loading.
        diarize = AsyncMock(return_value=[DiarizedSegment("auto_unknown", b"fake-pcm")])
        job = retranscribe.transcription_jobs.create_job(
            self.sid, "retranscription", "stub", 2
        )
        with ExitStack() as patches:
            patches.enter_context(
                patch.object(retranscribe, "async_session", self.sessions)
            )
            patches.enter_context(
                patch.object(retranscribe, "data_dir", return_value=self.root)
            )
            patches.enter_context(
                patch.object(
                    retranscribe,
                    "get_diarizer_runtime_config",
                    AsyncMock(return_value=runtime),
                )
            )
            patches.enter_context(
                patch.object(
                    import_router,
                    "get_diarizer_runtime_config",
                    AsyncMock(return_value=runtime),
                )
            )
            patches.enter_context(
                patch.object(
                    import_router,
                    "get_transcription_runtime_config",
                    AsyncMock(
                        return_value=SimpleNamespace(
                            batch_model_id="stub", language="en"
                        )
                    ),
                )
            )
            patches.enter_context(
                patch.object(
                    import_router,
                    "convert_to_pcm16",
                    side_effect=lambda data, _fmt: data,
                )
            )
            patches.enter_context(
                patch.object(
                    import_router, "create_diarizer", Mock(return_value=object())
                )
            )
            patches.enter_context(
                patch.object(
                    import_router, "create_transcriber", return_value=transcriber
                )
            )
            patches.enter_context(patch.object(import_router, "_diarize_pcm", diarize))
            patches.enter_context(
                patch.object(
                    import_router.shield,
                    "protect_text",
                    AsyncMock(side_effect=lambda _db, _sid, text: text),
                )
            )
            await retranscribe._run_retranscription_job(self.sid, job.id)
        async with self.sessions() as db:
            rows = list(
                (
                    await db.execute(
                        select(TranscriptEntry)
                        .where(TranscriptEntry.session_id == self.sid)
                        .order_by(TranscriptEntry.sequence)
                    )
                ).scalars()
            )
        return job.snapshot(), rows, transcriber

    async def test_asr_failure_after_success_keeps_original_rows(self):
        (self.root / "one.wav").write_bytes(b"one")
        (self.root / "two.wav").write_bytes(b"two")
        await self.add_segments([{"audio_path": "one.wav"}, {"audio_path": "two.wav"}])
        job, rows, _ = await self.run_job(
            ["New partial transcript", TranscriptionError("synthetic provider failure")]
        )
        self.assertEqual("failed", job["status"])
        self.assertEqual(
            [(self.old_id, "Keep original transcript")],
            [(row.id, row.text) for row in rows],
        )

    async def test_missing_stored_segment_keeps_original_rows(self):
        (self.root / "one.wav").write_bytes(b"one")
        await self.add_segments(
            [{"audio_path": "one.wav"}, {"audio_path": "missing.wav"}]
        )
        job, rows, transcriber = await self.run_job(["New partial transcript"])
        self.assertEqual("failed", job["status"])
        self.assertEqual([self.old_id], [row.id for row in rows])
        transcriber.transcribe_segment.assert_not_awaited()

    async def test_missing_side_of_declared_split_keeps_original_rows(self):
        (self.root / "mic.wav").write_bytes(b"mic")
        await self.add_segments(
            [{"mic_audio_path": "mic.wav", "system_audio_path": "missing.wav"}]
        )
        job, rows, transcriber = await self.run_job(["Only local person"])
        self.assertEqual("failed", job["status"])
        self.assertEqual([self.old_id], [row.id for row in rows])
        transcriber.transcribe_segment.assert_not_awaited()

    async def test_complete_success_replaces_original_rows(self):
        (self.root / "one.wav").write_bytes(b"one")
        (self.root / "two.wav").write_bytes(b"two")
        await self.add_segments([{"audio_path": "one.wav"}, {"audio_path": "two.wav"}])
        job, rows, _ = await self.run_job(["New first", "New second"])
        self.assertEqual("completed", job["status"])
        self.assertEqual(["New first", "New second"], [row.text for row in rows])
        self.assertNotIn(self.old_id, [row.id for row in rows])


if __name__ == "__main__":
    unittest.main(verbosity=2)
