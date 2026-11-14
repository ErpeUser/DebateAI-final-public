from app.services.agents.objection_handler import (
    DebateRecommendation,
    normalize_experimental_strategies,
)


def test_experimental_strategy_normalizer_produces_four_moves():
    recommendation = DebateRecommendation(
        target_claim="Töten ist schlecht.",
        answer_now="Notwehr ist ein Gegenbeispiel.",
        counterargument="Nicht jedes Töten ist schlecht.",
        counter_question="Ist Notwehr dann auch schlecht?",
        analogy="Wenn jemand dich angreift, darfst du dich schützen.",
    )
    options = normalize_experimental_strategies(recommendation)
    assert [item["kind"] for item in options] == [
        "contradiction",
        "example",
        "counter_question",
        "refutation",
    ]
    assert options[1]["text"] == recommendation.analogy


def test_experimental_fields_are_optional_for_standard_clients():
    recommendation = DebateRecommendation(target_claim="Claim")
    assert recommendation.pipeline_mode == "standard"
    assert recommendation.strategy_options == []
