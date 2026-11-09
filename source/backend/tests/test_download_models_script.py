import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "download_models.py"
spec = importlib.util.spec_from_file_location("download_models_script", SCRIPT)
download_models = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(download_models)


class DownloadModelsContractTests(unittest.TestCase):
    def test_every_model_spec_is_pinned_and_auditable(self):
        all_specs = {
            **download_models.MODEL_SPECS,
            **download_models.OPTIONAL_MODEL_SPECS,
        }
        self.assertTrue(all_specs)
        for filename, model in all_specs.items():
            self.assertRegex(model["url"], r"/(?:resolve|raw)/[0-9a-f]{7,40}/")
            self.assertRegex(model["revision"], r"^[0-9a-f]{7,40}$")
            self.assertRegex(model["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(model["license"])
            self.assertGreater(model["size_bytes"], 0, filename)

    def test_existing_file_hash_is_verified_before_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "model.onnx"
            target.write_bytes(b"not the pinned model")
            old_dir = download_models.MODELS_DIR
            download_models.MODELS_DIR = tmp
            try:
                with self.assertRaisesRegex(RuntimeError, "sha256 mismatch"):
                    download_models._fetch(
                        {
                            "model.onnx": {
                                "url": "https://example.invalid/resolve/abcdef1/model.onnx",
                                "revision": "abcdef1",
                                "sha256": hashlib.sha256(b"expected").hexdigest(),
                                "license": "MIT",
                                "size_bytes": 8,
                            }
                        }
                    )
            finally:
                download_models.MODELS_DIR = old_dir

    def test_download_is_verified_before_installing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = download_models.MODELS_DIR
            download_models.MODELS_DIR = tmp
            model = {
                "url": "https://example.invalid/resolve/abcdef1/model.onnx",
                "revision": "abcdef1",
                "sha256": hashlib.sha256(b"verified").hexdigest(),
                "license": "MIT",
                "size_bytes": 8,
            }
            try:
                with patch.object(download_models.urllib.request, "urlretrieve") as retrieve:
                    def fake_retrieve(_url, destination):
                        Path(destination).write_bytes(b"verified")

                    retrieve.side_effect = fake_retrieve
                    download_models._fetch({"model.onnx": model})
                self.assertEqual(b"verified", (Path(tmp) / "model.onnx").read_bytes())
                self.assertFalse((Path(tmp) / "model.onnx.download").exists())
            finally:
                download_models.MODELS_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
