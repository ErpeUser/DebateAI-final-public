"""Emission-time near-duplicate suppression (ALP-286).

The reference meeting (session 99985052, 57 minutes, internal_checkin) produced
199 insights, and the synthesizer later merged 21 of them away as duplicates.
The median gap between a merged pair was 1.0 minute and 90 percent were within
2.1 minutes, so the old 60-second window structurally could not see 13 of the
21 -- they were caught afterwards by the synthesizer at full corpus cost.

The pairs below are real insight texts from that meeting.
"""

import time
import unittest
from unittest.mock import patch

from app.services.agents.orchestrator import AgentOrchestrator, _DEDUP_WINDOW_SECONDS, _texts_similar

# (earlier text, later text, gap in seconds) drawn from the reference meeting.
MERGED_PAIRS = [
    (
        "Develop standardized AI governance enablement playbooks and reusable artifact"
        " repositories to streamline project onboarding",
        "Develop an internal AI Governance Enablement Playbook and reusable artifact"
        " repository to streamline project onboarding",
        54,
    ),
    (
        "The organization uses a three-stage agile go-to-market model for AI topics,"
        " funneling field patterns into bi-weekly 30-minute pitch sessions",
        "The organization uses a multi-stage agile go-to-market model for AI topics,"
        " funneling field patterns into bi-weekly 30-minute pitch sessions",
        66,
    ),
    (
        "Develop a standardized cross-practice enablement framework and pitch repository"
        " for field CTOs covering Cyber, Total Experience",
        "Develop a unified cross-practice enablement matrix and standard pitch/handoff"
        " guide for Field CTOs covering Cyber, Total Experience",
        60,
    ),
]


def _prune(recent: dict[str, float], now: float) -> dict[str, float]:
    """The window prune from _save_and_send_insight, isolated from the DB."""
    return {k: v for k, v in recent.items() if now - v < _DEDUP_WINDOW_SECONDS}


class DedupWindowTests(unittest.TestCase):
    def test_window_covers_the_observed_restatement_distribution(self):
        # 90 percent of merged pairs were within 2.1 minutes; the window needs
        # headroom past that or the synthesizer keeps paying to merge them.
        self.assertGreaterEqual(_DEDUP_WINDOW_SECONDS, 126)

    def test_real_restatements_are_caught_at_their_actual_gap(self):
        for earlier, later, gap in MERGED_PAIRS:
            with self.subTest(text=earlier[:40]):
                start = time.time()
                recent = {earlier: start}
                # Fast-forward to when the restatement actually arrived.
                surviving = _prune(recent, start + gap)
                self.assertIn(
                    earlier, surviving, "entry aged out before its restatement arrived"
                )
                self.assertTrue(_texts_similar(later, earlier))

    def test_the_old_sixty_second_window_would_have_missed_them(self):
        # Documents the regression this change fixes: at 60s, two of the three
        # pairs above had already aged out of the map when the restatement came.
        aged_out = [gap for _, _, gap in MERGED_PAIRS if gap >= 60]
        self.assertTrue(aged_out)

    def test_entries_still_age_out_eventually(self):
        start = time.time()
        recent = {"some insight text": start}
        self.assertEqual({}, _prune(recent, start + _DEDUP_WINDOW_SECONDS + 1))


class TextSimilarityTests(unittest.TestCase):
    def test_changed_numbers_are_not_deduplicated(self):
        self.assertFalse(
            _texts_similar(
                "Die Reform senkt die Kosten um 10 Prozent",
                "Die Reform senkt die Kosten um 20 Prozent",
            )
        )

    def test_changed_negation_is_not_deduplicated(self):
        self.assertFalse(
            _texts_similar(
                "Die Reform senkt die Kosten",
                "Die Reform senkt die Kosten nicht",
            )
        )

    def test_changed_time_scope_is_not_deduplicated(self):
        self.assertFalse(
            _texts_similar(
                "Die Reform senkt die Kosten ab 2027",
                "Die Reform senkt die Kosten ab 2028",
            )
        )

    def test_added_condition_is_not_deduplicated(self):
        self.assertFalse(
            _texts_similar(
                "Die Reform senkt die Kosten",
                "Wenn die Nachfrage steigt, senkt die Reform die Kosten",
            )
        )

    def test_unrelated_insights_are_not_merged(self):
        self.assertFalse(
            _texts_similar(
                "Develop an internal AI Governance Enablement Playbook",
                "Budget approval for the data center refresh slipped to Q3",
            )
        )

    def test_empty_text_never_matches(self):
        self.assertFalse(_texts_similar("", "anything at all"))
        self.assertFalse(_texts_similar("anything at all", ""))


class EmissionLookupTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = object.__new__(AgentOrchestrator)
        self.orchestrator._recent_insights = {}

    def test_lookup_does_not_remember_an_uncommitted_candidate(self):
        text = "Validate the rollout plan with the project team"
        self.assertFalse(self.orchestrator._is_duplicate_insight(text))
        self.assertFalse(self.orchestrator._is_duplicate_insight(text))
        self.assertEqual(self.orchestrator._recent_insights, {})

    def test_lookup_does_not_extend_or_prune_committed_history(self):
        text = "Validate the rollout plan with the project team"
        with patch("app.services.agents.orchestrator.time.time", return_value=1000.0):
            self.orchestrator._remember_committed_insight(text)
        history = self.orchestrator._recent_insights.copy()
        with patch("app.services.agents.orchestrator.time.time", return_value=1100.0):
            self.assertTrue(self.orchestrator._is_duplicate_insight(text))
        with patch("app.services.agents.orchestrator.time.time", return_value=1300.0):
            self.assertFalse(self.orchestrator._is_duplicate_insight(text))
        self.assertEqual(self.orchestrator._recent_insights, history)

    def test_successful_remember_prunes_expired_emissions(self):
        with patch("app.services.agents.orchestrator.time.time", return_value=1000.0):
            self.orchestrator._remember_committed_insight("Validate the rollout plan")
        with patch("app.services.agents.orchestrator.time.time", return_value=1301.0):
            self.orchestrator._remember_committed_insight("Discuss the separate budget approval")
            self.assertFalse(self.orchestrator._is_duplicate_insight("Validate the rollout plan"))
            self.assertTrue(self.orchestrator._is_duplicate_insight("Discuss the separate budget approval"))
        self.assertEqual(len(self.orchestrator._recent_insights), 1)


if __name__ == "__main__":
    unittest.main()
