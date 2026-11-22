import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.main import _retry_gemini_file_deletions


class GeminiFileDeleteRetryWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_retries_due_items_until_cancelled(self):
        retry = AsyncMock(side_effect=asyncio.CancelledError)
        with patch("app.main.retry_pending_file_deletions", retry):
            with self.assertRaises(asyncio.CancelledError):
                await _retry_gemini_file_deletions()
        retry.assert_awaited_once_with(max_items=16)

    async def test_provider_failure_does_not_stop_the_worker(self):
        retry = AsyncMock(
            side_effect=[RuntimeError("provider unavailable"), asyncio.CancelledError]
        )
        with patch("app.main.retry_pending_file_deletions", retry), patch(
            "app.main.asyncio.sleep", new=AsyncMock(return_value=None)
        ):
            with self.assertRaises(asyncio.CancelledError):
                await _retry_gemini_file_deletions()
        self.assertEqual(2, retry.await_count)


if __name__ == "__main__":
    unittest.main()
