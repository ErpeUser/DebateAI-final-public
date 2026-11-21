from app.services.video_eval_evaluator import (
    EvalCaseRecord,
    build_split_manifest,
    score_blind_pairs,
)


def test_split_keeps_video_and_claim_families_together():
    records = [
        EvalCaseRecord("a1", "video-a", "Prices rose", "family-a"),
        EvalCaseRecord("a2", "video-a", "Prices rose again", "family-a"),
        EvalCaseRecord("b1", "video-b", "Taxes changed", "family-b"),
        EvalCaseRecord("c1", "video-c", "A new example", "family-c"),
        EvalCaseRecord("d1", "video-d", "Another claim", "family-d"),
        EvalCaseRecord("e1", "video-e", "Final claim", "family-e"),
    ]
    manifest = build_split_manifest(records, seed="test")
    assert manifest.leakage_checks["passed"] is True
    assert sum(len(rows) for rows in manifest.splits.values()) == len(records)
    assert manifest.blind_pairs
    assert all(row["blind"] for row in manifest.blind_pairs)


def test_blind_scores_are_aggregated_without_revealing_labels():
    result = score_blind_pairs(
        [
            {"decision": "a"},
            {"decision": "b"},
            {"decision": "tie"},
            {"decision": ""},
        ]
    )
    assert result == {
        "pairs": 4,
        "scored": 3,
        "a_wins": 1,
        "b_wins": 1,
        "ties": 1,
        "completion": 0.75,
    }
