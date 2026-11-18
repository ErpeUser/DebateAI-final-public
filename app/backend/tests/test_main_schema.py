import importlib.util
import logging
import os
import runpy
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from app.main import (
    _add_missing_columns,
    _backend_root,
    _cleanup_orphan_audio,
    _recover_interrupted_audio,
    _schema_startup_action,
)
from app.models import SessionSynthesis, SpeakerRevalidationBatch
from app.schemas import RevalidationBatchOut, SessionSynthesisOut


class FakeInspector:
    def get_table_names(self):
        return ["call_segments"]

    def get_columns(self, table):
        self.assert_call_segments(table)
        return [{"name": "audio_path"}]

    @staticmethod
    def assert_call_segments(table):
        if table != "call_segments":
            raise AssertionError(table)


class FakeRevalidationInspector:
    def get_table_names(self):
        return [
            "sessions",
            "questions",
            "session_syntheses",
            "speaker_revalidation_batches",
        ]

    def get_columns(self, table):
        existing = {
            "sessions": {"speaker_context_dirty", "speaker_context_enhanced_at"},
            "questions": {"enhanced"},
            "session_syntheses": {"status"},
            "speaker_revalidation_batches": {"status"},
        }
        return [{"name": name} for name in existing[table]]


class FakeSyncConnection:
    def __init__(self):
        self.executed = []

    def execute(self, statement):
        self.executed.append(str(statement))


class FakeAsyncConnection:
    def __init__(self):
        self.sync = FakeSyncConnection()

    async def run_sync(self, callback):
        callback(self.sync)


class FakeCleanupConnection:
    async def execute(self, statement):
        del statement
        return [
            ("audio/session/segment_1_mic.wav", "audio/session/segment_1_sys.wav"),
            (None, "audio/session/segment_2_sys.wav"),
        ]


class FakeRecoveryConnection:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    async def execute(self, statement, params=None):
        if params is None:
            return self.rows
        self.updates.append((str(statement), params))
        return None


class StartupSchemaPatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovers_fsynced_open_segment_and_repairs_wav_before_orphan_cleanup(self):
        session_id = "session-1"
        row = SimpleNamespace(
            id="segment-1",
            session_id=session_id,
            segment_number=3,
            audio_path=None,
            mic_audio_path=None,
            system_audio_path=None,
        )
        connection = FakeRecoveryConnection([row])
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch("app.main.audio_file_path") as file_path,
                patch("app.main.repair_wav_file", return_value=True) as repair,
            ):
                root = Path(temp) / "audio" / "session-1"
                mixed = root / "segment_3.wav"
                mixed.parent.mkdir(parents=True, exist_ok=True)
                mixed.write_bytes(b"RIFF" + b"\x00" * 40)
                file_path.side_effect = lambda _session, _number, track: {
                    "mixed": mixed,
                    "mic": root / "segment_3_mic.wav",
                    "sys": root / "segment_3_sys.wav",
                }[track]
                await _recover_interrupted_audio(connection)

        repair.assert_called_once_with(mixed)
        self.assertEqual(1, len(connection.updates))
        statement, params = connection.updates[0]
        self.assertIn("ended_at=CURRENT_TIMESTAMP", statement)
        self.assertEqual("segment-1", params["id"])
        self.assertEqual("audio/session-1/segment_3.wav", params["audio_path"])

    async def test_adds_both_track_provenance_columns_to_existing_database(self):
        connection = FakeAsyncConnection()

        with patch("sqlalchemy.inspect", return_value=FakeInspector()):
            await _add_missing_columns(connection)

        sql = "\n".join(connection.sync.executed)
        self.assertIn("ADD COLUMN mic_audio_path VARCHAR(500)", sql)
        self.assertIn("ADD COLUMN system_audio_path VARCHAR(500)", sql)

    async def test_startup_cleanup_preserves_database_referenced_tracks(self):
        with patch("app.main.cleanup_orphan_track_audio", return_value=0) as cleanup:
            await _cleanup_orphan_audio(FakeCleanupConnection())

        cleanup.assert_called_once_with(
            {
                "audio/session/segment_1_mic.wav",
                "audio/session/segment_1_sys.wav",
                "audio/session/segment_2_sys.wav",
            }
        )

    async def test_adds_revalidation_revision_columns_to_existing_database(self):
        connection = FakeAsyncConnection()

        with patch("sqlalchemy.inspect", return_value=FakeRevalidationInspector()):
            await _add_missing_columns(connection)

        sql = "\n".join(connection.sync.executed)
        self.assertIn(
            "ADD COLUMN speaker_context_version INTEGER NOT NULL DEFAULT 0",
            sql,
        )
        self.assertIn("ADD COLUMN speaker_mapping_revision_id UUID", sql)
        self.assertEqual(2, sql.count("ADD COLUMN speaker_mapping_revision_id UUID"))

    async def test_adds_signal_history_to_existing_database(self):
        connection = FakeAsyncConnection()

        with patch("sqlalchemy.inspect", return_value=FakeRevalidationInspector()):
            await _add_missing_columns(connection)

        sql = "\n".join(connection.sync.executed)
        self.assertIn(
            "ADD COLUMN signal_history JSON NOT NULL DEFAULT '[]'",
            sql,
        )

    async def test_adds_revalidation_model_columns_to_existing_database(self):
        connection = FakeAsyncConnection()

        with patch("sqlalchemy.inspect", return_value=FakeRevalidationInspector()):
            await _add_missing_columns(connection)

        sql = "\n".join(connection.sync.executed)
        self.assertIn("ADD COLUMN requested_model_id VARCHAR(160)", sql)
        self.assertIn("ADD COLUMN model_id VARCHAR(160)", sql)


