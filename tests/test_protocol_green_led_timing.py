import os
import re
import pytest
import numpy as np
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
from scipy.stats import t

# Timing parameters for Agreen LED
WAIT_AFTER_ARED_S = 0.002
AGREEN_DELAY_S = 0.002

# Settings for t test
N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95

# Tolerance settings for Agreen LED timing
TOLERANCE_DELAY_S = 0.005
TOLERANCE_DURATION_S = 0.010  # This is pretty tight over, given its over many loops and actions. Lots of chance for variability.
TARGET_AGREEN_DURATION_S = 1.2
TARGET_AGREEN_DELAY_S = WAIT_AFTER_ARED_S + AGREEN_DELAY_S


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
def test_agreen_duration_timing_intervals(tmp_path):
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
            agreen_duration_s=TARGET_AGREEN_DURATION_S,
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

        duration_intervals.append(t_agreen_off - t_agreen_on)

        io.cleanup()

    # ---- Analysis ----
    duration_mean, duration_sem, duration_ci = compute_confidence_interval(
        duration_intervals, CONFIDENCE_LEVEL
    )

    print("\n--- Agreen Duration Stats ---")
    print(f"Mean: {duration_mean:.6f}s | SEM: {duration_sem:.6f}s")
    print(
        f"{int(CONFIDENCE_LEVEL*100)}% CI: {duration_ci[0]:.6f} to {duration_ci[1]:.6f}s"
    )
    # Process cap for the duration intervals
    cap_Cp_duration, cap_Cpk_duration, cap_mean_duration, cap_stddev_duration = process_capability_metrics(
        duration_intervals, TARGET_AGREEN_DURATION_S, TOLERANCE_DURATION_S
    )

    print(f"\nProcess Capability Metrics for Agreen Duration:")
    print(f"Cp: {cap_Cp_duration:.2f}, Cpk: {cap_Cpk_duration:.2f}, Mean: {cap_mean_duration:.6f}s, StdDev: {cap_stddev_duration:.6f}s")

    # Assertions for expected values, with soft failure handling
    failures = []

    if not (TARGET_AGREEN_DURATION_S >= duration_ci[0] and TARGET_AGREEN_DURATION_S <= duration_ci[1]):
        failures.append(
            f"Agreen duration target ({TARGET_AGREEN_DURATION_S}s) is outside the 95% confidence interval: "
            f"{duration_ci[0]:.6f}s to {duration_ci[1]:.6f}s"
        )

    print("\n--- Control Limits Checks for Agreen Duration ---")
    if not check_control_limits(
        duration_intervals, TARGET_AGREEN_DURATION_S, TOLERANCE_DURATION_S
    ):  
        failures.append("Agreen duration measurements are not within control limits")

    # now do the process capability checks
    if cap_Cp_duration <= 1.0:
        failures.append(f"Agreen_duration process capability Cp is too low: {cap_Cp_duration:.2f}")

    if cap_Cpk_duration < 0:
        failures.append("Warning: Cpk is negative for Agreen_duration. Process is centered outside of spec limits.")

        """
        Notes:
        Process is very tight (Cp is excellent)
        Mean is centered off target (Cpk negative)
        
        This is good for me, as I know that the timing is not perfect, but it is consistent.
        That means we can find out where in the protocol the timing is off, and fix
        that offset.
        """

    # ---- Summary and Assertion ----
    if failures:
        print("\nValidation Failures:")
        for msg in failures:
            print(f"- {msg}")
        raise AssertionError("Validation check(s) failed:\n" + "\n".join(failures))


@pytest.mark.hardware
def test_agreen_delay_timing_intervals(tmp_path):
    delay_intervals = []

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
            agreen_duration_s=TARGET_AGREEN_DURATION_S,
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

        io.cleanup()

    # ---- Analysis ----
    delay_mean, delay_sem, delay_ci = compute_confidence_interval(
        delay_intervals, CONFIDENCE_LEVEL
    )


    print("\n--- Agreen Delay Stats ---")
    print(f"Mean: {delay_mean:.6f}s | SEM: {delay_sem:.6f}s")
    print(f"{int(CONFIDENCE_LEVEL*100)}% CI: {delay_ci[0]:.6f} to {delay_ci[1]:.6f}s")


    # ---- Process Capability Metrics ----
    cap_Cp_delay, cap_Cpk_delay, cap_mean_delay, cap_stddev_delay = (
        process_capability_metrics(
            delay_intervals, TARGET_AGREEN_DELAY_S, TOLERANCE_DELAY_S
        )
    )

    print(f"\nProcess Capability Metrics for Agreen Delay:")
    print(
        f"Cp: {cap_Cp_delay:.2f}, Cpk: {cap_Cpk_delay:.2f}, Mean: {cap_mean_delay:.6f}s, StdDev: {cap_stddev_delay:.6f}s"
    )


    # Assertions for expected values, with soft failure handling
    failures = []

    # assertions for the t test results
    if not (
        TARGET_AGREEN_DELAY_S >= delay_ci[0] and TARGET_AGREEN_DELAY_S <= delay_ci[1]
    ):
        failures.append(
            f"Agreen delay target ({TARGET_AGREEN_DELAY_S}s) is outside the 95% confidence interval: "
            f"{delay_ci[0]:.6f}s to {delay_ci[1]:.6f}s"
        )


    # control limits checks for both delay and duration
    print("\n--- Control Limits Checks for Agreen Delay ---")
    if not check_control_limits(
        delay_intervals, TARGET_AGREEN_DELAY_S, TOLERANCE_DELAY_S
    ):
        failures.append("Agreen delay measurements are not within control limits")

    # now do the process capability checks
    if cap_Cp_delay <= 1.0:
        failures.append(
            f"Agreen_delay process capability Cp is too low: {cap_Cp_delay:.2f}"
        )

    if cap_Cpk_delay < 0:
        failures.append(
            "Warning: Cpk is negative for Agreen_delay. Process is centered outside of spec limits."
        )

    # ---- Summary and Assertion ----
    if failures:
        print("\nValidation Failures:")
        for msg in failures:
            print(f"- {msg}")
        raise AssertionError("Validation check(s) failed:\n" + "\n".join(failures))
