"""PostgreSQL startup-lock integration coverage.

The test deliberately exercises only the schema runner, not the full FastAPI
lifespan (which would start provider probes and background jobs).
"""

import asyncio
import os
import unittest
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import main

POSTGRES_URL = os.environ.get("DEBATEAI_TEST_POSTGRES_URL", "")
RUN_ID = os.environ.get("DEBATEAI_TEST_POSTGRES_RUN_ID", "")
ALLOW_SHARED_CI = os.environ.get("DEBATEAI_TEST_POSTGRES_ALLOW_SHARED", "").lower() == "true"


@unittest.skipUnless(
    POSTGRES_URL and RUN_ID and ALLOW_SHARED_CI,
    "isolated PostgreSQL CI database not configured",
)
class SchemaMigrationPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(POSTGRES_URL)
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
        self.backend_root = main._backend_root()
        config = Config(str(self.backend_root / "alembic.ini"))
        config.attributes["configure_logger"] = False
        config.set_main_option("script_location", str(self.backend_root / "alembic"))
        self.expected_head = ScriptDirectory.from_config(config).get_current_head()

    async def test_parallel_schema_runners_reach_one_head(self):
        with patch.object(main, "engine", self.engine), patch.object(
            main.settings, "DATABASE_URL", POSTGRES_URL
        ):
            await asyncio.gather(
                main._run_schema_migrations(),
                main._run_schema_migrations(),
            )

        async with self.engine.connect() as connection:
            rows = list(
                (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                ).scalars()
            )
        self.assertEqual(rows, [self.expected_head])


if __name__ == "__main__":
    unittest.main()