class MigrationPathTests(unittest.TestCase):
    def test_empty_database_bootstraps_from_current_metadata(self):
        self.assertEqual("bootstrap", _schema_startup_action(set()))

    def test_existing_unversioned_database_is_adopted(self):
        self.assertEqual(
            "adopt",
            _schema_startup_action({"sessions", "transcript_entries"}),
        )

    def test_versioned_database_runs_pending_migrations(self):
        self.assertEqual(
            "upgrade",
            _schema_startup_action({"sessions", "alembic_version"}),
        )

    def test_backend_root_is_the_parent_of_the_app_package(self):
        if os.name != "nt":
            self.skipTest("Packaged path assertion is Windows-specific")
        module_path = Path("C:/bundle/_internal/app/main.py")

        self.assertEqual(
            Path("C:/bundle/_internal"),
            _backend_root(module_path),
        )

    def test_embedded_migration_preserves_host_process_logging(self):
        import alembic

        class TrackingHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.was_closed = False

            def close(self):
                self.was_closed = True
                super().close()

        backend_root = Path(__file__).resolve().parents[1]
        fake_context = SimpleNamespace(
            config=SimpleNamespace(
                attributes={"configure_logger": False},
                config_file_name=str(backend_root / "alembic.ini"),
                get_main_option=lambda _name: "sqlite://",
            ),
            is_offline_mode=lambda: True,
            configure=lambda **_kwargs: None,
            begin_transaction=lambda: nullcontext(),
            run_migrations=lambda: None,
        )
        root = logging.getLogger()
        original_handlers = list(root.handlers)
        original_level = root.level
        handler = TrackingHandler()
        root.handlers = [handler]
        try:
            with patch.object(alembic, "context", fake_context):
                runpy.run_path(str(backend_root / "alembic" / "env.py"))

            self.assertEqual([handler], root.handlers)
            self.assertFalse(handler.was_closed)
        finally:
            for current in root.handlers:
                if current not in original_handlers:
                    current.close()
            root.handlers = original_handlers
            root.setLevel(original_level)


class SessionSynthesisSchemaTests(unittest.TestCase):
    def test_signal_history_is_exposed_for_opt_in_reads(self):
        self.assertIn("signal_history", SessionSynthesis.__table__.columns)
        self.assertIn("signal_history", SessionSynthesisOut.model_fields)
        self.assertIn("signal_history_count", SessionSynthesisOut.model_fields)


class SpeakerRevalidationModelSchemaTests(unittest.TestCase):
    def test_batch_model_ids_are_nullable_and_exposed(self):
        requested = SpeakerRevalidationBatch.__table__.columns["requested_model_id"]
        actual = SpeakerRevalidationBatch.__table__.columns["model_id"]

        self.assertTrue(requested.nullable)
        self.assertTrue(actual.nullable)
        self.assertEqual(160, requested.type.length)
        self.assertEqual(160, actual.type.length)
        self.assertIn("requested_model_id", RevalidationBatchOut.model_fields)
        self.assertIn("model_id", RevalidationBatchOut.model_fields)


class AlembicTrackPathRevisionTests(unittest.TestCase):
    def test_revision_016_upgrade_and_downgrade(self):
        path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "016_add_call_segment_track_paths.py"
        )
        spec = importlib.util.spec_from_file_location("alembic_revision_016", path)
        self.assertIsNotNone(spec)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()

        revision.upgrade()

        added = revision.op.add_column.call_args_list
        self.assertEqual(
            ["mic_audio_path", "system_audio_path"],
            [call.args[1].name for call in added],
        )
        self.assertEqual([500, 500], [call.args[1].type.length for call in added])
        self.assertEqual([True, True], [call.args[1].nullable for call in added])

        revision.downgrade()

        self.assertEqual(
            [
                (("call_segments", "system_audio_path"), {}),
                (("call_segments", "mic_audio_path"), {}),
            ],
            [(call.args, call.kwargs) for call in revision.op.drop_column.call_args_list],
        )


