import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.agents.objection_handler import build_deep_analysis_prompt


class PromptResourceTests(unittest.TestCase):
    def test_missing_resource_uses_the_checked_in_fallback(self):
        from app.services.agents.prompt_resources import load_prompt_resource

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                self.assertEqual(
                    "fallback prompt",
                    load_prompt_resource("debate_live_v2", "fallback prompt"),
                )

    def test_resource_edit_is_visible_without_reimport_or_process_restart(self):
        from app.services.agents.prompt_resources import load_prompt_resource

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debate_live_v2.txt"
            path.write_text("version one", encoding="utf-8")
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                self.assertEqual(
                    "version one",
                    load_prompt_resource("debate_live_v2", "fallback"),
                )
                path.write_text("version two", encoding="utf-8")
                self.assertEqual(
                    "version two",
                    load_prompt_resource("debate_live_v2", "fallback"),
                )

    def test_custom_agent_prompt_is_not_replaced_by_external_default(self):
        from app.services.agents.objection_handler import ObjectionHandlerAgent

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "debate_live_v2.txt").write_text(
                "external default", encoding="utf-8"
            )
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                agent = ObjectionHandlerAgent(
                    prompt_override="Custom {transcript_window}",
                    recommendation_only=True,
                )
                self.assertEqual(
                    "Custom {transcript_window}", agent._current_prompt_template()
                )

    def test_deep_debate_prompt_is_loaded_from_the_editable_ai_directory(self):
        from app.services.agents.objection_handler import build_deep_analysis_prompt

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "debate_deep_v1.txt").write_text(
                "CLAIM={claim}\nPOSITION={own_position}\nCONTEXT={relevant_context}\n"
                "SOURCES={evidence}\nRELATIONEN NUR MIT CLAIM-ID",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                prompt = build_deep_analysis_prompt(
                    claim="Die Kosten steigen.",
                    own_position="Gesamtkosten vergleichen.",
                    relevant_context="claim:alt Die Kosten sinken.",
                    sources=[],
                )

        self.assertIn("CLAIM=Die Kosten steigen.", prompt)
        self.assertIn("claim:alt", prompt)
        self.assertIn("RELATIONEN NUR MIT CLAIM-ID", prompt)

    def test_provider_background_file_keeps_placeholders_across_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                first = build_deep_analysis_prompt(
                    claim="Erster konkreter Claim.",
                    own_position="Erste Position.",
                    relevant_context="",
                    sources=[],
                    prompt_name="background.gpt6",
                )
                second = build_deep_analysis_prompt(
                    claim="Zweiter neuer Claim.",
                    own_position="Zweite Position.",
                    relevant_context="",
                    sources=[],
                    prompt_name="background.gpt6",
                )
                stored = (Path(tmp) / "background.gpt6.txt").read_text(
                    encoding="utf-8"
                )

        self.assertIn("Erster konkreter Claim.", first)
        self.assertIn("Zweiter neuer Claim.", second)
        self.assertNotIn("Erster konkreter Claim.", second)
        self.assertIn("{claim}", stored)

    def test_invalid_user_prompt_falls_back_without_overwriting_the_file(self):
        from app.services.agents.prompt_resources import load_prompt_resource

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debate_deep_v1.txt"
            original = "ungueltig {"
            path.write_text(original, encoding="utf-8")
            with patch.dict(os.environ, {"BACKCHANNEL_PROMPT_DIR": tmp}):
                fallback = "Claim {claim}\nPosition {own_position}\nContext {relevant_context}\nEvidence {evidence}"
                self.assertEqual(fallback, load_prompt_resource("debate_deep_v1", fallback))
            self.assertEqual(original, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
