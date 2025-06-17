# This is for the TimedAction class, which is used to perform actions during a recording session
# that are time-based.

from src.event_logger import EventLogger
import time


class TimedAction:
    def __init__(self, action_time_s: float, action_fn: callable, label: str):
        self.action_time_s = action_time_s
        self.action_fn = action_fn
        self.label = label
        self._executed = False

    def should_execute(self, elapsed_time: float) -> bool:
        return not self._executed and elapsed_time >= self.action_time_s

    def execute(self, logger: EventLogger):
        if self._executed:
            return  # Prevent repeated calls
        self.action_fn()
        logger.log_event(f"action_{self.label}_executed_at_{self.action_time_s:.3f}_s")
        self._executed = True