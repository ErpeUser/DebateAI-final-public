from app.services.video_eval_pipeline import (
    SourceCandidate,
    TranscriptSegment,
    build_eval_cases,
    build_rhetorical_profile,
    extract_source_candidates,
)


def test_extract_source_candidates_keeps_urls_dois_and_study_years():
    text = "Siehe https://example.org/report, DOI 10.1234/ABC-1 und Studie zur Wirkung 2021."
    rows = extract_source_candidates(text)
    assert {row.kind for row in rows} == {"url", "doi", "study_reference"}
    assert any(row.value == "https://example.org/report" for row in rows)


def test_rhetorical_profile_counts_debate_moves():
    segments = [
        TranscriptSegment(0, 2, "Ist das wirklich immer so?"),
        TranscriptSegment(2, 5, "Nein, aber ein Beispiel ist der Handytarif."),
        TranscriptSegment(5, 8, "Das stimmt nicht, weil der Maßstab sonst doppelt wäre."),
    ]
    profile = build_rhetorical_profile(segments, source_candidates=[])
    assert profile["question_rate"] > 0
    assert profile["rebuttal_rate"] > 0
    assert profile["analogy_rate"] > 0


def test_eval_cases_do_not_turn_transcript_into_ground_truth():
    segments = [TranscriptSegment(0, 2, "Alles wird teurer.", speaker="S1")]
    candidates = [SourceCandidate("10.1234/x", "doi", "context", 0)]
    cases = build_eval_cases(segments, source_candidates=candidates)
    assert cases[0]["expected_response"] == ""
    assert cases[0]["difficulty"] == "source_check"
    assert cases[0]["source_candidates"] == ["10.1234/x"]
