import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('safety', ROOT / 'sync_final_workspace.py')
safety = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(safety)


def git(path, *args):
    p = subprocess.run(['git', '-C', str(path), *args], capture_output=True, check=True)
    return p.stdout.decode('utf-8').strip()


class WorkspaceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.remote = self.root / 'remote'
        self.remote.mkdir()
        git(self.remote, 'init', '-b', 'master')
        git(self.remote, 'config', 'user.email', 'fixture@example.invalid')
        git(self.remote, 'config', 'user.name', 'Fixture')
        (self.remote / '.gitignore').write_text('private/\n*.secret\n', encoding='utf-8')
        (self.remote / 'app.txt').write_text('baseline', encoding='utf-8')
        git(self.remote, 'add', '.')
        git(self.remote, 'commit', '-m', 'baseline')
        self.local = self.root / 'local'
        git(self.root, 'clone', str(self.remote), str(self.local))
        git(self.local, 'config', 'user.email', 'fixture@example.invalid')
        git(self.local, 'config', 'user.name', 'Fixture')

    def tearDown(self):
        self.tmp.cleanup()

    def incoming(self, name):
        p = self.remote / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('upstream', encoding='utf-8')
        git(self.remote, 'add', '-f', name)
        git(self.remote, 'commit', '-m', 'incoming')
        git(self.local, 'fetch', 'origin')

    def test_ignored_collision_is_blocked_before_any_stash(self):
        self.assertTrue(hasattr(safety, 'protect_local_only_files'))
        self.incoming('private/settings.secret')
        p = self.local / 'private/settings.secret'
        p.parent.mkdir(exist_ok=True)
        p.write_text('unique user data', encoding='utf-8')
        (self.local / 'app.txt').write_text('unique code', encoding='utf-8')
        head = git(self.local, 'rev-parse', 'HEAD')
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)
        self.assertEqual(p.read_text(), 'unique user data')
        self.assertEqual((self.local / 'app.txt').read_text(), 'unique code')
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), head)
        self.assertEqual(git(self.local, 'stash', 'list'), '')

    def test_git_itself_can_overwrite_ignored_file(self):
        self.incoming('private/settings.secret')
        p = self.local / 'private/settings.secret'
        p.parent.mkdir(exist_ok=True)
        p.write_text('unique user data')
        git(self.local, 'merge', '--ff-only', 'origin/master')
        self.assertEqual(p.read_text(), 'upstream')

    def test_unrelated_ignored_data_allows_fast_forward(self):
        self.incoming('new.py')
        p = self.local / 'cache.secret'
        p.write_text('preserve')
        safety.protect_local_only_files(self.local)
        git(self.local, 'merge', '--ff-only', 'origin/master')
        self.assertEqual(p.read_text(), 'preserve')

    def test_untracked_file_collision(self):
        self.incoming('new.py')
        (self.local / 'new.py').write_text('local')
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)

    def test_file_over_directory_collision(self):
        self.incoming('private')
        (self.local / 'private').mkdir()
        (self.local / 'private/data.secret').write_text('saved')
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)

    def test_directory_over_file_collision(self):
        self.incoming('private/module.py')
        (self.local / 'private').write_text('saved')
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)

    def test_case_insensitive_collision_for_windows(self):
        self.incoming('Config.secret')
        (self.local / 'config.secret').write_text('saved')
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)

    def test_prefix_is_not_a_path_collision(self):
        self.incoming('cache.secret-extra')
        (self.local / 'cache.secret').write_text('saved')
        safety.protect_local_only_files(self.local)

    def test_symlink_is_not_followed(self):
        self.incoming('private/data.txt')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'data.txt').write_text('saved')
        try:
            (self.local / 'private').symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Creating symlinks requires a Windows privilege unavailable to this process')
            raise
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)
        self.assertEqual((outside / 'data.txt').read_text(), 'saved')

    @unittest.skipIf(os.name == 'nt', 'Win32 filenames cannot contain a newline')
    def test_newline_in_filename_is_preserved(self):
        self.incoming("\nprivate.secret")
        (self.local / "\nprivate.secret").write_text("saved")
        with self.assertRaises(safety.WorkspaceCollision):
            safety.protect_local_only_files(self.local)

    def test_clean_workspace_has_no_collision(self):
        safety.protect_local_only_files(self.local)

    def test_real_sync_blocks_before_stash_and_preserves_ignored_data(self):
        self.incoming('private/settings.secret')
        p = self.local / 'private/settings.secret'
        p.parent.mkdir(exist_ok=True); p.write_text('saved')
        (self.local / 'app.txt').write_text('unique code')
        with self.assertRaises(safety.SyncError):
            safety.sync(self.local, str(self.remote))
        self.assertEqual(p.read_text(), 'saved')
        self.assertEqual(git(self.local, 'stash', 'list'), '')
        self.assertEqual((self.local/'app.txt').read_text(), 'unique code')

    def test_canonical_and_migration_origins_are_accepted(self):
        for name in ('DebateAI', 'backchannel-v6-private'):
            for prefix in ('https://github.com/', 'git@github.com:', 'ssh://git@github.com/'):
                safety.validate_origin(prefix+'ErpeUser/'+name+'.git', None)
        with self.assertRaises(safety.SyncError):
            safety.validate_origin('https://github.com/other/DebateAI', None)

if __name__ == '__main__':
    unittest.main()
