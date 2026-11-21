import unittest

from app.services.external_reasoning import AdaptiveReasoningEffort


class AdaptiveReasoningEffortTests(unittest.TestCase):
    def controller(self):
        return AdaptiveReasoningEffort(
            latency_threshold_ms=1000,
            queue_threshold=1,
            stable_calls_to_restore=2,
            new_topic_effort="xhigh",
            follow_up_effort="high",
            deep_reanalysis_effort="xhigh",
        )

    def test_new_topic_uses_xhigh_once_and_related_follow_up_uses_high(self):
        controller = self.controller()

        self.assertEqual(
            "xhigh", controller.effort_for_next(queue_depth=0, is_new_topic=True)
        )
        self.assertEqual(
            "high", controller.effort_for_next(queue_depth=0, is_new_topic=False)
        )

    def test_queue_pressure_forces_high_even_for_new_topic(self):
        controller = self.controller()

        self.assertEqual(
            "high", controller.effort_for_next(queue_depth=1, is_new_topic=True)
        )

    def test_material_deep_reanalysis_uses_xhigh_without_queue_pressure(self):
        controller = self.controller()

        self.assertEqual(
            "xhigh",
            controller.effort_for_next(
                queue_depth=0, is_new_topic=False, needs_deep_reanalysis=True
            ),
        )
        self.assertEqual(
            "high",
            controller.effort_for_next(
                queue_depth=1, is_new_topic=False, needs_deep_reanalysis=True
            ),
        )

    def test_slow_result_keeps_later_calls_on_high_until_stable(self):
        controller = self.controller()
        controller.observe(latency_ms=1500, queue_depth=0)

        self.assertEqual(
            "high", controller.effort_for_next(queue_depth=0, is_new_topic=True)
        )
        controller.observe(latency_ms=400, queue_depth=0)
        controller.observe(latency_ms=500, queue_depth=0)
        self.assertEqual(
            "xhigh", controller.effort_for_next(queue_depth=0, is_new_topic=True)
        )


if __name__ == "__main__":
    unittest.main()
