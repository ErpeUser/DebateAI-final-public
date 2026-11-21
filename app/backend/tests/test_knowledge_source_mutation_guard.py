import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models import KnowledgeSource
from app.routers.knowledge import update_source
from fastapi import HTTPException


class FakeDB:
    def __init__(self, source):
        self.source = source
        self.commits = 0

    async def get(self, model, _key):
        if model is KnowledgeSource:
            return self.source
        raise AssertionError(model)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _source):
        return None

    async def scalar(self, _query):
        return 2


class KnowledgeSourceMutationGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_rejects_builtin_offerings_source(self):
        source = SimpleNamespace(source_type="offerings", updated_at=None)
        db = FakeDB(source)
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "Changed"})
        with self.assertRaises(HTTPException) as error:
            await update_source(uuid.uuid4(), body, db)
        self.assertEqual(400, error.exception.status_code)
        self.assertEqual(0, db.commits)

    async def test_update_allows_user_managed_source(self):
        source = KnowledgeSource(
            id=uuid.uuid4(),
            source_type="files",
            name="Before",
            description="",
            config="{}",
            active=True,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        db = FakeDB(source)
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "After"})
        result = await update_source(uuid.uuid4(), body, db)
        self.assertEqual(source.id, result.id)
        self.assertEqual("After", result.name)
        self.assertEqual(2, result.record_count)
        self.assertEqual("After", source.name)
        self.assertEqual(1, db.commits)

    async def test_update_rejects_missing_source(self):
        db = FakeDB(None)
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"name": "Changed"})
        with self.assertRaises(HTTPException) as error:
            await update_source(uuid.uuid4(), body, db)
        self.assertEqual(404, error.exception.status_code)


if __name__ == "__main__":
    unittest.main()
