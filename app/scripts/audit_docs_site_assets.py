#!/usr/bin/env python3
"""Check that local links and assets in a built docs-site snapshot exist.

The check is deliberately filesystem-only. External URLs and API routes are
left to the site/integration tests; local routes and static assets must be
present in the distributable snapshot or the audit fails with path-only
findings.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

_ATTR_RE = re.compile(r"(?P<attr>href|src)\s*=\s*['\"](?P<value>[^'\"]+)['\"]", re.I)
_CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)
_SKIP_SCHEMES = {"data", "mailto", "tel", "javascript", "blob"}
_SKIP_ROUTE_PREFIXES = ("/api/", "/cdn-cgi/")
_ROUTE_ALIASES = {
    "/admin.css": "/admin/admin.css",
    "/admin.js": "/admin/admin.js",
    "/admin-core.js": "/admin/admin-core.js",
    "/early-access.js": "/admin/early-access.js",
    "/users.js": "/admin/users.js",
    "/authorization.js": "/admin/authorization.js",
    "/downloads.css": "/downloads/downloads.css",
    "/downloads.js": "/downloads/downloads.js",
}


def _local_reference(value: str, *, attribute: str = "src") -> str | None:
    value = value.strip()
    if not value or value.startswith("#") or value.startswith("//"):
        return None
    parsed = urlsplit(value)
    if parsed.scheme.lower() in _SKIP_SCHEMES or parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path or path.startswith(_SKIP_ROUTE_PREFIXES):
        return None
    # Extensionless hrefs are application routes. Static assets referenced by
    # href (stylesheets, manifests, JSON baselines) retain an extension and
    # are checked; dynamic admin/download routes are covered by worker tests.
    if attribute == "href" and not path.endswith("/") and not Path(path).suffix:
        return None
    return _ROUTE_ALIASES.get(path, path)


def _resolve(root: Path, source: Path, path: str) -> Path | None:
    candidate = root / path.lstrip("/") if path.startswith("/") else source.parent / path
    try:
        candidate = candidate.resolve()
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def audit(snapshot: Path) -> list[dict[str, str]]:
    root = Path(snapshot).resolve()
    findings: list[dict[str, str]] = []
    if not root.is_dir():
        return [{"rule": "missing_snapshot", "path": root.as_posix()}]
    for source in sorted(root.rglob("*")):
        if source.suffix.lower() not in {".html", ".css"} or not source.is_file():
            continue
        text = source.read_text(encoding="utf-8", errors="ignore")
        values = (
            [(match.group("attr"), match.group("value")) for match in _ATTR_RE.finditer(text)]
            if source.suffix.lower() == ".html"
            else []
        )
        # CSS ``url(...)`` references are meaningful only in stylesheets.  Do
        # not scan HTML prose/code for the same pattern: documentation often
        # discusses the syntax literally (for example ``url(...)``), and
        # treating the placeholder as a path creates a false missing-asset
        # finding in the assembled docs snapshot.
        if source.suffix.lower() == ".css":
            values.extend(("css", value) for value in _CSS_URL_RE.findall(text))
        for attribute, value in values:
            path = _local_reference(value, attribute=attribute)
            if path is None:
                continue
            target = _resolve(root, source, path)
            if target is None or not target.is_file():
                findings.append(
                    {
                        "rule": "missing_local_asset",
                        "path": source.relative_to(root).as_posix(),
                        "reference": value,
                    }
                )
    return sorted(findings, key=lambda item: (item["path"], item["reference"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    findings = audit(args.snapshot)
    for finding in findings:
        print(f"{finding['rule']}: {finding['path']} -> {finding['reference']}")
    if not findings:
        print(f"Docs-site asset audit OK: {args.snapshot}")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
