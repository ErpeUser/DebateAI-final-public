"""Vault cache entries must not outlive or escape their database transaction."""

import importlib.util
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.models import PiiVaultEntry, Speaker
from app.services.pii import shield, vault
from app.services.pii.recognizers import PERSON
from cryptography.fernet import Fernet
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@unittest.skipUnless(
    importlib.util.find_spec("aiosqlite"), "optional aiosqlite test dependency"
)
class VaultTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        key_patch = patch.dict(
            os.environ, {"CREDENTIALS_MASTER_KEY": Fernet.generate_key().decode()}
        )
        key_patch.start()
        self.addCleanup(key_patch.stop)
        vault.reset_keys_for_tests()
        shield.invalidate_roster()
        self.addCleanup(vault.reset_keys_for_tests)
        self.addCleanup(shield.invalidate_roster)
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///" + str(Path(self.directory.name) / "vault.sqlite")
        )

        # Explicit BEGIN is required for SQLite SAVEPOINTs to participate in
        # the outer transaction instead of becoming independently durable.
        @event.listens_for(self.engine.sync_engine, "connect")
        def disable_driver_begin(connection, _record):
            connection.isolation_level = None

        @event.listens_for(self.engine.sync_engine, "begin")
        def begin(connection):
            connection.exec_driver_sql("BEGIN")

        async with self.engine.begin() as connection:
            await connection.run_sync(PiiVaultEntry.__table__.create)
            await connection.run_sync(Speaker.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_id = uuid.uuid4()
        self.settings = shield.ShieldSettings(enabled=True, ner=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_rolled_back_token_is_persisted_by_the_next_writer(self):
        async with self.sessions() as first:
            await vault.token_for(first, self.session_id, PERSON, "Alice Example")
            await first.rollback()
        async with self.sessions() as second:
            token = await vault.token_for(
                second, self.session_id, PERSON, "Alice Example"
            )
            await second.commit()
        vault.forget()
        async with self.sessions() as reader:
            self.assertEqual(
                await vault.reveal_map(reader, self.session_id),
                {token: "Alice Example"},
            )

    async def test_uncommitted_token_and_roster_are_invisible_to_other_sessions(self):
        async with self.sessions() as writer, self.sessions() as reader:
            await vault.token_for(writer, self.session_id, PERSON, "Alice Example")
            roster = await shield.session_roster(writer, self.session_id, self.settings)
            self.assertEqual([entry.value for entry in roster], ["Alice Example"])
            self.assertEqual(await vault.reveal_map(reader, self.session_id), {})
            self.assertEqual(
                await shield.session_roster(reader, self.session_id, self.settings), []
            )
            await reader.rollback()
            await writer.rollback()

    async def test_reused_database_session_drops_rolled_back_vault_and_roster(self):
        async with self.sessions() as db:
            await vault.token_for(db, self.session_id, PERSON, "Alice Example")
            await shield.session_roster(db, self.session_id, self.settings)
            await db.rollback()
            self.assertEqual(await vault.entry_count(db, self.session_id), 0)
            self.assertEqual(
                await shield.session_roster(db, self.session_id, self.settings), []
            )
            await vault.token_for(db, self.session_id, PERSON, "Bob Example")
            await db.commit()
            self.assertEqual(
                await vault.reveal_map(db, self.session_id),
                {"[PERSON_1]": "Bob Example"},
            )

    async def test_caller_savepoint_rollback_drops_token_from_outer_transaction_cache(
        self,
    ):
        async with self.sessions() as db, db.begin():
            savepoint = await db.begin_nested()
            await vault.token_for(db, self.session_id, PERSON, "Alice Example")
            await shield.session_roster(db, self.session_id, self.settings)
            await savepoint.rollback()
            self.assertEqual(await vault.entry_count(db, self.session_id), 0)
            self.assertEqual(
                await shield.session_roster(db, self.session_id, self.settings), []
            )
            token = await vault.token_for(db, self.session_id, PERSON, "Alice Example")
        vault.forget()
        async with self.sessions() as reader:
            self.assertEqual(
                await vault.reveal_map(reader, self.session_id),
                {token: "Alice Example"},
            )

    async def test_committed_token_remains_reusable_without_duplicate_rows(self):
        async with self.sessions() as db:
            token = await vault.token_for(db, self.session_id, PERSON, "Alice Example")
            await db.commit()
            self.assertEqual(
                await vault.token_for(db, self.session_id, PERSON, "alice example"),
                token,
            )
            await db.commit()
            rows = (await db.execute(select(PiiVaultEntry))).scalars().all()
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
