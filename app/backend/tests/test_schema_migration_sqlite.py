"""Real SQLite startup-migration coverage for fresh and legacy databases.

These tests exercise the same async engine and embedded Alembic path used by
the desktop runtime.  The PostgreSQL advisory-lock test remains a separate,
environment-gated integration test; SQLite is the available local runner for
the fresh/legacy schema matrix.
"""

import importlib.util
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from app import main


@unittest.skipUnless(
    importlib.util.find_spec("aiosqlite"), "optional aiosqlite test dependency"
)
class SQLiteSchemaMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, engine, url):
        with (
            patch.object(main, "engine", engine),
            patch.object(main.settings, "DATABASE_URL", url),
        ):
            await main._run_schema_migrations_unlocked()

    @staticmethod
    def _expected_head() -> str:
        backend_root = main._backend_root()
        config = Config(str(backend_root / "alembic.ini"))
        config.set_main_option("script_location", str(backend_root / "alembic"))
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        if len(heads) != 1:
            raise AssertionError(f"expected one Alembic head, got {heads!r}")
        return heads[0]

    async def test_fresh_database_reaches_one_head_and_safe_retry(self):
        with tempfile.TemporaryDirectory(prefix="debateai-migration-") as temp:
            url = "sqlite+aiosqlite:///" + str(Path(temp) / "fresh.sqlite")
            engine = create_async_engine(url)
            self.addAsyncCleanup(engine.dispose)

            await self._run(engine, url)
            # A second startup against the same versioned database is the
            # retry path: no migration should rerun or create duplicate state.
            await self._run(engine, url)

            async with engine.connect() as connection:
                tables = await connection.run_sync(
                    lambda sync: set(inspect(sync).get_table_names())
                )
                versions = list(
                    (
                        await connection.execute(
                            text("SELECT version_num FROM alembic_version")
                        )
                    ).scalars()
                )
                indexes = await connection.run_sync(
                    lambda sync: {
                        item["name"]
                        for item in inspect(sync).get_indexes("questions")
                    }
                )

            self.assertEqual([self._expected_head()], versions)
            self.assertIn("questions", tables)
            self.assertIn("knowledge_records", tables)
            self.assertIn("ix_questions_session_created_id", indexes)

    async def test_unversioned_legacy_duplicates_are_resequenced_and_retried(self):
        with tempfile.TemporaryDirectory(prefix="debateai-legacy-") as temp:
            url = "sqlite+aiosqlite:///" + str(Path(temp) / "legacy.sqlite")
            engine = create_async_engine(url)
            self.addAsyncCleanup(engine.dispose)
            session_id = uuid.uuid4().hex

            # This is the smallest shape of an old create_all database that
            # reaches the current adoption path.  It intentionally lacks the
            # alembic_version table and contains duplicate transcript sequence
            # values that revision 029 must repair before adding its constraint.
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "CREATE TABLE sessions ("
                        "id CHAR(32) PRIMARY KEY, name VARCHAR(255), "
                        "state VARCHAR(20), created_at DATETIME)"
                    )
                )
                await connection.execute(
                    text(
                        "CREATE TABLE transcript_entries ("
                        "id CHAR(32) PRIMARY KEY, session_id CHAR(32), "
                        "text TEXT, timestamp DATETIME, sequence INTEGER)"
                    )
                )
                await connection.execute(
                    text(
                        "INSERT INTO sessions (id, name, state, created_at) "
                        "VALUES (:id, 'legacy', 'completed', '2026-01-01')"
                    ),
                    {"id": session_id},
                )
                for value in range(2):
                    await connection.execute(
                        text(
                            "INSERT INTO transcript_entries "
                            "(id, session_id, text, timestamp, sequence) "
                            "VALUES (:id, :session_id, :text, '2026-01-01', 1)"
                        ),
                        {
                            "id": uuid.uuid4().hex,
                            "session_id": session_id,
                            "text": f"legacy row {value}",
                        },
                    )

            await self._run(engine, url)
            # Startup can be retried after an interrupted legacy adoption; the
            # already-versioned database must remain a no-op at the same head.
            await self._run(engine, url)

            async with engine.connect() as connection:
                versions = list(
                    (
                        await connection.execute(
                            text("SELECT version_num FROM alembic_version")
                        )
                    ).scalars()
                )
                sequences = list(
                    (
                        await connection.execute(
                            text(
                                "SELECT sequence FROM transcript_entries "
                                "WHERE session_id=:session_id ORDER BY sequence"
                            ),
                            {"session_id": session_id},
                        )
                    ).scalars()
                )
                constraints = await connection.run_sync(
                    lambda sync: inspect(sync).get_unique_constraints(
                        "transcript_entries"
                    )
                )

            self.assertEqual([self._expected_head()], versions)
            self.assertEqual([1, 2], sequences)
            self.assertIn(
                "uq_transcript_entries_session_sequence",
                {item["name"] for item in constraints},
            )

    async def test_failed_legacy_tail_can_be_repaired_and_retried(self):
        with tempfile.TemporaryDirectory(prefix="debateai-failed-migration-") as temp:
            url = "sqlite+aiosqlite:///" + str(Path(temp) / "failed.sqlite")
            engine = create_async_engine(url)
            self.addAsyncCleanup(engine.dispose)
            session_id = uuid.uuid4().hex

            # Omit sessions.created_at to force the real 033 index migration
            # to fail after the legacy adoption has stamped revision 028.
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "CREATE TABLE sessions ("
                        "id CHAR(32) PRIMARY KEY, name VARCHAR(255), "
                        "state VARCHAR(20))"
                    )
                )
                await connection.execute(
                    text(
                        "CREATE TABLE transcript_entries ("
                        "id CHAR(32) PRIMARY KEY, session_id CHAR(32), "
                        "text TEXT, timestamp DATETIME, sequence INTEGER)"
                    )
                )
                await connection.execute(
                    text(
                        "INSERT INTO sessions (id, name, state) "
                        "VALUES (:id, 'legacy', 'completed')"
                    ),
                    {"id": session_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO transcript_entries "
                        "(id, session_id, text, timestamp, sequence) "
                        "VALUES (:id, :session_id, 'legacy row', '2026-01-01', 1)"
                    ),
                    {"id": uuid.uuid4().hex, "session_id": session_id},
                )

            with self.assertRaises(OperationalError):
                await self._run(engine, url)

            async with engine.begin() as connection:
                version = (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                ).scalar_one()
                temp_tables = await connection.run_sync(
                    lambda sync: {
                        item
                        for item in inspect(sync).get_table_names()
                        if item.startswith("_alembic_tmp_")
                    }
                )
                await connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN created_at DATETIME")
                )

            self.assertEqual("028_debate_claim_records", version)
            self.assertIn("_alembic_tmp_transcript_entries", temp_tables)

            # Repair the legacy shape and retry the same startup operation.
            # Revision 029 removes the stale batch table, while revision 033
            # skips any indexes left behind by a partial attempt.
            await self._run(engine, url)

            async with engine.connect() as connection:
                versions = list(
                    (
                        await connection.execute(
                            text("SELECT version_num FROM alembic_version")
                        )
                    ).scalars()
                )
                temp_tables = await connection.run_sync(
                    lambda sync: {
                        item
                        for item in inspect(sync).get_table_names()
                        if item.startswith("_alembic_tmp_")
                    }
                )

            self.assertEqual([self._expected_head()], versions)
            self.assertEqual(set(), temp_tables)


if __name__ == "__main__":
    unittest.main()
