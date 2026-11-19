import re
import unittest
from pathlib import Path


MATRIX = Path(__file__).parents[2] / ".ai" / "DEBATE_AI_OPTIMIERUNG.md"


class V3MatrixCoverageTests(unittest.TestCase):
    def setUp(self):
        # The detailed V3 matrix is private acceptance evidence and is
        # intentionally excluded from the public source tree by the
        # repository layout contract.  Keep these checks active for a local
        # evidence checkout, while making the public CI suite honest about
        # the unavailable input instead of failing with FileNotFoundError.
        if not MATRIX.is_file():
            self.skipTest("private V3 acceptance matrix is not present in public checkout")

    def test_matrix_lists_all_atomics_and_priority_contracts(self):
        text = MATRIX.read_text(encoding="utf-8")
        first_cells = {
            line.split("|", 2)[1].strip()
            for line in text.splitlines()
            if line.startswith("| ") and line.count("|") >= 4
        }
        for identifier in [*(f"A{i:02d}" for i in range(1, 25)), "N1", "N2", "N3", "N4"]:
            self.assertTrue(
                any(re.search(rf"\b{identifier}\b", cell) for cell in first_cells),
                identifier,
            )
        for prefix, end in (("P0", 10), ("P1", 8), ("P2", 9), ("P3", 7)):
            for number in range(1, end + 1):
                identifier = f"{prefix}.{number}"
                self.assertIn(f"| {identifier} |", text)

    def test_matrix_has_a_status_and_evidence_column(self):
        text = MATRIX.read_text(encoding="utf-8")
        rows = [line for line in text.splitlines() if line.startswith("| ")]
        self.assertGreaterEqual(len(rows), 24 + 34)
        for row in rows:
            if re.match(r"\|\s*(?:A\d{2}|N\d|P[0-3](?:\.\d|-[A-G]))", row):
                self.assertGreaterEqual(row.count("|"), 4)
                self.assertRegex(
                    row,
                    r"\|\s*(?:BESTANDEN|IMPLEMENTIERT|OFFEN|IN ARBEIT|BLOCKED|FEHLGESCHLAGEN)",
                )


if __name__ == "__main__":
    unittest.main()
