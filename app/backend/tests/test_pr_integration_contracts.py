"""Regressions for combining review PRs 11, 12 and 13 without live providers."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.services import debate_research, external_audit


class AuditMergeContractTests(unittest.TestCase):
    def test_raw_hex_claim_is_not_mistaken_for_a_trusted_digest(self):
        raw = "0123456789abcdef0123456789abcdef"
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(
                external_audit, "_audit_path", return_value=Path(tmp) / "events.jsonl"
            ),
        ):
            external_audit.record_external_request(
                provider_route="test", approval=False, status="blocked", claim_id=raw
            )
            records = [
                json.loads(line)
                for line in external_audit._audit_path().read_text().splitlines()
            ]
        self.assertEqual(records[0]["claim_id"], expected)
        self.assertNotEqual(records[0]["claim_id"], raw)

    def test_explicit_trusted_claim_survives_cancelled_lifecycle(self):
        claim = "synthetic merge regression"
        expected = hashlib.sha256(claim.encode("utf-8")).hexdigest()[:32]
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(
                external_audit, "_audit_path", return_value=Path(tmp) / "events.jsonl"
            ),
        ):
            with external_audit.audit_context(claim=claim, approval=False):
                request_id = external_audit.start_external_request(
                    provider_route="test",
                    approval=False,
                    claim_id=external_audit.current_claim_id(),
                )
                external_audit.finish_external_request(
                    request_id,
                    provider_route="test",
                    approval=False,
                    status="cancelled",
                )
            records = [
                json.loads(line)
                for line in external_audit._audit_path().read_text().splitlines()
            ]
        self.assertEqual([row["claim_id"] for row in records], [expected, expected])
        self.assertEqual(
            [row["request_id"] for row in records], [request_id, request_id]
        )
        self.assertEqual([row["status"] for row in records], ["started", "cancelled"])
        self.assertTrue(all(row["approval"] is False for row in records))


class ResearchApprovalMergeTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_inherits_real_outer_approval_without_mocking_getter(self):
        for approved in (False, True):
            with self.subTest(approved=approved):
                observed = []

                async def fake_generate_text(*_args, **_kwargs):
                    observed.append(external_audit.current_approval())
                    return "https://example.org/source"

                with external_audit.audit_context(approval=approved):
                    with (
                        mock.patch.object(
                            debate_research,
                            "_research_provider_ready",
                            return_value=True,
                        ),
                        mock.patch(
                            "app.services.llm.generate_text", new=fake_generate_text
                        ),
                    ):
                        sources = await debate_research._ai_web_sources(
                            "A public synthetic claim",
                            "Find a public source",
                            ["gemini_api"],
                        )
                    self.assertEqual(external_audit.current_approval(), approved)
                self.assertEqual(observed, [approved])
                self.assertEqual(
                    [source.url for source in sources], ["https://example.org/source"]
                )


if __name__ == "__main__":
    unittest.main()
