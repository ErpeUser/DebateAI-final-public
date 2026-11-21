"""Regression tests for the credential-free outbound request audit."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import external_audit


class ExternalAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.audit_file = Path(self.tmp.name) / "external-requests.jsonl"
        self.path_patch = patch.object(
            external_audit, "_audit_path", lambda: self.audit_file
        )
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def _records(self):
        return [
            json.loads(line)
            for line in self.audit_file.read_text(encoding="utf-8").splitlines()
        ]

    def test_request_lifecycle_contains_required_fields_without_secrets(self):
        claim = "The private customer claim must never be written to the audit file."
        with external_audit.audit_context(
            claim=claim,
            data_category="research_claim",
            approval=False,
        ):
            request_id = external_audit.start_external_request(
                provider_route="chatgpt-web:gpt-6",
                approval=external_audit.current_approval(),
                data_category=external_audit.current_data_category(),
                target_host="https://user:secret@example.test/search?api_key=token",
            )
            external_audit.finish_external_request(
                request_id,
                approval=external_audit.current_approval(),
                status="failed",
                provider_route="chatgpt-web:gpt-6",
                data_category=external_audit.current_data_category(),
                error_class="HTTPStatusError",
            )

        records = self._records()
        self.assertEqual([item["status"] for item in records], ["started", "failed"])
        for item in records:
            self.assertIn("timestamp", item)
            self.assertIn("provider_route", item)
            self.assertIn("approval", item)
            self.assertIn("data_category", item)
            self.assertIn("claim_id", item)
            self.assertIn("status", item)
            self.assertFalse(item["approval"])
            self.assertEqual(item["data_category"], "research_claim")
            self.assertEqual(item["claim_id"], external_audit.claim_id_for(claim))
        serialized = self.audit_file.read_text(encoding="utf-8")
        for secret in (
            "secret",
            "api_key",
            "token",
            "customer claim",
            "cookie",
            "prompt",
        ):
            self.assertNotIn(secret, serialized)

    def test_context_is_scoped_and_source_categories_are_bounded(self):
        self.assertTrue(external_audit.current_approval())
        self.assertEqual(external_audit.current_data_category(), "unknown")
        with external_audit.audit_context(
            claim="A",
            data_category="source_document",
            approval=False,
        ):
            self.assertFalse(external_audit.current_approval())
            self.assertEqual(
                external_audit.data_category_for_source("video_transcript"),
                "transcript_excerpt",
            )
        self.assertTrue(external_audit.current_approval())
        self.assertEqual(external_audit.current_claim_id(), "")

    def test_explicit_digest_and_context_keep_one_claim_across_request_lifecycle(self):
        expected = external_audit.claim_id_for("synthetic research claim")
        with external_audit.audit_context(claim="synthetic research claim"):
            request_id = external_audit.start_external_request(
                provider_route="test",
                approval=True,
                claim_id=external_audit.current_claim_id(),
            )
            external_audit.finish_external_request(
                request_id, provider_route="test", approval=True, status="completed"
            )
        self.assertEqual(
            [row["claim_id"] for row in self._records()], [expected, expected]
        )

    def test_independent_digest_is_preserved_but_untrusted_text_is_hashed(self):
        digest = external_audit.claim_id_for("different synthetic claim")
        raw = "0123456789abcdef0123456789abcdef"
        for value in (digest, raw):
            external_audit.record_external_request(
                provider_route="test", approval=True, status="started", claim_id=value
            )
        self.assertEqual(
            [row["claim_id"] for row in self._records()],
            [digest, external_audit.claim_id_for(raw)],
        )


if __name__ == "__main__":
    unittest.main()
