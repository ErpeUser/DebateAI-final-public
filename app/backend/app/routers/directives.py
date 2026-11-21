import uuid
from datetime import datetime

from app.database import get_db
from app.models import Directive, Question
from app.schemas import DirectiveCreate, DirectiveOut, DirectiveUpdate
from app.services.cursor_pagination import InvalidCursor, decode_cursor, encode_cursor
from app.services.pii import shield
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/sessions/{session_id}/directives", tags=["directives"])


@router.post("", response_model=DirectiveOut, status_code=201)
async def create_directive(
    session_id: uuid.UUID, body: DirectiveCreate, db: AsyncSession = Depends(get_db)
):
    directive = Directive(
        session_id=session_id, text=await shield.protect_text(db, session_id, body.text)
    )
    db.add(directive)
    await db.commit()
    await db.refresh(directive)
    return directive


@router.get("", response_model=list[DirectiveOut])
async def list_directives(
    session_id: uuid.UUID,
    response: Response,
    limit: int = Query(200, ge=1, le=1000),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(Directive)
        .where(Directive.session_id == session_id)
        .order_by(Directive.created_at, Directive.id)
    )
    if cursor:
        try:
            marker = decode_cursor(cursor, "directives")
            marker_created = datetime.fromisoformat(str(marker["created_at"]))
            marker_id = uuid.UUID(str(marker["id"]))
        except (InvalidCursor, KeyError, TypeError, ValueError):
            raise HTTPException(400, "Invalid directive cursor") from None
        statement = statement.where(
            or_(
                Directive.created_at > marker_created,
                and_(Directive.created_at == marker_created, Directive.id > marker_id),
            )
        )
    result = await db.execute(statement.limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    if has_more and rows:
        last = rows[-1]
        response.headers["X-Next-Cursor"] = encode_cursor(
            "directives", created_at=last.created_at.isoformat(), id=str(last.id)
        )
    return rows


@router.patch("/{directive_id}", response_model=DirectiveOut)
async def update_directive(
    session_id: uuid.UUID,
    directive_id: uuid.UUID,
    body: DirectiveUpdate,
    db: AsyncSession = Depends(get_db),
):
    directive = await db.get(Directive, directive_id)
    if not directive or directive.session_id != session_id:
        raise HTTPException(404, "Directive not found")
    if body.text is not None:
        directive.text = await shield.protect_text(db, session_id, body.text)
    if body.active is not None:
        directive.active = body.active
    await db.commit()
    await db.refresh(directive)
    return directive


@router.delete("/{directive_id}", status_code=204)
async def delete_directive(
    session_id: uuid.UUID, directive_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    directive = await db.get(Directive, directive_id)
    if not directive or directive.session_id != session_id:
        raise HTTPException(404, "Directive not found")
    await db.execute(
        update(Question)
        .where(Question.directive_id == directive_id)
        .values(directive_id=None)
    )
    await db.delete(directive)
    await db.commit()
