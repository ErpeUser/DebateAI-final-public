"""One Speaker-to-prompt mapping shared by all three consumers."""

import unittest
from types import SimpleNamespace

from app.services.agents.speaker_context import speaker_to_dict
from app.services.agents.synthesizer import _speaker_dict as synthesizer_dict
from app.services.briefing_synthesis import _speaker_dict as briefing_dict
from app.services.speaker_context_enhancer import _speaker_dict as enhancer_dict


class SharedSpeakerSerializationTests(unittest.TestCase):
    def test_historical_imports_delegate_to_one_implementation(self):
        for serializer in (synthesizer_dict, briefing_dict, enhancer_dict):
            with self.subTest(serializer=serializer):
                self.assertIs(serializer, speaker_to_dict)

    def test_serialization_keeps_the_prompt_schema(self):
        row = SimpleNamespace(
            id=42, name="Analyst", role="Lead", speaker_type="team",
            display_name="Dana", display_name_enabled=False,
        )
        self.assertEqual(speaker_to_dict(row), {
            "id": "42", "name": "Analyst", "role": "Lead",
            "speaker_type": "team", "display_name": "Dana",
            "display_name_enabled": False,
        })

    def test_empty_optional_names_are_not_modified(self):
        row = SimpleNamespace(
            id="s-1", name=None, role=None, speaker_type=None,
            display_name=None, display_name_enabled=None,
        )
        result = speaker_to_dict(row)
        self.assertEqual(result["id"], "s-1")
        self.assertIsNone(result["display_name_enabled"])


if __name__ == "__main__":
    unittest.main()
