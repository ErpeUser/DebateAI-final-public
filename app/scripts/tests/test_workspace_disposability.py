"""Regression guards: deleting Generated must not remove source, Git or runtime."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "workspace_refs.py"
SPEC = importlib.util.spec_from_file_location("debate_workspace_refs", SCRIPT)
refs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refs)


class DisposableWorkspaceTests(unittest.TestCase):
    def test_workspace_scripts_survive_cache_deletion(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue((refs.ROOT / "Start-DebateAI.ps1").is_file())
        self.assertTrue((refs.ROOT / "Start-DebateAI.cmd").is_file())
        self.assertFalse(SCRIPT.is_relative_to(refs.GENERATED))

    def test_git_and_runtime_live_outside_generated(self):
        result = refs.collect()
        self.assertTrue(result["git_independent_of_generated"])
        self.assertTrue(result["runtime_independent_of_generated"])
        self.assertFalse((refs.ROOT / ".git").is_relative_to(refs.GENERATED))

    def test_generated_can_be_absent_without_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            absent = Path(td) / "not_created"
            with mock.patch.object(refs, "GENERATED", absent):
                report = refs.collect()
            self.assertFalse(report["generated_exists"])
            self.assertFalse(absent.exists())

    def test_gitfile_relative_sibling_survives_move(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "DebateAI"
            root.mkdir()
            gitdir = parent / "DebateAI-GIT-METADATA"
            gitdir.mkdir()
            (root / ".git").write_text(
                "gitdir: ../DebateAI-GIT-METADATA\n", encoding="utf-8"
            )
            with mock.patch.object(refs, "ROOT", root):
                self.assertEqual(refs.git_metadata_dir().resolve(), gitdir.resolve())

    def test_internal_git_directory_is_the_default_metadata_location(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gitdir = root / ".git"
            gitdir.mkdir()
            (gitdir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            with mock.patch.object(refs, "ROOT", root):
                self.assertEqual(refs.git_metadata_dir().resolve(), gitdir.resolve())

    def test_missing_legacy_pointer_is_reported_as_essential(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").write_text(
                "gitdir: ../missing-metadata\n", encoding="utf-8"
            )
            for name in ("backend", "frontend", "desktop"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source\n", encoding="utf-8")
            adjusted = {
                "source_backend": root / "backend",
                "source_frontend": root / "frontend",
                "source_desktop": root / "desktop",
            }
            with mock.patch.object(refs, "ROOT", root), mock.patch.object(
                refs, "RESOURCES", adjusted
            ):
                report = refs.collect(source_only=True)
            self.assertTrue(report["essential_missing"])

    def test_metadata_pointer_inside_generated_is_not_independent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generated = root / "Generated"
            gitdir = generated / "git"
            gitdir.mkdir(parents=True)
            (gitdir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (root / ".git").write_text(
                "gitdir: Generated/git\n", encoding="utf-8"
            )
            source_paths = {}
            for key in ("source_backend", "source_frontend", "source_desktop"):
                path = root / key
                path.write_text("source\n", encoding="utf-8")
                source_paths[key] = path
            with mock.patch.object(refs, "ROOT", root), mock.patch.object(
                refs, "GENERATED", generated
            ), mock.patch.object(refs, "RESOURCES", source_paths):
                report = refs.collect(source_only=True)
            self.assertFalse(report["git_independent_of_generated"])

    def test_no_critical_directories_in_generated(self):
        forbidden = {"git", "backups", "databases", "tools", "configs", "agents", "docs", "runtime"}
        first_parts = {Path(p).parts[0] for p in refs.GENERATED_DIRS}
        self.assertTrue(forbidden.isdisjoint(first_parts))

    def test_ci_source_only_audit_tolerates_missing_native_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            absent = Path(td)
            adjusted = dict(refs.RESOURCES)
            adjusted.update({
                "runtime_executable": absent / "DebateAI.exe",
                "runtime_updater": absent / "DebateAIUpdater.exe",
                "runtime_internal": absent / "_internal",
            })
            with mock.patch.object(refs, "RESOURCES", adjusted):
                result = refs.collect(source_only=True)
                self.assertEqual(result["essential_missing"], [])
                full = refs.collect(source_only=False)
                self.assertNotEqual(full["essential_missing"], [])

    def test_release_build_outputs_are_disposable(self):
        generated = refs.ROOT / "DebateAI_Generated"
        self.assertEqual(refs.RESOURCES["build_release_bundle"],
                         generated / "build/releases/DebateAI")
        self.assertEqual(refs.RESOURCES["build_release_archive"],
                         generated / "build/releases/DebateAI-windows-x64.zip")
        self.assertEqual(refs.RESOURCES["npm_cache"], generated / "cache/npm")

    def test_ci_runs_disposable_source_and_native_launcher_contracts(self):
        ci = (refs.ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("workspace_refs.py --source-only --strict", ci)
        self.assertIn("test_start_debateai.ps1", ci)
        self.assertIn("test_build_debate_assistant.ps1", ci)


if __name__ == "__main__":
    unittest.main()
