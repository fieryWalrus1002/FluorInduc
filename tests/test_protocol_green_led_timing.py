import os
import re
import pytest
import numpy as np
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
from scipy.stats import t

# Settings
N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95
TOLERANCE_S = 0.005  # 5 ms tolerance

WAIT_AFTER_ARED_S = 0.002
AGREEN_DELAY_S = 0.002
AGREEN_DURATION_S = 1.2
EXPECTED_DELAY = WAIT_AFTER_ARED_S + AGREEN_DELAY_S


def get_event_time_by_pattern(events, pattern: str):
    compiled = re.compile(pattern)
    for time_point, label in events:
        if compiled.search(label):
            return time_point
    raise AssertionError(f"No event label matched the pattern: '{pattern}'")


def get_relative_event_times(events, reference_label="ared_on"):
    reference_time = None
    for time_point, label in events:
        if label == reference_label:
            reference_time = time_point
            break
    if reference_time is None:
        raise AssertionError(f"Reference event '{reference_label}' not found")
    return [(time_point - reference_time, label) for time_point, label in events]


def compute_confidence_interval(data, confidence=0.95):
    arr = np.array(data)
    mean = arr.mean()
    std_err = arr.std(ddof=1) / np.sqrt(len(arr))
    ci = t.interval(confidence, len(arr) - 1, loc=mean, scale=std_err)
    return mean, std_err, ci


@pytest.mark.hardware
def test_agreen_timing_intervals(tmp_path):
    delay_intervals = []
    duration_intervals = []

    for i in range(N_REPEATS):
        io = IOController()
        io.open_device()
        print(f"Running protocol iteration {i + 1}/{N_REPEATS}")
        filename = tmp_path / f"run_{i}_output.csv"

        cfg = ExperimentConfig(
            actinic_led_intensity=75,
            measurement_led_intensity=30,
            recording_length_s=2.0,
            recording_hz=1000,
            ared_duration_s=1.0,
            wait_after_ared_s=WAIT_AFTER_ARED_S,
            agreen_delay_s=AGREEN_DELAY_S,
            agreen_duration_s=AGREEN_DURATION_S,
            filename=str(filename),
        )

        runner = ProtocolRunner(io, Recorder(io))
        result = runner.run_protocol(cfg, debug=False)
        assert "Protocol completed successfully" in result

        events = cfg.event_logger.get_events()
        relative_events = get_relative_event_times(events, "ared_on")

        t_ared_off = get_event_time_by_pattern(
            relative_events, r"action_ared_off_executed_at_"
        )
        t_agreen_on = get_event_time_by_pattern(
            relative_events, r"action_agreen_on_executed_at_"
        )
        t_agreen_off = get_event_time_by_pattern(relative_events, r"agreen_off")

        delay_intervals.append(t_agreen_on - t_ared_off)
        duration_intervals.append(t_agreen_off - t_agreen_on)

        io.cleanup()

    # ---- Analysis ----
    delay_mean, delay_sem, delay_ci = compute_confidence_interval(
        delay_intervals, CONFIDENCE_LEVEL
    )
    duration_mean, duration_sem, duration_ci = compute_confidence_interval(
        duration_intervals, CONFIDENCE_LEVEL
    )

    print("\n--- Agreen Delay Stats ---")
    print(f"Mean: {delay_mean:.6f}s | SEM: {delay_sem:.6f}s")
    print(f"{int(CONFIDENCE_LEVEL*100)}% CI: {delay_ci[0]:.6f} to {delay_ci[1]:.6f}s")

    print("\n--- Agreen Duration Stats ---")
    print(f"Mean: {duration_mean:.6f}s | SEM: {duration_sem:.6f}s")
    print(
        f"{int(CONFIDENCE_LEVEL*100)}% CI: {duration_ci[0]:.6f} to {duration_ci[1]:.6f}s"
    )

    # green duration is failing, find out why
    # --- Agreen Delay Stats ---
    # Mean: 0.017368s | SEM: 0.002168s
    # 95% CI: 0.012463 to 0.022273s

    # --- Agreen Duration Stats ---
    # Mean: 1.978831s | SEM: 0.004155s
    # 95% CI: 1.969431 to 1.988231s

    # ---- Assertions ----
    assert (
        abs(delay_mean - EXPECTED_DELAY) < TOLERANCE_S
    ), f"Agreen ON delay too far from expected ({EXPECTED_DELAY}s). Got {delay_mean:.6f}s"

    assert (
        abs(duration_mean - AGREEN_DURATION_S) < TOLERANCE_S
    ), f"Agreen duration too far from expected ({AGREEN_DURATION_S}s). Got {duration_mean:.6f}s"
