import os
import re
import pytest
import numpy as np
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
from scipy.stats import t
import csv
from pathlib import Path

from tests.utils import (
    check_control_limits,
    process_capability_metrics,
    compute_confidence_interval,
    get_event_time_by_pattern,
    pretty_print_events
)

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


def run_protocol_and_extract_events(
    tmp_path,
    i: int,
    config_overrides: dict = None,
):
    io = IOController()
    io.open_device()

    # basic settings, we will override
    cfg = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_hz=1000,
        ared_duration_s=1.0,
        wait_after_ared_s=0.002,
        agreen_delay_s=AGREEN_DELAY_S,
        agreen_duration_s=TARGET_AGREEN_DURATION_S,
        filename=str(tmp_path / f"run_{i}.csv"),
    )

    # Apply overrides if needed
    if config_overrides:
        for k, v in config_overrides.items():
            setattr(cfg, k, v)

    runner = ProtocolRunner(io, Recorder(io))
    result = runner.run_protocol(cfg, debug=False)
    assert "Protocol completed successfully" in result

    events = cfg.event_logger.get_events()
    assert len(events) > 0, "No events recorded during protocol run"
    
    pretty_print_events(events)
    return events


def print_stats(title, durations, target, mean, stddev, sem, ci, Cp, Cpk):
    print(f"\n--- {title} ---")
    print(f"Samples: {len(durations)} | Target: {target:.6f}s")
    print(f"Mean: {mean:.6f}s | StdDev: {stddev:.6f}s | SEM: {sem:.6f}s")
    print(f"CI: {ci[0]:.6f}s to {ci[1]:.6f}s")
    print(f"Cp: {Cp:.2f} | Cpk: {Cpk:.2f}")


def analyze_event_interval(
    tmp_path,
    start_event: str,
    end_event: str,
    target_duration: float = 1.0,
    tolerance: float = 0.01,
    n_repeats: int = 10,
    confidence_level: float = 0.95,
    config_overrides: dict = None,
    csv_output_path: Path = None,
):
    """
    Run N protocol iterations, compute interval duration between two events,
    and assess statistical properties (CI, control limits, Cp, Cpk).
    """

    durations = []

    for i in range(n_repeats):
        events = run_protocol_and_extract_events(tmp_path, i, config_overrides)
        t_start = get_event_time_by_pattern(events, start_event)
        t_end = get_event_time_by_pattern(events, end_event)
        print(f"Run {i}: {start_event} at {t_start:.6f}, {end_event} at {t_end:.6f}, Δ = {t_end - t_start:.6f}")
        durations.append(t_end - t_start)

    # -- Statistics --
    mean, sem, ci = compute_confidence_interval(durations, confidence_level)
    Cp, Cpk, pmean, stddev = process_capability_metrics(
        durations, target_duration, tolerance
    )

    # -- Print results --
    print_stats(
        f"Interval: {start_event} → {end_event}",
        durations,
        target_duration,
        mean,
        stddev,
        sem,
        ci,
        Cp,
        Cpk
    )
    # --- Write to CSV if requested ---
    if csv_output_path:
        csv_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Run", "StartEvent", "EndEvent", "Duration_s"])
            for i, d in enumerate(durations):
                writer.writerow([i, start_event, end_event, f"{d:.6f}"])
            writer.writerow([])
            writer.writerow(["Stat", "Value"])
            writer.writerow(["TargetDuration", f"{target_duration:.6f}"])
            writer.writerow(["Mean", f"{mean:.6f}"])
            writer.writerow(["StdDev", f"{stddev:.6f}"])
            writer.writerow(["SEM", f"{sem:.6f}"])
            writer.writerow(["CI Lower", f"{ci[0]:.6f}"])
            writer.writerow(["CI Upper", f"{ci[1]:.6f}"])
            writer.writerow(["Cp", f"{Cp:.2f}"])
            writer.writerow(["Cpk", f"{Cpk:.2f}"])

    # -- Validation --
    failures = []

    if not (ci[0] <= target_duration <= ci[1]):
        failures.append(
            f"Target duration {target_duration:.6f}s not in CI: ({ci[0]:.6f}, {ci[1]:.6f})"
        )

    if not check_control_limits(durations, target_duration, tolerance):
        failures.append("Interval measurements not within control limits")

    if Cp <= 1.0:
        failures.append(f"Cp too low: {Cp:.2f}")
    if Cpk < 0:
        failures.append(f"Cpk is negative: {Cpk:.2f}")

    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"- {f}")
        raise AssertionError("Validation failed:\n" + "\n".join(failures))


# @pytest.mark.parametrize(
#     "start_event,end_event,target,tolerance",
#     [
#         ("action_agreen_on", "agreen_off", 1.2, 0.01),
#         ("action_ared_off_executed_at_", "action_agreen_on_executed_at_", 0.004, 0.005),
#     ],
# )
# @pytest.mark.hardware
# def test_event_intervals(tmp_path, start_event, end_event, target, tolerance):
#     analyze_event_interval(
#         tmp_path=tmp_path,
#         start_event=start_event,
#         end_event=end_event,
#         target_duration=target,
#         tolerance=tolerance,
#         n_repeats=10,
#     )


