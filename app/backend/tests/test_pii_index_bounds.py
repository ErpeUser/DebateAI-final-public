import unittest
import uuid

from app.services.pii import vault
from app.services import redaction


class PiiIndexBoundTests(unittest.TestCase):
    def tearDown(self):
        vault.reset_keys_for_tests()
        redaction.clear_registered_secrets()

    def test_plaintext_index_is_session_aware_and_expires(self):
        first = uuid.uuid4()
        second = uuid.uuid4()
        vault._remember_plaintext("Alice Example", "PERSON", first, now=100000)
        vault._remember_plaintext("Bob Example", "PERSON", second, now=100000)
        self.assertEqual({"Alice Example", "Bob Example"}, {value for value, _ in vault.known_plaintext_values(now=100000)})
        vault.forget(first)
        self.assertEqual({"Bob Example"}, {value for value, _ in vault.known_plaintext_values()})
        self.assertEqual("Alice Example", redaction.redact_text("Alice Example"))
        vault._remember_plaintext("Old Example", "PERSON", second, now=0)
        self.assertEqual({"Bob Example"}, {value for value, _ in vault.known_plaintext_values(now=100000)})

    def test_redaction_secret_index_has_lru_bound(self):
        old_max = redaction.MAX_REGISTERED_SECRETS
        try:
            redaction.MAX_REGISTERED_SECRETS = 2
            redaction.register_secret("first-secret-12345", now=0)
            redaction.register_secret("second-secret-12345", now=0)
            redaction.register_secret("third-secret-12345", now=0)
            self.assertEqual(2, redaction.registered_secret_count(now=0))
            self.assertEqual("first-secret-12345", redaction.redact_text("first-secret-12345", now=0))
        finally:
            redaction.MAX_REGISTERED_SECRETS = old_max
