import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.services.prompt_optimization import (
    EvaluationResult,
    OptimizationPolicy,
    PromptOptimizationStore,
    candidate_digest,
    compare_evaluations,
)


class PromptOptimizationEvaluationTests(unittest.TestCase):
    def test_holdout_regression_blocks_candidate_even_when_fixed_cases_improve(self):
        baseline = [
            EvaluationResult("fixed-1", "fixed", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}),
            EvaluationResult("holdout-1", "holdout", {"naturalness": .8, "factuality": .9, "argument_strength": .8, "source_honesty": .9, "latency_ms": 100}),
        ]
        candidate = [
            EvaluationResult("fixed-1", "fixed", {"naturalness": .9, "factuality": .9, "argument_strength": .9, "source_honesty": .9, "latency_ms": 100}),
            EvaluationResult("holdout-1", "holdout", {"naturalness": .4, "factuality": .7, "argument_strength": .4, "source_honesty": .6, "latency_ms": 100}),
        ]
        decision = compare_evaluations(baseline, candidate)
        self.assertFalse(decision.approved)
        self.assertIn("holdout", " ".join(decision.reasons).lower())
        self.assertIn("factuality", " ".join(decision.reasons).lower())

    def test_candidate_digest_is_stable_and_changes_with_content(self):
        first = candidate_digest("prompt A")
        self.assertEqual(first, candidate_digest("prompt A"))
        self.assertNotEqual(first, candidate_digest("prompt B"))
        self.assertEqual(64, len(first))


class PromptOptimizationStoreTests(unittest.TestCase):
    def test_manual_apply_records_audit_and_rollback_restores_previous_content(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            prompt_path = root / "answer.txt"
            prompt_path.write_text("old prompt\n", encoding="utf-8")
            store = PromptOptimizationStore(root)
            policy = OptimizationPolicy()
            baseline = [
                EvaluationResult("case-1", "fixed", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}),
                EvaluationResult("holdout-1", "holdout", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}),
            ]
            candidate = [
                EvaluationResult("case-1", "fixed", {"naturalness": .8, "factuality": .9, "argument_strength": .8, "source_honesty": .9, "latency_ms": 100}),
                EvaluationResult("holdout-1", "holdout", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}),
            ]
            result = store.apply(
                prompt_name="answer",
                candidate_content="new prompt",
                rationale="remove meta phrasing",
                baseline_results=baseline,
                candidate_results=candidate,
                policy=policy,
                approved_by_user=True,
            )
            self.assertEqual("applied", result["status"])
            self.assertEqual("new prompt", prompt_path.read_text(encoding="utf-8").strip())
            self.assertEqual(candidate_digest("new prompt"), result["candidate_hash"])
            state = json.loads((root / "optimization-state.json").read_text(encoding="utf-8"))
            self.assertEqual("answer", state["active"]["prompt_name"])
            restored = store.rollback("answer")
            self.assertEqual("rolled_back", restored["status"])
            self.assertEqual("old prompt", prompt_path.read_text(encoding="utf-8").strip())

    def test_auto_apply_requires_explicit_enable_and_rejects_holdout_failure(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "answer.txt").write_text("old", encoding="utf-8")
            store = PromptOptimizationStore(root)
            baseline = [EvaluationResult("case-1", "holdout", {"naturalness": .8, "factuality": .9, "argument_strength": .8, "source_honesty": .9, "latency_ms": 100})]
            candidate = [EvaluationResult("case-1", "holdout", {"naturalness": .4, "factuality": .4, "argument_strength": .4, "source_honesty": .4, "latency_ms": 100})]
            with self.assertRaisesRegex(ValueError, "explicit"):
                store.apply(
                    prompt_name="answer",
                    candidate_content="new",
                    rationale="test",
                    baseline_results=baseline,
                    candidate_results=candidate,
                    policy=OptimizationPolicy(auto_apply_enabled=True),
                    auto_apply=True,
                    explicit_auto_apply=False,
                )
            rejected = store.apply(
                prompt_name="answer",
                candidate_content="new",
                rationale="test",
                baseline_results=baseline,
                candidate_results=candidate,
                policy=OptimizationPolicy(auto_apply_enabled=True),
                auto_apply=True,
                explicit_auto_apply=True,
            )
            self.assertEqual("rejected", rejected["status"])
            self.assertEqual("old", (root / "answer.txt").read_text(encoding="utf-8"))

    def test_invalid_prompt_placeholder_is_rejected_before_activation(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "debate_deep_v1.txt").write_text("{claim} {own_position} {relevant_context} {evidence}", encoding="utf-8")
            store = PromptOptimizationStore(root)
            base = [EvaluationResult("case", "holdout", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100})]
            with self.assertRaisesRegex(ValueError, "platzhalter"):
                store.apply("debate_deep_v1", "{claim} {unknown}", "bad", base, base, OptimizationPolicy(), approved_by_user=True)

    def test_regression_automatically_rolls_back_the_active_candidate(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "answer.txt"
            path.write_text("old", encoding="utf-8")
            store = PromptOptimizationStore(root)
            baseline = [EvaluationResult("holdout", "holdout", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100})]
            improved = [EvaluationResult("holdout", "holdout", {"naturalness": .8, "factuality": .9, "argument_strength": .8, "source_honesty": .9, "latency_ms": 100})]
            store.apply("answer", "candidate", "test", baseline, improved, OptimizationPolicy(), approved_by_user=True)
            regressed = [EvaluationResult("holdout", "holdout", {"naturalness": .3, "factuality": .4, "argument_strength": .3, "source_honesty": .4, "latency_ms": 100})]
            result = store.rollback_if_regressed("answer", improved, regressed)
            self.assertEqual("rolled_back", result["status"])
            self.assertEqual("old", path.read_text(encoding="utf-8").strip())

    def test_manual_apply_requires_approval_and_preserves_user_prompt(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "answer.txt"
            path.write_text("user prompt", encoding="utf-8")
            store = PromptOptimizationStore(root)
            base = [EvaluationResult("case", "fixed", {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100})]
            with self.assertRaisesRegex(ValueError, "approval"):
                store.apply("answer", "candidate", "reason", base, base, OptimizationPolicy())
            path.write_text("user edited prompt", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "user"):
                store.apply("answer", "candidate", "reason", base, base, OptimizationPolicy(), approved_by_user=True, user_managed=True)


class MissingScoreRegressionTests(unittest.TestCase):
    def test_missing_candidate_quality_metric_cannot_masquerade_as_zero(self):
        baseline = [EvaluationResult("holdout", "holdout", {"naturalness": 0.8, "factuality": 0.9, "source_honesty": 0.9})]
        candidate = [EvaluationResult("holdout", "holdout", {"factuality": 0.9, "source_honesty": 0.9})]
        decision = compare_evaluations(baseline, candidate)
        self.assertFalse(decision.approved)
        self.assertTrue(any("naturalness" in reason for reason in decision.reasons))

    def test_missing_baseline_metric_cannot_create_false_quality_gain(self):
        baseline = [EvaluationResult("holdout", "holdout", {"factuality": 0.9, "source_honesty": 0.9})]
        candidate = [EvaluationResult("holdout", "holdout", {"naturalness": 0.9, "factuality": 0.9, "source_honesty": 0.9})]
        decision = compare_evaluations(baseline, candidate)
        self.assertFalse(decision.approved)
