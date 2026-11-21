"""Knowledge source and record CRUD + import/upload endpoints."""

import csv
import io
import json
import uuid
from datetime import UTC, datetime

from app.database import get_db
from app.models import AgentConfig, KnowledgeRecord, KnowledgeSource
from app.schemas import (
    KnowledgeRecordCreate,
    KnowledgeRecordOut,
    KnowledgeRecordUpdate,
    KnowledgeSourceCreate,
    KnowledgeSourceOut,
    KnowledgeSourceUpdate,
)
from app.services.cursor_pagination import InvalidCursor, decode_cursor, encode_cursor
from app.services.knowledge import USER_SOURCE_TYPES
from app.services.markdown_conversion import (
    MarkdownConversionError,
    convert_to_markdown,
    file_extension,
)
from app.services.office_archive import OfficeArchiveError, preflight_office_archive
from app.services.upload_limits import UploadTooLarge, read_bounded_upload
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
MAX_KNOWLEDGE_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_KNOWLEDGE_IMPORT_BYTES = 25 * 1024 * 1024
MAX_KNOWLEDGE_MARKDOWN_CHARS = 100_000


async def _get_source_or_404(source_id: uuid.UUID, db: AsyncSession) -> KnowledgeSource:
    source = await db.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(404, "Knowledge source not found")
    return source


def _require_user_source(source: KnowledgeSource):
    if source.source_type not in USER_SOURCE_TYPES:
        raise HTTPException(
            400,
            "Records for this source are managed elsewhere (see the Offerings manager)",
        )


async def _source_out(source: KnowledgeSource, db: AsyncSession) -> KnowledgeSourceOut:
    count = await db.scalar(
        select(func.count())
        .select_from(KnowledgeRecord)
        .where(KnowledgeRecord.source_id == source.id)
    )
    out = KnowledgeSourceOut.model_validate(source)
    out.record_count = int(count or 0)
    return out


