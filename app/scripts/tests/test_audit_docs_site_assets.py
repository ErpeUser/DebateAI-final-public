import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "audit_docs_site_assets.py"
SPEC = importlib.util.spec_from_file_location("audit_docs_site_assets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DocsSiteAssetAuditTests(unittest.TestCase):
    def make_snapshot(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "assets").mkdir()
        (root / "assets" / "logo.svg").write_text("<svg />", encoding="utf-8")
        (root / "index.html").write_text(
            '<link href="/assets/site.css"><img src="/assets/logo.svg">'
            '<a href="/docs/">Docs</a><a href="https://example.com">External</a>'
            '<code>CSS url(...)</code>',
            encoding="utf-8",
        )
        (root / "docs").mkdir()
        (root / "docs" / "index.html").write_text("ok", encoding="utf-8")
        (root / "assets" / "site.css").write_text(
            'body { background: url("/assets/logo.svg"); }', encoding="utf-8"
        )
        return root

    def test_built_snapshot_accepts_local_routes_assets_and_external_urls(self):
        self.assertEqual([], MODULE.audit(self.make_snapshot()))

    def test_worker_asset_aliases_resolve_to_private_snapshot_assets(self):
        root = self.make_snapshot()
        (root / "admin").mkdir()
        (root / "admin" / "admin.css").write_text("body {}", encoding="utf-8")
        (root / "admin" / "admin.js").write_text("", encoding="utf-8")
        (root / "admin" / "admin-core.js").write_text("", encoding="utf-8")
        (root / "index.html").write_text(
            '<link rel="stylesheet" href="/admin.css?v=1">'
            '<script src="/admin.js#route"></script>'
            '<script src="/admin-core.js"></script>',
            encoding="utf-8",
        )
        self.assertEqual([], MODULE.audit(root))

    def test_missing_local_reference_is_reported_without_reading_content(self):
        root = self.make_snapshot()
        (root / "index.html").write_text(
            '<img src="/assets/missing.webp">', encoding="utf-8"
        )
        findings = MODULE.audit(root)
        self.assertEqual({"missing_local_asset"}, {item["rule"] for item in findings})
        self.assertEqual("/assets/missing.webp", findings[0]["reference"])


if __name__ == "__main__":
    unittest.main()
