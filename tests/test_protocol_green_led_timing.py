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

# Control limits for Agreen duration
# Very lax limits to allow for some variability in hardware timing
# This is a soft failure test, so we allow some leeway in the timing
TARGET_DURATION = 1.200
TOLERANCE = 0.1  # 100 ms tolerance for Agreen duration

def check_control_limits(data, target, tolerance):
    """
    Check if the data is within control limits defined by target and tolerance.
    
    :param data: list or np.array of measurements
    :param target: target value for the process
    :param tolerance: acceptable deviation from the target
    :return: True if all data points are within limits, False otherwise
    
    Prints out the control limits and whether the data is within those limits.
    """
    upper_limit = target + tolerance
    lower_limit = target - tolerance
    if isinstance(data, list):
        data = np.array(data)

    within_limits = np.all((data >= lower_limit) & (data <= upper_limit))

    print(f"Control Limits: LCL={lower_limit}, UCL={upper_limit}")
    print(f"Data within control limits: {within_limits}")
    
    if not within_limits:
        failures = [(i, val) for i, val in enumerate(data) if not (lower_limit <= val <= upper_limit)]
        print("Out-of-control data points:")
        for idx, val in failures:
            print(f"  Index {idx}: {val:.6f} s")
    else:
        print("All data points are within control limits.")

    return within_limits


def process_capability_metrics(data, target, tolerance):
    """ Calculate process capability metrics Cp and Cpk.
    param data: list or np.array of measurements
    param target: target value for the process
    param tolerance: acceptable deviation from the target
    
    Cp is the process capability index, which measures how well a process can produce output within specified limits.
    Cpk is the process capability index adjusted for the mean of the process.
    
    Good values for Cp and Cpk are typically above 1.33, indicating a capable process.
    1.0 is the minimum acceptable value, while values above 2.0 indicate an excellent process.
    
    Returns Cp, Cpk, mean, and standard deviation of the data.
    
    """
    mean = np.mean(data)
    stddev = np.std(data, ddof=1)

    USL = target + tolerance
    LSL = target - tolerance

    Cp = (USL - LSL) / (6 * stddev)
    Cpk = min((USL - mean), (mean - LSL)) / (3 * stddev)

    return Cp, Cpk, mean, stddev


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
    
    # ---- Process Capability Metrics ----
    cap_Cp, cap_Cpk, cap_mean, cap_stddev = process_capability_metrics(
        delay_intervals, EXPECTED_DELAY, TOLERANCE_S
    )
    
    print(f"\nProcess Capability Metrics for Agreen Delay:")
    print(f"Cp: {cap_Cp:.2f}, Cpk: {cap_Cpk:.2f}, Mean: {cap_mean:.6f}s, StdDev: {cap_stddev:.6f}s")

    # Assertions for expected values, with soft failure handling
    failures = []

    if abs(delay_mean - EXPECTED_DELAY) >= TOLERANCE_S:
        failures.append(
            f"Agreen ON delay too far from expected ({EXPECTED_DELAY}s). Got {delay_mean:.6f}s"
        )

    if abs(duration_mean - AGREEN_DURATION_S) >= TOLERANCE_S:
        failures.append(
            f"Agreen duration too far from expected ({AGREEN_DURATION_S}s). Got {duration_mean:.6f}s"
        )

    if cap_Cp <= 1.0:
        failures.append(f"Process capability Cp is too low: {cap_Cp:.2f}")

    if cap_Cpk <= 1.0:
        failures.append(f"Process capability Cpk is too low: {cap_Cpk:.2f}")

    if not check_control_limits(duration_intervals, AGREEN_DURATION_S, TOLERANCE_S):
        failures.append("Agreen duration measurements are not within control limits")

    # ---- Summary and Assertion ----
    if failures:
        print("\nValidation Failures:")
        for msg in failures:
            print(f"- {msg}")
        raise AssertionError("Validation check(s) failed:\n" + "\n".join(failures))