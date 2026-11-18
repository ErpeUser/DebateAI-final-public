import asyncio
import unittest

from app.services.inference_scheduler import (
    InferencePreempted,
    InferencePriority,
    run_local_inference,
)


class InferenceSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_endpoint_requests_never_overlap(self):
        active = 0
        peak = 0

        async def operation(label: str):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return label

        results = await asyncio.gather(
            run_local_inference(
                "http://ollama.test/v1",
                InferencePriority.NORMAL,
                lambda: operation("first"),
            ),
            run_local_inference(
                "http://ollama.test/v1",
                InferencePriority.NORMAL,
                lambda: operation("second"),
            ),
        )

        self.assertEqual(["first", "second"], results)
        self.assertEqual(1, peak)

    async def test_high_priority_request_preempts_running_normal_operation(self):
        normal_started = asyncio.Event()
        normal_cancelled = asyncio.Event()

        async def slow_normal():
            normal_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                normal_cancelled.set()

        normal = asyncio.create_task(
            run_local_inference(
                "http://ollama.test/v1",
                InferencePriority.NORMAL,
                slow_normal,
            )
        )
        await normal_started.wait()

        high = await run_local_inference(
            "http://ollama.test/v1",
            InferencePriority.HIGH,
            lambda: asyncio.sleep(0, result="debate"),
        )

        self.assertEqual("debate", high)
        await normal_cancelled.wait()
        with self.assertRaises(InferencePreempted):
            await normal

    async def test_different_endpoints_can_run_concurrently(self):
        both_started = asyncio.Event()
        active = 0

        async def operation(label: str):
            nonlocal active
            active += 1
            if active == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=0.5)
            active -= 1
            return label

        results = await asyncio.gather(
            run_local_inference(
                "http://first.test/v1",
                InferencePriority.NORMAL,
                lambda: operation("first"),
            ),
            run_local_inference(
                "http://second.test/v1",
                InferencePriority.NORMAL,
                lambda: operation("second"),
            ),
        )

        self.assertCountEqual(["first", "second"], results)

    async def test_cancelled_caller_releases_endpoint_for_next_request(self):
        started = asyncio.Event()
        operation_cancelled = asyncio.Event()

        async def cancelled_operation():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                operation_cancelled.set()

        caller = asyncio.create_task(
            run_local_inference(
                "http://ollama.test/v1",
                InferencePriority.NORMAL,
                cancelled_operation,
            )
        )
        await started.wait()
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        await operation_cancelled.wait()

        result = await run_local_inference(
            "http://ollama.test/v1",
            InferencePriority.NORMAL,
            lambda: asyncio.sleep(0, result="reused"),
        )
        self.assertEqual("reused", result)


if __name__ == "__main__":
    unittest.main()
