import asyncio
import unittest

from app.services.agents.event_bus import CooldownSubscriber


class CooldownSubscriberTests(unittest.IsolatedAsyncioTestCase):
    async def test_events_arriving_during_handler_are_scheduled_after_it_finishes(self):
        handler_started = asyncio.Event()
        release_handler = asyncio.Event()
        batches: list[list[dict]] = []

        async def handler(batch: list[dict]):
            batches.append(batch)
            if len(batches) == 1:
                handler_started.set()
                await release_handler.wait()

        subscriber = CooldownSubscriber(handler, cooldown_seconds=0)
        first = asyncio.create_task(subscriber({"id": 1}))
        await asyncio.wait_for(handler_started.wait(), 0.2)

        await subscriber({"id": 2})
        release_handler.set()
        await first
        await asyncio.sleep(0.02)

        self.assertEqual([[{"id": 1}], [{"id": 2}]], batches)
        subscriber.stop()


if __name__ == "__main__":
    unittest.main()
