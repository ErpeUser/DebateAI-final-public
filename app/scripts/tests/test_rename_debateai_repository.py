import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "rename_debateai_repository.py"
OLD = "ErpeUser/backchannel-v6-private"
NEW = "ErpeUser/DebateAI"


class RenameTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            SCRIPT.is_file(), "verified repository rename helper is missing"
        )
        spec = importlib.util.spec_from_file_location("rename_fixture", SCRIPT)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.url = f"https://github.com/{OLD}.git"
        self.identity = {"id": 1450951492, "private": True, "full_name": OLD}
        self.calls = []
        self.fail_rename = False
        self.fail_verify = False
        self.explicit_push = False
        self.second_url = False

    def run_command(self, repo, *args):
        self.calls.append(args)
        if args == ("git", "rev-parse", "--show-toplevel"):
            return str(self.root)
        if args == ("git", "remote", "get-url", "--all", "origin"):
            return self.url + (
                "\nhttps://github.com/other/project" if self.second_url else ""
            )
        if args == ("git", "config", "--get-regexp", r"^remote\.origin\."):
            return (
                "remote.origin.url "
                + self.url
                + ("\nremote.origin.pushurl " + self.url if self.explicit_push else "")
            )
        if args[:2] == ("gh", "api"):
            if self.fail_verify and self.identity["full_name"] == NEW:
                raise self.m.RenameError("offline")
            return json.dumps(self.identity)
        if args[:3] == ("gh", "repo", "rename"):
            if self.fail_rename:
                raise self.m.RenameError("denied")
            self.identity = {**self.identity, "full_name": NEW}
            return ""
        if args[:3] == ("git", "remote", "set-url"):
            self.url = args[-1]
            return ""
        raise AssertionError(args)

    def execute(self, apply=False):
        return self.m.rename_repository(self.root, apply=apply, run=self.run_command)

    def test_dry_run_has_no_remote_or_local_mutations(self):
        result = self.execute()
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["remote_name"], OLD)
        self.assertFalse(
            any(
                a[1:3] in [("repo", "rename"), ("remote", "set-url")]
                for a in self.calls
            )
        )

    def test_apply_verifies_remote_before_repointing_origin(self):
        result = self.execute(True)
        self.assertEqual(result["remote_name"], NEW)
        self.assertEqual(self.url, f"https://github.com/{NEW}.git")
        rename = next(
            i for i, a in enumerate(self.calls) if a[:3] == ("gh", "repo", "rename")
        )
        write = next(
            i for i, a in enumerate(self.calls) if a[:3] == ("git", "remote", "set-url")
        )
        self.assertTrue(
            any(a[:2] == ("gh", "api") for a in self.calls[rename + 1 : write])
        )
        self.assertTrue(
            any(a[:3] == ("git", "remote", "get-url") for a in self.calls[write + 1 :])
        )

    def test_already_renamed_is_idempotent(self):
        self.identity["full_name"] = NEW
        self.url = f"https://github.com/{NEW}.git"
        self.execute(True)
        self.assertFalse(any(a[:3] == ("gh", "repo", "rename") for a in self.calls))

    def test_ssh_transport_preserved(self):
        for prefix in ["git@github.com:", "ssh://git@github.com/"]:
            self.url = prefix + OLD + ".git"
            self.execute(True)
            self.assertEqual(self.url, prefix + NEW + ".git")

    def test_wrong_id_rejected_before_rename(self):
        self.identity["id"] = 123
        with self.assertRaises(self.m.RenameError):
            self.execute(True)
        self.assertFalse(any(a[:3] == ("gh", "repo", "rename") for a in self.calls))

    def test_private_state_is_required(self):
        self.identity["private"] = False
        with self.assertRaises(self.m.RenameError):
            self.execute(True)

    def test_unrelated_remote_rejected(self):
        self.url = "https://github.com/other/project.git"
        with self.assertRaises(self.m.RenameError):
            self.execute(True)
        self.assertFalse(any(a[0] == "gh" for a in self.calls))

    def test_embedded_credentials_rejected_without_echo(self):
        self.url = f"https://secret@github.com/{OLD}.git"
        with self.assertRaises(self.m.RenameError) as cm:
            self.execute(True)
        self.assertNotIn("secret", str(cm.exception))

    def test_explicit_push_override_requires_review(self):
        self.explicit_push = True
        with self.assertRaises(self.m.RenameError):
            self.execute(True)
        self.assertFalse(any(a[0] == "gh" for a in self.calls))

    def test_multiple_urls_rejected(self):
        self.second_url = True
        with self.assertRaises(self.m.RenameError):
            self.execute(True)

    def test_rename_denied_leaves_origin_unchanged(self):
        self.fail_rename = True
        with self.assertRaises(self.m.RenameError):
            self.execute(True)
        self.assertEqual(self.url, f"https://github.com/{OLD}.git")

    def test_unverified_rename_does_not_repoint_origin(self):
        self.fail_verify = True
        with self.assertRaisesRegex(self.m.RenameError, "may have succeeded"):
            self.execute(True)
        self.assertEqual(self.url, f"https://github.com/{OLD}.git")


if __name__ == "__main__":
    unittest.main()
