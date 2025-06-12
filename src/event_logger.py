import time
from typing import List, Tuple, Optional
import json


class EventLogger:
    def __init__(self):
        self._start_time: Optional[float] = None
        self._events: List[Tuple[float, str]] = []

    def start_event(self, label: str = "start"):
        """Marks the beginning of the timeline with an optional label."""
        self._start_time = time.time()
        self._events.clear()
        self._events.append((0.0, label))

    def log_event(self, label: str):
        """Logs a labeled event with the time offset (in seconds) from the start."""
        if self._start_time is None:
            raise RuntimeError("EventLogger must be started using start_event() before logging events.")
        now = time.time()
        elapsed = now - self._start_time
        self._events.append((elapsed, label))

    def get_events(self) -> List[Tuple[float, str]]:
        """Returns the list of logged events as (elapsed_time_s, label) tuples."""
        return self._events

    def to_json(self, indent: int = 2) -> str:
        """Returns the events as a JSON-formatted string."""
        events_dict = [
            {"time_s": round(t, 6), "label": label} for t, label in self._events
        ]
        return json.dumps(events_dict, indent=indent)

    def save_to_file(self, path: str):
        """Saves the event log to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    def to_dict(self) -> list[dict]:
        """Returns the events as a list of dictionaries for JSON serialization."""
        return [{"time_s": round(t, 6), "label": label} for t, label in self._events]

    @classmethod
    def from_dict(cls, data: list[dict]) -> "EventLogger":
        logger = cls()
        logger._start_time = 0  # synthetic start time
        logger._events = [(item["time_s"], item["label"]) for item in data]
        return logger

    def __str__(self):
        return "\n".join(f"{t:.6f}s - {label}" for t, label in self._events)


if __name__ == "__main__":
    logger = EventLogger()
    logger.start_event("test_event")
    logger.log_event("step_1_completed")
    logger.log_event("step_2_completed")
    print(logger.to_json())
