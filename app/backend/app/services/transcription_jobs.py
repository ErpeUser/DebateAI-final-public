"""In-process progress for long audio transcription work."""

from dataclasses import dataclass, field
import time
import uuid
import threading


ACTIVE_STATUSES = {"queued", "running", "canceling"}


class JobAlreadyRunning(RuntimeError):
    pass


class JobCanceled(RuntimeError):
    pass


@dataclass
class TranscriptionJob:
    session_id: uuid.UUID
    kind: str
    model_id: str
    total_segments: int
    filename: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "queued"
    segments_done: int = 0
    entries: int = 0
    error: str = ""
    cancel_requested: bool = False
    _last_touched: float = field(default_factory=time.monotonic, repr=False)
    _finished_at: float | None = field(default=None, repr=False)

    def _touch(self) -> None:
        self._last_touched = time.monotonic()

    def snapshot(self) -> dict:
        with _jobs_lock:
            self._touch()
            progress = 100 if self.status == "completed" else round(
                self.segments_done * 100 / max(1, self.total_segments)
            )
            return {
                "job_id": str(self.id),
                "kind": self.kind,
                "status": self.status,
                "model_id": self.model_id,
                "segments_done": self.segments_done,
                "total_segments": self.total_segments,
                "entries": self.entries,
                "progress": progress,
                "filename": self.filename,
                "error": self.error,
            }

    def check_canceled(self) -> None:
        with _jobs_lock:
            self._touch()
            if self.cancel_requested:
                raise JobCanceled()

    def start(self) -> None:
        with _jobs_lock:
            self.check_canceled()
            self.status = "running"
            self._touch()

    def update_entries(self, entries: int) -> None:
        with _jobs_lock:
            self.entries = max(0, int(entries))
            self._touch()

    def finish_segment(self, entries: int) -> None:
        with _jobs_lock:
            self.entries = max(0, int(entries))
            self.segments_done += 1
            self._touch()

    def complete(self) -> None:
        with _jobs_lock:
            self.status = "completed"
            self.segments_done = self.total_segments
            self._finished_at = time.monotonic()
            self._touch()

    def fail(self, message: str) -> None:
        with _jobs_lock:
            self.status = "failed"
            self.error = str(message)[:500]
            self._finished_at = time.monotonic()
            self._touch()

    def cancel(self) -> None:
        with _jobs_lock:
            if self.status in ACTIVE_STATUSES:
                self.cancel_requested = True
                self.status = "canceling"
                self._touch()

    def mark_canceled(self) -> None:
        with _jobs_lock:
            self.status = "canceled"
            self._finished_at = time.monotonic()
            self._touch()


# ponytail: one process owns the desktop API; persist jobs if multi-worker or
# restart recovery becomes a requirement.
_jobs: dict[uuid.UUID, TranscriptionJob] = {}
_jobs_lock = threading.RLock()


def create_job(
    session_id: uuid.UUID,
    kind: str,
    model_id: str,
    total_segments: int,
    *,
    filename: str | None = None,
) -> TranscriptionJob:
    sweep_jobs()
    with _jobs_lock:
        current = _jobs.get(session_id)
        if current and current.status in ACTIVE_STATUSES:
            raise JobAlreadyRunning(f"A {current.kind.replace('_', ' ')} job is already running")
        job = TranscriptionJob(
            session_id=session_id,
            kind=kind,
            model_id=model_id,
            total_segments=max(1, total_segments),
            filename=filename,
        )
        _jobs[session_id] = job
        return job


def get_job(
    session_id: uuid.UUID,
    *,
    kind: str | None = None,
    job_id: uuid.UUID | None = None,
) -> TranscriptionJob | None:
    sweep_jobs()
    with _jobs_lock:
        job = _jobs.get(session_id)
        if not job or (kind and job.kind != kind) or (job_id and job.id != job_id):
            return None
        return job


def forget_session(session_id: uuid.UUID) -> None:
    """Drop a deleted session's completed job snapshot from the process cache."""
    with _jobs_lock:
        _jobs.pop(session_id, None)


def sweep_jobs(
    *,
    now: float | None = None,
    terminal_ttl_seconds: float = 60 * 60,
) -> int:
    """Drop terminal job snapshots after a bounded in-process retention window."""
    now = time.monotonic() if now is None else now
    terminal = {"completed", "failed", "canceled"}
    with _jobs_lock:
        expired = [
            session_id
            for session_id, job in _jobs.items()
            if job.status in terminal
            and now - (job._finished_at or job._last_touched) >= terminal_ttl_seconds
        ]
        for session_id in expired:
            _jobs.pop(session_id, None)
        return len(expired)
