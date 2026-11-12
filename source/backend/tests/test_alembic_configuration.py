import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class AlembicConfigurationTests(unittest.TestCase):
    def test_ini_uses_canonical_non_secret_defaults(self):
        ini = (BACKEND_ROOT / "alembic.ini").read_text(encoding="utf-8")
        self.assertIn("postgresql+asyncpg://debateai:", ini)
        self.assertIn("/debateai", ini)
        self.assertNotIn("callhelper", ini.lower())
        self.assertNotIn("changeme", ini.lower())

    def test_env_routes_cli_migrations_through_runtime_settings(self):
        env = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
        self.assertIn("from app.config import settings", env)
        self.assertIn('set_main_option("sqlalchemy.url"', env)
        self.assertIn("settings.DATABASE_URL", env)


if __name__ == "__main__":
    unittest.main()
