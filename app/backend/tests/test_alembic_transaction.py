"""CLI migrations must commit their DDL prelude and migration as one unit."""

import runpy
import tempfile
import unittest
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine


class MigrationTransactionTests(unittest.TestCase):
    def _run(self, fail):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
            engine = create_engine(
                "sqlite:///" + str(Path(directory) / "migration.sqlite")
            )
            cleanup.callback(engine.dispose)
            with engine.begin() as connection:
                connection.exec_driver_sql("CREATE TABLE proof (value TEXT NOT NULL)")

            class PreludeConnection:
                dialect = SimpleNamespace(name="postgresql")

                def __init__(self, connection):
                    self.connection = connection

                def exec_driver_sql(self, sql):
                    # Preserve real autobegin while adapting PostgreSQL ALTER
                    # syntax to the isolated SQLite transaction test.
                    return self.connection.exec_driver_sql(
                        "SELECT 1" if "ALTER COLUMN" in sql else sql
                    )

            class AsyncConnection:
                def __init__(self, connection):
                    self.connection = connection

                async def run_sync(self, callback):
                    callback(PreludeConnection(self.connection))

            class EngineAdapter:
                @asynccontextmanager
                async def connect(self):
                    with engine.connect() as connection:
                        yield AsyncConnection(connection)

                @asynccontextmanager
                async def begin(self):
                    with engine.begin() as connection:
                        yield AsyncConnection(connection)

                async def dispose(self):
                    pass

            class Environment:
                config = SimpleNamespace(
                    config_file_name=None,
                    config_ini_section="alembic",
                    get_section=lambda *_: {},
                    set_main_option=lambda *_: None,
                )

                def is_offline_mode(self):
                    return False

                def configure(self, connection, target_metadata):
                    self.connection = connection.connection
                    self.migration = MigrationContext.configure(
                        self.connection, opts={"transactional_ddl": True}
                    )

                def begin_transaction(self):
                    return self.migration.begin_transaction()

                def run_migrations(self):
                    self.connection.exec_driver_sql(
                        "INSERT INTO proof VALUES ('migrated')"
                    )
                    if fail:
                        raise RuntimeError("migration failed")

            with (
                patch("alembic.context", Environment()),
                patch(
                    "sqlalchemy.ext.asyncio.async_engine_from_config",
                    return_value=EngineAdapter(),
                ),
            ):
                env_path = Path(__file__).resolve().parents[1] / "alembic" / "env.py"
                if fail:
                    with self.assertRaisesRegex(RuntimeError, "migration failed"):
                        runpy.run_path(str(env_path))
                else:
                    runpy.run_path(str(env_path))
            with engine.connect() as connection:
                return connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM proof"
                ).scalar_one()

    def test_successful_migration_survives_connection_close(self):
        self.assertEqual(self._run(False), 1)

    def test_failed_migration_rolls_back_its_changes(self):
        self.assertEqual(self._run(True), 0)


if __name__ == "__main__":
    unittest.main()
