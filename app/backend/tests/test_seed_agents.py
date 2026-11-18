import unittest
from types import SimpleNamespace
from unittest import mock

from app.services.agents.prompts import (
    DEBATE_RECOMMENDATION_PROMPT,
    OPPORTUNITY_SPECIALIST_PROMPT,
)
from app.models import AgentConfig
from app.services.seed_agents import (
    DESKTOP_DEBATE_MODEL_ID,
    SEED_CONFIGS,
    configure_desktop_debate_runtime,
    seed_agent_configs,
)
from app.routers.endpoints import _merge_desktop_qwen_models
from app.services.transcription_runtime import SETTING_BATCH_TRANSCRIBER_MODEL
from app.services.transcription_language import SETTING_TRANSCRIPTION_LANGUAGE


class SeedAgentConfigTests(unittest.TestCase):
    def test_objection_handler_is_presented_as_event_driven_debate_copilot(self):
        cfg = _seed_config("objection_handler")

        self.assertEqual("Debate Copilot", cfg["name"])
        self.assertIn("ereignisgesteuert", cfg["description"].casefold())
        self.assertIn("Deutsch", cfg["description"])

    def test_strategic_signals_is_a_configurable_live_agent(self):
        cfg = _seed_config("strategic_signals")

        self.assertEqual("Strategische Signale", cfg["name"])
        self.assertEqual("meta", cfg["agent_type"])
        self.assertEqual("", cfg["model_id"])
        self.assertEqual(45, cfg["interval_seconds"])
        self.assertTrue(cfg["enabled"])
        self.assertIn("{insights_text}", cfg["prompt"])
        self.assertIn("evidence_refs", cfg["prompt"])

    def test_every_fresh_agent_starts_unselected(self):
        self.assertTrue(SEED_CONFIGS)
        self.assertEqual({""}, {cfg["model_id"] for cfg in SEED_CONFIGS})


class SeedPromptTests(unittest.TestCase):
    def test_default_prompt_uses_knowledge_context_placeholder(self):
        self.assertIn("{knowledge_context}", OPPORTUNITY_SPECIALIST_PROMPT)
        self.assertIn("{opportunities_json}", OPPORTUNITY_SPECIALIST_PROMPT)
        self.assertNotIn("{offerings_catalog}", OPPORTUNITY_SPECIALIST_PROMPT)
        # Must format without KeyError (braces in JSON examples are escaped)
        OPPORTUNITY_SPECIALIST_PROMPT.format(knowledge_context="ctx", opportunities_json="[]")


class SeedPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_model_prompt_interval_and_batch_choice_are_preserved(self):
        agents = [_existing_agent(cfg) for cfg in SEED_CONFIGS]
        analyst = next(agent for agent in agents if agent.slug == "consolidated_analyst")
        analyst.model_id = "gpt-5.6-terra"
        analyst.prompt = "My saved prompt"
        analyst.interval_seconds = 45
        batch = SimpleNamespace(
            key=SETTING_BATCH_TRANSCRIBER_MODEL,
            value="gpt-4o-mini-transcribe",
        )
        db = _FakeSession(agents=agents, settings={batch.key: batch})

        await seed_agent_configs(db)

        self.assertEqual("gpt-5.6-terra", analyst.model_id)
        self.assertEqual("My saved prompt", analyst.prompt)
        self.assertEqual(45, analyst.interval_seconds)
        self.assertEqual("gpt-4o-mini-transcribe", batch.value)
        db.commit.assert_awaited_once()

    async def test_missing_rows_are_blank_and_missing_batch_setting_uses_fixed_german_whisper(self):
        db = _FakeSession(agents=[])

        await seed_agent_configs(db)

        added_agents = [item for item in db.added if isinstance(item, AgentConfig)]
        self.assertEqual(len(SEED_CONFIGS), len(added_agents))
        self.assertEqual({""}, {agent.model_id for agent in added_agents})
        self.assertEqual(
            "local-whisper-base",
            db.settings[SETTING_BATCH_TRANSCRIBER_MODEL].value,
        )
        self.assertEqual("de", db.settings[SETTING_TRANSCRIPTION_LANGUAGE].value)

    async def test_old_auto_language_is_migrated_to_german(self):
        language = SimpleNamespace(
            key=SETTING_TRANSCRIPTION_LANGUAGE,
            value="auto",
        )
        db = _FakeSession(agents=[], settings={language.key: language})

        await seed_agent_configs(db)

        self.assertEqual("de", db.settings[SETTING_TRANSCRIPTION_LANGUAGE].value)

    async def test_old_german_parakeet_default_is_migrated_to_fixed_german_whisper(self):
        batch = SimpleNamespace(
            key=SETTING_BATCH_TRANSCRIBER_MODEL,
            value="local-parakeet-tdt-0.6b-v3",
        )
        db = _FakeSession(agents=[], settings={batch.key: batch})

        await seed_agent_configs(db)

        self.assertEqual("local-whisper-base", batch.value)


class DesktopDebateRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_only_actually_served_qwen35_models_become_alternatives(self):
        current = [{"id": "qwen3:4b", "label": "Qwen3 4B"}]

        merged = _merge_desktop_qwen_models(
            current,
            ["qwen3.5:4b", "qwen3.5:9b", "llama3:8b"],
        )

        self.assertEqual(
            ["qwen3:4b", "qwen3.5:4b", "qwen3.5:9b"],
            [item["id"] for item in merged],
        )
        self.assertNotIn("llama3:8b", [item["id"] for item in merged])
    async def test_first_desktop_start_registers_local_live_model_once(self):
        objection = _existing_agent(_seed_config("objection_handler"))
        objection.model_id = "gemini-3-flash-preview"
        db = _DesktopFakeSession(objection=objection)

        with mock.patch.dict("os.environ", {"DEBATEAI_DESKTOP": "1"}):
            await configure_desktop_debate_runtime(db)

        self.assertEqual(DESKTOP_DEBATE_MODEL_ID, objection.model_id)
        self.assertEqual(DEBATE_RECOMMENDATION_PROMPT, objection.prompt)
        endpoint = next(item for item in db.added if item.__class__.__name__ == "CustomEndpoint")
        self.assertEqual("http://127.0.0.1:11434/v1", endpoint.base_url)
        self.assertEqual([{"id": "qwen3:4b", "label": "Qwen3 4B – Deutsche Live-Debatte"}], endpoint.models)
        self.assertEqual("1", db.settings["debate.desktop.local_live.v1"].value)
        self.assertEqual(
            "debate_live_v3",
            db.settings["debate.prompt.objection_handler.version"].value,
        )

    async def test_completed_bootstrap_preserves_later_user_model_choice(self):
        objection = _existing_agent(_seed_config("objection_handler"))
        objection.model_id = "gemini-3.8-flash"
        objection.prompt = "My later custom prompt"
        marker = SimpleNamespace(key="debate.desktop.local_live.v1", value="1")
        db = _DesktopFakeSession(objection=objection, settings={marker.key: marker})

        with mock.patch.dict("os.environ", {"DEBATEAI_DESKTOP": "1"}):
            await configure_desktop_debate_runtime(db)

        self.assertEqual("gemini-3.8-flash", objection.model_id)
        self.assertEqual("My later custom prompt", objection.prompt)
        self.assertFalse(any(item.__class__.__name__ == "CustomEndpoint" for item in db.added))
        self.assertEqual(
            "manual-preserved",
            db.settings["debate.prompt.objection_handler.version"].value,
        )

    async def test_non_desktop_runtime_is_untouched(self):
        objection = _existing_agent(_seed_config("objection_handler"))
        db = _DesktopFakeSession(objection=objection)

        with mock.patch.dict("os.environ", {}, clear=True):
            await configure_desktop_debate_runtime(db)

        self.assertEqual("", objection.model_id)
        self.assertEqual([], db.added)


def _seed_config(slug: str) -> dict:
    return next(cfg for cfg in SEED_CONFIGS if cfg["slug"] == slug)


class _FakeSession:
    def __init__(self, *, agents, settings=None):
        self.agents = agents
        self.settings = dict(settings or {})
        self._results = iter(
            SimpleNamespace(scalar_one_or_none=lambda agent=agent: agent)
            for agent in agents
        )
        self.execute = mock.AsyncMock(side_effect=self._execute)
        self.flush = mock.AsyncMock()
        self.commit = mock.AsyncMock()
        self.added = []

    async def get(self, _model, key):
        return self.settings.get(key)

    def add(self, item):
        self.added.append(item)
        if hasattr(item, "key"):
            self.settings[item.key] = item

    def _execute(self, _statement):
        return next(
            self._results,
            SimpleNamespace(scalar_one_or_none=lambda: None),
        )


class _DesktopFakeSession:
    def __init__(self, *, objection, settings=None):
        self.objection = objection
        self.settings = dict(settings or {})
        self.added = []
        self.flush = mock.AsyncMock()

    async def get(self, model, key):
        if model.__name__ == "AppSetting":
            return self.settings.get(key)
        return None

    async def execute(self, _statement):
        return SimpleNamespace(
            scalar_one_or_none=lambda: self.objection,
            scalars=lambda: SimpleNamespace(all=lambda: []),
        )

    def add(self, item):
        self.added.append(item)
        if hasattr(item, "key"):
            self.settings[item.key] = item


def _existing_agent(cfg: dict):
    values = dict(cfg)
    values.setdefault("lenses", "")
    values.setdefault("sub_types", "")
    values.setdefault("interval_seconds", 0)
    return SimpleNamespace(**values)


if __name__ == "__main__":
    unittest.main()
