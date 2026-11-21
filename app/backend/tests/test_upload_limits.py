import ast
import unittest
from pathlib import Path

from app.services.upload_limits import UploadTooLarge, read_bounded_upload


class FakeUpload:
    def __init__(self, content: bytes):
        self.content = content
        self.requested = None

    async def read(self, size: int = -1) -> bytes:
        self.requested = size
        return self.content if size < 0 else self.content[:size]


class BoundedUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_exact_boundary_with_one_sentinel_byte(self):
        upload = FakeUpload(b"12345678")
        self.assertEqual(b"12345678", await read_bounded_upload(upload, max_bytes=8))
        self.assertEqual(9, upload.requested)

    async def test_rejects_content_above_limit(self):
        upload = FakeUpload(b"123456789")
        with self.assertRaises(UploadTooLarge) as context:
            await read_bounded_upload(upload, max_bytes=8)
        self.assertEqual(8, context.exception.max_bytes)
        self.assertEqual(9, upload.requested)

    async def test_allows_empty_upload_for_format_specific_validation(self):
        upload = FakeUpload(b"")
        self.assertEqual(b"", await read_bounded_upload(upload, max_bytes=8))


class BoundedUploadRouteContractTests(unittest.TestCase):
    def test_file_import_routes_do_not_use_unbounded_reads(self):
        backend = Path(__file__).resolve().parents[1]
        routes = {
            "app/routers/dossiers.py": 1,
            "app/routers/knowledge.py": 2,
            "app/routers/offerings.py": 1,
        }
        for relative, expected_calls in routes.items():
            source = (backend / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn("content = await file.read()", source)
                self.assertEqual(
                    expected_calls, source.count("read_bounded_upload(file")
                )
                ast.parse(source)

    def test_knowledge_markdown_output_is_bounded_before_persistence(self):
        source = (
            Path(__file__).resolve().parents[1] / "app/routers/knowledge.py"
        ).read_text(encoding="utf-8")
        self.assertIn("MAX_KNOWLEDGE_MARKDOWN_CHARS = 100_000", source)
        self.assertIn("body=markdown[:MAX_KNOWLEDGE_MARKDOWN_CHARS]", source)


if __name__ == "__main__":
    unittest.main()
