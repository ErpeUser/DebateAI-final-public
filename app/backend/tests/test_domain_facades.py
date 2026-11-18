"""Domain entry points must preserve the existing service APIs."""
import unittest

from app.services import update_signing, debateai_update_channel
from app.services import transcription_language, diarizer_selection
from app.services import privacy, privacy_state


class DomainFacadeTests(unittest.TestCase):
    def test_updates_export_existing_signed_verification(self):
        from app.services.domains import updates
        self.assertIs(updates.verify_update_descriptor,
                      update_signing.verify_update_descriptor)
        self.assertIs(updates.channel_configuration,
                      debateai_update_channel.channel_configuration)

    def test_transcription_export_existing_language_helpers(self):
        from app.services.domains import transcription
        self.assertIs(transcription.normalize_language,
                      transcription_language.normalize_language)
        self.assertIs(transcription.normalize_diarizer_mode,
                      diarizer_selection.normalize_diarizer_mode)
        self.assertEqual(transcription.normalize_language("de"), "de")

    def test_privacy_export_existing_local_only_flags(self):
        from app.services.domains import privacy as domain_privacy
        self.assertIs(domain_privacy.get_local_only, privacy_state.get_local_only)
        self.assertIs(domain_privacy.LocalOnlyModeError,
                      privacy.LocalOnlyModeError)


if __name__ == "__main__":
    unittest.main()
