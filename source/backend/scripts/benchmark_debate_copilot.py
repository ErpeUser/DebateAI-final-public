    try:
        live_agent = ObjectionHandlerAgent(
            model_override=app_model_id,
            recommendation_only=True,
            style_focus="natural",
            debate_mode=mode,
        )
        prompt_template_sha256 = hashlib.sha256(
            live_agent._current_prompt_template().encode("utf-8")
        ).hexdigest()
        replay = create_application_replay(live_agent)
        records: list[dict] = []
        for index, turn in enumerate(turns):
            records.append(
                await replay.measure_turn(
                    dict(turn),
                    turn_index=index,
                    timeout_seconds=args.timeout,
                )
            )

        if getattr(args, "skip_probes", False):
            probe = {
                "status": "not_requested",
                "cancellation_count": 0,
                "failure_count": 0,
                "stale_publishes": 0,
            }
            interim_probe = {"status": "not_requested", "stale_publishes": 0}
            spoken_playbook_probe = {"status": "not_requested", "stale_publishes": 0}
        elif replay._unavailable:
            probe = {
                "status": "not_run_after_timeout",
                "cancellation_count": 0,
                "failure_count": 1,
                "stale_publishes": 0,
            }
            interim_probe = {"status": "not_run_after_timeout", "stale_publishes": 0}
            spoken_playbook_probe = {"status": "not_run_after_timeout", "stale_publishes": 0}
        else:
            probe_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            probe = await probe_replay.supersession_probe(
                turns[: min(3, len(turns))],
                delay_seconds=args.cancellation_delay_ms / 1000.0,
                timeout_seconds=args.timeout,
            )
            interim_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            interim_probe = await interim_replay.interim_continuation_probe(
                partial="Solarstrom ist nachts nutzlos, weil",
                continuation=(
                    "Solarstrom ist nachts nutzlos, weil keine Sonne scheint und "
                    "Speicher angeblich zu teuer sind."
                ),
                delay_seconds=args.cancellation_delay_ms / 1000.0,
                timeout_seconds=args.timeout,
            )
            control_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            spoken_playbook_probe = await control_replay.spoken_playbook_probe(
                context=turns[0]["text"],
                timeout_seconds=args.timeout,
            )
    finally:
        llm.resolve_endpoint = original_resolve_endpoint
        llm.is_local_only = original_is_local_only
        llm.record_token_usage = original_record_token_usage
        llm.pii_egress.protect_and_guard = original_protect_and_guard
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "measurement_path": "transcript_ingest_to_debate_update",
        "mode": mode,
        "prompt_template_sha256": prompt_template_sha256,
        "prompt_fingerprint_scope": "resolved live template only; excludes dynamic inputs",
        "fixture_sha256": hashlib.sha256(json.dumps(
            turns, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "acceptance_scope": "headless orchestrator callback; not real UI paint or human acceptance",
        "endpoint": args.endpoint,
        "model": args.model,
        "app_model_id": app_model_id,
        "model_metadata": await _ollama_metadata(args.endpoint, args.model),
        "fixture": "built-in-german-debate" if args.fixture is None else str(args.fixture),
        "research_egress": "disabled",
        "generation_egress": endpoint_scope(args.endpoint),
        "turns": records,
        "supersession_probe": probe,
        "interim_continuation_probe": interim_probe,
        "spoken_playbook_probe": spoken_playbook_probe,
        "summary": summarize(
            records,
            cancellation_count=probe["cancellation_count"],
            probe_failure_count=probe["failure_count"],
            stale_publishes=(
                sum(int(record.get("stale_publishes") or 0) for record in records)
                + int(probe.get("stale_publishes") or 0)
                + int(interim_probe.get("stale_publishes") or 0)
                + int(spoken_playbook_probe.get("stale_publishes") or 0)
            ),
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--mode", choices=("persuasive", "forceful"), default="persuasive")
    parser.add_argument(
        "--api-key",
        default="",
        help="Bearer key for the benchmark endpoint; omitted for local Ollama",
    )
    parser.add_argument(
        "--app-model-id",
        help=(