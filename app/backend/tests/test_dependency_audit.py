import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_dependencies import audit_requirements, parse_requirement


class DependencyAuditTests(unittest.TestCase):
    def test_parser_keeps_name_constraint_and_marker(self):
        record = parse_requirement("PyAudioWPatch>=0.2.12.7; sys_platform == 'win32'")
        self.assertEqual("PyAudioWPatch", record["name"])
        self.assertEqual(">=0.2.12.7", record["constraint"])
        self.assertEqual("sys_platform == 'win32'", record["marker"])

    def test_audit_records_installed_version_and_native_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "requirements.txt"
            output = Path(tmp) / "audit.json"
            requirements.write_text(
                "onnxruntime==1.21.1\nrequests>=2.0\n", encoding="utf-8"
            )
            with patch(
                "scripts.audit_dependencies.metadata.version",
                side_effect={"onnxruntime": "1.21.1", "requests": "2.32.0"}.get,
            ):
                records = audit_requirements(requirements)
            self.assertEqual(2, len(records))
            self.assertEqual("1.21.1", records[0]["installed"])
            self.assertTrue(records[0]["native"])
            self.assertEqual("local ONNX inference", records[0]["purpose"])
            self.assertIn("platform", records[0])
            self.assertEqual("not_scanned", records[0]["security_status"])
            self.assertFalse(records[1]["native"])
            output.write_text(json.dumps(records), encoding="utf-8")
            self.assertEqual(2, len(json.loads(output.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
