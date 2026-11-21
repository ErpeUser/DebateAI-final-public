import inspect
import os
import uuid

from app.database import get_db
from app.models import Document, Session
from app.schemas import DocumentOut
from app.services.file_parsing import (
    parse_docx,
    parse_markdown,
    parse_text,
    safe_upload_filename,
)
from app.services.gemini_files import delete_uploaded_file, upload_and_summarize
from app.services.office_archive import OfficeArchiveError, preflight_office_archive
from app.services.pii import shield
from app.services.privacy import is_local_only
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/sessions/{session_id}/documents", tags=["documents"])

# Bound for the Privacy First local excerpt stored as the document summary.
LOCAL_EXTRACT_CHARS = 4000
MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_DOCUMENT_FILENAME_CHARS = 255

_LOCAL_EXTRACT_EXTS = {".txt", ".md", ".markdown", ".docx"}


async def _maybe_await(value):
    """Support the real AsyncSession and lightweight synchronous test doubles."""
    return await value if inspect.isawaitable(value) else value


def local_extract_summary(content: bytes, filename: str, shielded: bool = False) -> str:
    """Bounded plain-text excerpt for Privacy First uploads; no cloud calls.

    ponytail: excerpt, not a summary - compressing through an admitted local
    text model is the upgrade path if excerpts prove too coarse (ALP-181).
    """
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _LOCAL_EXTRACT_EXTS:
        mode = "The PII Shield is on" if shielded else "Privacy First is on"
        remedy = "turn the PII Shield off" if shielded else "turn Privacy First off"
        raise HTTPException(
            400,
            f"{mode}, so documents are read on this machine instead "
            "of being uploaded. Only .txt, .md, and .docx files can be read "
            f"locally; {remedy} to attach other formats.",
        )
    if ext == ".docx":
        segments = parse_docx(content)
    elif ext == ".txt":
        segments = parse_text(content.decode("utf-8", errors="replace"))
    else:
        segments = parse_markdown(content.decode("utf-8", errors="replace"))

    excerpt = ""
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        if excerpt and len(excerpt) + len(segment) + 2 > LOCAL_EXTRACT_CHARS:
            break
        excerpt = f"{excerpt}\n\n{segment}" if excerpt else segment
    return excerpt[:LOCAL_EXTRACT_CHARS]


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    session_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)
):
    if await _maybe_await(db.get(Session, session_id)) is None:
        raise HTTPException(404, "Session not found")
    filename = safe_upload_filename(
        file.filename, fallback="document", max_length=MAX_DOCUMENT_FILENAME_CHARS
    )
    content = await file.read(MAX_DOCUMENT_UPLOAD_BYTES + 1)
    if len(content) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(413, "Document exceeds the 25 MiB upload limit")
    try:
        preflight_office_archive(content, filename)
    except OfficeArchiveError as error:
        raise HTTPException(400, str(error)) from error
    shielded = (await shield.get_settings(db)).enabled
    if await is_local_only() or shielded:
        # With the PII Shield on, the file itself never leaves the machine:
        # its text is read here and protected before it is stored or shown
        # to any model.
        doc = Document(
            session_id=session_id,
            filename=filename,
            mime_type=file.content_type or "application/octet-stream",
            gemini_file_uri="",
            summary=await shield.protect_text(
                db,
                session_id,
                local_extract_summary(content, filename, shielded=shielded),
            ),
            summary_source="local_extract",
        )
    else:
        doc = Document(
            session_id=session_id,
            filename=filename,
            mime_type=file.content_type or "application/octet-stream",
            gemini_file_uri=await upload_and_summarize(
                content, filename, file.content_type
            ),
        )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    session_id: uuid.UUID,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    if await db.get(Session, session_id) is None:
        raise HTTPException(404, "Session not found")
    result = await db.execute(
        select(Document)
        .where(Document.session_id == session_id)
        .order_by(Document.uploaded_at, Document.id)
        .limit(limit)
    )
    return result.scalars().all()


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    session_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    doc = await db.get(Document, document_id)
    if not doc or doc.session_id != session_id:
        raise HTTPException(404, "Document not found")
    remote_uri = doc.gemini_file_uri or ""
    await db.delete(doc)
    await db.commit()
    if remote_uri:
        await delete_uploaded_file(remote_uri)
