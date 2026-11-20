"""Failure/retry coverage for serialized schema startup migrations."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import main


class _FakeLockConnection:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self):
        self.executed = []
        self.closed = False

    async def execute(self, statement):
        self.executed.append(str(statement))

    async def close(self):
        self.closed = True


class _FakeEngine:
    def __init__(self):
        self.connections = []

    async def connect(self):
        connection = _FakeLockConnection()
        self.connections.append(connection)
        return connection


class SchemaMigrationLockRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_runner_releases_lock_and_allows_retry(self):
        engine = _FakeEngine()
        runner = AsyncMock(side_effect=[RuntimeError("migration failed"), None])

        with (
            patch.object(main, "engine", engine),
            patch.object(main, "_run_schema_migrations_unlocked", runner),
        ):
            with self.assertRaisesRegex(RuntimeError, "migration failed"):
                await main._run_schema_migrations()
            await main._run_schema_migrations()

        self.assertEqual(2, runner.await_count)
        self.assertEqual(2, len(engine.connections))
        for connection in engine.connections:
            self.assertTrue(connection.closed)
            self.assertEqual(2, len(connection.executed))
            self.assertIn("pg_advisory_lock", connection.executed[0])
            self.assertIn("pg_advisory_unlock", connection.executed[1])


if __name__ == "__main__":
    unittest.main()
