# At the top of the file
from datetime import datetime
from pathlib import Path
from src.experiment_config import ExperimentConfig
import pytest
from tests.timing_utils import (
    run_protocol_and_extract_all_events,
    extract_intervals,
    summarize_durations,
    export_durations_csv,
)
from pathlib import Path
from datetime import datetime

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def get_results_filename(prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    return TEST_RESULTS_DIR / f"{prefix}_{timestamp}.csv"


N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95

interval_specs = [
    ("ared_duration", 
        r"ared_on", 
        r"ared_off", 
        1.0),
    (
        "delay_after_ared",
        r"ared_off",
        r"agreen_on",
        0.004,
    ),
    (
        "agreen_duration",
        r"agreen_on",
        r"agreen_off",
        1.2,
    ),
]

expected_durations = {name: expected for name, _, _, expected in interval_specs}


@pytest.fixture(scope="module")
def collected_durations():
    config = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_hz=1000,
        ared_duration_s=expected_durations["ared_duration"],
        wait_after_ared_s=0.002,
        agreen_delay_s=0.002,
        agreen_duration_s=expected_durations["agreen_duration"],
        filename="",  # overridden per run
    )

    durations_by_name = {name: [] for name, *_ in interval_specs}

    for i in range(N_REPEATS):
        # Just use TEST_RESULTS_DIR (not a subdir)
        events = run_protocol_and_extract_all_events(TEST_RESULTS_DIR, i, config)
        intervals = extract_intervals(
            events, [(name, start, end) for name, start, end, _ in interval_specs]
        )
        for name, duration in intervals.items():
            durations_by_name[name].append(duration)

    # Save combined output to timestamped CSV
    out_csv = get_results_filename("interval_durations")
    export_durations_csv(durations_by_name, out_csv)
    print(f"\nExported duration data to: {out_csv}")

    return durations_by_name


@pytest.mark.parametrize("name,start,end,expected", interval_specs)
def test_duration_intervals_within_expected_range(
    name, start, end, expected, collected_durations
):
    durations = collected_durations[name]
    print(f"\n==== Interval: {name} ====")
    summarize_durations(durations, expected, confidence=CONFIDENCE_LEVEL)


# @pytest.mark.hardware
# def test_multiple_intervals_combined(collected_durations):
#     for name, durations in collected_durations.items():
#         print(f"\n==== Interval: {name} ====")
#         summarize_durations(
#             durations, expected_durations[name], confidence=CONFIDENCE_LEVEL
#         )
