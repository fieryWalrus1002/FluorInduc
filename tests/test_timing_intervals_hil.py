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
    summarize_durations_with_jitter_awareness,
    IntervalSpec,
    MeasuredDuration
)
from pathlib import Path
from src.timed_action import TimedAction
from datetime import datetime
from math import sqrt
from dataclasses import dataclass
from scipy.stats import t

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# statistical parameters
N_REPEATS = 10
CONFIDENCE_LEVEL = 0.95
EPSILON = 0.0  # seconds, allows actions to occur slightly before  their scheduled time


def get_results_filename(prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    return TEST_RESULTS_DIR / f"{prefix}_{timestamp}.csv"


class CustomTimedActionFactory(TimedActionFactory):
    def get_test_actions(
        self,
        actinic_red_voltage: float,
        meas_green_voltage: float,
        logger: EventLogger = None,
    ) -> list[TimedAction]:
        """
        Get a list of all actions for production.
        """
        return [
            self.make_ared_on(voltage=actinic_red_voltage),  # ared_on
            self.make_combined_ared_off_and_shutter_opened(
                logger=logger
            ),  # ared_on and shutter_opened
            self.make_agreen_on(voltage=meas_green_voltage),  # agreen_on
            self.make_agreen_off(),  # agreen_off
            self.end_recording(),  # end_recording
        ]

    def create_full_protocol(
        self,
        red_voltage: float = 0.0,
        green_voltage: float = 0.0,
        logger: EventLogger = None,
    ) -> list[TimedAction]:
        return self.get_test_actions(red_voltage, green_voltage, logger=logger)

class CombinedAredOffAndAgreenOnFactory(TimedActionFactory):
    def get_test_actions(
        self,
        actinic_red_voltage: float,
        meas_green_voltage: float,
        logger: EventLogger = None,
    ) -> list[TimedAction]: 
        """
        Get a list of all actions for production.
        """
        return [
            self.make_ared_on(voltage=actinic_red_voltage),  # ared_on
            self.make_combined_ared_off_and_agreen_on(
                meas_green_voltage=meas_green_voltage,  # ared_off and agreen_on
                logger=logger
            ),  # ared_off and agreen_on
            self.make_agreen_off(),  # agreen_off
            self.end_recording(),  # end_recording
        ]

    def create_full_protocol(
        self,
        red_voltage: float = 0.0,
        green_voltage: float = 0.0,
        logger: EventLogger = None,
    ) -> list[TimedAction]:
        return self.get_test_actions(red_voltage, green_voltage, logger=logger)


def calculate_combined_stddevs(*stddevs):
    """
    Calculate the combined standard deviation from multiple sources of jitter.
    Uses the formula for combining independent standard deviations:
    sqrt(σ1² + σ2² + ... + σn²)
    """
    return sqrt(sum(sd ** 2 for sd in stddevs))

# constants for the protocol
ARED_DURATION = 0.5  # seconds
WAIT_AFTER_ARED = 0.0  # seconds
AGREEN_DELAY = 0.0  # seconds
AGREEN_DURATION = 0.5  # seconds

# 6-26-25
# tests/test_timed_action_execution_hil.py::test_timed_action_execution DWF Version: b'3.23.4'
# Opening first device
# Running TimedAction execution timing tests
# ared_on                        n: 60 Mean: 0.002080 s, StdDev: 0.000358 s
# ared_off                       n: 60 Mean: 0.002335 s, StdDev: 0.000583 s
# shutter_opened                 n: 60 Mean: 0.000375 s, StdDev: 0.000011 s
# agreen_on                      n: 60 Mean: 0.002487 s, StdDev: 0.001882 s
# agreen_off                     n: 60 Mean: 0.002209 s, StdDev: 0.000776 s
# wait_after_ared                n: 60 Mean: 0.000004 s, StdDev: 0.000002 s
# combined_ared_off_and_shutter_opened n: 60 Mean: 0.002722 s, StdDev: 0.000674 s
# combined_ared_off_and_agreen_on n: 60 Mean: 0.004832 s, StdDev: 0.000638 s
# combined_ared_off_and_shutter_opened_followed_by_agreen_on n: 60 Mean: 0.006109 s, StdDev: 0.003597 s
MEAS_ARED_ON_EX = MeasuredDuration(
    label="ared_on",
    duration=0.002391,  # seconds
    stddev=0.000774,  # seconds
    n_repeats=30,  # number of measurements taken
)
print(f"Expected:\n{MEAS_ARED_ON_EX}")

MEAS_ARED_OFF_UNTIL_SHUTTER_OPENING_EX = MeasuredDuration(
    label="ared_off_until_shutter_opening",
    duration=0.0007533,  # seconds
    stddev=0.000123,  # seconds
    n_repeats=30,  # number of measurements taken
)
print(f"Expected:\n{MEAS_ARED_OFF_UNTIL_SHUTTER_OPENING_EX}")

# ==== Interval: shutter_open_duration ====
# Durations: [0.0014690000098198652, 0.0007356000132858753, 0.0004913999000564218, 0.0009538999292999506, 0.0010258000111207366, 0.001660300069488585, 0.0005403999239206314, 0.0006997999735176563, 0.0004881999921053648, 0.0006026000482961535]
# Expected:  0.000753 s
# Mean:      0.000867 s
# Std Dev:   0.000412 s
# 95% CI: [0.000572, 0.001162]
# Jitter-aware expected range (±2.262σ): [0.000475, 0.001032]
# PASSED
# Note: This is so messy here because this is included multiple loops of the record loop, until the trigger time is caught.
# This time could be reduced by including the agreen delay into the combined_ared_off_and_shutter_opened action, as it
# would benefit from the more precise timing logic.
MEAS_SHUTTER_OPEN_UNTIL_AGREEN_ON_EX = MeasuredDuration(
    label="shutter_opened_until_agreen_on",
    duration=0.002412,  # seconds
    stddev=0.000576,  # seconds
    n_repeats=30,  # number of measurements taken
)
print(f"Expected:\n{MEAS_SHUTTER_OPEN_UNTIL_AGREEN_ON_EX}")

MEAS_ARED_OFF_UNTIL_AGREEN_ON_EX = MeasuredDuration(
    label="ared_off_until_agreen_on",
    duration=0.004896,  # seconds, expected duration
    stddev=0.000656,  # seconds, measured jitter
    n_repeats=30,  # number of measurements taken
)
print(f"Expected:\n{MEAS_ARED_OFF_UNTIL_AGREEN_ON_EX}")

MEAS_AGREEN_ON_EX = MeasuredDuration(
    label="agreen_on",
    duration=0.002113,  # seconds
    stddev=0.000421,  # seconds
    n_repeats=30  # number of measurements taken
)
print(f"Expected:\n{MEAS_AGREEN_ON_EX}")

MEAS_AGREEN_OFF_EX = MeasuredDuration(
    label="agreen_off",
    duration=0.002298,  # seconds
    stddev=0.000723,  # seconds
    n_repeats=30  # number of measurements taken
)
print(f"Expected:\n{MEAS_ARED_ON_EX}")

########## Longer durations, with waits included ##########
# ==== Interval: ared_duration ====
# Expected:  0.500000 s
# Mean:      0.499564 s
# Std Dev:   0.000968 s
MEAS_ARED_ON_DURATION = MeasuredDuration(
    label="ared_on_duration",
    duration=ARED_DURATION,  # seconds, currently placeholder
    stddev=0.00097,
    n_repeats=N_REPEATS  # number of measurements taken
)
print(f"Expected:\n{MEAS_ARED_ON_DURATION}")

# ==== Interval: agreen_duration ====
# Expected:  0.500000 s
# Mean:      0.499172 s
# Std Dev:   0.003510 s
# 95% CI: [0.496662, 0.501683]
MEAS_AGREEN_DURATION = MeasuredDuration(
    label="agreen_duration",
    duration=AGREEN_DURATION,  # seconds
    stddev=0.0035,
    n_repeats=N_REPEATS  # number of measurements taken
)
print(f"Expected:\n{MEAS_AGREEN_DURATION}")

# ==== Interval: whole_protocol_duration ====
# Expected:  1.0 s
# Mean:      1.001722 s
# Std Dev:   0.003140 s
# figure out our end recording duration
WHOLE_PROTOCOL_DURATION_EX = (
    MEAS_ARED_ON_DURATION
    + MEAS_ARED_OFF_UNTIL_AGREEN_ON_EX
    + MEAS_AGREEN_DURATION
    + MEAS_AGREEN_OFF_EX
)
print(f"Expected:\n{WHOLE_PROTOCOL_DURATION_EX}")


# available label markers in the protocol:
# ared_on              @ raw=1.015273, delta=0.000000 s
# ared_off             @ raw=1.513851, delta=0.498578 s
# shutter_opened       @ raw=1.514422, delta=0.499149 s
# agreen_on            @ raw=1.516647, delta=0.501373 s
# agreen_off           @ raw=2.019105, delta=1.003832 s
interval_specs = [
    IntervalSpec(
        name="ared_duration",
        start_label="ared_on",
        end_label="ared_off",
        measured=MEAS_ARED_ON_DURATION,
    ),
    IntervalSpec(
        name="shutter_open_duration",
        start_label=r"ared_off",  # we don't have a marker for when the ared_off is started, just completed
        end_label=r"shutter_opened",
        measured=MEAS_ARED_OFF_UNTIL_SHUTTER_OPENING_EX,
    ),
    IntervalSpec(
        name="gap_between_shutter_opened_and_agreen_on",
        start_label=r"shutter_opened",
        end_label=r"agreen_on",
        measured=MEAS_SHUTTER_OPEN_UNTIL_AGREEN_ON_EX,
    ),
    IntervalSpec(
        name="gap_between_ared_off_and_agreen_on",
        start_label=r"ared_off",
        end_label=r"agreen_on",
        measured=MEAS_ARED_OFF_UNTIL_AGREEN_ON_EX,
    ),
    IntervalSpec(
        name="agreen_duration",
        start_label=r"agreen_on",
        end_label=r"agreen_off",
        measured=MEAS_AGREEN_DURATION,
    ),
    IntervalSpec(
        name="whole_protocol_duration",
        start_label=r"ared_on",
        end_label=r"agreen_off",
        measured=WHOLE_PROTOCOL_DURATION_EX,
    ),
]

# does this need to be a fixture?
delay_overrides = {
    "ared_off": -0.004, # adjusts to bring the ARED off action closer to the expected duration
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

    # durations_by_name = {name: [] for name, *_ in interval_specs}
    durations_by_name = {spec.name: [] for spec in interval_specs}

    for i in range(N_REPEATS):
        events = run_protocol_and_extract_all_events(
            tmp_path=TEST_RESULTS_DIR, i=i, config=config, expected_labels=labels, delay_overrides=delay_overrides, factory=custom_factory, io=io
        )
        intervals = extract_intervals(
            events,
            [(spec.name, spec.start_label, spec.end_label) for spec in interval_specs],
        )

        for name, duration in intervals.items():
            durations_by_name[name].append(duration)

    out_csv = get_results_filename("interval_durations")
    export_durations_csv(durations_by_name, out_csv)
    print(f"\nExported duration data to: {out_csv}")

    return durations_by_name


@pytest.mark.hardware
@pytest.mark.parametrize("spec", interval_specs)
def test_duration_intervals_within_expected_range(
    spec: IntervalSpec, collected_durations
):
    durations = collected_durations[spec.name]
    print(f"\n\n==== Interval: {spec.name} ====")

    summarize_durations_with_jitter_awareness(
        name=spec.name,
        durations=durations,
        expected_duration=spec.measured.duration,
        component_stddev=spec.measured.stddev,
        confidence=CONFIDENCE_LEVEL,
        tolerance=spec.tolerance,
    )

# --- Recorded Event Times (relative to t_zero = ared_on) ---
# ared_on              @ raw=1.017703, delta=0.000000 s
# ared_off             @ raw=1.516518, delta=0.498815 s
# shutter_opened       @ raw=1.517120, delta=0.499418 s
# agreen_on           @ raw=1.519313, delta=0.501611 s
# agreen_off           @ raw=2.016565, delta=0.998862 s
# ------------------------------------------------------------


# Exported duration data to: D:\repos\FluorInduc\tests\test_results\interval_durations_2025-06-26-12-52.csv


# ==== Interval: ared_duration ====
# Durations: [0.5013505999231711, 0.5002113999798894, 0.4991857000859454, 0.4991856999695301, 0.5003810999915004, 0.5037851999513805, 0.49955549999140203, 0.5004291000077501, 0.49896500003524125, 0.49881499994080514]
# Expected:  0.500000 s
# Mean:      0.500186 s
# Std Dev:   0.001497 s
# 95% CI: [0.499115, 0.501258]
# Jitter-aware expected range (±2.262σ): [0.497806, 0.502194]
# PASSED
# tests/test_timing_intervals_hil.py::test_duration_intervals_within_expected_range[spec1]

# ==== Interval: shutter_open_duration ====
# Durations: [0.0014690000098198652, 0.0007356000132858753, 0.0004913999000564218, 0.0009538999292999506, 0.0010258000111207366, 0.001660300069488585, 0.0005403999239206314, 0.0006997999735176563, 0.0004881999921053648, 0.0006026000482961535]
# Expected:  0.000753 s
# Mean:      0.000867 s
# Std Dev:   0.000412 s
# 95% CI: [0.000572, 0.001162]
# Jitter-aware expected range (±2.262σ): [0.000475, 0.001032]
# PASSED
# tests/test_timing_intervals_hil.py::test_duration_intervals_within_expected_range[spec2]

# ==== Interval: gap_between_shutter_opened_and_agreen_on ====

# Durations: [0.0041059000650420785, 0.002629099995829165, 0.002172500011511147, 0.0028418999863788486, 0.0025553000159561634, 0.005395899992436171, 0.002521499991416931, 0.0020852000452578068, 0.001988500007428229, 0.002193200052715838]
# Expected:  0.002412 s
# Mean:      0.002849 s
# Std Dev:   0.001081 s
# 95% CI: [0.002075, 0.003622]
# Jitter-aware expected range (±2.262σ): [0.001109, 0.003715]
# PASSED
# tests/test_timing_intervals_hil.py::test_duration_intervals_within_expected_range[spec3]

# ==== Interval: gap_between_ared_off_and_agreen_on ====

# Durations: [0.005574900074861944, 0.0033647000091150403, 0.0026638999115675688, 0.003795799915678799, 0.0035811000270769, 0.007056200061924756, 0.0030618999153375626, 0.002785000018775463, 0.0024766999995335937, 0.0027958001010119915]
# Expected:  0.004896 s
# Mean:      0.003716 s
# Std Dev:   0.001474 s
# 95% CI: [0.002661, 0.004770]
# Jitter-aware expected range (±2.262σ): [0.003412, 0.006380]
# PASSED
# tests/test_timing_intervals_hil.py::test_duration_intervals_within_expected_range[spec4]

# ==== Interval: agreen_duration ====

# Durations: [0.4933483999921009, 0.4954962000483647, 0.49953920010011643, 0.49727350007742643, 0.49518149998039007, 0.495604999945499, 0.49689449998550117, 0.4957533000269905, 0.49825459998100996, 0.49725139990914613]
# Expected:  0.500000 s
# Mean:      0.496460 s
# Std Dev:   0.001753 s
# 95% CI: [0.495206, 0.497714]
# Jitter-aware expected range (±2.262σ): [0.492082, 0.507918]
# PASSED
# tests/test_timing_intervals_hil.py::test_duration_intervals_within_expected_range[spec5]

# ==== Interval: whole_protocol_duration ====

# Durations: [1.000273899990134, 0.9990723000373691, 1.0013888000976294, 1.0002549999626353, 0.9991436999989673, 1.0064463999588042, 0.9995118998922408, 0.998967400053516, 0.9996963000157848, 0.9988621999509633]
# Expected:  1.007194 s
# Mean:      1.000362 s
# Std Dev:   0.002276 s
# 95% CI: [0.998734, 1.001990]
# Jitter-aware expected range (±2.262σ): [0.998686, 1.015702]
# PASSED

# ================================================= 6 passed in 25.88s ==================================================

# (.venv) D:\repos\FluorInduc>
