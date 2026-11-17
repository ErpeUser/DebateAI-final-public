"""Call actual route functions through an isolated ASGI app, never app.main."""
import io
import asyncio
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, UploadFile
from httpx import ASGITransport, AsyncClient

from app.routers import documents, imports, knowledge, offerings
from tests.test_office_archive import DTD, office_bytes, repack


class OfficeHTTPRejectionTests(unittest.TestCase):
    def check_route(self, route, content, filename, *, local=False):
        db = MagicMock()
        db.get = AsyncMock(return_value=SimpleNamespace(source_type="files", id=uuid.uuid4()))
        db.execute = AsyncMock(side_effect=AssertionError("unexpected DB query"))
        db.add.side_effect = AssertionError("unsafe input reached DB mutation")
        db.commit = AsyncMock(side_effect=AssertionError("unsafe input reached commit"))
        app = FastAPI()

        @app.post("/synthetic")
        async def upload(file: UploadFile):
            if route is offerings.import_offerings:
                return await route(file=file, db=db)
            parameter = "source_id" if route is knowledge.upload_knowledge_file else "session_id"
            return await route(**{parameter: uuid.uuid4()}, file=file, db=db)

        protect = AsyncMock(side_effect=AssertionError("unsafe input reached PII writes"))
        with patch.object(documents, "is_local_only", AsyncMock(return_value=local)), patch.object(documents.shield, "get_settings", AsyncMock(return_value=SimpleNamespace(enabled=False))), patch.object(documents.shield, "protect_text", protect), patch.object(documents, "upload_and_summarize", AsyncMock(side_effect=AssertionError("unsafe upload reached provider"))):
            async def request():
                async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://synthetic.invalid") as client:
                    return await client.post("/synthetic", files={"file": (filename, content)})
            response = asyncio.run(request())
        self.assertEqual(400, response.status_code, response.text[:500])
        self.assertLess(len(response.content), 1000)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
        protect.assert_not_awaited()

    def test_document_rejects_before_local_or_remote_processing(self):
        unsafe = repack(office_bytes(), [("unused.xml", DTD)])
        for local in (True, False):
            with self.subTest(local=local):
                self.check_route(documents.upload_document, unsafe, "synthetic.docx", local=local)

    def test_transcript_rejects_before_pii_and_db_writes(self):
        self.check_route(imports.import_transcript, repack(office_bytes(), [("unused.xml", DTD)]), "synthetic.docx")

    def test_direct_offerings_rejects_before_db_writes(self):
        self.check_route(offerings.import_offerings, repack(office_bytes("xlsx"), [("unused.xml", DTD)]), "synthetic.xlsx")

    def test_knowledge_conversions_reject_before_db_writes(self):
        # The production knowledge route already maps MarkdownConversionError to 400.
        for kind in ("docx", "xlsx", "pptx"):
            with self.subTest(kind=kind):
                self.check_route(knowledge.upload_knowledge_file, repack(office_bytes(kind), [("unused.xml", DTD)]), "synthetic." + kind)

    def test_corrupt_office_files_are_400(self):
        for route, filename in ((documents.upload_document, "bad.docx"), (imports.import_transcript, "bad.docx"), (offerings.import_offerings, "bad.xlsx")):
            with self.subTest(route=route.__name__):
                self.check_route(route, b"PK\x03\x04broken", filename, local=True)

    def test_real_xlsx_offerings_still_imports(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
        db.commit = AsyncMock()
        result = asyncio.run(offerings.import_offerings(file=UploadFile(filename="ordinary.xlsx", file=io.BytesIO(office_bytes("xlsx"))), db=db))
        self.assertEqual({"created": 1, "skipped": 0, "total_rows": 1}, result)
        self.assertEqual("Synthetic product", db.add.call_args.args[0].product_name)


if __name__ == "__main__":
    unittest.main()
