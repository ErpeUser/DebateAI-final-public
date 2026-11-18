"""Repository layout, GitHub ownership, and Git ignore regression contracts."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[2]
ROOT = APP.parent
# Other tests load app/backend/scripts as a top-level 'scripts' package.
# Import this tool by its unique file path to avoid suite-order coupling.
SPEC = importlib.util.spec_from_file_location(
    "debateai_repository_layout_guard", APP / "scripts/verify_repository_layout.py"
)
layout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout)


class RepositoryLayoutTests(unittest.TestCase):
    def good(self):
        return set(layout.REQUIRED_FILES) | {
            "app/.env.example",
            "app/site/index.html",
            "app/docs-site/worker.js",
            "app/.github/release-notes/v0.6.6.md",
            "app/frontend/package-lock.json",
        }

    def test_minimal_supported_layout_is_accepted(self):
        self.assertEqual(layout.validate_paths(self.good()), [])

    def test_public_root_license_is_allowed(self):
        self.assertEqual(layout.validate_paths(self.good() | {"LICENSE"}), [])

    def test_missing_versioned_app_and_workflows_are_rejected(self):
        broken = self.good() - {"app/backend/app/main.py"}
        violations = layout.validate_paths(broken)
        self.assertTrue(any("app/backend/app/main.py" in v for v in violations))

    def test_disposable_runtime_and_generator_must_not_be_tracked(self):
        for bad in (
            "runtime/DebateAI/DebateAI.exe",
            "DebateAI_Generated/build/stage.zip",
            "app/backend/.venv/Scripts/python.exe",
            "app/frontend/node_modules/react/index.js",
            "app/frontend/dist/index.html",
            "app/build/pyinstaller/work.spec",
        ):
            with self.subTest(path=bad):
                violations = layout.validate_paths(self.good() | {bad})
                self.assertTrue(violations, bad)

    def test_secret_env_variants_and_keys_are_rejected(self):
        for path in ("app/.env", "app/.env.staging",
                     "app/backend/.env.production", "app/desktop/private.key",
                     "app/backend/data.sqlite", "app/desktop/signing.p12"):
            with self.subTest(path=path):
                self.assertTrue(layout.validate_paths(self.good() | {path}))

    def test_new_root_source_alias_is_forbidden(self):
        for path in ("source/backend/main.py", "backend/main.py",
                     ".github/workflows/private.env", "app/unknown/input.py"):
            with self.subTest(path=path):
                self.assertTrue(layout.validate_paths(self.good() | {path}))

    def test_windows_case_collisions_and_noncanonical_names_rejected(self):
        for path in ("APP/site/index.html", "app/../runtime/new.exe",
                     "app\\site\\index.html", "app/site//index.html"):
            with self.subTest(path=path):
                self.assertTrue(layout.validate_paths(self.good() | {path}))

    def test_real_worktree_layout_has_no_violations(self):
        files = layout.tracked_and_new_files(ROOT)
        self.assertEqual(layout.validate_paths(files), [])

    def test_expected_ignore_patterns_are_enforced(self):
        ignored = (
            "DebateAI_Generated/cache/file.bin",
            "runtime/DebateAI/DebateAI.exe",
            "app/backend/.env.staging",
            "app/.env.production",
            "app/desktop/secrets.p12",
            "app/frontend/node_modules/react/index.js",
            "app/frontend/dist/index.html",
            "app/backend/__pycache__/main.pyc",
            "app/scripts/.pytest_cache/cache",
            "app/scripts/graphify-out/graph.json",
        )
        for path in ignored:
            with self.subTest(ignored=path):
                result = subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", path],
                                        cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, path)
        for path in (
            "app/.env.example",
            "app/backend/app/main.py",
            "app/frontend/package-lock.json",
            "app/site/index.html",
            "app/docs-site/worker.js",
            ".github/workflows/tests.yml",
            "app/desktop/release_signing_keys.json",
        ):
            with self.subTest(versioned=path):
                result = subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", path],
                                        cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 1, path)

    def test_structure_workflow_has_blocking_repository_gate(self):
        source = (ROOT / ".github/workflows/structure.yml").read_text(encoding="utf-8")
        self.assertIn("repository-layout:", source)
        self.assertIn("python app/scripts/verify_repository_layout.py", source)
        self.assertIn("checkout@11d5960a326750d5838078e36cf38b85af677262", source)
        head = source.split("repository-layout:", 1)[1].split("\n  sentrux:", 1)[0]
        self.assertNotIn("continue-on-error: true", head)

    def test_codeowners_cover_real_app_paths(self):
        owners = (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")
        for entry in ("/.github/", "/app/backend/", "/app/desktop/",
                      "/app/scripts/", "/app/site/", "/app/docs-site/",
                      "/.gitignore", "/AGENTS.md"):
            with self.subTest(path=entry):
                self.assertIn(entry + " @ErpeUser", owners)


if __name__ == "__main__":
    unittest.main()
