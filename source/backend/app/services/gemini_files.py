import logging
import tempfile
import os
from urllib.parse import urlsplit

from google import genai

from app.config import settings
from app.services.privacy import LocalOnlyModeError, is_local_only
from app.services.secrets import resolve_provider_key
from app.services.token_usage import record_token_usage

logger = logging.getLogger(__name__)


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
        uploaded = await client.aio.files.upload(file=tmp_path, config={"mime_type": mime_type})
        logger.info(f"Uploaded file {filename} -> {uploaded.uri}")
        return uploaded.uri
    finally:
        os.unlink(tmp_path)


async def delete_uploaded_file(file_uri: str) -> None:
    """Best-effort delete of a Gemini Files resource after local deletion.

    Local DB deletion must never be held open by a provider request. A failed
    remote delete is logged for later cleanup rather than making the local
    user action fail.
    """
    if not file_uri or await is_local_only():
        return
    try:
        client = genai.Client(api_key=await resolve_provider_key("google"))
        raw = str(file_uri).strip()
        if "/files/" in raw:
            resource_name = "files/" + urlsplit(raw).path.split("/files/", 1)[1].strip("/")
        else:
            resource_name = raw.removeprefix("files/")
        if not resource_name or resource_name == "files/":
            logger.warning("Cannot derive Gemini Files resource name from %r", file_uri[:160])
            return
        await client.aio.files.delete(name=resource_name)
        logger.info("Deleted remote Gemini file %s", resource_name)
    except Exception:
        logger.warning("Could not delete remote Gemini file %r", file_uri[:160], exc_info=True)


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
                    {"text": "Summarize this document concisely. Focus on key concepts, capabilities, metrics, decisions, risks, talking points, and follow-up context that may be relevant to the session. Keep it under 500 words."},
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
