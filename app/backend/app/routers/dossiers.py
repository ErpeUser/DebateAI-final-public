"""Session-scoped, local-only preparation dossiers."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from app.database import get_db
from app.models import KnowledgeRecord, KnowledgeSource, Session
from app.services.knowledge_context import prepare_knowledge_record_embeddings
from app.services.markdown_conversion import (
    MarkdownConversionError,
    convert_to_markdown,
    file_extension,
)
from app.services.upload_limits import UploadTooLarge, read_bounded_upload
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/sessions/{session_id}/dossier", tags=["dossier"])
logger = logging.getLogger(__name__)
MAX_DOSSIER_UPLOAD_BYTES = 25 * 1024 * 1024


class DossierEntry(BaseModel):
    kind: str
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=60_000)
    origin: str = Field(default="Eigene Notiz", max_length=500)
    page_reference: str = Field(default="", max_length=120)


def _config(session_id: uuid.UUID) -> str:
    return json.dumps(
        {"kind": "session_dossier", "session_id": str(session_id), "local_only": True}
    )


async def _source(
    db: AsyncSession, session_id: uuid.UUID, *, create: bool
) -> KnowledgeSource | None:
    result = await db.execute(select(KnowledgeSource))
    for source in result.scalars().all():
        try:
            config = json.loads(source.config or "{}")
        except ValueError:
            continue
        if not isinstance(config, dict):
            continue
        if (
            bool(getattr(source, "active", False))
            and config.get("kind") == "session_dossier"
            and config.get("session_id") == str(session_id)
            and config.get("local_only") is True
        ):
            return source
    if not create:
        return None
    if await db.get(Session, session_id) is None:
        raise HTTPException(404, "Session not found")
    source = KnowledgeSource(
        name="Vorbereitungsdossier",
        source_type="files",
        description="Lokales, sitzungsbezogenes Vorbereitungsdossier",
        config=_config(session_id),
    )
    db.add(source)
    await db.flush()
    return source


def _record_out(record: KnowledgeRecord) -> dict:
    try:
        meta = json.loads(record.meta or "{}")
    except ValueError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "id": str(record.id),
        "title": record.title,
        "body": record.body,
        "kind": meta.get("kind", "document"),
        "origin": meta.get("origin", record.title),
        "page_reference": meta.get("page_reference", ""),
        "independent_evidence": bool(meta.get("independent_evidence", False)),
    }


async def _prepare_record_embedding(record: KnowledgeRecord) -> None:
    try:
        await asyncio.to_thread(prepare_knowledge_record_embeddings, [record])
    except Exception as error:
        logger.warning(
            "Dossier embedding preparation unavailable for %s: %s",
            record.id,
            error,
        )


@router.get("")
async def read_dossier(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await _source(db, session_id, create=False)
    if source is None:
        return {"source_id": "", "entries": []}
    result = await db.execute(
        select(KnowledgeRecord)
        .where(KnowledgeRecord.source_id == source.id)
        .order_by(KnowledgeRecord.created_at)
    )
    return {
        "source_id": str(source.id),
        "entries": [_record_out(row) for row in result.scalars().all()],
    }


@router.post("/entries", status_code=201)
async def create_dossier_entry(
    session_id: uuid.UUID,
    body: DossierEntry,
    db: AsyncSession = Depends(get_db),
):
    if body.kind not in {"thesis", "term", "counterposition"}:
        raise HTTPException(400, "Invalid dossier entry kind")
    source = await _source(db, session_id, create=True)
    record = KnowledgeRecord(
        source_id=source.id,
        title=body.title,
        body=body.body,
        meta=json.dumps(
            {
                "kind": body.kind,
                "origin": body.origin,
                "page_reference": body.page_reference,
                "independent_evidence": False,
            },
            ensure_ascii=False,
        ),
    )
    db.add(record)
    await db.flush()
    await _prepare_record_embedding(record)
    await db.commit()
    await db.refresh(record)
    return _record_out(record)


@router.post("/files", status_code=201)
async def upload_dossier_file(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    page_reference: str = "",
    db: AsyncSession = Depends(get_db),
):
    try:
        content = await read_bounded_upload(file, max_bytes=MAX_DOSSIER_UPLOAD_BYTES)
    except UploadTooLarge as error:
        raise HTTPException(
            413, "Dossier file exceeds the 25 MiB upload limit"
        ) from error
    filename = file.filename or "Unterlage"
    try:
        markdown = convert_to_markdown(content, filename)
    except MarkdownConversionError as error:
        raise HTTPException(400, str(error)) from error
    source = await _source(db, session_id, create=True)
    record = KnowledgeRecord(
        source_id=source.id,
        title=filename,
        body=markdown[:100_000],
        meta=json.dumps(
            {
                "kind": "document",
                "origin": filename,
                "page_reference": page_reference,
                "format": file_extension(filename),
                "independent_evidence": True,
                "local_only": True,
            },
            ensure_ascii=False,
        ),
    )
    db.add(record)
    await db.flush()
    await _prepare_record_embedding(record)
    await db.commit()
    await db.refresh(record)
    return _record_out(record)


@router.delete("/entries/{record_id}", status_code=204)
async def delete_dossier_entry(
    session_id: uuid.UUID,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    source = await _source(db, session_id, create=False)
    record = await db.get(KnowledgeRecord, record_id)
    if source is None or record is None or record.source_id != source.id:
        raise HTTPException(404, "Dossier entry not found")
    await db.delete(record)
    await db.commit()


@router.delete("", status_code=204)
async def delete_dossier(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await _source(db, session_id, create=False)
    if source is None:
        return
    await db.execute(
        delete(KnowledgeRecord).where(KnowledgeRecord.source_id == source.id)
    )
    await db.delete(source)
    await db.commit()
