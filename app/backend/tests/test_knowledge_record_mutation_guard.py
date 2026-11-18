import unittest
import uuid
from types import SimpleNamespace

from fastapi import HTTPException

from app.models import KnowledgeRecord, KnowledgeSource
from app.routers.knowledge import delete_record, update_record


class FakeDB:
    def __init__(self, record, source):
        self.record = record
        self.source = source
        self.deleted = None
        self.commits = 0

    async def get(self, model, _key):
        if model is KnowledgeRecord:
            return self.record
        if model is KnowledgeSource:
            return self.source
        raise AssertionError(model)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _record):
        return None

    async def delete(self, record):
        self.deleted = record


def _record():
    return SimpleNamespace(
        source_id=uuid.uuid4(),
        title="Managed item",
        body="Before",
        updated_at=None,
    )


class KnowledgeRecordMutationGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_rejects_builtin_offerings_source(self):
        db = FakeDB(_record(), SimpleNamespace(source_type="offerings"))
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"body": "After"})
        with self.assertRaises(HTTPException) as error:
            await update_record(uuid.uuid4(), body, db)
        self.assertEqual(400, error.exception.status_code)
        self.assertEqual(0, db.commits)

    async def test_delete_rejects_builtin_offerings_source(self):
        db = FakeDB(_record(), SimpleNamespace(source_type="offerings"))
        with self.assertRaises(HTTPException) as error:
            await delete_record(uuid.uuid4(), db)
        self.assertEqual(400, error.exception.status_code)
        self.assertIsNone(db.deleted)

    async def test_update_and_delete_allow_user_managed_sources(self):
        record = _record()
        db = FakeDB(record, SimpleNamespace(source_type="files"))
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"body": "After"})
        updated = await update_record(uuid.uuid4(), body, db)
        self.assertIs(updated, record)
        self.assertEqual("After", record.body)
        self.assertEqual(1, db.commits)

        await delete_record(uuid.uuid4(), db)
        self.assertIs(record, db.deleted)
        self.assertEqual(2, db.commits)

    async def test_unknown_source_is_not_mutable(self):
        db = FakeDB(_record(), None)
        body = SimpleNamespace(model_dump=lambda exclude_unset: {"body": "After"})
        with self.assertRaises(HTTPException) as error:
            await update_record(uuid.uuid4(), body, db)
        self.assertEqual(404, error.exception.status_code)


if __name__ == "__main__":
    unittest.main()
