import uuid
from datetime import datetime

from app.database import get_db
from app.models import Question
from app.schemas import QuestionOut, QuestionUpdate
from app.services.cursor_pagination import InvalidCursor, decode_cursor, encode_cursor
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/sessions/{session_id}/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
async def list_questions(
    session_id: uuid.UUID,
    response: Response,
    limit: int = Query(200, ge=1, le=1000),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(Question)
        .where(Question.session_id == session_id)
        .order_by(Question.created_at.desc(), Question.id)
    )
    if cursor:
        try:
            marker = decode_cursor(cursor, "questions")
            marker_created = datetime.fromisoformat(str(marker["created_at"]))
            marker_id = uuid.UUID(str(marker["id"]))
        except (InvalidCursor, KeyError, TypeError, ValueError):
            raise HTTPException(400, "Invalid question cursor") from None
        statement = statement.where(
            or_(
                Question.created_at < marker_created,
                and_(Question.created_at == marker_created, Question.id > marker_id),
            )
        )
    result = await db.execute(statement.limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    if has_more and rows:
        last = rows[-1]
        response.headers["X-Next-Cursor"] = encode_cursor(
            "questions", created_at=last.created_at.isoformat(), id=str(last.id)
        )
    return rows


@router.patch("/{question_id}", response_model=QuestionOut)
async def update_question(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    body: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    question = await db.get(Question, question_id)
    if not question or question.session_id != session_id:
        raise HTTPException(404, "Question not found")
    if body.starred is not None:
        question.starred = body.starred
    if body.dismissed is not None:
        question.dismissed = body.dismissed
    if body.vote is not None:
        question.vote = body.vote
    await db.commit()
    await db.refresh(question)
    return question