@router.get("", response_model=list[KnowledgeSourceOut])
async def list_sources(
    response: Response,
    limit: int = Query(200, ge=1, le=1000),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(KnowledgeSource, func.count(KnowledgeRecord.id))
        .outerjoin(KnowledgeRecord, KnowledgeRecord.source_id == KnowledgeSource.id)
        .group_by(KnowledgeSource.id)
        .order_by(KnowledgeSource.created_at, KnowledgeSource.id)
    )
    if cursor:
        try:
            marker = decode_cursor(cursor, "knowledge_sources")
            marker_created = datetime.fromisoformat(str(marker["created_at"]))
            marker_id = uuid.UUID(str(marker["id"]))
        except (InvalidCursor, KeyError, TypeError, ValueError):
            raise HTTPException(400, "Invalid knowledge source cursor") from None
        statement = statement.where(
            or_(
                KnowledgeSource.created_at > marker_created,
                and_(
                    KnowledgeSource.created_at == marker_created,
                    KnowledgeSource.id > marker_id,
                ),
            )
        )
    result = await db.execute(statement.limit(limit + 1))
    rows = list(result.all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    out = []
    for source, count in rows:
        item = KnowledgeSourceOut.model_validate(source)
        item.record_count = int(count or 0)
        out.append(item)
    if has_more and rows:
        last = rows[-1][0]
        response.headers["X-Next-Cursor"] = encode_cursor(
            "knowledge_sources", created_at=last.created_at.isoformat(), id=str(last.id)
        )
    return out


@router.post("", response_model=KnowledgeSourceOut)
async def create_source(
    body: KnowledgeSourceCreate, db: AsyncSession = Depends(get_db)
):
    if body.source_type not in USER_SOURCE_TYPES:
        raise HTTPException(
            400, f"source_type must be one of {sorted(USER_SOURCE_TYPES)}"
        )
    source = KnowledgeSource(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return await _source_out(source, db)


@router.get("/{source_id}", response_model=KnowledgeSourceOut)
async def get_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await _get_source_or_404(source_id, db)
    return await _source_out(source, db)


@router.patch("/{source_id}", response_model=KnowledgeSourceOut)
async def update_source(
    source_id: uuid.UUID,
    body: KnowledgeSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    source = await _get_source_or_404(source_id, db)
    _require_user_source(source)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    source.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(source)
    return await _source_out(source, db)


@router.delete("/{source_id}")
async def delete_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await _get_source_or_404(source_id, db)
    if source.source_type == "offerings":
        raise HTTPException(400, "The built-in offerings source cannot be deleted")
    result = await db.execute(
        select(AgentConfig.slug).where(
            AgentConfig.knowledge_source_ids.contains(str(source_id))
        )
    )
    referencing = [row[0] for row in result.all()]
    if referencing:
        raise HTTPException(
            400,
            f"Source is in use by agent(s): {', '.join(referencing)}. Point them elsewhere first.",
        )
    await db.execute(
        delete(KnowledgeRecord).where(KnowledgeRecord.source_id == source_id)
    )
    await db.delete(source)
    await db.commit()
    return {"ok": True}


# --- Records ---


@router.get("/{source_id}/records", response_model=list[KnowledgeRecordOut])
async def list_records(
    source_id: uuid.UUID,
    response: Response,
    limit: int = Query(500, ge=1, le=2000),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    await _get_source_or_404(source_id, db)
    statement = (
        select(KnowledgeRecord)
        .where(KnowledgeRecord.source_id == source_id)
        .order_by(KnowledgeRecord.title, KnowledgeRecord.created_at, KnowledgeRecord.id)
    )
    if cursor:
        try:
            marker = decode_cursor(cursor, "knowledge_records")
            marker_title = str(marker["title"])
            marker_created = datetime.fromisoformat(str(marker["created_at"]))
            marker_id = uuid.UUID(str(marker["id"]))
        except (InvalidCursor, KeyError, TypeError, ValueError):
            raise HTTPException(400, "Invalid knowledge record cursor") from None
        statement = statement.where(
            or_(
                KnowledgeRecord.title > marker_title,
                and_(
                    KnowledgeRecord.title == marker_title,
                    KnowledgeRecord.created_at > marker_created,
                ),
                and_(
                    KnowledgeRecord.title == marker_title,
                    KnowledgeRecord.created_at == marker_created,
                    KnowledgeRecord.id > marker_id,
                ),
            )
        )
    result = await db.execute(statement.limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    if has_more and rows:
        last = rows[-1]
        response.headers["X-Next-Cursor"] = encode_cursor(
            "knowledge_records",
            title=last.title,
            created_at=last.created_at.isoformat(),
            id=str(last.id),
        )
    return rows


@router.post("/{source_id}/records", response_model=KnowledgeRecordOut)
async def create_record(
    source_id: uuid.UUID,
    body: KnowledgeRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    source = await _get_source_or_404(source_id, db)
    _require_user_source(source)
    record = KnowledgeRecord(source_id=source_id, **body.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.patch("/records/{record_id}", response_model=KnowledgeRecordOut)
async def update_record(
    record_id: uuid.UUID,
    body: KnowledgeRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(KnowledgeRecord, record_id)
    if not record:
        raise HTTPException(404, "Knowledge record not found")
    source = await db.get(KnowledgeSource, record.source_id)
    if not source:
        raise HTTPException(404, "Knowledge source not found")
    _require_user_source(source)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/records/{record_id}")
async def delete_record(record_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    record = await db.get(KnowledgeRecord, record_id)
    if not record:
        raise HTTPException(404, "Knowledge record not found")
    source = await db.get(KnowledgeSource, record.source_id)
    if not source:
        raise HTTPException(404, "Knowledge source not found")
    _require_user_source(source)
    await db.delete(record)
    await db.commit()
    return {"ok": True}


# --- Import / upload ---


def normalize_record_import_row(row: dict) -> dict:
    """Map an import row to record fields; extra columns go into meta JSON."""
    normalized = {
        str(k or "").strip().lower().replace(" ", "_"): str(v or "").strip()
        for k, v in row.items()
    }
    title = normalized.pop("title", "")
    body = normalized.pop("body", "")
    extras = {k: v for k, v in normalized.items() if v}
    return {
        "title": title,
        "body": body,
        "meta": json.dumps(extras) if extras else "{}",
    }


@router.post("/{source_id}/records/import")
async def import_records(
    source_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import records from CSV or Excel. Expected columns: title, body.
    Any additional columns are stored in the record's meta JSON."""
    source = await _get_source_or_404(source_id, db)
    _require_user_source(source)

    try:
        content = await read_bounded_upload(file, max_bytes=MAX_KNOWLEDGE_IMPORT_BYTES)
    except UploadTooLarge as error:
        raise HTTPException(
            413, "Knowledge import exceeds the 25 MiB upload limit"
        ) from error
    filename = (file.filename or "").lower()
    try:
        preflight_office_archive(content, filename)
    except OfficeArchiveError as error:
        raise HTTPException(400, str(error)) from error

    rows: list[dict] = []
    if filename.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    elif filename.endswith((".xlsx", ".xls")):
        try:
            import openpyxl
        except ImportError:
            raise HTTPException(
                400,
                "openpyxl is required for Excel imports. Install it with: pip install openpyxl",
            )
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        headers = [
            str(c.value or "").strip().lower().replace(" ", "_")
            for c in next(ws.iter_rows(min_row=1, max_row=1))
        ]
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = str(val) if val is not None else ""
            rows.append(row_dict)
    else:
        raise HTTPException(400, "Unsupported file format. Use .csv or .xlsx")

    created = 0
    skipped = 0
    for row in rows:
        normalized = normalize_record_import_row(row)
        if not normalized["title"] or not normalized["body"]:
            skipped += 1
            continue

        existing = await db.execute(
            select(KnowledgeRecord).where(
                KnowledgeRecord.source_id == source_id,
                KnowledgeRecord.title == normalized["title"],
            )
        )
        if existing.scalars().first():
            skipped += 1
            continue

        db.add(KnowledgeRecord(source_id=source_id, **normalized))
        created += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "total_rows": len(rows)}


@router.post("/{source_id}/files")
async def upload_knowledge_file(
    source_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document; it is converted to Markdown (via MarkItDown) and
    stored as one record. Only the Markdown text is persisted — the original
    file is never written to the file system."""
    source = await _get_source_or_404(source_id, db)
    _require_user_source(source)

    try:
        content = await read_bounded_upload(file, max_bytes=MAX_KNOWLEDGE_UPLOAD_BYTES)
    except UploadTooLarge as error:
        raise HTTPException(
            413, "Knowledge file exceeds the 25 MiB upload limit"
        ) from error
    filename = file.filename or "upload"
    ext = file_extension(filename)

    try:
        markdown = convert_to_markdown(content, filename)
    except MarkdownConversionError as e:
        raise HTTPException(400, str(e))

    record = KnowledgeRecord(
        source_id=source_id,
        title=filename,
        body=markdown[:MAX_KNOWLEDGE_MARKDOWN_CHARS],
        meta=json.dumps(
            {
                "filename": filename,
                "format": ext,
                "original_bytes": len(content),
                "converted_to_markdown": True,
            }
        ),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "record_id": str(record.id),
        "title": record.title,
        "chars": len(record.body),
    }
