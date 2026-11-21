import unittest
from unittest.mock import AsyncMock, patch

from app.main import readiness


class HealthReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_is_ok_only_with_database(self):
        with patch("app.main._database_ready", new=AsyncMock(return_value=True)):
            self.assertEqual({"status": "ok"}, await readiness())

    async def test_readiness_reports_database_outage_without_details(self):
        with patch("app.main._database_ready", new=AsyncMock(return_value=False)):
            response = await readiness()

        self.assertEqual(503, response.status_code)
        self.assertEqual(
            b'{"status":"degraded","database":"unavailable"}', response.body
        )
