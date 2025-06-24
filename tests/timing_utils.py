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
import csv
from datetime import datetime
from pathlib import Path

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


def run_protocol_and_extract_all_events(tmp_path, i, config: ExperimentConfig):
    io = IOController()
    io.open_device()

    # Ensure filename is unique per run
    cfg = config.clone_with(filename=str(tmp_path / f"data/run_{i}.csv"))

    runner = ProtocolRunner(io, Recorder(io))
    result = runner.run_protocol(cfg, debug=False)
    assert "Protocol completed successfully" in result

    events = cfg.event_logger.get_events()
    io.cleanup()
    return events

def summarize_durations(durations, expected_duration, confidence=0.95):
    arr = np.array(durations)
    mean = arr.mean()
    std_dev = arr.std(ddof=1)
    sem = std_dev / np.sqrt(len(arr))
    ci = t.interval(confidence, len(arr) - 1, loc=mean, scale=sem)

    print(f"\nDurations: {durations}")
    print(f"Mean: {mean:.6f} s")
    print(f"Std Dev: {std_dev:.6f} s")
    print(f"{int(confidence*100)}% CI: {ci[0]:.6f} to {ci[1]:.6f} s")

    assert (
        abs(mean - expected_duration) < 0.01
    ), f"Mean duration {mean:.6f}s differs from expected {expected_duration:.6f}s"
    assert (
        ci[0] <= expected_duration <= ci[1]
    ), f"Expected duration {expected_duration:.6f}s not in CI: {ci}"


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
