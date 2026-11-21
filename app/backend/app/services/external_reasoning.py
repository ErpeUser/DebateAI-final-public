"""Adaptive effort for serialized, non-live external debate analysis."""

from __future__ import annotations


class AdaptiveReasoningEffort:
    """Choose xhigh/high for the next call from measured load.

    An effort value is returned once and never mutated for an in-flight call.
    Observations only affect later calls.
    """

    def __init__(
        self,
        *,
        latency_threshold_ms: int,
        queue_threshold: int,
        stable_calls_to_restore: int,
        new_topic_effort: str = "xhigh",
        follow_up_effort: str = "high",
        deep_reanalysis_effort: str = "xhigh",
    ) -> None:
        self.latency_threshold_ms = max(1000, int(latency_threshold_ms))
        self.queue_threshold = max(1, int(queue_threshold))
        self.stable_calls_to_restore = max(1, int(stable_calls_to_restore))
        self.new_topic_effort = (
            new_topic_effort if new_topic_effort in {"high", "xhigh"} else "xhigh"
        )
        self.follow_up_effort = (
            follow_up_effort if follow_up_effort in {"high", "xhigh"} else "high"
        )
        self.deep_reanalysis_effort = (
            deep_reanalysis_effort
            if deep_reanalysis_effort in {"high", "xhigh"}
            else "xhigh"
        )
        self._overloaded = False
        self._stable_calls = 0

    @property
    def current(self) -> str:
        return "high" if self._overloaded else self.follow_up_effort

    def effort_for_next(
        self,
        *,
        queue_depth: int,
        is_new_topic: bool = False,
        needs_deep_reanalysis: bool = False,
    ) -> str:
        if queue_depth >= self.queue_threshold:
            self._overloaded = True
            self._stable_calls = 0
        if self._overloaded:
            return "high"
        if is_new_topic:
            return self.new_topic_effort
        if needs_deep_reanalysis:
            return self.deep_reanalysis_effort
        return self.follow_up_effort

    def observe(self, *, latency_ms: int, queue_depth: int) -> None:
        overloaded = (
            latency_ms >= self.latency_threshold_ms
            or queue_depth >= self.queue_threshold
        )
        if overloaded:
            self._overloaded = True
            self._stable_calls = 0
            return
        if not self._overloaded:
            return
        self._stable_calls += 1
        if self._stable_calls >= self.stable_calls_to_restore:
            self._overloaded = False
            self._stable_calls = 0
