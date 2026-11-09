import asyncio
import threading
import time
import unittest

from app.services.native_inference import NativeInferenceLane, run_native_until_complete


class NativeInferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_releases_caller_but_keeps_lane_reserved(self):
        started = threading.Event()
        finished = threading.Event()
        release = threading.Event()

        def native_work():
            started.set()
            release.wait(1)
            finished.set()
            return "stale"

        lane = NativeInferenceLane("test")
        task = asyncio.create_task(lane.run(native_work))
        await asyncio.to_thread(started.wait, 0.5)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 0.1)
        self.assertFalse(finished.is_set())
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            await lane.run(lambda: "must not run")
        release.set()
        await asyncio.to_thread(finished.wait, 0.5)
        self.assertTrue(finished.is_set())

    async def test_unowned_native_helper_does_not_hold_cancelled_shutdown(self):
        release = threading.Event()

        task = asyncio.create_task(run_native_until_complete(release.wait, 1))
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 0.1)
        release.set()


if __name__ == "__main__":
    unittest.main()
