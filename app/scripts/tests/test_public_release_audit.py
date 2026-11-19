from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "public_release_audit.py"
SPEC = importlib.util.spec_from_file_location("public_release_audit", SCRIPT)
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


class PublicReleaseAuditTests(unittest.TestCase):
    def make_repo(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "app").mkdir()
        (root / "app" / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (root / "app" / "main.py").write_text("print('safe')\n", encoding="utf-8")
        return root

    def test_safe_source_passes(self):
        report = audit_module.audit(self.make_repo())
        self.assertEqual(report["findings"], [])

    def test_private_key_marker_fails_without_exposing_value(self):
        root = self.make_repo()
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        secret = marker + "\nnever-publish-this\n"
        (root / "app" / "config.py").write_text(secret, encoding="utf-8")
        report = audit_module.audit(root)
        self.assertIn("secret_marker", {item["rule"] for item in report["findings"]})
        self.assertNotIn("never-publish-this", json.dumps(report))

    def test_local_data_and_runtime_paths_fail(self):
        root = self.make_repo()
        (root / "app" / "private.sqlite").write_bytes(b"db")
        (root / "runtime" / "DebateAI").mkdir(parents=True)
        (root / "runtime" / "DebateAI" / "DebateAI.exe").write_bytes(b"exe")
        (root / "DebateAI_Generated" / "reports").mkdir(parents=True)
        (root / "DebateAI_Generated" / "reports" / "report.json").write_text("{}")
        report = audit_module.audit(root)
        rules = {item["rule"] for item in report["findings"]}
        self.assertIn("private_data_path", rules)
        self.assertIn("runtime_path", rules)
        self.assertIn("generated_path", rules)

    def test_missing_root_license_fails(self):
        root = self.make_repo()
        (root / "LICENSE").unlink()
        report = audit_module.audit(root)
        self.assertIn("missing_root_license", {item["rule"] for item in report["findings"]})

    def test_external_git_pointer_fails(self):
        root = self.make_repo()
        (root / ".git").write_text("gitdir: ../private-metadata\n", encoding="utf-8")
        report = audit_module.audit(root)
        self.assertIn("external_git_pointer", {item["rule"] for item in report["findings"]})

    def test_literal_credential_assignment_fails_without_exposing_value(self):
        root = self.make_repo()
        value = "super-secret-value"
        (root / "app" / "config.py").write_text(
            f'API_KEY = "{value}"\n', encoding="utf-8"
        )
        report = audit_module.audit(root)
        self.assertIn("credential_assignment", {item["rule"] for item in report["findings"]})
        self.assertNotIn(value, json.dumps(report))


if __name__ == "__main__":
    unittest.main()
