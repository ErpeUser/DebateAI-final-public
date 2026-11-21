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


class _UnlockFailingConnection(_FakeLockConnection):
    async def execute(self, statement):
        self.executed.append(str(statement))
        if "pg_advisory_unlock" in str(statement):
            raise RuntimeError("unlock failed")


class _FakeEngine:
    def __init__(self):
        self.connections = []

    async def connect(self):
        connection = _FakeLockConnection()
        self.connections.append(connection)
        return connection


class _UnlockFailingEngine(_FakeEngine):
    async def connect(self):
        connection = _UnlockFailingConnection()
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

    async def test_unlock_failure_still_closes_the_lock_connection(self):
        engine = _UnlockFailingEngine()

        with (
            patch.object(main, "engine", engine),
            patch.object(main, "_run_schema_migrations_unlocked", AsyncMock()),
        ):
            with self.assertRaisesRegex(RuntimeError, "unlock failed"):
                await main._run_schema_migrations()

        self.assertEqual(1, len(engine.connections))
        self.assertTrue(engine.connections[0].closed)


if __name__ == "__main__":
    unittest.main()
