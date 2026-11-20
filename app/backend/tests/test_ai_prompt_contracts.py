"""Saved prompts must match the formatter contract of their actual consumer."""

import unittest
from unittest.mock import patch

from app.services import ai_config


class PromptContractTests(unittest.TestCase):
    def test_python_templates_reject_fields_their_consumer_cannot_render(self):
        for template in (
            "{claim}", "{}", "{0}", "{transcript_text[99]}",
            "{transcript_text.missing}", "{transcript_text:{claim}}",
            "{transcript_text:invalid}", "{transcript_text!x}",
        ):
            with self.subTest(template=template), self.assertRaises(ValueError):
                ai_config._validate_prompt_content("analyze_transcript", template)

    def test_literal_json_is_valid_in_raw_and_literal_replacement_prompts(self):
        raw = 'Return JSON: {"answer": "text"}'
        self.assertEqual(ai_config._validate_prompt_content("postcall_chat_system", raw), raw)
        deep = '{claim}\n{own_position}\n{relevant_context}\n{evidence}\n' + raw
        self.assertEqual(ai_config._validate_prompt_content("debate_deep_v1", deep), deep)

    def test_valid_python_fields_and_escaped_json_remain_renderable(self):
        template = '{meeting_context_text}\n{transcript_text}\n{{"answer": "text"}}'
        validated = ai_config._validate_prompt_content("analyze_transcript", template)
        self.assertEqual(
            validated.format(meeting_context_text="context", transcript_text="speech"),
            'context\nspeech\n{"answer": "text"}',
        )


class ResearchOptOutTests(unittest.TestCase):
    def test_explicitly_disabled_provider_is_removed_from_every_fallback(self):
        for fallback in (None, ["gemini_api", "gemini_web", "cliproxyapi"]):
            research = {"providers": [{"id": "gemini_api", "enabled": False}]}
            if fallback is not None:
                research["fallback_providers"] = fallback
            with self.subTest(fallback=fallback), patch.object(
                ai_config, "load_ai_json", return_value={"research": research}
            ):
                settings = ai_config.research_settings()
            self.assertNotIn("gemini_api", settings["providers"])
            self.assertNotIn("gemini_api", settings["fallback_providers"])
            self.assertIn("gemini_web", settings["fallback_providers"])
            self.assertIn("cliproxyapi", settings["fallback_providers"])


if __name__ == "__main__":
    unittest.main()

class LivePromptQualityContractTests(unittest.TestCase):
    def test_live_prompt_requires_spoken_answer_and_honest_support(self):
        path = ai_config.ai_directory() / "debate_live_v2.txt"
        prompt = path.read_text(encoding="utf-8")
        self.assertIn("hoechstens 25 Woertern", prompt)
        self.assertIn("stuetzt die Antwort mit dem staerksten ehrlichen Grund", prompt)
        self.assertIn("argumentiert niemals dagegen", prompt)
        self.assertIn("keine Fakten", prompt)
        self.assertIn("Negationen", prompt)
