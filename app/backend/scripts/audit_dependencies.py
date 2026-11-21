"""Emit a reproducible inventory for direct production dependencies.

This is an audit aid, not an updater. It records the declared constraint,
installed version, marker, native-component hint, and package metadata so a
release review can make an explicit compatibility/licence decision.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib import metadata
from pathlib import Path

_REQ = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(?P<constraint>(?:===|==|~=|!=|<=|>=|<|>).*?)?\s*(?:;\s*(?P<marker>.*))?$"
)
_NATIVE_HINTS = {
    "onnxruntime",
    "kaldi-native-fbank",
    "numpy",
    "PyAudioWPatch",
    "soundfile",
    "pywebview",
    "pyinstaller",
}
_PURPOSES = {
    "fastapi": "HTTP API and WebSocket routing",
    "uvicorn": "ASGI server",
    "websockets": "WebSocket transport",
    "PyAudioWPatch": "Windows microphone/system-audio capture",
    "sqlalchemy": "database ORM",
    "asyncpg": "PostgreSQL driver",
    "alembic": "schema migrations",
    "pydantic-settings": "typed configuration",
    "python-multipart": "multipart upload parsing",
    "google-genai": "Gemini provider adapter",
    "python-docx": "document import",
    "openpyxl": "XLSX export/import",
    "markitdown": "document conversion",
    "onnxruntime": "local ONNX inference",
    "kaldi-native-fbank": "local audio features",
    "numpy": "audio and model arrays",
    "fastembed": "local embeddings",
    "soundfile": "audio file I/O",
    "cryptography": "secret encryption",
    "certifi": "TLS trust roots",
    "onnx-asr": "local ASR adapter",
    "huggingface-hub": "explicit model maintenance downloads",
    "pystray": "desktop tray integration",
    "pillow": "image handling",
    "pyinstaller": "desktop packaging",
}


def parse_requirement(line: str) -> dict[str, str]:
    match = _REQ.match(line)
    if not match:
        raise ValueError(f"unsupported requirement line: {line!r}")
    return {
        "name": match.group("name"),
        "constraint": (match.group("constraint") or "").strip(),
        "marker": (match.group("marker") or "").strip(),
    }


def _metadata(name: str) -> tuple[str, str]:
    try:
        package = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return "missing", ""
    license_name = (package.metadata.get("License") or "").strip()
    if not license_name:
        classifiers = package.metadata.get_all("Classifier") or []
        licenses = [
            item.split(" :: ")[-1] for item in classifiers if "License ::" in item
        ]
        license_name = "; ".join(licenses)
    return package.version, license_name


def audit_requirements(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        requirement = parse_requirement(line)
        installed, license_name = _metadata(requirement["name"])
        records.append(
            {
                **requirement,
                "installed": installed,
                "license": license_name or "metadata-unreported",
                "native": requirement["name"] in _NATIVE_HINTS,
                "platform": sys.platform,
                "purpose": _PURPOSES.get(
                    requirement["name"], "direct production dependency"
                ),
                "security_status": "not_scanned",
                "deprecation_status": "manual_review",
                "review": "compatibility-and-security-review-required",
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = {
        "schema": 1,
        "requirements": str(args.requirements),
        "records": audit_requirements(args.requirements),
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
