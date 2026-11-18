import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "v3-asset-inventory.json"


class V3AssetManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_has_non_destructive_policy(self):
        policy = self.manifest["policy"]
        self.assertTrue(policy["no_destructive_cleanup_performed"])
        self.assertTrue(policy["unknown_acl_paths_preserved"])
        self.assertEqual([], policy["removed"])
        self.assertEqual([], policy["merged"])
        self.assertEqual("sha256", policy["hash_algorithm"])

    def test_runtime_and_rollback_assets_are_explicit(self):
        artifacts = {item["path"]: item for item in self.manifest["artifacts"]}
        for path in (
            "backend/models/silero_vad.onnx",
            "backend/models/voxceleb_resnet152_LM.onnx",
            "desktop/ffmpeg/ffmpeg.exe",
            "desktop/pgsql",
            "dist/DebateAIUpdater.exe",
        ):
            self.assertEqual("needed", artifacts[path]["status"])
            self.assertTrue(artifacts[path]["owner"])
            self.assertTrue(artifacts[path]["reason"])

        for path in (
            "dist/DebateAI-windows-x64.zip",
            "dist/.DebateAI*.previous*",
        ):
            self.assertEqual("rollback-candidate", artifacts[path]["status"])
            self.assertTrue(artifacts[path]["rollback"])

        for item in self.manifest["artifacts"]:
            if "sha256" in item:
                self.assertRegex(item["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            if item["status"] == "open-unreviewed":
                self.assertTrue(item["reason"])

    def test_real_audio_candidates_are_preserved_without_acceptance_claim(self):
        artifacts = {item["path"]: item for item in self.manifest["artifacts"]}
        candidates = {
            "artifacts/real-smoke/german-asr.wav",
            "backend/.tmp/asr-real/phrase-window.wav",
            "backend/.tmp/asr-real/window-a.wav",
            "backend/.tmp/asr-real/window-b.wav",
        }
        for path in candidates:
            item = artifacts[path]
            self.assertEqual("evidence-candidate", item["status"])
            self.assertRegex(item["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertIn("preserve original bytes", item["rollback"])

    def test_asr_preflight_record_is_not_an_a21_pass(self):
        item = next(
            item
            for item in self.manifest["artifacts"]
            if item["path"] == "docs/evidence/asr-local-wav-decision-2026-11-09.json"
        )
        self.assertEqual("evidence-record", item["status"])
        self.assertIn("not an A21 pass", item["rollback"])


if __name__ == "__main__":
    unittest.main()
