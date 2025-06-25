# At the top of the file
from datetime import datetime
from pathlib import Path
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
import pytest
from src.constants import LED_RED_PIN, LED_GREEN_PIN
from tests.timing_utils import (
    run_protocol_and_extract_all_events,
    extract_intervals,
    summarize_durations,
    export_durations_csv,
    suggest_delay_corrections,
)
from pathlib import Path
from src.timed_action_factory import TimedActionFactory
from src.timed_action import TimedAction
from datetime import datetime

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def get_results_filename(prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    return TEST_RESULTS_DIR / f"{prefix}_{timestamp}.csv"

N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95

EPSILON = 0.0005  # seconds, used to ensure actions are executed with minimal delay

ARED_DURATION = 1.0  # seconds
WAIT_AFTER_ARED = 0.002  # seconds
AGREEN_DELAY = 0.002  # seconds
AGREEN_DURATION = 2.0
WHOLE_PROTOCOL_DURATION = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION

interval_specs = [
    # (
    #     "ared_duration", 
    #     r"ared_on", 
    #     r"ared_off", 
    #     ARED_DURATION, 
    #     0.01
    # ),
    (
        "wait_after_ared",
        r"ared_off",
        r"agreen_on",
        WAIT_AFTER_ARED + AGREEN_DELAY,
        0.002,
    ),
    # (
    #     "agreen_duration", 
    #     r"agreen_on", 
    #     r"agreen_off", 
    #     AGREEN_DURATION, 
    #     0.05
    # ),
    # (
    #     "whole_protocol_duration",
    #     r"ared_on",
    #     r"agreen_off",
    #     WHOLE_PROTOCOL_DURATION,
    #     0.05,
    # ),
]

@pytest.fixture(scope="module")
def collected_durations():
    config = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_hz=1000,
        ared_duration_s=ARED_DURATION,
        wait_after_ared_s=WAIT_AFTER_ARED,
        agreen_delay_s=AGREEN_DELAY,
        agreen_duration_s=AGREEN_DURATION,
        filename="",  # overridden per run
        action_epsilon_s=EPSILON,
    )

    durations_by_name = {name: [] for name, *_ in interval_specs}

    for i in range(N_REPEATS):
        events = run_protocol_and_extract_all_events(TEST_RESULTS_DIR, i, config, delay_overrides)
        intervals = extract_intervals(
            events, [(name, start, end) for name, start, end, _, _ in interval_specs]
        )
        for name, duration in intervals.items():
            durations_by_name[name].append(duration)

    out_csv = get_results_filename("interval_durations")
    export_durations_csv(durations_by_name, out_csv)
    print(f"\nExported duration data to: {out_csv}")

    return durations_by_name


delay_overrides = {
    "ared_off": 0.0,
    "wait_after_ared": 0.0,
    "shutter_opened": 0.0,
    "agreen_on": 0.0,
    "agreen_off": 0.0,
}

@pytest.mark.hardware
@pytest.mark.parametrize("name, start, end, expected, tolerance", interval_specs)
def test_duration_intervals_within_expected_range(
    name, start, end, expected, tolerance, collected_durations
):
    durations_by_name = collected_durations[name]
    print(f"\n==== Interval: {name} ====")
    summarize_durations(
        durations_by_name, expected, confidence=CONFIDENCE_LEVEL, tolerance=tolerance
    )


# ared_off             @ raw=2.065740, delta=1.009678 s
# wait_after_ared      @ raw=2.073336, delta=1.017274 s
# shutter_opened       @ raw=2.073809, delta=1.017747 s
# agreen_on            @ raw=2.082645, delta=1.026583 s
# This period between ared_off and agreen_on should be much shorter, say 0.004s
# ==== Interval: wait_after_ared ====

# Durations: [0.021799599984660745, 0.01618779997806996, 0.02986879996024072, 0.02898740000091493, 0.02649109996855259, 0.03391990007366985, 0.013872899929992855, 0.017730000079609454, 0.020104499999433756, 0.016904699965380132]        
# Expected:  0.004000 s
# Mean:      0.022587 s
# Std Dev:   0.006809 s
# 95% CI: [0.017716, 0.027457]
# Tolerance: ±0.002000 s