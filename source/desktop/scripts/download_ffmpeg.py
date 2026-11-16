"""Download a self-contained LGPL ffmpeg build into desktop/ffmpeg.

Windows and Linux desktop bundles ship this binary so audio conversion
(webm voice recordings, mp3/m4a imports) works without a system ffmpeg.
macOS bundles stay ffmpeg-free, matching docs/releasing.md.
"""

import hashlib
import io
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "ffmpeg"

_FFMPEG_RELEASE = "autobuild-2026-11-15-12-40"
_FFMPEG_BASE = (
    "https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/"
    f"{_FFMPEG_RELEASE}"
)
_WINDOWS_ASSET = "ffmpeg-N-128915-g3d16b774d7-win64-lgpl.zip"
_LINUX_ASSET = "ffmpeg-N-128915-g3d16b774d7-linux64-lgpl.tar.xz"
WINDOWS_URL = f"{_FFMPEG_BASE}/{_WINDOWS_ASSET}"
LINUX_URL = f"{_FFMPEG_BASE}/{_LINUX_ASSET}"
SHA256_BY_URL = {
    WINDOWS_URL: "bc39b32bbcb56c0dd679e69a37e63cfce88b911240946cccfe966d30f9a279b4",
    LINUX_URL: "61c4e1fc02346ca60786b96d1d1c4672e527c20766ef1d02b6036672b32e4144",
}


def build_url() -> str | None:
    if sys.platform == "win32":
        return WINDOWS_URL
    if sys.platform.startswith("linux"):
        return LINUX_URL
    return None


def binary_name() -> str:
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

def download_payload(url: str) -> io.BytesIO:
    expected = SHA256_BY_URL.get(url)
    if expected is None:
        raise ValueError(f"no checksum pinned for ffmpeg URL: {url}")
    with urllib.request.urlopen(url) as resp:
        payload = resp.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"ffmpeg checksum mismatch for {url}: expected {expected}, got {actual}"
        )
    return io.BytesIO(payload)


def main() -> None:
    target = DEST / binary_name()
    if target.exists():
        print(f"ffmpeg already present at {target}")
        return
    url = build_url()
    if url is None:
        print("no bundled ffmpeg for this platform; skipping")
        return
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    payload = download_payload(url)
    if url.endswith(".zip"):
        with zipfile.ZipFile(payload) as zf:
            binary = next(n for n in zf.namelist() if n.endswith("bin/ffmpeg.exe"))
            target.write_bytes(zf.read(binary))
            license_member = next(
                (n for n in zf.namelist() if n.endswith("LICENSE.txt")), None
            )
            if license_member:
                (DEST / "LICENSE.txt").write_bytes(zf.read(license_member))
    else:
        with tarfile.open(fileobj=payload, mode="r:xz") as tf:
            binary = next(m for m in tf.getmembers() if m.name.endswith("bin/ffmpeg"))
            binary.name = binary_name()
            tf.extract(binary, DEST, filter="tar")  # "tar" keeps the +x bit
            license_member = next(
                (m for m in tf.getmembers() if m.name.endswith("LICENSE.txt")), None
            )
            if license_member:
                license_member.name = "LICENSE.txt"
                tf.extract(license_member, DEST, filter="tar")
    print(f"extracted ffmpeg to {target}")


if __name__ == "__main__":
    main()
