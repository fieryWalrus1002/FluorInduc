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
from typing import List
from math import sqrt
import numpy as np
from scipy.stats import t
from dataclasses import dataclass


@dataclass
class MeasuredDuration:
    """
    Represents a previous measurement of an action's execution time and its standard deviation.
    This is used to calculate the expected duration of an action in the protocol.
    """

    label: str
    duration: float  # in seconds
    stddev: float  # in seconds
    n_repeats: int  # number of measurements taken, not really used?

    def __add__(self, other):
        if not isinstance(other, MeasuredDuration):
            return NotImplemented

        combined_label = f"{self.label} + {other.label}"
        combined_duration = self.duration + other.duration
        combined_stddev = sqrt(self.stddev**2 + other.stddev**2)

        return MeasuredDuration(
            label=combined_label,
            duration=combined_duration,
            stddev=combined_stddev,
            n_repeats=min(self.n_repeats, other.n_repeats),
        )

    def confidence_interval(self, confidence_level=0.95):
        """
        Returns the confidence interval as (lower_bound, upper_bound) using Student's t-distribution.
        """
        if self.n_repeats < 2:
            raise ValueError(
                "At least two measurements are required for confidence interval calculation."
            )

        # Degrees of freedom
        df = self.n_repeats - 1

        # Standard error of the mean (SEM)
        sem = self.stddev / sqrt(self.n_repeats)

        # t-score for the given confidence level
        t_score = t.ppf((1 + confidence_level) / 2.0, df)

        margin = t_score * sem

        return (self.duration - margin, self.duration + margin)

    def __str__(self):
        return (
            f"{self.label}: {self.duration:.6f} s\n"
            f"StdDev: {self.stddev:.6f} s\n"
            f"n_repeats: {self.n_repeats}"
        )

@dataclass
class IntervalSpec:
    name: str
    start_label: str
    end_label: str
    measured: MeasuredDuration
    tolerance: float | None = None


def get_t_score(confidence: float, sample_size: int) -> float:
    dof = sample_size - 1
    return t.ppf(1 - (1 - confidence) / 2, dof)


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

    # Sort labels by event time
    sorted_labels = sorted(labels, key=lambda lbl: times[lbl])

    print("\n--- Recorded Event Times (relative to t_zero = ared_on) ---")
    for label in sorted_labels:
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


def run_protocol_and_extract_all_events(
    tmp_path, 
    i,
    config: ExperimentConfig,
    expected_labels: List[str] = None,
    delay_overrides: dict = None,
    factory: TimedActionFactory = None,
    io: IOController = None
):
    
    
    own_io = False
    if io is None:
        io = IOController()
        print("Created new IOController instance")
        own_io = True
    else:
        print("Using provided IOController instance")
        
    io.open_device()

    # Ensure filename is unique per run
    cfg = config.clone_with(filename=str(tmp_path / f"data/run_{i}.csv"))

    cfg.print_config()

    if delay_overrides is not None:
        print("Using custom delay overrides:")
        for key, value in delay_overrides.items():
            print(f"  {key}: {value:.6f} seconds")

    factory = factory or TimedActionFactory(io, cfg, delay_overrides=delay_overrides)
    print(f"Using factory: {factory.__class__.__name__}")
    # factory.print_timeline()

    runner = ProtocolRunner(io, Recorder(io))
    result = runner.run_protocol(cfg, factory=factory, debug=False)
    assert "Protocol completed successfully" in result

    events = cfg.event_logger.get_events()

    if not expected_labels:
        expected_labels = [
            "ared_on",
            "ared_off",
            "wait_after_ared",
            "shutter_opened",
            "agreen_on",
            "agreen_off",
            "end_recording",
        ]
        
    missing = [label for label in expected_labels if not any(label in e for _, e in events)]
    if missing:
        print("Warning: missing expected labels:", missing)

    print_event_timeline(events, expected_labels)

    if own_io:
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


def summarize_durations_with_jitter_awareness(
    name: str,
    durations,
    expected_duration: float,
    component_stddev: float = None,
    confidence: float = 0.95,
    tolerance: float = None,
):
    arr = np.array(durations)
    mean = arr.mean()
    std_dev = arr.std(ddof=1)
    sem = std_dev / np.sqrt(len(arr))

    # confidence interval
    dof = len(arr) - 1
    t_score = t.ppf(1 - (1 - confidence) / 2, dof)
    ci_low = mean - t_score * sem
    ci_high = mean + t_score * sem

    # Jitter-aware confidence range
    jitter_margin = t_score * component_stddev
    lower_bound = expected_duration - jitter_margin
    upper_bound = expected_duration + jitter_margin

    print(f"\nDurations: {durations}")
    print(f"Expected:  {expected_duration:.6f} s")
    print(f"Mean:      {mean:.6f} s")
    print(f"Std Dev:   {std_dev:.6f} s")
    print(f"{int(confidence * 100)}% CI: [{ci_low:.6f}, {ci_high:.6f}]")
    print(
        f"Jitter-aware expected range (±{t_score:.3f}σ): [{lower_bound:.6f}, {upper_bound:.6f}]"
    )

    if tolerance is not None:
        print(f"Tolerance: ±{tolerance:.6f} s")
        assert abs(mean - expected_duration) < tolerance, (
            f"Mean duration {mean:.6f}s differs from expected {expected_duration:.6f}s "
            f"beyond allowed tolerance {tolerance:.6f}s"
        )

    # Optional: test if mean falls within jitter-aware interval
    assert lower_bound <= mean <= upper_bound, (
        f"{name} mean duration {mean:.6f}s falls outside jitter-aware range "
        f"[{lower_bound:.6f}, {upper_bound:.6f}]"
    )
