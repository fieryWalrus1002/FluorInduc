from datetime import datetime
from pathlib import Path
from src.experiment_config import ExperimentConfig
from src.event_logger import EventLogger
from src.timed_action_factory import TimedActionFactory
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
from src.timed_action import TimedAction
from datetime import datetime

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def get_results_filename(prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    return TEST_RESULTS_DIR / f"{prefix}_{timestamp}.csv"

class CustomTimedActionFactory(TimedActionFactory):
    def get_test_actions(self, actinic_red_voltage: float, meas_green_voltage: float, logger: EventLogger = None) -> list[TimedAction]:
        """
        Get a list of all actions for production.
        """
        return [
            self.make_ared_on(voltage=actinic_red_voltage), #ared_on
            self.make_combined_ared_off_and_shutter_opened(logger=logger), #ared_on and shutter_opened
            self.make_agreen_on(voltage=meas_green_voltage), # agreen_on
            self.make_agreen_off(), # agreen_off
            self.end_recording(), # end_recording
        ]

    def create_full_protocol(
        self, red_voltage: float = 0.0, green_voltage: float = 0.0, logger: EventLogger = None
    ) -> list[TimedAction]:
        return self.get_test_actions(red_voltage, green_voltage, logger=logger)

# constants from measured data
MEASURED_SHUTTER_OPENING_DURATION = 0.00075  # seconds, time it takes to open the shutter
MEASURED_LED_ON_DURATION = 0.002588  # seconds, time it takes for the Agreen LED to turn

# constants for the protocol
ARED_DURATION = 1.0  # seconds
WAIT_AFTER_ARED = 0.0  # seconds
AGREEN_DELAY = 0.0  # seconds
AGREEN_DURATION = 2.0


# expected durations based on the constants
EXPECTED_SHUTTER_OPENING_DURATION = (
    WAIT_AFTER_ARED + AGREEN_DELAY + MEASURED_SHUTTER_OPENING_DURATION
)
WHOLE_PROTOCOL_DURATION = (
    ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION
)


# statistical parameters
N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95
EPSILON = 0.0005  # seconds, used to ensure actions are executed with minimal delay


# these are the interval names, the event labels we look for, the expected duration, and
# the tolerance it is allowed to deviate from the expected duration
interval_specs = [
    ("ared_duration", r"ared_on", r"ared_off", ARED_DURATION, 0.01),
    (
        "gap_between_ared_off_and_agreen_on",
        r"ared_off",
        r"agreen_on",
        EXPECTED_SHUTTER_OPENING_DURATION + AGREEN_DELAY + MEASURED_LED_ON_DURATION,
        0.001,
    ),
    (
        "shutter_open_duration",
        r"ared_off",
        r"shutter_opened",
        EXPECTED_SHUTTER_OPENING_DURATION,
        0.001,
    ),
]

# does this need to be a fixture?
delay_overrides = {
    "ared_off": -0.004,
    "wait_after_ared": 0.0,
    "shutter_opened": 0.0,
    "agreen_on": 0.0,
    "agreen_off": 0.0,
}

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

    io = IOController()

    custom_factory = CustomTimedActionFactory(
        io=io,
        cfg=config,
        stop_flag=None,  # the protocol_runner passes in the stop flag before calling create_full_protocol
        delay_overrides=delay_overrides
    )

    labels = ["ared_on", "ared_off", "agreen_on", "agreen_off", "shutter_opened"]

    durations_by_name = {name: [] for name, *_ in interval_specs}

    for i in range(N_REPEATS):
        events = run_protocol_and_extract_all_events(
            tmp_path=TEST_RESULTS_DIR, i=i, config=config, expected_labels=labels, delay_overrides=delay_overrides, factory=custom_factory, io=io
        )
        # this is throwing an error because it can't ind the event
        intervals = extract_intervals(
            events, [(name, start, end) for name, start, end, _, _ in interval_specs]
        )
        for name, duration in intervals.items():
            durations_by_name[name].append(duration)

    out_csv = get_results_filename("interval_durations")
    export_durations_csv(durations_by_name, out_csv)
    print(f"\nExported duration data to: {out_csv}")

    return durations_by_name


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

# ==== Interval: ared_duration ====
# Durations: [1.003607299993746, 1.0025574000319466, 1.0104857000987977, 1.0045013999333605, 1.0019921000348404, 1.0046015999978408, 1.0028933000285178, 1.0018098000437021, 1.002804199932143, 1.0037614000029862]
# Expected:  1.000000 s
# Mean:      1.003901 s
# Std Dev:   0.002502 s
# 95% CI: [1.002111, 1.005691]
# Tolerance: ±0.010000 s
# T-statistic: 4.930
# P-value:     0.0008 (alpha = 0.0500)
# FAILED

# ==== Interval: gap_between_ared_off_and_agreen_on ====
# Durations: [0.010941699962131679, 0.01067950006108731, 0.02159129991196096, 0.01001140009611845, 0.009034099988639355, 0.010631999932229519, 0.010235500056296587, 0.009109399979934096, 0.010876000043936074, 0.013742499984800816]
# Expected:  0.006000 s
# Mean:      0.011685 s
# Std Dev:   0.003716 s
# 95% CI: [0.009027, 0.014343]
# Tolerance: ±0.001000 s
# FAILED
