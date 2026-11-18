import unittest
from pathlib import Path
from types import SimpleNamespace

from app.main import app
from app.services.briefing_document import BriefingData, render_record


class DebateBrandingTests(unittest.TestCase):
    def test_api_and_export_use_the_active_product_name(self):
        session = SimpleNamespace(name="Testdebatte", meeting_type="general")

        document = render_record(BriefingData(session=session))

        self.assertEqual("DebateAI", app.title)
        self.assertIn("<b>Debate AI</b>", document)
        self.assertIn("Prepared by Debate AI", document)
        self.assertNotIn("Prepared by DebateAI", document)

    def test_frontend_declares_german_document_language(self):
        index = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
        html = index.read_text(encoding="utf-8")
        self.assertIn('<html lang="de">', html)
        self.assertIn("DebateAI", html)


if __name__ == "__main__":
    unittest.main()
