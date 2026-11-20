import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.ai_config as ai_config_module
import app.routers.ai_config as ai_config_router
from app.services.ai_config import (
    active_prompt,
    adaptive_reasoning_settings,
    analysis_deadline_seconds,
    configuration_generation,
    live_research_deadline_seconds,
    deep_analysis_models,
    ensure_gemini_cli_route,
    ensure_gemini_web_route,
    max_parallel_analyses,
    list_prompt_versions,
    provider_configuration,
    reset_provider_configuration,
    restore_prompt_version,
    save_prompt,
    save_provider_configuration,
)


class PackagedAiDirectoryTests(unittest.TestCase):
    def test_bundled_defaults_are_merged_only_once_per_process(self):
        if os.name != "nt":
            self.skipTest("Windows packaged paths are platform-specific")
        ai_config_module._packaged_ai_directory.cache_clear()
        with (
            patch.dict(
                os.environ,
                {
                    "DATA_DIR": "C:/DebateAI/data",
                    "DEBATE_AI_CONFIG_DIR": "",
                    "DEBATEAI_PROMPT_DIR": "",
                },
                clear=False,
            ),
            patch.object(ai_config_module.sys, "_MEIPASS", "C:/bundle", create=True),
            patch.object(Path, "mkdir"),
            patch.object(ai_config_module, "_bundled_ai_directory", return_value=Path("C:/bundle/ai")),
            patch.object(ai_config_module, "_merge_bundled_defaults") as merge,
        ):
            first = ai_config_module.ai_directory()
            second = ai_config_module.ai_directory()

        ai_config_module._packaged_ai_directory.cache_clear()
        self.assertEqual(Path("C:/DebateAI/ai"), first)
        self.assertEqual(first, second)
        merge.assert_called_once_with(Path("C:/bundle/ai"), Path("C:/DebateAI/ai"))

    def test_known_old_bundled_provider_order_migrates_to_new_web_first_default(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as root:
            root = Path(root)
            source = root / "bundle"
            target = root / "user"
            baseline = target / ".bundled-baseline"
            source.mkdir()
            baseline.mkdir(parents=True)
            old = b'{"routes":[{"id":"cliproxyapi"},{"id":"oracle"}]}'
            new = b'{"routes":[{"id":"oracle"},{"id":"gemini_web"},{"id":"cliproxyapi"}]}'
            (source / "providers.json").write_bytes(new)
            (target / "providers.json").write_bytes(old)
            (baseline / "providers.json").write_bytes(old)

            ai_config_module._merge_bundled_defaults(source, target)

            self.assertEqual(new, (target / "providers.json").read_bytes())
            self.assertEqual(new, (baseline / "providers.json").read_bytes())

    def test_individually_changed_provider_order_survives_bundled_update(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as root:
            root = Path(root)
            source = root / "bundle"
            target = root / "user"
            baseline = target / ".bundled-baseline"
            source.mkdir()
            baseline.mkdir(parents=True)
            old = b'{"routes":[{"id":"cliproxyapi"},{"id":"oracle"}]}'
            custom = b'{"routes":[{"id":"gemini_web"},{"id":"oracle"}]}'
            new = b'{"routes":[{"id":"oracle"},{"id":"gemini_web"},{"id":"cliproxyapi"}]}'
            (source / "providers.json").write_bytes(new)
            (target / "providers.json").write_bytes(custom)
            (baseline / "providers.json").write_bytes(old)

            ai_config_module._merge_bundled_defaults(source, target)

            self.assertEqual(custom, (target / "providers.json").read_bytes())
            self.assertEqual(new, (baseline / "providers.json").read_bytes())

    def test_explicit_portable_mode_uses_started_exe_directory_not_meipass(self):
        if os.name != "nt":
            self.skipTest("Windows packaged paths are platform-specific")
        ai_config_module._packaged_ai_directory.cache_clear()
        with (
            patch.dict(
                os.environ,
                {
                    "DATA_DIR": "C:/ignored/data",
                    "DEBATE_AI_CONFIG_DIR": "",
                    "DEBATEAI_PROMPT_DIR": "",
                    "DEBATEAI_PORTABLE": "1",
                },
                clear=False,
            ),
            patch.object(ai_config_module.sys, "frozen", True, create=True),
            patch.object(ai_config_module.sys, "executable", "C:/release/DebateAI.exe", create=True),
            patch.object(ai_config_module.sys, "_MEIPASS", "C:/release/_internal", create=True),
            patch.object(ai_config_module, "_bundled_ai_directory", return_value=Path("C:/release/_internal/ai")),
            patch.object(ai_config_module, "_merge_bundled_defaults"),
        ):
            resolved = ai_config_module.ai_directory()

        self.assertEqual(Path("C:/release/ai"), resolved)
        self.assertNotIn("_internal", str(resolved))
        ai_config_module._packaged_ai_directory.cache_clear()

    def test_frozen_override_inside_meipass_is_rejected(self):
        with (
            patch.dict(os.environ, {"DEBATE_AI_CONFIG_DIR": "C:/release/_internal/ai"}, clear=False),
            patch.object(ai_config_module.sys, "frozen", True, create=True),
            patch.object(ai_config_module.sys, "_MEIPASS", "C:/release/_internal", create=True),
        ):
            self.assertNotEqual(Path("C:/release/_internal/ai"), ai_config_module._explicit_external_directory())


class AiConfigurationRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_configuration_serializes_nonempty_playbooks(self):
        with (
            patch.object(ai_config_router, "_ensure_agent_prompts", AsyncMock()),
            patch.object(ai_config_router, "_ensure_static_prompts"),
            patch.object(ai_config_router, "load_ai_json", return_value=[{"id": "probe"}]),
            patch.object(ai_config_router, "provider_configuration", return_value={"routes": []}),
            patch.object(ai_config_router, "provider_capability_payload", return_value={}),
        ):
            payload = await ai_config_router.read_ai_configuration(db=MagicMock())

        playbooks = next(item for item in payload["prompts"] if item["name"] == "rhetoriciq.playbooks")
        self.assertIn('"id": "probe"', playbooks["content"])


class AiConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.ai_dir = Path(self.temp.name)
        self.env = patch.dict(
            os.environ,
            {"DEBATE_AI_CONFIG_DIR": str(self.ai_dir)},
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_saved_route_order_and_enabled_state_drive_runtime_selection(self):
        config = {
            "routes": [
                {"id": "oracle", "model_id": "chatgpt-web:gpt-6", "enabled": True, "reasoning_effort": "xhigh"},
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": False, "reasoning_effort": "high"},
                {"id": "gemini", "model_id": "endpoint:gemini-web:gemini-3.1-pro", "enabled": True, "reasoning_effort": "high"},
            ],
            "fallback_enabled": True,
        }

        save_provider_configuration(config)

        self.assertEqual(
            deep_analysis_models(["unused-default"]),
            ["chatgpt-web:gpt-6", "endpoint:gemini-web:gemini-3.1-pro"],
        )
        self.assertEqual(provider_configuration()["routes"], config["routes"])

    def test_invalid_provider_update_preserves_last_valid_file(self):
        valid = {
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True, "reasoning_effort": "xhigh"}
            ]
        }
        save_provider_configuration(valid)
        before = (self.ai_dir / "providers.json").read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            save_provider_configuration({"routes": [{"id": "broken", "model_id": "", "enabled": True}]})

        self.assertEqual((self.ai_dir / "providers.json").read_text(encoding="utf-8"), before)

    def test_malformed_provider_json_is_not_silently_treated_as_empty(self):
        (self.ai_dir / "providers.json").write_text('{"routes":[}', encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "ungueltiges JSON"):
            ai_config_module._read_provider_configuration()

    def test_disabling_every_route_does_not_reenable_hardcoded_defaults(self):
        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": False}
            ]
        })

        self.assertEqual(deep_analysis_models(["must-not-return"]), [])

    def test_bundled_paid_api_route_requires_explicit_enablement(self):
        defaults_path = Path(__file__).resolve().parents[2] / "ai" / "providers.default.json"
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        official = next(
            route for route in defaults["routes"] if route["id"] == "official_gemini"
        )

        self.assertFalse(official["enabled"])
        self.assertNotIn("requires_cost_approval", official)

    def test_bundled_web_accounts_precede_cli_work_fallbacks(self):
        defaults_path = Path(__file__).resolve().parents[2] / "ai" / "providers.default.json"
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))

        route_ids = [route["id"] for route in defaults["routes"]]

        self.assertEqual(
            ["oracle", "gemini_web", "cliproxyapi", "gemini_cli"],
            route_ids[:4],
        )

    def test_gemini_cli_oauth_route_is_merged_without_resetting_user_routes(self):
        save_provider_configuration({
            "routes": [
                {"id": "custom", "label": "Mein Anbieter", "model_id": "endpoint:lab:model", "enabled": False}
            ],
            "fallback_enabled": False,
        })

        migrated = ensure_gemini_cli_route()

        self.assertEqual("custom", migrated["routes"][0]["id"])
        self.assertFalse(migrated["routes"][0]["enabled"])
        self.assertFalse(migrated["fallback_enabled"])
        gemini = next(route for route in migrated["routes"] if route["id"] == "gemini_cli")
        self.assertEqual("endpoint:subscription-ai:gemini-3.1-pro-preview", gemini["model_id"])
        self.assertEqual("high", gemini["reasoning_effort"])

    def test_gemini_cli_route_tracks_the_model_the_bridge_actually_serves(self):
        save_provider_configuration({
            "routes": [
                {
                    "id": "gemini_cli",
                    "label": "Gemini CLI OAuth (3.1 Pro High)",
                    "provider": "google-login",
                    "model_id": "endpoint:subscription-ai:gemini-3.1-pro-preview",
                    "enabled": True,
                    "reasoning_effort": "high",
                }
            ],
            "fallback_enabled": True,
        })

        migrated = ensure_gemini_cli_route("gemini-3.8-flash-high")

        route = migrated["routes"][0]
        self.assertEqual(
            "endpoint:subscription-ai:gemini-3.8-flash-high",
            route["model_id"],
        )
        self.assertEqual("Gemini CLI OAuth (gemini-3.8-flash-high, High)", route["label"])

    def test_gemini_web_route_tracks_the_model_the_account_actually_serves(self):
        save_provider_configuration({
            "routes": [
                {
                    "id": "gemini_web",
                    "label": "Gemini-Webproxy (Google AI Pro)",
                    "provider": "google-web",
                    "model_id": "endpoint:gemini-web:gemini-3.1-pro",
                    "enabled": True,
                    "reasoning_effort": "high",
                }
            ],
            "fallback_enabled": True,
        })

        migrated = ensure_gemini_web_route("gemini-deeper-analysis")

        route = migrated["routes"][0]
        self.assertEqual(
            "endpoint:gemini-web:gemini-deeper-analysis",
            route["model_id"],
        )
        self.assertEqual(
            "Gemini-Webproxy (gemini-deeper-analysis, High)",
            route["label"],
        )

    def test_adaptive_topic_reuse_and_parallelism_are_runtime_settings(self):
        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "max_parallel_analyses": 3,
            "adaptive_reasoning": {
                "reuse_topic_analysis": False,
                "topic_similarity_threshold": 0.57,
            },
        })

        adaptive = adaptive_reasoning_settings()
        self.assertEqual(max_parallel_analyses(), 3)
        self.assertFalse(adaptive["reuse_topic_analysis"])
        self.assertEqual(adaptive["topic_similarity_threshold"], 0.57)

    def test_external_analysis_deadline_is_one_bounded_end_to_end_budget(self):
        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "analysis_deadline_seconds": 75,
        })

        self.assertEqual(75, analysis_deadline_seconds())

        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "analysis_deadline_seconds": 99999,
        })
        self.assertEqual(900, analysis_deadline_seconds())

    def test_live_research_deadline_is_bounded_to_short_budget(self):
        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "live_research_deadline_seconds": 10,
        })
        self.assertEqual(10, live_research_deadline_seconds())

        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "live_research_deadline_seconds": 1,
        })
        self.assertEqual(8, live_research_deadline_seconds())

        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ],
            "live_research_deadline_seconds": 99,
        })
        self.assertEqual(15, live_research_deadline_seconds())
    def test_configuration_generation_changes_when_an_active_prompt_changes(self):
        save_provider_configuration({
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True}
            ]
        })
        save_prompt("debate_live_v2", "Erste Fassung")
        first = configuration_generation()

        save_prompt("debate_live_v2", "Zweite Fassung")
        second = configuration_generation()

        self.assertIsInstance(first, int)
        self.assertNotEqual(first, second)

    def test_reset_restores_separate_bundled_default(self):
        defaults = {
            "routes": [
                {"id": "cli", "model_id": "endpoint:subscription-ai:gpt-6-sol", "enabled": True, "reasoning_effort": "xhigh"}
            ]
        }
        (self.ai_dir / "providers.default.json").write_text(json.dumps(defaults), encoding="utf-8")
        save_provider_configuration({
            "routes": [
                {"id": "oracle", "model_id": "chatgpt-web:gpt-6", "enabled": True, "reasoning_effort": "high"}
            ]
        })

        restored = reset_provider_configuration()

        self.assertEqual(restored["routes"], defaults["routes"])
        self.assertEqual(deep_analysis_models([]), ["endpoint:subscription-ai:gpt-6-sol"])

    def test_prompt_save_is_active_immediately_and_previous_version_can_be_restored(self):
        save_prompt("agent.objection_handler", "Erste aktive Fassung")
        save_prompt("agent.objection_handler", "Zweite aktive Fassung")

        versions = list_prompt_versions("agent.objection_handler")
        self.assertEqual(active_prompt("agent.objection_handler", "Fallback"), "Zweite aktive Fassung")
        self.assertEqual(len(versions), 1)

        restore_prompt_version("agent.objection_handler", versions[0]["version"])

        self.assertEqual(active_prompt("agent.objection_handler", "Fallback"), "Erste aktive Fassung")

    def test_prompt_name_cannot_escape_ai_directory(self):
        with self.assertRaises(ValueError):
            save_prompt("../secret", "no")


if __name__ == "__main__":
    unittest.main()