class AlembicSpeakerRevalidationRevisionTests(unittest.TestCase):
    def test_revision_018_upgrade_and_downgrade(self):
        path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "018_add_speaker_revalidation.py"
        )
        spec = importlib.util.spec_from_file_location("alembic_revision_018", path)
        self.assertIsNotNone(spec)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()

        revision.upgrade()

        self.assertEqual(
            [
                "speaker_mapping_revisions",
                "speaker_revalidation_runs",
                "speaker_revalidation_batches",
            ],
            [call.args[0] for call in revision.op.create_table.call_args_list],
        )
        self.assertEqual(
            [
                ("sessions", "speaker_context_version"),
                ("questions", "speaker_mapping_revision_id"),
                ("session_syntheses", "speaker_mapping_revision_id"),
            ],
            [
                (call.args[0], call.args[1].name)
                for call in revision.op.add_column.call_args_list
            ],
        )

        revision.downgrade()

        self.assertEqual(
            [
                "speaker_revalidation_batches",
                "speaker_revalidation_runs",
                "speaker_mapping_revisions",
            ],
            [call.args[0] for call in revision.op.drop_table.call_args_list],
        )
        self.assertEqual(
            [
                ("session_syntheses", "speaker_mapping_revision_id"),
                ("questions", "speaker_mapping_revision_id"),
                ("sessions", "speaker_context_version"),
            ],
            [call.args for call in revision.op.drop_column.call_args_list],
        )


class AlembicSignalHistoryRevisionTests(unittest.TestCase):
    def test_revision_021_upgrade_and_downgrade(self):
        path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "021_add_signal_history.py"
        )
        spec = importlib.util.spec_from_file_location("alembic_revision_021", path)
        self.assertIsNotNone(spec)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()

        self.assertEqual("021_signal_history", revision.revision)
        self.assertEqual("020_endpoint_tombstones", revision.down_revision)

        revision.upgrade()

        added = revision.op.add_column.call_args
        self.assertEqual("session_syntheses", added.args[0])
        column = added.args[1]
        self.assertEqual("signal_history", column.name)
        self.assertFalse(column.nullable)
        self.assertEqual("[]", str(column.server_default.arg))

        revision.downgrade()

        revision.op.drop_column.assert_called_once_with(
            "session_syntheses",
            "signal_history",
        )


class AlembicRevalidationModelsRevisionTests(unittest.TestCase):
    def test_revision_023_upgrade_and_downgrade(self):
        path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "023_record_revalidation_models.py"
        )
        spec = importlib.util.spec_from_file_location("alembic_revision_023", path)
        self.assertIsNotNone(spec)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()

        self.assertEqual("023_revalidation_models", revision.revision)
        self.assertEqual("022_document_summaries", revision.down_revision)

        revision.upgrade()

        added = revision.op.add_column.call_args_list
        self.assertEqual(
            ["requested_model_id", "model_id"],
            [call.args[1].name for call in added],
        )
        self.assertEqual([160, 160], [call.args[1].type.length for call in added])
        self.assertEqual([True, True], [call.args[1].nullable for call in added])

        revision.downgrade()

        self.assertEqual(
            [
                ("speaker_revalidation_batches", "model_id"),
                ("speaker_revalidation_batches", "requested_model_id"),
            ],
            [call.args for call in revision.op.drop_column.call_args_list],
        )


class ProvisionalTranscriptMigrationTests(unittest.TestCase):
    def _revision(self):
        path = Path(__file__).parents[1] / "alembic" / "versions" / "030_provisional_transcript_revisions.py"
        spec = importlib.util.spec_from_file_location("alembic_revision_030", path)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()
        return revision

    def test_revision_030_skips_table_created_during_legacy_adoption(self):
        revision = self._revision()
        inspector = MagicMock()
        inspector.get_table_names.return_value = ["provisional_transcript_revisions"]

        with patch.object(revision.sa, "inspect", return_value=inspector):
            revision.upgrade()

        revision.op.create_table.assert_not_called()

    def test_revision_030_creates_table_and_index_for_versioned_upgrade(self):
        revision = self._revision()
        inspector = MagicMock()
        inspector.get_table_names.return_value = []

        with patch.object(revision.sa, "inspect", return_value=inspector):
            revision.upgrade()

        revision.op.create_table.assert_called_once()
        revision.op.create_index.assert_called_once()


class TranscriptRevisionMigrationTests(unittest.TestCase):
    def _revision(self):
        path = Path(__file__).parents[1] / "alembic" / "versions" / "031_transcript_entry_revisions.py"
        spec = importlib.util.spec_from_file_location("alembic_revision_031", path)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        revision.op = MagicMock()
        return revision

    def test_revision_031_adds_manual_marker_history_and_indexes(self):
        revision = self._revision()
        inspector = MagicMock()
        inspector.get_table_names.return_value = []
        inspector.get_columns.return_value = [{"name": "id"}]

        with patch.object(revision.sa, "inspect", return_value=inspector):
            revision.upgrade()

        self.assertEqual(3, revision.op.add_column.call_count)
        revision.op.create_table.assert_called_once()
        self.assertEqual(2, revision.op.create_index.call_count)


if __name__ == "__main__":
    unittest.main()
