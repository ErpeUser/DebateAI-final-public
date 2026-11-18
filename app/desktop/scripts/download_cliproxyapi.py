"""Download and checksum-verify the pinned official CLIProxyAPI components."""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path


VERSION = "8.0.54"
GEMINI_PLUGIN_VERSION = "1.0.5"
DEST = Path(__file__).resolve().parent.parent / "cliproxyapi"
CPA_BASE = f"https://github.com/router-for-me/CLIProxyAPI/releases/download/v{VERSION}"
CPA_ARCHIVE = f"CLIProxyAPI_{VERSION}_windows_amd64.zip"
PLUGIN_BASE = (
    "https://github.com/router-for-me/cpa-plugin-gemini-cli/releases/download/"
    f"v{GEMINI_PLUGIN_VERSION}"
)
PLUGIN_ARCHIVE = (
    f"gemini-cli_{GEMINI_PLUGIN_VERSION}_windows_amd64.zip"
)


def _download(base_url: str, name: str) -> bytes:
    request = urllib.request.Request(
        f"{base_url}/{name}", headers={"User-Agent": "DebateAI-build"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _verified_archive(base_url: str, archive_name: str) -> bytes:
    checksums = _download(base_url, "checksums.txt").decode("utf-8")
    expected = ""
    for line in checksums.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == archive_name:
            expected = parts[0].casefold()
            break
    if not expected:
        raise RuntimeError(f"No checksum published for {archive_name}")
    payload = _download(base_url, archive_name)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Checksum mismatch for {archive_name}: expected {expected}, got {actual}"
        )
    return payload


def _install_proxy() -> None:
    target = DEST / "cli-proxy-api.exe"
    version_file = DEST / "VERSION"
    if target.is_file() and version_file.is_file():
        if version_file.read_text(encoding="ascii").strip() == VERSION:
            return
    payload = _verified_archive(CPA_BASE, CPA_ARCHIVE)
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        executable = next(
            (name for name in archive.namelist() if name.endswith("cli-proxy-api.exe")),
            None,
        )
        if executable is None:
            raise RuntimeError("CLIProxyAPI archive has no cli-proxy-api.exe")
        target.write_bytes(archive.read(executable))
        license_name = next(
            (
                name
                for name in archive.namelist()
                if Path(name).name.upper().startswith("LICENSE")
            ),
            None,
        )
        if license_name:
            (DEST / Path(license_name).name).write_bytes(archive.read(license_name))
    version_file.write_text(VERSION + "\n", encoding="ascii")


def _install_gemini_plugin() -> None:
    plugin_dir = DEST / "plugins" / "windows" / "amd64"
    target = plugin_dir / f"gemini-cli-v{GEMINI_PLUGIN_VERSION}.dll"
    version_file = DEST / "GEMINI_PLUGIN_VERSION"
    if target.is_file() and version_file.is_file():
        if version_file.read_text(encoding="ascii").strip() == GEMINI_PLUGIN_VERSION:
            return
    payload = _verified_archive(PLUGIN_BASE, PLUGIN_ARCHIVE)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        library = next(
            (name for name in archive.namelist() if name.casefold().endswith(".dll")),
            None,
        )
        if library is None:
            raise RuntimeError("Gemini CLI plugin archive has no Windows DLL")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(library))
    version_file.write_text(GEMINI_PLUGIN_VERSION + "\n", encoding="ascii")


def main() -> None:
    if sys.platform != "win32":
        print("CLIProxyAPI is bundled only with the Windows desktop app; skipping")
        return
    _install_proxy()
    _install_gemini_plugin()
    print(
        f"verified CLIProxyAPI {VERSION} and Gemini CLI plugin "
        f"{GEMINI_PLUGIN_VERSION} in {DEST}"
    )


if __name__ == "__main__":
    main()
