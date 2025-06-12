import pytest
import time
from src.event_logger import EventLogger


def assert_event_deltas(events, expected_deltas, tolerance=0.01):
    """
    Check that the time between consecutive events matches expected deltas within a tolerance.

    :param events: List of (timestamp, label) tuples
    :param expected_deltas: List of expected time differences between events
    :param tolerance: Acceptable error in seconds (default: 0.01)
    """
    assert (
        len(events) == len(expected_deltas) + 1
    ), "Expected one more event than deltas"

    for i, expected_delta in enumerate(expected_deltas, start=1):
        actual_delta = events[i][0] - events[i - 1][0]
        assert abs(actual_delta - expected_delta) <= tolerance, (
            f"Delta between '{events[i - 1][1]}' and '{events[i][1]}' "
            f"was {actual_delta:.6f}, expected {expected_delta:.6f} ± {tolerance}"
        )


def test_event_logger_timing():
    logger = EventLogger()
    logger.start_event("protocol_start")
    time.sleep(0.002)
    logger.log_event("leds_off_being_set")
    time.sleep(0.800)
    logger.log_event("recording_started")
    time.sleep(0.010)
    logger.log_event("action_triggered_at_sample_2000")
    time.sleep(0.500)
    logger.log_event("recording_finished")

    events = logger.get_events()

    expected_labels = [
        "protocol_start",
        "leds_off_being_set",
        "recording_started",
        "action_triggered_at_sample_2000",
        "recording_finished",
    ]
    actual_labels = [label for _, label in events]
    assert actual_labels == expected_labels

    # Delta sequence: between event 0→1, 1→2, 2→3, 3→4
    assert_event_deltas(events, [0.002, 0.800, 0.010, 0.500], tolerance=0.02)
