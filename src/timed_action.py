# This is for the TimedAction class, which is used to perform actions during a recording session
# that are time-based.

from src.event_logger import EventLogger
import time


class TimedAction:
    def __init__(self, action_time_s: float, action_fn: callable, label: str, epsilon: float = 0.002):
        self.action_time_s = action_time_s
        self.action_fn = action_fn
        self.label = label
        self.epsilon = epsilon
        self._executed = False

        if action_time_s < 0:
            raise ValueError("Action time cannot be negative.")

    def should_execute(self, elapsed_time: float) -> bool:
        return not self._executed and elapsed_time >= (self.action_time_s - self.epsilon)

    # def should_execute(self, elapsed_time: float) -> bool:
    #     return not self._executed and elapsed_time >= self.action_time_s

    # def execute(self, logger: EventLogger) -> float:
    #     if self._executed:
    #         return 0.0
    #     self.action_fn()
    #     actual_time = time.perf_counter()
    #     logger.log_event(
    #         f"action_{self.label}_executed (scheduled=+{self.action_time_s:.3f}s)"
    #     )
    #     self._executed = True
    #     return actual_time

    def execute(self, logger: EventLogger, t_zero: float = None) -> float:
        if self._executed:
            return 0.0
        self.action_fn()
        actual_time = time.perf_counter()
        self._executed = True

        if t_zero is not None:
            elapsed_actual = actual_time - t_zero
            latency = elapsed_actual - self.action_time_s
            logger.log_event(
                f"action_{self.label}_executed "
                f"(scheduled=+{self.action_time_s:.3f}s, actual=+{elapsed_actual:.3f}s, latency={latency:.3f}s)"
            )
        else:
            logger.log_event(
                f"action_{self.label}_executed (scheduled=+{self.action_time_s:.3f}s)"
            )
        return actual_time
