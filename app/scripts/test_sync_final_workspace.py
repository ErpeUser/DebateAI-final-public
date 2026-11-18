"""Fixture tests for Codex's FINAL local-checkout synchronization.

Run in app/scripts:
    python -m unittest -v test_sync_final_workspace.py

Uses only temporary local Git repositories, no GitHub access or real user data.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from sync_final_workspace import sync, SyncError


def git(repo, *args):
    p = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True
    )
    if p.returncode:
        raise AssertionError((args, p.stderr))
    return p.stdout.strip()


class FinalSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        self.author = self.root / "author"
        self.local = self.root / "local"
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=master", str(self.origin)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "clone", str(self.origin), str(self.author)],
            check=True, capture_output=True,
        )
        for key, value in [("user.email", "test@example.org"), ("user.name", "Test User")]:
            git(self.author, "config", key, value)
        (self.author / "app.py").write_text("stable=1\n")
        git(self.author, "add", "app.py")
        git(self.author, "commit", "-m", "first")
        git(self.author, "push", "origin", "master")
        subprocess.run(
            ["git", "clone", str(self.origin), str(self.local)],
            check=True, capture_output=True,
        )
        for key, value in [("user.email", "test@example.org"), ("user.name", "Test User")]:
            git(self.local, "config", key, value)

    def advance_remote(self, file="app.py", content="stable=2\n"):
        (self.author / file).write_text(content)
        git(self.author, "add", file)
        git(self.author, "commit", "-m", "fix")
        git(self.author, "push", "origin", "master")

    def test_clean_local_fast_forwards(self):
        self.advance_remote()
        outcome = sync(self.local, str(self.origin))
        self.assertEqual(outcome["action"], "fast_forward_to_newest_master")
        self.assertTrue(outcome["matches_origin_master"])
        self.assertEqual((self.local / "app.py").read_text(), "stable=2\n")

    def test_outdated_tracked_edits_replaced_without_deleting_user_data(self):
        (self.local / "app.py").write_text("stable=OLD\n")
        (self.local / "secrets.env").write_text("SECRET=local\n")
        self.advance_remote()
        outcome = sync(self.local, str(self.origin))
        self.assertTrue(outcome["local_changes_stash"])
        self.assertTrue(outcome["matches_origin_master"])
        self.assertEqual((self.local / "app.py").read_text(), "stable=2\n")
        self.assertEqual((self.local / "secrets.env").read_text(), "SECRET=local\n")
        self.assertIn(
            "stable=OLD",
            git(self.local, "stash", "show", "-p", outcome["local_changes_stash"]),
        )

    def test_divergent_unique_local_commit_rebased(self):
        (self.local / "unique.py").write_text("unique=1\n")
        git(self.local, "add", "unique.py")
        git(self.local, "commit", "-m", "unique feature")
        self.advance_remote()
        outcome = sync(self.local, str(self.origin))
        self.assertEqual(outcome["action"], "rebased_local_commits_onto_newest_master")
        self.assertTrue(outcome["local_commits_backup"])
        self.assertTrue((self.local / "unique.py").exists())
        self.assertEqual((self.local / "app.py").read_text(), "stable=2\n")
        self.assertFalse(outcome["matches_origin_master"])

    def test_local_ahead_changes_kept_for_review(self):
        (self.local / "unique.py").write_text("new=1\n")
        git(self.local, "add", "unique.py")
        git(self.local, "commit", "-m", "new feature")
        outcome = sync(self.local, str(self.origin))
        self.assertEqual(outcome["action"], "local_commits_ahead_review_needed")
        self.assertTrue((self.local / "unique.py").exists())

    def test_unexpected_origin_rejected(self):
        (self.local / "app.py").write_text("PRIVATE\n")
        with self.assertRaises(SyncError):
            sync(self.local, "unexpected")
        self.assertEqual((self.local / "app.py").read_text(), "PRIVATE\n")

    def test_conflict_requires_semantic_codex_resolution(self):
        (self.local / "app.py").write_text("local=1\n")
        git(self.local, "add", "app.py")
        git(self.local, "commit", "-m", "local change")
        self.advance_remote(content="remote=2\n")
        outcome = sync(self.local, str(self.origin))
        self.assertEqual(outcome["action"], "rebase_conflict_codex_must_resolve")
        self.assertTrue(outcome["local_commits_backup"])
        git(self.local, "rebase", "--abort")
        self.assertEqual((self.local / "app.py").read_text(), "local=1\n")


if __name__ == "__main__":
    unittest.main()
