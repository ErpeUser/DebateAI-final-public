from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOTS = (
    ROOT / "backend" / "app",
    ROOT / "desktop" / "debateai_desktop",
    ROOT / "desktop" / "launcher.py",
    ROOT / "desktop" / "updater.py",
    ROOT / "frontend" / "src",
    ROOT / "scripts",
)
TEXT_SUFFIXES = {
    ".cjs",
    ".css",
    ".html",
    ".js",
    ".json",
    ".mjs",
    ".patch",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".yml",
    ".yaml",
}
FORBIDDEN = (
    re.compile(r"BACKCHANNEL_[A-Z0-9_]+"),
    re.compile(r"X-Backchannel-Instance"),
    re.compile(r"\bbcdesktop\b"),
    re.compile(r"backchannel\.spec"),
    re.compile(r"Backchannel\.exe"),
    re.compile(r"(?:downloads|signing)\.backchannel\.page"),
)


def _runtime_files():
    for root in RUNTIME_ROOTS:
        if root.is_file():
            yield root
            continue
        if root.is_dir():
            yield from (
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
            )


def test_active_runtime_has_no_legacy_identity_identifiers():
    violations = []
    for path in _runtime_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                violations.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
    assert not violations, "legacy runtime identifiers found:\n" + "\n".join(violations)
