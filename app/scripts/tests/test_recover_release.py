"""Signed release bootstrap must fail closed on every untrusted input."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.update_signing import public_update_descriptor, sign_platform_manifest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SPEC = importlib.util.spec_from_file_location(
    "signed_recovery", ROOT / "scripts/recover_release.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

BASE = "https://download.example.org"
DESCRIPTOR_URL = BASE + "/api/update/latest/{platform_id}"
ASSET_URL = BASE + "/api/update/assets/{version}/{platform_id}"
FILES = {
    "DebateAI/DebateAI.exe": b"native-launcher",
    "DebateAI/DebateAIUpdater.exe": b"updater",
    "DebateAI/_internal/pgsql/bin/postgres.exe": b"postgres",
    "DebateAI/_internal/pgsql/bin/initdb.exe": b"initdb",
    "DebateAI/_internal/ffmpeg/ffmpeg.exe": b"ffmpeg",
    "DebateAI/_internal/frontend/index.html": b"<html></html>",
    "DebateAI/_internal/models/silero_vad.onnx": b"model",
    "DebateAI/_internal/models/voxceleb_resnet152_LM.onnx": b"other-model",
}


def archive(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, value in entries.items():
            if isinstance(value, zipfile.ZipInfo):
                target.writestr(value, b"symlink")
            else:
                target.writestr(name, value)
    return buffer.getvalue()


class Response(io.BytesIO):
    status = 200

    def __init__(self, payload, url):
        super().__init__(payload)
        self.url = url

    def geturl(self):
        return self.url


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.keys = self.root / "keys.json"
        self.output = self.root / "output"
        self.private = Ed25519PrivateKey.generate()
        pub = self.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.keys.write_text(
            json.dumps(
                {
                    "active": "key-2026",
                    "keys": {
                        "key-2026": base64.urlsafe_b64encode(pub).rstrip(b"=").decode()
                    },
                }
            ),
            encoding="utf-8",
        )

    def descriptor(self, payload):
        manifest = {
            "version": "v1.2.3",
            "commit": "a" * 40,
            "published_at": "2026-11-18T20:00:00Z",
            "release_notes": "Verified release",
            "asset": {
                "id": "windows-x64",
                "platform": "Windows x64",
                "filename": "DebateAI-windows-x64.zip",
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "key": "releases/v1.2.3/DebateAI-windows-x64.zip",
                "content_type": "application/zip",
            },
        }
        private_bytes = self.private.private_bytes_raw()
        return public_update_descriptor(
            sign_platform_manifest(manifest, "key-2026", private_bytes)
        )

    def run_recovery(
        self,
        payload,
        *,
        descriptor=None,
        urls=None,
        descriptor_url=DESCRIPTOR_URL,
        asset_url=ASSET_URL,
    ):
        descriptor = descriptor if descriptor is not None else self.descriptor(payload)
        durl = descriptor_url.format(platform_id="windows-x64")
        aurl = asset_url.format(version="v1.2.3", platform_id="windows-x64")
        supplied = urls or {durl: json.dumps(descriptor).encode(), aurl: payload}

        def opener(request, timeout, origin):
            url = request.full_url
            entry = supplied[url]
            if isinstance(entry, tuple):
                return Response(entry[0], entry[1])
            return Response(entry, url)

        return mod.recover(
            descriptor_url, asset_url, self.keys, self.output, open_url=opener
        )

    def test_valid_signed_archive_is_staged(self):
        root = self.run_recovery(archive(FILES))
        self.assertEqual(root.name, "DebateAI")
        self.assertEqual((root / "DebateAI.exe").read_bytes(), b"native-launcher")
        self.assertFalse(any(self.output.rglob("*.zip")))

    def test_cli_default_keys_ignore_ambient_trust_override(self):
        observed = {}

        def stopped(descriptor_url, asset_url, keys, output_dir):
            observed["keys"] = keys
            raise ValueError("stop before network")

        with (
            mock.patch.object(sys, "argv", ["recover_release.py"]),
            mock.patch.object(mod, "recover", side_effect=stopped),
            mock.patch.dict(os.environ, {"DEBATEAI_UPDATE_KEYS": str(self.keys)}),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(mod.main(), 2)
        self.assertEqual(observed["keys"], ROOT / "desktop/release_signing_keys.json")

    def test_tampered_signature_rejected(self):
        payload = archive(FILES)
        descriptor = self.descriptor(payload)
        descriptor["release_notes"] = "modified"
        with self.assertRaises(ValueError):
            self.run_recovery(payload, descriptor=descriptor)
        self.assertFalse(any(self.output.rglob("DebateAI.exe")))

    def test_wrong_download_hash_rejected(self):
        good = archive(FILES)
        tampered = good + b"tamper"
        descriptor = self.descriptor(good)
        with self.assertRaises(ValueError):
            self.run_recovery(tampered, descriptor=descriptor)
        self.assertFalse(any(self.output.rglob("DebateAI.exe")))

    def test_low_disk_space_rejected_before_writing_bundle(self):
        with (
            mock.patch.object(
                mod.shutil, "disk_usage", return_value=SimpleNamespace(free=1)
            ),
            self.assertRaises(ValueError),
        ):
            self.run_recovery(archive(FILES))
        self.assertFalse(any(self.output.rglob("DebateAI.exe")))

    def test_incomplete_release_bundle_rejected(self):
        files = dict(FILES)
        files.pop("DebateAI/DebateAIUpdater.exe")
        with self.assertRaises(ValueError):
            self.run_recovery(archive(files))

    def test_traversal_archive_rejected(self):
        bad = {**FILES, "DebateAI/../../escape.exe": b"evil"}
        with self.assertRaises(ValueError):
            self.run_recovery(archive(bad))
        self.assertFalse((self.root / "escape.exe").exists())

    def test_absolute_and_drive_archive_paths_rejected(self):
        for name in ("/DebateAI/escape", "DebateAI/C:/evil.exe"):
            with self.subTest(path=name), self.assertRaises(ValueError):
                self.run_recovery(archive({**FILES, name: b"evil"}))

    def test_symlink_archive_rejected(self):
        link = zipfile.ZipInfo("DebateAI/_internal/malicious")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            self.run_recovery(archive({**FILES, link.filename: link}))

    def test_casefold_filename_collision_rejected(self):
        with self.assertRaises(ValueError):
            self.run_recovery(
                archive(
                    {**FILES, "DebateAI/_internal/Models/silero_vad.onnx": b"duplicate"}
                )
            )

    def test_cross_origin_redirect_rejected(self):
        payload = archive(FILES)
        durl = DESCRIPTOR_URL.format(platform_id="windows-x64")
        aurl = ASSET_URL.format(version="v1.2.3", platform_id="windows-x64")
        with self.assertRaises(ValueError):
            self.run_recovery(
                payload,
                urls={
                    durl: (json.dumps(self.descriptor(payload)).encode(), durl),
                    aurl: (payload, "https://evil.example.org/asset"),
                },
            )

    def test_http_and_wrong_origin_urls_rejected_before_request(self):
        for durl, aurl in (
            ("http://download.example.org/api/update/latest/{platform_id}", ASSET_URL),
            (DESCRIPTOR_URL, "https://evil.example.org/{version}/{platform_id}"),
        ):
            with self.subTest(durl=durl), self.assertRaises(ValueError):
                self.run_recovery(archive(FILES), descriptor_url=durl, asset_url=aurl)


if __name__ == "__main__":
    unittest.main()
