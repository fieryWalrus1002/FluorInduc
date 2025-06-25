# timing_utils.py
# timing_utils.py
# for the various durations and delays in the protocol
import numpy as np
from scipy.stats import t
import re
from src.protocol_runner import ProtocolRunner
from src.io_controller import IOController
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig
from src.timed_action_factory import TimedActionFactory
import csv
from datetime import datetime
from pathlib import Path
from scipy.stats import ttest_1samp


def get_event_time_by_pattern(events, pattern: str):
    compiled = re.compile(pattern)
    for time_point, label in events:
        if compiled.search(label):
            return time_point

    # Print all available events for debugging
    print("\nAvailable event labels:")
    for _, label in events:
        print(f"  - {label}")

    raise AssertionError(f"No event label matched the pattern: '{pattern}'")



def suggest_delay_corrections(current_overrides, durations_by_name, expected_values):
    print("\n--- Suggested delay_overrides ---")
    corrected = {}
    for name, values in durations_by_name.items():
        if name not in expected_values:
            continue
        mean = sum(values) / len(values)
        expected = expected_values[name]
        drift = mean - expected
        current = current_overrides.get(name, 0.0)
        corrected[name] = current - drift

    # Print as ready-to-paste dict
    print("delay_overrides = {")
    for name, value in corrected.items():
        print(f'    "{name}": {value:+.6f},')
    print("}")
    print("--------------------------------------------------------\n")


def print_event_timeline(events, labels):
    times = {}
    for label in labels:
        times[label] = get_event_time_by_pattern(events, label)

    t_zero = times["ared_on"]

    print("\n--- Recorded Event Times (relative to t_zero = ared_on) ---")
    for label in labels:
        delta = times[label] - t_zero
        print(f"{label:<20} @ raw={times[label]:.6f}, delta={delta:.6f} s")
    print("------------------------------------------------------------\n")


def extract_intervals(events, interval_specs):
    """
    interval_specs: List of (name, start_pattern, end_pattern)
    Returns dict: name -> duration
    """
    results = {}
    for name, start_pat, end_pat in interval_specs:
        t0 = get_event_time_by_pattern(events, start_pat)
        t1 = get_event_time_by_pattern(events, end_pat)
        results[name] = t1 - t0
    return results


def run_protocol_and_extract_all_events(tmp_path, i, config: ExperimentConfig, delay_overrides: dict = None):
    io = IOController()
    io.open_device()

    # Ensure filename is unique per run
    cfg = config.clone_with(filename=str(tmp_path / f"data/run_{i}.csv"))

    cfg.print_config()

    if delay_overrides is not None:
        print("Using custom delay overrides:")
        for key, value in delay_overrides.items():
            print(f"  {key}: {value:.6f} seconds")

    factory = TimedActionFactory(io, cfg, delay_overrides=delay_overrides)
    factory.print_timeline()

    runner = ProtocolRunner(io, Recorder(io))
    result = runner.run_protocol(cfg, factory=factory, debug=False)
    assert "Protocol completed successfully" in result

    events = cfg.event_logger.get_events()

    labels = [
        "ared_on",
        "ared_off",
        "wait_after_ared",
        "shutter_opened",
        "agreen_on",
        "agreen_off",
        "end_recording",
    ]
    missing = [label for label in labels if not any(label in e for _, e in events)]
    if missing:
        print("Warning: missing expected labels:", missing)

    print_event_timeline(events, labels)

    io.cleanup()
    return events


def perform_ttest_against_expected(values, expected_mean, confidence=0.95):
    """
    Performs a one-sample t-test to check if the sample mean equals the expected mean.
    Returns the t-statistic and p-value. Raises AssertionError if null hypothesis is rejected.
    """
    t_stat, p_value = ttest_1samp(values, expected_mean)
    alpha = 1 - confidence

    print(f"T-statistic: {t_stat:.3f}")
    print(f"P-value:     {p_value:.4f} (alpha = {alpha:.4f})")

    assert p_value > alpha, (
        f"Expected duration {expected_mean:.6f}s rejected by t-test "
        f"(p = {p_value:.4f}, alpha = {alpha:.4f})"
    )

    return t_stat, p_value


def summarize_durations(durations, expected_duration, confidence=0.95, tolerance=None):
    arr = np.array(durations)
    mean = arr.mean()
    std_dev = arr.std(ddof=1)
    sem = std_dev / np.sqrt(len(arr))
    ci = t.interval(confidence, len(arr) - 1, loc=mean, scale=sem)

    print(f"\nDurations: {durations}")
    print(f"Expected:  {expected_duration:.6f} s")
    print(f"Mean:      {mean:.6f} s")
    print(f"Std Dev:   {std_dev:.6f} s")
    print(f"{int(confidence * 100)}% CI: [{ci[0]:.6f}, {ci[1]:.6f}]")

    if tolerance is not None:
        print(f"Tolerance: ±{tolerance:.6f} s")
        assert abs(mean - expected_duration) < tolerance, (
            f"Mean duration {mean:.6f}s differs from expected {expected_duration:.6f}s "
            f"beyond allowed tolerance {tolerance:.6f}s"
        )

    # Delegate statistical check
    perform_ttest_against_expected(arr, expected_duration, confidence=confidence)


def export_durations_csv(durations_by_name, path: Path):
    """
    Exports all interval durations into a CSV where each row is a run,
    and each column is a named interval (e.g., ared_duration, agreen_duration, etc.)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(durations_by_name.keys())
    rows = zip(*[durations_by_name[name] for name in names])

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Run"] + names)
        for i, row in enumerate(rows):
            writer.writerow([i] + [f"{val:.6f}" for val in row])
