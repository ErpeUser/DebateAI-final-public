import asyncio
import unittest

from app.services import runtime_activity as runtime


class ActivityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertTrue(
            hasattr(runtime, "exclusive"), "exclusive diagnostic reservation missing"
        )

    async def test_running_call_blocks_calibration(self):
        with runtime.track("active call"):
            with self.assertRaises(runtime.ShutdownReserved):
                with runtime.exclusive("calibration"):
                    self.fail("entered")

    async def test_exclusive_owner_allows_own_native_download_tracking(self):
        with runtime.exclusive("calibration"):

            def native():
                with runtime.track("ASR model download"):
                    return True

            self.assertTrue(await asyncio.to_thread(native))
            self.assertFalse(runtime.reserve_shutdown())
        self.assertEqual(runtime.busy_reason(), "")

    async def test_concurrent_call_is_blocked_without_losing_reservation(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def calibration():
            with runtime.exclusive("calibration"):
                entered.set()
                await release.wait()

        worker = asyncio.create_task(calibration())
        await asyncio.wait_for(entered.wait(), 0.5)
        with self.assertRaises(runtime.ShutdownReserved):
            with runtime.track("active call"):
                self.fail("entered")
        release.set()
        await worker
        with runtime.track("active call"):
            self.assertEqual(runtime.busy_reason(), "active call")

    async def test_shutdown_blocks_exclusive(self):
        self.assertTrue(runtime.reserve_shutdown())
        try:
            with self.assertRaises(runtime.ShutdownReserved):
                with runtime.exclusive("calibration"):
                    self.fail("entered")
        finally:
            runtime.release_shutdown()

    async def test_failed_exclusive_job_releases(self):
        with self.assertRaises(ValueError), runtime.exclusive("calibration"):
            raise ValueError("fixture")
        self.assertEqual(runtime.busy_reason(), "")

    async def test_nested_exclusive_rejected(self):
        with runtime.exclusive("calibration"):
            with self.assertRaises(runtime.ShutdownReserved):
                with runtime.exclusive("other"):
                    self.fail("entered")


if __name__ == "__main__":
    unittest.main()
