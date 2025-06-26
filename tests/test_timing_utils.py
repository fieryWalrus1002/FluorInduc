import pytest
from tests.timing_utils import (
    get_event_time_by_pattern,
    extract_intervals,
    summarize_durations,
)
import numpy as np


@pytest.fixture
def mock_events():
    return [
        (1.000, "ared_on"),
        (2.000, "ared_off"),
        (2.005, "wait_after_ared"),
        (2.005, "shutter_opened"),
        (2.007, "agreen_on"),
        (3.207, "agreen_off"),
        (3.208, "end_recording"),
    ]


def test_get_event_time_by_pattern_success(mock_events):
    assert get_event_time_by_pattern(mock_events, r"ared_on") == 1.000
    assert get_event_time_by_pattern(mock_events, r"shutter") == 2.005
    assert get_event_time_by_pattern(mock_events, r"green_off") == 3.207


def test_get_event_time_by_pattern_missing_label(mock_events, capsys):
    with pytest.raises(
        AssertionError, match="No event label matched the pattern: 'nonexistent'"
    ):
        get_event_time_by_pattern(mock_events, r"nonexistent")

    # Check if the label list was printed to help debug
    captured = capsys.readouterr()
    assert "Available event labels:" in captured.out
    assert "ared_on" in captured.out


def test_extract_intervals_correct_durations(mock_events):
    specs = [
        ("ared_duration", r"ared_on", r"ared_off"),
        ("agreen_duration", r"agreen_on", r"agreen_off"),
        ("recording_total", r"ared_on", r"end_recording"),
    ]
    durations = extract_intervals(mock_events, specs)

    assert pytest.approx(durations["ared_duration"], abs=1e-6) == 1.000
    assert pytest.approx(durations["agreen_duration"], abs=1e-6) == 1.200
    assert pytest.approx(durations["recording_total"], abs=1e-6) == 2.208


def test_summarize_durations_within_ci_passes(capsys):
    durations = [1.01, 1.00, 1.00, 0.99, 1.01]
    summarize_durations(durations, expected_duration=1.00, confidence=0.95)

    output = capsys.readouterr().out
    assert "Mean" in output
    assert "CI" in output
    assert "Std Dev" in output

def test_summarize_durations_ci_failure_raises():
    durations = [1.10, 1.09, 1.11, 1.12, 1.13]  # Mean is 1.11, expected is 1.00

    with pytest.raises(AssertionError) as excinfo:
        summarize_durations(durations, expected_duration=1.00, confidence=0.95)

    # Check that either of the two assertions could have failed
    msg = str(excinfo.value)
    assert "rejected by t-test" in msg, f"Unexpected AssertionError message: {msg}"


################## actual data extraction tests ##################

@pytest.fixture
def fake_event_log():
    return [
        (1.000, "action_ared_on_executed (scheduled=+0.000s)"),
        (2.005, "action_ared_off_executed (scheduled=+1.005s)"),
        (2.009, "action_agreen_on_executed (scheduled=+1.004s)"),
        (3.209, "action_agreen_off_executed (scheduled=+3.004s)"),
    ]


def test_get_event_time_by_pattern_success(fake_event_log):
    t = get_event_time_by_pattern(fake_event_log, r"ared_on")
    assert t == 1.000

    t = get_event_time_by_pattern(fake_event_log, r"agreen_on")
    assert t == 2.009


def test_get_event_time_by_pattern_missing_label(fake_event_log):
    with pytest.raises(AssertionError, match="No event label matched the pattern"):
        get_event_time_by_pattern(fake_event_log, r"nonexistent_label")


def test_extract_intervals_correct_durations(fake_event_log):
    interval_specs = [
        ("ared_duration", r"ared_on", r"ared_off"),
        ("delay_after_ared", r"ared_off", r"agreen_on"),
        ("agreen_duration", r"agreen_on", r"agreen_off"),
        ("whole_protocol_duration", r"ared_on", r"agreen_off"),
    ]

    intervals = extract_intervals(fake_event_log, interval_specs)

    assert intervals["ared_duration"] == pytest.approx(1.005)
    assert intervals["delay_after_ared"] == pytest.approx(0.004)
    assert intervals["agreen_duration"] == pytest.approx(1.200)
    assert intervals["whole_protocol_duration"] == pytest.approx(2.209)
