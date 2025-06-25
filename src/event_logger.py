import time
from typing import List, Tuple, Optional
import json


class EventLogger:
    def __init__(self, begin: str = None):
        self._start_time: Optional[float] = None
        self._events: List[Tuple[float, str]] = []
        if begin:
            self.start_event(begin)

    def start_event(self, label: str = "start"):
        """Marks the beginning of the timeline with an optional label."""
        self._start_time = time.perf_counter()
        self._events.clear()
        self._events.append((0.0, label))

    def log_event(self, label: str):
        """Logs a labeled event with the time offset (in seconds) from the start."""
        if self._start_time is None:
            raise RuntimeError("EventLogger must be started using start_event() before logging events.")
        now = time.perf_counter()
        elapsed = now - self._start_time
        self._events.append((elapsed, label))

    def get_events(self) -> List[Tuple[float, str]]:
        """Returns the list of logged events as (elapsed_time_s, label) tuples."""
        return self._events

    def get_event_time(self, label: str) -> Optional[float]:
        """Returns the elapsed time in seconds for a specific event label."""
        for t, lbl in self._events:
            if lbl == label:
                return t
        return None

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

    @classmethod
    def from_dict(cls, data: list[dict]) -> "EventLogger":
        logger = cls()
        logger._start_time = 0  # synthetic start time
        logger._events = [
            (float(item.get("time_s", 0.0)), str(item.get("label", "")))
            for item in data
            if isinstance(item, dict) and "time_s" in item and "label" in item
        ]
        return logger

    def __str__(self):
        return "\n".join(f"{t:.6f}s - {label}" for t, label in self._events)

    def to_csv(self) -> str:
        """Returns the events in CSV format."""
        return "time_s,label\n" + "\n".join(f"{t:.6f},{label}" for t, label in self._events)