@pytest.mark.hardware
def test_agreen_duration_is_precise(tmp_path):

    # get the date and time as a "YY-MM-DD" string
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    output_file = Path(f"tests/test_results/{date_str}_agreen_duration_stats_.csv")
    analyze_event_interval(
        tmp_path=tmp_path,
        start_event="action_agreen_on",
        end_event="agreen_off",
        target_duration=TARGET_AGREEN_DURATION_S,
        tolerance= TOLERANCE_DURATION_S,
        n_repeats=N_REPEATS,
        csv_output_path=output_file
    )


# @pytest.mark.hardware
# def test_agreen_delay_is_precise(tmp_path):
#     analyze_event_interval(
#         tmp_path=tmp_path,
#         start_event="action_ared_off_executed_at_",
#         end_event="action_agreen_on_executed_at_",
#         target_duration=0.004,  # 0.002 wait + 0.002 delay
#         tolerance=0.005,
#         n_repeats=10,
#     )


# @pytest.mark.hardware
# def test_agreen_duration_timing_intervals(tmp_path):
#     duration_intervals = []

#     for i in range(N_REPEATS):
#         print(f"Running protocol iteration {i + 1}/{N_REPEATS}")
#         filename = tmp_path / f"run_{i}_output.csv"

#         cfg = ExperimentConfig(
#             actinic_led_intensity=75,
#             measurement_led_intensity=30,
#             recording_hz=1000,
#             ared_duration_s=1.0,
#             wait_after_ared_s=WAIT_AFTER_ARED_S,
#             agreen_delay_s=AGREEN_DELAY_S,
#             agreen_duration_s=TARGET_AGREEN_DURATION_S,
#             filename=str(filename),
#         )

#         events = run_protocol_and_extract_events(cfg, tmp_path, i)

#         t_agreen_on = get_event_time_by_pattern(
#             events, r"action_agreen_on"
#         )
#         t_agreen_off = get_event_time_by_pattern(events, r"agreen_off")

#         duration_intervals.append(t_agreen_off - t_agreen_on)

#     # ---- Analysis ----
#     duration_mean, duration_sem, duration_ci = compute_confidence_interval(
#         duration_intervals, CONFIDENCE_LEVEL
#     )

#     print("\n--- Agreen Duration Stats ---")
#     print(f"Number of measurements: {len(duration_intervals)}")
#     print(f"Target Agreen Duration: {TARGET_AGREEN_DURATION_S:.6f}s")
#     print(f"Mean: {duration_mean:.6f}s | SEM: {duration_sem:.6f}s")
#     print(
#         f"{int(CONFIDENCE_LEVEL*100)}% CI: {duration_ci[0]:.6f} to {duration_ci[1]:.6f}s"
#     )
#     # Process cap for the duration intervals
#     cap_Cp_duration, cap_Cpk_duration, cap_mean_duration, cap_stddev_duration = process_capability_metrics(
#         duration_intervals, TARGET_AGREEN_DURATION_S, TOLERANCE_DURATION_S
#     )

#     print(f"\nProcess Capability Metrics for Agreen Duration:")
#     print(f"Cp: {cap_Cp_duration:.2f}, Cpk: {cap_Cpk_duration:.2f}, Mean: {cap_mean_duration:.6f}s, StdDev: {cap_stddev_duration:.6f}s")

#     # Assertions for expected values, with soft failure handling
#     failures = []

#     if not (TARGET_AGREEN_DURATION_S >= duration_ci[0] and TARGET_AGREEN_DURATION_S <= duration_ci[1]):
#         failures.append(
#             f"Agreen duration target ({TARGET_AGREEN_DURATION_S}s) is outside the 95% confidence interval: "
#             f"{duration_ci[0]:.6f}s to {duration_ci[1]:.6f}s"
#         )

#     print("\n--- Control Limits Checks for Agreen Duration ---")
#     if not check_control_limits(
#         duration_intervals, TARGET_AGREEN_DURATION_S, TOLERANCE_DURATION_S
#     ):
#         failures.append("Agreen duration measurements are not within control limits")

#     # now do the process capability checks
#     if cap_Cp_duration <= 1.0:
#         failures.append(f"Agreen_duration process capability Cp is too low: {cap_Cp_duration:.2f}")

#     if cap_Cpk_duration < 0:
#         failures.append("Warning: Cpk is negative for Agreen_duration. Process is centered outside of spec limits.")

#         """
#         Notes:
#         Process is very tight (Cp is excellent)
#         Mean is centered off target (Cpk negative)

#         This is good for me, as I know that the timing is not perfect, but it is consistent.
#         That means we can find out where in the protocol the timing is off, and fix
#         that offset.
#         """

#     # ---- Summary and Assertion ----
#     if failures:
#         print("\nValidation Failures:")
#         for msg in failures:
#             print(f"- {msg}")
#         raise AssertionError("Validation check(s) failed:\n" + "\n".join(failures))
