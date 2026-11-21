from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "debateai_github_sync", APP / "scripts/github_sync.py"
)
github_sync = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(github_sync)


class GithubSyncImpactTests(unittest.TestCase):
    def test_frontend_and_launcher_changes_require_desktop_refresh(self):
        impact = github_sync.changed_impact(
            [
                "app/frontend/src/App.tsx",
                "Start-DebateAI.ps1",
            ]
        )
        self.assertEqual(impact["desktop_action"], "rebuild-required")
        self.assertEqual(impact["shortcut_action"], "verify-after-build")

    def test_extension_directory_changes_are_detected(self):
        impact = github_sync.changed_impact(
            [
                "app/browser-extension/src/background.ts",
            ]
        )
        self.assertEqual(impact["extension_action"], "rebuild-required")

    def test_docs_and_release_manifests_do_not_trigger_extension_build(self):
        impact = github_sync.changed_impact(
            [
                "app/docs/release-manifest.json",
                "app/site/index.html",
            ]
        )
        self.assertEqual(impact["extension_action"], "none")
        self.assertEqual(impact["desktop_action"], "none")


if __name__ == "__main__":
    unittest.main()
