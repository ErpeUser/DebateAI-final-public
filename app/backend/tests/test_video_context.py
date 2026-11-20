import json
from datetime import UTC, datetime

import pytest

from app.services.video_context import (
    CheckpointStore,
    ErrorKind,
    RolloverAction,
    classify_error,
    merge_checkpoints,
    rollover_action,
    segment_context,
    validate_response,
)


def test_error_kinds_are_distinct_and_rollover_is_limited_to_context_failures():
    assert classify_error("HTTP 413 request entity too large") is ErrorKind.MESSAGE_TOO_LARGE
    assert classify_error("maximum context length is 128k tokens") is ErrorKind.CONTEXT_FULL
    assert classify_error("429 rate limit exceeded") is ErrorKind.RATE_LIMIT
    assert classify_error("please log in to continue") is ErrorKind.PROVIDER_ACCESS
    assert classify_error("browser_busy") is ErrorKind.BROWSER_BUSY

    assert rollover_action(ErrorKind.MESSAGE_TOO_LARGE) is RolloverAction.ROLLOVER
    assert rollover_action(ErrorKind.CONTEXT_FULL) is RolloverAction.ROLLOVER
    assert rollover_action(ErrorKind.RATE_LIMIT) is RolloverAction.NONE
    assert rollover_action(ErrorKind.PROVIDER_ACCESS) is RolloverAction.NONE


def test_segment_context_respects_token_budget_and_has_stable_ids_and_overlap():
    source = (
        "00:00 Alice: First sentence is complete. Second sentence follows.\n"
        "00:04 Bob: A topic starts here.\n\n"
        "00:08 Alice: The final sentence closes the topic."
    )
    first = segment_context(source, max_tokens=28, overlap_tokens=12)
    second = segment_context(source, max_tokens=28, overlap_tokens=12)
    assert first == second
    assert len(first) > 1
    assert all(chunk.token_estimate <= 28 for chunk in first)
    assert any(first[index].text.splitlines()[-1] in first[index + 1].text for index in range(len(first) - 1))
    assert all(chunk.chunk_id and chunk.start_ts is not None for chunk in first)


def test_validate_response_rejects_malformed_and_truncated_payloads():
    assert validate_response('{"answer":"ok"}') == {"answer": "ok"}
    with pytest.raises(ValueError, match="malformed"):
        validate_response('{"answer":"unterminated}')
    with pytest.raises(ValueError, match="truncated"):
        validate_response({"answer": "partial", "finish_reason": "length"})


def test_checkpoint_store_and_merge_are_deterministic_and_do_not_persist_secrets(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoint.json")
    timestamp = datetime(2026, 1, 2, tzinfo=UTC)
    checkpoint = {
        "session_id": "session-1",
        "chunks": [{"chunk_id": "a", "text": "one", "start_ts": timestamp.isoformat()}],
        "completed": ["a"],
        "responses": {"a": "answer"},
        "api_key": "sk-secret",
    }
    store.save(checkpoint)
    loaded = store.load()
    assert loaded["completed"] == ["a"]
    assert "api_key" not in loaded
    assert "sk-secret" not in json.dumps(loaded)
    merged = merge_checkpoints(loaded, {"chunks": [{"chunk_id": "a", "text": "one"}, {"chunk_id": "b", "text": "two"}], "completed": ["b"], "responses": {"a": "answer"}})
    assert [chunk["chunk_id"] for chunk in merged["chunks"]] == ["a", "b"]
    assert merged["completed"] == ["a", "b"]


@pytest.mark.asyncio
async def test_context_rollover_only_for_context_errors_and_resumes_from_checkpoint(tmp_path):
    from app.services.video_context import CheckpointStore, run_with_context_rollover

    calls = []

    async def first_chat(prompt):
        calls.append(("old", prompt))
        if len(calls) == 2:
            raise RuntimeError("maximum context length")
        return {"answer": "ok"}

    async def replacement_chat(prompt):
        calls.append(("new", prompt))
        return {"answer": "ok"}

    result = await run_with_context_rollover(
        "First sentence. Second sentence. Third sentence.",
        call=first_chat,
        new_chat=replacement_chat,
        checkpoint_store=CheckpointStore(tmp_path / "context.json"),
        session_id="session-1",
        max_tokens=3,
        overlap_tokens=1,
    )
    assert result["status"] == "completed"
    assert any(kind == "new" for kind, _ in calls)
    assert "api_key" not in json.dumps(result)


@pytest.mark.asyncio
async def test_context_rollover_does_not_bypass_rate_limit(tmp_path):
    from app.services.video_context import CheckpointStore, run_with_context_rollover

    calls = []

    async def rate_limited(_prompt):
        calls.append("old")
        raise RuntimeError("429 rate limit exceeded")

    async def should_not_run(_prompt):
        calls.append("new")
        return {"answer": "unexpected"}

    result = await run_with_context_rollover(
        "One sentence.",
        call=rate_limited,
        new_chat=should_not_run,
        checkpoint_store=CheckpointStore(tmp_path / "rate.json"),
        session_id="session-2",
    )
    assert result["status"] == "failed"
    assert result["error_kind"] == "rate_limit"
    assert calls == ["old"]
