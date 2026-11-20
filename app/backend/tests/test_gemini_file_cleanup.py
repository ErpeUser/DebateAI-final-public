import unittest
from unittest.mock import AsyncMock, patch

from app.services import gemini_files


class GeminiFileCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        gemini_files._delete_outbox.clear()

    async def test_failed_delete_is_visible_in_bounded_outbox(self):
        with patch.object(
            gemini_files,
            "_delete_uploaded_file",
            new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ):
            result = await gemini_files.delete_uploaded_file("files/demo")

        self.assertFalse(result)
        self.assertEqual(1, len(gemini_files.pending_file_deletions()))
        self.assertEqual(1, gemini_files.pending_file_deletions()[0]["attempts"])

    async def test_due_retry_removes_completed_item(self):
        gemini_files._queue_file_deletion("files/demo", "offline", now=0)
        task = gemini_files._delete_outbox["files/demo"]
        task.next_attempt_at = 0
        with patch.object(
            gemini_files,
            "_delete_uploaded_file",
            new=AsyncMock(return_value=None),
        ):
            completed = await gemini_files.retry_pending_file_deletions(now=1)

        self.assertEqual(1, completed)
        self.assertEqual([], gemini_files.pending_file_deletions())


if __name__ == "__main__":
    unittest.main()
