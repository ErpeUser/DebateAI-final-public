import json
import unittest
from types import SimpleNamespace
from unittest import mock

from pydantic import ValidationError


class _Store:
    def __init__(self, raw: str = ""):
        self.raw = raw
        self.saved = None

    async def get(self, _db, _key, _default=""):
        return self.raw

    async def set(self, _db, _key, value):
        self.saved = value


class DebateSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_desktop_bundle_defaults_to_research_disabled_and_never(self):
        from app.services import debate_settings

        store = _Store()
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=True),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertFalse(result.research_enabled)
        self.assertEqual(result.research_frequency, "never")
        self.assertEqual(result.mode, "persuasive")
        self.assertFalse(result.always_analogy)
        self.assertEqual(result.style_focus, "natural")
        self.assertTrue(result.voice_commands_enabled)
        self.assertTrue(result.argument_memory_enabled)
        self.assertFalse(result.audio_archive_enabled)
        self.assertEqual(result.memory_similarity_threshold, 0.34)

    async def test_existing_explicit_analogy_preference_is_preserved(self):
        from app.services import debate_settings

        store = _Store('{"always_analogy":true}')
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=True),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertTrue(result.always_analogy)

    async def test_existing_explicit_audio_archive_preference_is_preserved(self):
        from app.services import debate_settings

        store = _Store('{"audio_archive_enabled":true}')
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=True),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertTrue(result.audio_archive_enabled)

    async def test_source_install_defaults_to_research_disabled_and_normal(self):
        from app.services import debate_settings

        store = _Store()
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=False),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertFalse(result.research_enabled)
        self.assertEqual(result.research_frequency, "normal")

    async def test_invalid_persisted_values_fall_back_to_disabled_desktop_default(self):
        from app.services import debate_settings

        store = _Store('{"mode":"insults","research_frequency":"constant"}')
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=True),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertEqual(result.mode, "persuasive")
        self.assertEqual(result.research_frequency, "never")
        self.assertFalse(result.research_enabled)

    async def test_set_persists_validated_json(self):
        from app.services import debate_settings

        store = _Store()
        settings = debate_settings.DebateSettings(
            mode="forceful",
            research_enabled=True,
            research_frequency="low",
            always_analogy=True,
            voice_commands_enabled=False,
            argument_memory_enabled=False,
            memory_similarity_threshold=0.58,
        )
        with mock.patch.object(debate_settings, "set_app_setting", store.set):
            await debate_settings.set_debate_settings(object(), settings)

        self.assertEqual(
            json.loads(store.saved),
            {
                "mode": "forceful",
                "research_enabled": True,
                "research_frequency": "low",
                "always_analogy": True,
                "style_focus": "natural",
                "voice_commands_enabled": False,
                "argument_memory_enabled": False,
                "transcript_retention_enabled": True,
                "audio_archive_enabled": False,
                "session_retrieval_enabled": True,
                "learning_examples_enabled": True,
                "graph_recording_enabled": True,
                "memory_similarity_threshold": 0.58,
                "performance_profile": "balanced",
                "simple_1to1_audio_mode": False,
                "profile_id": "",
                "profile_directive": "",
                "pipeline_mode": "standard",
            },
        )

    async def test_invalid_memory_threshold_falls_back_to_safe_default(self):
        from app.services import debate_settings

        store = _Store('{"memory_similarity_threshold":1.5}')
        with (
            mock.patch.object(debate_settings, "get_app_setting", store.get),
            mock.patch.object(debate_settings, "is_desktop_bundle", return_value=False),
        ):
            result = await debate_settings.get_debate_settings(object())

        self.assertEqual(result.memory_similarity_threshold, 0.34)

    def test_patch_rejects_unknown_mode_and_frequency(self):
        from app.routers.debate_settings import DebateSettingsUpdate

        with self.assertRaises(ValidationError):
            DebateSettingsUpdate(mode="insults")
        with self.assertRaises(ValidationError):
            DebateSettingsUpdate(research_frequency="constant")
        with self.assertRaises(ValidationError):
            DebateSettingsUpdate(memory_similarity_threshold=1.1)

    async def test_patch_merges_fields_commits_and_returns_cooldown(self):
        from app.routers import debate_settings as router
        from app.services.debate_settings import DebateSettings

        db = SimpleNamespace(commit=mock.AsyncMock())
        current = DebateSettings(
            mode="persuasive",
            research_enabled=True,
            research_frequency="often",
            always_analogy=True,
        )
        saved = []

        async def save(_db, value):
            saved.append(value)
            return value

        with (
            mock.patch.object(
                router, "get_debate_settings", mock.AsyncMock(return_value=current)
            ),
            mock.patch.object(router, "set_debate_settings", save),
        ):
            payload = await router.update_debate_settings(
                router.DebateSettingsUpdate(mode="forceful", research_frequency="low"),
                db=db,
            )

        self.assertEqual(saved[0].mode, "forceful")
        self.assertEqual(saved[0].research_frequency, "low")
        self.assertTrue(saved[0].research_enabled)
        db.commit.assert_awaited_once()
        self.assertEqual(payload["cooldown_seconds"], 180)


if __name__ == "__main__":
    unittest.main()
