import logging
import os
import tempfile
import time
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.config import settings
from app.services.privacy import LocalOnlyModeError, is_local_only
from app.services.redaction import redact_text
from app.services.secrets import resolve_provider_key
from app.services.token_usage import record_token_usage
from google import genai

logger = logging.getLogger(__name__)

MAX_FILE_DELETE_OUTBOX = 1024
FILE_DELETE_RETRY_BASE_SECONDS = 30.0
FILE_DELETE_RETRY_MAX_SECONDS = 60 * 60


@dataclass
class PendingFileDeletion:
    file_uri: str
    attempts: int = 0
    next_attempt_at: float = 0.0
    last_error: str = ""

    def snapshot(self) -> dict[str, object]:
        return {
            "file_uri": self.file_uri,
            "attempts": self.attempts,
            "next_attempt_at": self.next_attempt_at,
            "last_error": self.last_error,
        }


_delete_outbox: OrderedDict[str, PendingFileDeletion] = OrderedDict()


def _queue_file_deletion(
    file_uri: str, error: Exception | str, *, now: float | None = None
) -> None:
    raw = str(file_uri).strip()
    if not raw:
        return
    now = time.monotonic() if now is None else now
    task = _delete_outbox.pop(raw, None) or PendingFileDeletion(raw)
    task.attempts += 1
    task.last_error = str(error)[:500]
    delay = min(
        FILE_DELETE_RETRY_MAX_SECONDS,
        FILE_DELETE_RETRY_BASE_SECONDS * (2 ** min(task.attempts - 1, 8)),
    )
    task.next_attempt_at = now + delay
    _delete_outbox[raw] = task
    while len(_delete_outbox) > MAX_FILE_DELETE_OUTBOX:
        _delete_outbox.popitem(last=False)


def pending_file_deletions() -> list[dict[str, object]]:
    """Return bounded, non-secret cleanup status for retry/operations UI."""
    return [task.snapshot() for task in _delete_outbox.values()]


async def _delete_uploaded_file(file_uri: str) -> None:
    client = genai.Client(api_key=await resolve_provider_key("google"))
    raw = str(file_uri).strip()
    if "/files/" in raw:
        resource_name = "files/" + urlsplit(raw).path.split("/files/", 1)[1].strip("/")
    else:
        resource_name = raw.removeprefix("files/")
    if not resource_name or resource_name == "files/":
        raise ValueError(
            f"Cannot derive Gemini Files resource name from {file_uri[:160]!r}"
        )
    await client.aio.files.delete(name=resource_name)
    logger.info("Deleted remote Gemini file %s", resource_name)


async def upload_and_summarize(content: bytes, filename: str, mime_type: str) -> str:
    """Upload a file to Gemini Files API and return the file URI."""
    if await is_local_only():
        raise LocalOnlyModeError("document upload to the Gemini Files API")
    client = genai.Client(api_key=await resolve_provider_key("google"))

    # Write to temp file for upload
    suffix = os.path.splitext(filename)[1] if filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        uploaded = await client.aio.files.upload(
            file=tmp_path, config={"mime_type": mime_type}
        )
        logger.info(
            "Uploaded document (%d filename chars) to Gemini Files API: %s",
            len(filename or ""),
            redact_text(str(uploaded.uri))[:160],
        )
        return uploaded.uri
    finally:
        os.unlink(tmp_path)


async def delete_uploaded_file(file_uri: str) -> bool:
    """Delete a Gemini Files resource, queueing failures for bounded retry.

    Local DB deletion must never be held open by a provider request. A failed
    remote delete is logged for later cleanup rather than making the local
    user action fail.
    """
    if not file_uri:
        return True
    try:
        await _delete_uploaded_file(file_uri)
        _delete_outbox.pop(str(file_uri).strip(), None)
        return True
    except Exception as exc:
        _queue_file_deletion(file_uri, exc)
        logger.warning(
            "Could not delete remote Gemini file %r", file_uri[:160], exc_info=True
        )
        return False


async def retry_pending_file_deletions(
    *, now: float | None = None, max_items: int = 16
) -> int:
    """Retry due remote deletes without blocking local session deletion."""
    now = time.monotonic() if now is None else now
    completed = 0
    for file_uri, task in list(_delete_outbox.items())[: max(0, max_items)]:
        if task.next_attempt_at > now:
            continue
        try:
            await _delete_uploaded_file(file_uri)
        except Exception as exc:
            _queue_file_deletion(file_uri, exc, now=now)
            logger.warning(
                "Retry of remote Gemini file delete failed for %r", file_uri[:160]
            )
        else:
            _delete_outbox.pop(file_uri, None)
            completed += 1
    return completed


async def summarize_document(file_uri: str, session_id=None) -> str:
    """Use Gemini to summarize an uploaded document for context injection."""
    if await is_local_only():
        raise LocalOnlyModeError("document summarization via Gemini")
    client = genai.Client(api_key=await resolve_provider_key("google"))

    response = await client.aio.models.generate_content(
        model=settings.REFINEMENT_MODEL,
        contents=[
            {
                "parts": [
                    {"file_data": {"file_uri": file_uri}},
                    {
                        "text": "Summarize this document concisely. Focus on key concepts, capabilities, metrics, decisions, risks, talking points, and follow-up context that may be relevant to the session. Keep it under 500 words."
                    },
                ]
            }
        ],
    )
    await record_token_usage(
        session_id,
        "document_summary",
        settings.REFINEMENT_MODEL,
        getattr(response, "usage_metadata", None),
    )
    return response.text
