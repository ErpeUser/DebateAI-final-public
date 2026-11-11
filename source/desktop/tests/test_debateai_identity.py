import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class IdentityTests(unittest.TestCase):
    def load(self):
        path = ROOT / 'debateai_identity.py'
        self.assertTrue(path.is_file(), 'standalone identity module must exist')
        spec = importlib.util.spec_from_file_location('debateai_identity', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_brand_is_canonical(self):
        module = self.load()
        self.assertEqual(module.PRODUCT_NAME, 'DebateAI')
        self.assertEqual(module.WINDOWS_LAUNCHER, 'DebateAI.exe')
        self.assertEqual(module.WINDOWS_UPDATER, 'DebateAIUpdater.exe')

    def test_legacy_executable_names_remain_explicit_aliases(self):
        module = self.load()
        self.assertIn('Backchannel.exe', module.legacy_launchers('win32'))
        self.assertIn('BackchannelUpdater.exe', module.legacy_updaters('win32'))

    def test_new_install_uses_independent_directory(self):
        m = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.resolve_data_root(base=Path(tmp), environment={}), Path(tmp) / 'DebateAI')
            self.assertFalse((Path(tmp) / 'DebateAI').exists())

    def test_legacy_data_not_silently_abandoned(self):
        m = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / 'Backchannel'
            old.mkdir(); (old / 'master.key').write_bytes(b'opaque-fixture')
            self.assertEqual(m.resolve_data_root(base=Path(tmp), environment={}), old)
            self.assertEqual((old / 'master.key').read_bytes(), b'opaque-fixture')

    def test_existing_new_directory_wins_without_merging(self):
        m = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'Backchannel').mkdir(); (base / 'DebateAI').mkdir()
            (base / 'Backchannel' / 'state').write_text('old')
            (base / 'DebateAI' / 'current').write_text('current')
            self.assertEqual(m.resolve_data_root(base=base, environment={}), base / 'DebateAI')
            self.assertFalse((base / 'DebateAI' / 'state').exists())

    def test_explicit_new_override_has_priority(self):
        m = self.load()
        value = m.resolve_data_root(base=Path('/fixture'), environment={
            'DEBATEAI_DATA_DIR': '/new-fixture', 'BACKCHANNEL_DATA_DIR': '/old-fixture'})
        self.assertEqual(value, Path('/new-fixture'))

    def test_legacy_override_preserved(self):
        m = self.load()
        self.assertEqual(m.resolve_data_root(base=Path('/fixture'), environment={
            'BACKCHANNEL_DATA_DIR': '/custom-fixture'}), Path('/custom-fixture'))

    def test_linux_name_and_legacy_directory(self):
        m = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertEqual(m.resolve_data_root(base=base, environment={}, lowercase=True), base/'debateai')
            (base/'backchannel').mkdir(); (base/'backchannel'/'state').write_text('saved')
            self.assertEqual(m.resolve_data_root(base=base, environment={}, lowercase=True), base/'backchannel')

    def test_empty_new_directory_cannot_hide_existing_legacy_data(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); (base/'Backchannel').mkdir(); (base/'DebateAI').mkdir()
            (base/'Backchannel'/'state').write_text('saved')
            self.assertEqual(m.resolve_data_root(base=base,environment={}),base/'Backchannel')

    def test_empty_legacy_directory_does_not_keep_old_brand(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); (base/'Backchannel').mkdir()
            self.assertEqual(m.resolve_data_root(base=base,environment={}),base/'DebateAI')

    def test_file_collision_is_not_used_as_data_directory(self):
        m = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'DebateAI').write_text('not a directory')
            with self.assertRaises(NotADirectoryError):
                m.resolve_data_root(base=Path(tmp), environment={})


if __name__ == '__main__':
    unittest.main()
