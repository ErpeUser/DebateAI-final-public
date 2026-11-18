"""Download zonky.io embedded Postgres binaries for the current platform."""

import hashlib
import io
import platform
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

PG_VERSION = "16.4.0"
# Maven Central .jar.sha256 checksums for the matching Zonky release artifacts.
PG_JAR_SHA256 = {
    "windows-amd64": "5748a1b03f3771cd7a6d8aa624975e2777f62525694bf63af9640deaa48cc87a",
    "linux-amd64": "14a5cf546aee7d327a2f5b46be6c571f2f724a2b485c270d46f3e44a1ac3df18",
    "darwin-amd64": "e9a4d0de025426978d39087e2dfad265cb22a70ad19aa388857e4dcf6cf55f25",
    "darwin-arm64v8": "ad810a174664012341f1c9c1ff9667f61930d054f34bd650ceb2bc0c8796ccf9",
}
DEST = Path(__file__).resolve().parent.parent / "pgsql"
REQUIRED_BINARIES = ("postgres", "initdb", "pg_ctl")


def artifact_platform() -> str:
    if sys.platform == "win32":
        return "windows-amd64"
    if sys.platform == "darwin":
        if platform.machine() == "arm64":
            return "darwin-arm64v8"
        return "darwin-amd64"
    return "linux-amd64"


def jar_url(plat: str) -> str:
    name = f"embedded-postgres-binaries-{plat}"
    return (
        "https://repo1.maven.org/maven2/io/zonky/test/postgres/"
        f"{name}/{PG_VERSION}/{name}-{PG_VERSION}.jar"
    )


def has_complete_install() -> bool:
    suffix = ".exe" if sys.platform == "win32" else ""
    return all(
        (path := DEST / "bin" / f"{name}{suffix}").is_file()
        and path.stat().st_size > 0
        for name in REQUIRED_BINARIES
    )


def main() -> None:
    if has_complete_install():
        print(f"pgsql already present at {DEST}")
        return
    plat = artifact_platform()
    expected = PG_JAR_SHA256[plat]
    url = jar_url(plat)
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        payload = resp.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"PostgreSQL checksum mismatch for {url}: expected {expected}, got {actual}"
        )
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        txz_name = next(n for n in zf.namelist() if n.endswith(".txz"))
        txz = io.BytesIO(zf.read(txz_name))
    DEST.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=txz, mode="r:xz") as tf:
        tf.extractall(DEST, filter="tar")  # "tar" keeps the +x bits binaries need
    print(f"extracted postgres to {DEST}")


if __name__ == "__main__":
    main()
