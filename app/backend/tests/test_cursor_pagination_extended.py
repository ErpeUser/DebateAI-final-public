import importlib.util
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException, Response

from app.routers.directives import list_directives
from app.routers.documents import list_documents
from app.routers.knowledge import list_records, list_sources
from app.routers.questions import list_questions
from app.models import (
    Base,
    Directive,
    Document,
    KnowledgeRecord,
    KnowledgeSource,
    Question,
    Session,
)
from app.services.cursor_pagination import decode_cursor
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _rows(count=3, **extra):
    now = datetime(2026, 11, 22, 10, tzinfo=UTC)
    return [
        SimpleNamespace(id=uuid4(), created_at=now, **extra)
        for _ in range(count)
    ]


def _result(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.all.return_value = rows
    return result


class ExtendedCursorHeaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_question_directive_document_and_record_lists_emit_cursors(self):
        session_id = uuid4()
        for route, kind, rows in (
            (list_questions, "questions", _rows()),
            (list_directives, "directives", _rows()),
            (
                list_documents,
                "documents",
                [
                    SimpleNamespace(
                        id=uuid4(),
                        uploaded_at=datetime(2026, 11, 22, 10, i, tzinfo=UTC),
                    )
                    for i in range(3)
                ],
            ),
        ):
            with self.subTest(kind=kind):
                db = AsyncMock()
                db.execute.return_value = _result(rows)
                response = Response()
                page = await route(
                    session_id,
                    response=response,
                    limit=2,
                    db=db,
                )
                self.assertEqual(rows[:2], page)
                marker = decode_cursor(response.headers["X-Next-Cursor"], kind)
                self.assertEqual(str(rows[1].id), marker["id"])

        source_id = uuid4()
        source_rows = [
            SimpleNamespace(
                id=uuid4(),
                name=f"Source {i}",
                source_type="collection",
                description="",
                config="{}",
                active=True,
                created_at=datetime(2026, 11, 22, 10, i, tzinfo=UTC),
                updated_at=None,
            )
            for i in range(3)
        ]
        source_result = MagicMock()
        source_result.all.return_value = [(source, 0) for source in source_rows]
        db = AsyncMock()
        db.execute.return_value = source_result
        response = Response()
        page = await list_sources(response=response, limit=2, db=db)
        self.assertEqual(2, len(page))
        marker = decode_cursor(response.headers["X-Next-Cursor"], "knowledge_sources")
        self.assertEqual(str(source_rows[1].id), marker["id"])

        record_rows = [
            SimpleNamespace(
                id=uuid4(),
                source_id=source_id,
                title=f"Record {i}",
                body="body",
                meta="{}",
                active=True,
                created_at=datetime(2026, 11, 22, 10, i, tzinfo=UTC),
                updated_at=None,
            )
            for i in range(3)
        ]
        db = AsyncMock()
        db.get.return_value = source_rows[0]
        db.execute.return_value = _result(record_rows)
        response = Response()
        page = await list_records(
            source_id,
            response=response,
            limit=2,
            db=db,
        )
        self.assertEqual(record_rows[:2], page)
        marker = decode_cursor(response.headers["X-Next-Cursor"], "knowledge_records")
        self.assertEqual(str(record_rows[1].id), marker["id"])


class ExtendedCursorValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_extended_route_rejects_wrong_endpoint_and_malformed_cursors(self):
        session_id = uuid4()
        source_id = uuid4()
        cases = (
            (list_questions, (session_id,), "Invalid question cursor"),
            (list_directives, (session_id,), "Invalid directive cursor"),
            (list_documents, (session_id,), "Invalid document cursor"),
            (list_sources, (), "Invalid knowledge source cursor"),
            (list_records, (source_id,), "Invalid knowledge record cursor"),
        )
        from app.services.cursor_pagination import encode_cursor

        for route, args, message in cases:
            for cursor in (encode_cursor("sessions", id=str(uuid4())), "not-a-cursor"):
                with self.subTest(message=message, cursor=cursor), self.assertRaisesRegex(
                    HTTPException, message
                ):
                    db = AsyncMock()
                    db.get.return_value = SimpleNamespace(id=source_id)
                    await route(*args, response=Response(), cursor=cursor, db=db)


@unittest.skipUnless(
    importlib.util.find_spec("aiosqlite"), "optional aiosqlite test dependency"
)
class ExtendedCursorIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the actual SQL predicates, tie-breakers, and page boundaries."""

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_id = uuid4()
        self.source_id = uuid4()
        self.at = datetime(2026, 11, 22, 10, tzinfo=UTC)
        async with self.sessions() as db:
            db.add(Session(id=self.session_id, name="Cursor test", state="pre_call"))
            db.add(
                KnowledgeSource(
                    id=self.source_id,
                    name="Record source",
                    source_type="collection",
                    created_at=self.at,
                )
            )
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_all_extended_lists_continue_without_duplicates_on_tie_breakers(self):
        """The second page starts strictly after the encoded (timestamp, id) marker."""
        # Fixed UUIDs make the id tie-breaker deterministic on every database.
        ids = [self.source_id, uuid4(), uuid4()]
        ids.sort()
        async with self.sessions() as db:
            db.add_all(
                [
                    Question(
                        id=row_id,
                        session_id=self.session_id,
                        question=f"question {i}",
                        created_at=self.at,
                    )
                    for i, row_id in enumerate(ids)
                ]
            )
            db.add_all(
                [
                    Directive(
                        id=row_id,
                        session_id=self.session_id,
                        text=f"directive {i}",
                        created_at=self.at,
                    )
                    for i, row_id in enumerate(ids)
                ]
            )
            db.add_all(
                [
                    Document(
                        id=row_id,
                        session_id=self.session_id,
                        filename=f"document-{i}.txt",
                        mime_type="text/plain",
                        uploaded_at=self.at,
                    )
                    for i, row_id in enumerate(ids)
                ]
            )
            db.add_all(
                [
                    KnowledgeSource(
                        id=row_id,
                        name=f"Source {i}",
                        source_type="collection",
                        created_at=self.at,
                    )
                    for i, row_id in enumerate(ids)
                    if row_id != self.source_id
                ]
            )
            db.add_all(
                [
                    KnowledgeRecord(
                        id=row_id,
                        source_id=self.source_id,
                        title="Same title",
                        body=f"record {i}",
                        created_at=self.at,
                    )
                    for i, row_id in enumerate(ids)
                ]
            )
            await db.commit()

        async with self.sessions() as db:
            routes = (
                (list_questions, (self.session_id,), "questions", "created_at"),
                (list_directives, (self.session_id,), "directives", "created_at"),
                (list_documents, (self.session_id,), "documents", "uploaded_at"),
                (list_sources, (), "knowledge_sources", "created_at"),
                (list_records, (self.source_id,), "knowledge_records", "created_at"),
            )
            for route, args, kind, _marker_field in routes:
                with self.subTest(kind=kind):
                    first_response = Response()
                    first = await route(
                        *args,
                        response=first_response,
                        limit=2,
                        db=db,
                    )
                    self.assertEqual(2, len(first))
                    cursor = first_response.headers.get("X-Next-Cursor")
                    self.assertIsNotNone(cursor)
                    marker = decode_cursor(cursor, kind)
                    second_response = Response()
                    second = await route(
                        *args,
                        response=second_response,
                        limit=2,
                        cursor=cursor,
                        db=db,
                    )
                    self.assertEqual(1, len(second))
                    first_ids = {item.id for item in first}
                    second_ids = {item.id for item in second}
                    self.assertTrue(first_ids.isdisjoint(second_ids))
                    self.assertEqual(3, len(first_ids | second_ids))
                    self.assertEqual(ids, [item.id for item in first + second])
                    self.assertEqual(str(first[-1].id), marker["id"])
                    self.assertNotIn("X-Next-Cursor", second_response.headers)


if __name__ == "__main__":
    unittest.main()
