import unittest

from app.schemas import SessionCreate, SessionUpdate
from pydantic import ValidationError


class SessionNameValidationTests(unittest.TestCase):
    def test_create_rejects_name_longer_than_frontend_limit(self):
        with self.assertRaises(ValidationError):
            SessionCreate(name="x" * 121)

    def test_update_rejects_name_longer_than_frontend_limit(self):
        with self.assertRaises(ValidationError):
            SessionUpdate(name="x" * 121)


if __name__ == "__main__":
    unittest.main()
