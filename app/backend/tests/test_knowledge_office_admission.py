"""Synthetic HTTP regressions for the separate knowledge-record Excel route."""

import io
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.database import get_db
from app.routers import knowledge
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from tests.test_office_archive import DTD, repack


def workbook_bytes():
    output = io.BytesIO()
    book = Workbook()
    book.active.append(["title", "body"])
    book.active.append(["Synthetic title", "Synthetic body"])
    book.save(output)
    book.close()
    return output.getvalue()


class KnowledgeOfficeAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, body, filename):
        source_id = uuid.uuid4()
        rows = []
        db = MagicMock()
        db.get = AsyncMock(
            return_value=SimpleNamespace(id=source_id, source_type="files")
        )
        db.execute = AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(first=lambda: None)
            )
        )
        db.add = rows.append
        db.commit = AsyncMock()
        app = FastAPI()
        app.include_router(knowledge.router)
        app.dependency_overrides[get_db] = lambda: db
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://synthetic.invalid",
        ) as client:
            response = await client.post(
                f"/api/knowledge/{source_id}/records/import",
                files={"file": (filename, body)},
            )
        return response, rows, db

    async def test_ignored_entity_part_rejected_before_record_creation(self):
        body = repack(workbook_bytes(), [("unused.xml", DTD)])
        for suffix in ("xlsx", "xls", "csv"):
            with self.subTest(suffix=suffix):
                response, rows, db = await self.request(body, "synthetic." + suffix)
                self.assertEqual(400, response.status_code, response.text[:500])
                self.assertEqual([], rows)
                self.assertEqual(0, db.commit.await_count)
                self.assertEqual(0, db.execute.await_count)
                self.assertLess(len(response.content), 1000)

    async def test_malformed_xlsx_is_client_error_not_server_error(self):
        response, rows, db = await self.request(b"PK\x03\x04broken", "broken.xlsx")
        self.assertEqual(400, response.status_code)
        self.assertEqual([], rows)
        self.assertEqual(0, db.commit.await_count)

    async def test_regular_workbook_keeps_title_body_and_commit(self):
        response, rows, db = await self.request(workbook_bytes(), "ordinary.xlsx")
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual({"created": 1, "skipped": 0, "total_rows": 1}, response.json())
        self.assertEqual(
            [("Synthetic title", "Synthetic body")], [(r.title, r.body) for r in rows]
        )
        self.assertEqual(1, db.commit.await_count)

    async def test_regular_csv_still_imports(self):
        response, rows, db = await self.request(
            b"title,body\nSynthetic title,Synthetic body\n", "ordinary.csv"
        )
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(1, len(rows))
        self.assertEqual(1, db.commit.await_count)


if __name__ == "__main__":
    unittest.main()
