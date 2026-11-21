"""Download and safely stage an Ed25519-signed DebateAI Windows release.

The trust root is the checked-in public key file; no downloaded keys, remote
scripts, unsigned fallback or write into an existing installation are allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
import shutil
import ssl
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
sys.path.insert(0, str(APP / "backend"))
from app.services.debateai_update_channel import channel_configuration
from app.services.update_service import (
    MAX_DESCRIPTOR_BYTES,
    MAX_EXPANDED_BYTES,
    _open_update_url,
    _update_origin,
    _zip_extraction_root,
)
from app.services.update_signing import (
    parse_release_signing_keys,
    verify_update_descriptor,
)

PLATFORM = "windows-x64"
MAX_ARCHIVE_BYTES = 5 * 1024**3
MAX_ENTRIES = 100_000
REQUIRED = {
    "DebateAI/DebateAI.exe",
    "DebateAI/DebateAIUpdater.exe",
    "DebateAI/_internal/pgsql/bin/postgres.exe",
    "DebateAI/_internal/pgsql/bin/initdb.exe",
    "DebateAI/_internal/frontend/index.html",
    "DebateAI/_internal/ffmpeg/ffmpeg.exe",
    "DebateAI/_internal/models/silero_vad.onnx",
    "DebateAI/_internal/models/voxceleb_resnet152_LM.onnx",
}
RESERVED = {"con", "prn", "aux", "nul"}
RESERVED |= {f"com{i}" for i in range(1, 10)}
RESERVED |= {f"lpt{i}" for i in range(1, 10)}


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate signed descriptor field")
        value[key] = item
    return value


def _network_open(request, timeout, origin):
    # Reuses the updater's HTTPS and same-origin redirect policy.
    return _open_update_url(
        request,
        timeout=timeout,
        context=ssl.create_default_context(),
        source_origin=origin,
    )


def _read_response(url: str, origin, opener, limit: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "DebateAI-Bootstrap/1"},
    )
    with opener(request, 30, origin) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError("release descriptor request failed")
        if _update_origin(response.geturl()) != origin:
            raise ValueError("release source changed")
        result = response.read(limit + 1)
    if len(result) > limit:
        raise ValueError("release descriptor too large")
    return result


def _download_zip(
    url: str, origin, opener, target: Path, expected_size: int, expected_digest: str
) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "DebateAI-Bootstrap/1",
        },
    )
    hasher = hashlib.sha256()
    total = 0
    with opener(request, 90, origin) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError("release download request failed")
        if _update_origin(response.geturl()) != origin:
            raise ValueError("release source changed")
        with target.open("xb") as stream:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > expected_size:
                    raise ValueError("release download exceeded signed size")
                stream.write(chunk)
                hasher.update(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    if total != expected_size or not hmac.compare_digest(
        hasher.hexdigest(), expected_digest
    ):
        raise ValueError("release download hash or size mismatch")


def _checked_entry(info: zipfile.ZipInfo) -> tuple[str, bool]:
    name = info.filename
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or name.startswith(("/", "~"))
        or re.search(r"[\x00-\x1f\x7f]", name)
    ):
        raise ValueError("unsafe archive filename")
    is_dir = info.is_dir()
    stripped = name.rstrip("/") if is_dir else name
    parts = stripped.split("/")
    if (
        not parts
        or parts[0] != "DebateAI"
        or any(
            not part
            or part in {".", ".."}
            or part.endswith((" ", "."))
            or ":" in part
            or part.split(".")[0].casefold() in RESERVED
            for part in parts
        )
    ):
        raise ValueError("unsafe archive entry")
    if info.flag_bits & 1:
        raise ValueError("encrypted archive entry")
    unix_mode = (info.external_attr >> 16) & 0xFFFF
    file_kind = stat.S_IFMT(unix_mode)
    if file_kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError("unsupported archive file type")
    if info.file_size < 0:
        raise ValueError("negative archive entry size")
    return stripped, is_dir


def _stage_zip(archive_path: Path, stage_root: Path) -> Path:
    seen = {}
    total_expanded = 0
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ENTRIES:
            raise ValueError("unexpected number of release files")
        for info in infos:
            name, is_dir = _checked_entry(info)
            key = name.casefold()
            if key in seen:
                raise ValueError("duplicate archive entry")
            seen[key] = is_dir
            if not is_dir:
                total_expanded += info.file_size
                if total_expanded > MAX_EXPANDED_BYTES:
                    raise ValueError("archive expands beyond limit")
        if shutil.disk_usage(stage_root.parent).free < math.ceil(total_expanded * 1.1):
            raise ValueError("insufficient space for expanded signed release")
        for name, is_dir in ((i.filename.rstrip("/"), i.is_dir()) for i in infos):
            parts = name.casefold().split("/")
            if any(
                seen.get("/".join(parts[:index])) is False
                for index in range(1, len(parts))
            ):
                raise ValueError("file/directory archive collision")
        if not REQUIRED.issubset(
            {
                name
                for name, is_dir in ((_checked_entry(i)) for i in infos)
                if not is_dir
            }
        ):
            raise ValueError("incomplete release bundle")
        native_root = Path(_zip_extraction_root(stage_root))
        native_root.mkdir(parents=True, exist_ok=False)
        for info in infos:
            name, is_dir = _checked_entry(info)
            dest = native_root.joinpath(*name.split("/"))
            if is_dir:
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, dest.open("xb") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
        output = stage_root / "DebateAI"
        if not output.is_dir() or output.is_symlink():
            raise ValueError("release bundle root mismatch")
        return output


def recover(
    descriptor_url: str,
    asset_url: str,
    keys_path: Path,
    output_dir: Path,
    *,
    open_url=None,
) -> Path:
    """Fetch a signed descriptor and matching ZIP, verify and extract to a new stage.

    Returns stage/DebateAI. Does not replace an existing installation.
    The caller must run the native smoke and rollback-safe install step.
    """
    keys_path = Path(keys_path)
    config = channel_configuration(
        {
            "DEBATEAI_UPDATE_DESCRIPTOR_URL": descriptor_url,
            "DEBATEAI_UPDATE_ASSET_URL": asset_url,
            "DEBATEAI_UPDATE_KEYS": str(keys_path),
        }
    )
    if config is None:
        raise ValueError("explicit HTTPS update source required")
    desc_url = descriptor_url.format(platform_id=PLATFORM)
    origin = _update_origin(desc_url)
    if (
        _update_origin(asset_url.format(version="v0.0.0", platform_id=PLATFORM))
        != origin
    ):
        raise ValueError("release URLs must have the same origin")
    try:
        key_doc = json.loads(
            keys_path.read_text(encoding="utf-8"), object_pairs_hook=_unique
        )
        _, public_keys = parse_release_signing_keys(key_doc)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("local release public keys are invalid") from error
    opener = open_url or _network_open
    body = _read_response(desc_url, origin, opener, MAX_DESCRIPTOR_BYTES)
    try:
        descriptor = json.loads(body.decode("utf-8"), object_pairs_hook=_unique)
        signed = verify_update_descriptor(descriptor, PLATFORM, "0.0.0", public_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("release descriptor signature invalid") from error
    asset = signed["asset"]
    if asset["size"] > MAX_ARCHIVE_BYTES:
        raise ValueError("signed release exceeds maximum size")
    download_url = asset_url.format(version=signed["version"], platform_id=PLATFORM)
    if _update_origin(download_url) != origin:
        raise ValueError("release asset host differs")
    output_dir = Path(output_dir)
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ValueError("invalid release staging directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_dir).free < math.ceil(asset["size"] * 1.1):
        raise ValueError("insufficient space for signed release download")
    stage = output_dir / (".signed-release-" + uuid4().hex)
    stage.mkdir()
    try:
        archive = stage / "release.zip"
        _download_zip(
            download_url, origin, opener, archive, asset["size"], asset["sha256"]
        )
        # The signed descriptor is revalidated after the transfer.
        verify_update_descriptor(signed, PLATFORM, "0.0.0", public_keys)
        bundle = _stage_zip(archive, stage / "unpacked")
        archive.unlink()
        return bundle
    except Exception:
        shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--descriptor-url", default=os.environ.get("DEBATEAI_UPDATE_DESCRIPTOR_URL", "")
    )
    parser.add_argument(
        "--asset-url", default=os.environ.get("DEBATEAI_UPDATE_ASSET_URL", "")
    )
    parser.add_argument(
        "--keys", type=Path, default=APP / "desktop/release_signing_keys.json"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "DebateAI_Generated/build/recovery"
    )
    args = parser.parse_args()
    try:
        output = recover(
            args.descriptor_url, args.asset_url, args.keys, args.output_dir
        )
    except Exception as error:
        print("Signed release recovery unavailable: " + str(error), file=sys.stderr)
        return 2
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
