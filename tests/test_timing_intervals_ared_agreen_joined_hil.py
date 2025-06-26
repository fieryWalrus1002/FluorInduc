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
N_REPEATS = 25
CONFIDENCE_LEVEL = 0.95
EPSILON = 0.001  # seconds, allows actions to occur slightly before  their scheduled time


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
# ared_on              @ raw=1.022913, delta=0.000000 s
# ared_off             @ raw=1.521635, delta=0.498721 s
# shutter_opened       @ raw=1.522421, delta=0.499508 s
# agreen_on            @ raw=1.525120, delta=0.502207 s
# agreen_off           @ raw=2.028538, delta=1.005624 s
# ------------------------------------------------------------


# Exported duration data to: D:\repos\FluorInduc\tests\test_results\interval_durations_2025-06-26-13-22.csv  


# ==== Interval: ared_duration ====

# Durations: [0.5002799000358209, 0.49873350001871586, 0.501222399994731, 0.5008664999622852, 0.502912399941124, 0.499127299990505, 0.500700999982655, 0.49818749993573874, 0.4990339999785647, 0.4971207999624312, 0.49965670006349683, 0.4984285000246018, 0.4986891000298783, 0.504156699986197, 0.49814769998192787, 0.49965559993870556, 0.4994562999345362, 0.4985894999699667, 0.4988696000073105, 0.49875640007667243, 0.49895669997204095, 0.5005400999216363, 0.49834260006900877, 0.5009068000363186, 0.49872110004071146]
# Expected:  0.500000 s
# Mean:      0.499602 s
# Std Dev:   0.001569 s
# 95% CI: [0.498955, 0.500250]
# Jitter-aware expected range (±2.064σ): [0.497998, 0.502002]
# PASSED
# tests/test_timing_intervals_ared_agreen_joined_hil.py::test_duration_intervals_within_expected_range[spec1]


# ==== Interval: shutter_open_duration ====

# Durations: [0.0007001999765634537, 0.0007414999417960644, 0.0005302999634295702, 0.0005305999657139182, 0.0016553000314161181, 0.0006682000821456313, 0.000619000056758523, 0.0006030000513419509, 0.0005989000201225281, 0.0004151000175625086, 0.0006373999640345573, 0.00039519998244941235, 0.0005194999976083636, 0.0017062999540939927, 0.0005511000053957105, 0.0011529000476002693, 0.0005535000236704946, 0.00043080002069473267, 0.000633800053037703, 0.0004838999593630433, 0.0004390000831335783, 0.0013984000543132424, 0.00039219995960593224, 0.0007275999523699284, 0.0007867999374866486]
# Expected:  0.000753 s
# Mean:      0.000715 s
# Std Dev:   0.000368 s
# 95% CI: [0.000563, 0.000867]
# Jitter-aware expected range (±2.064σ): [0.000499, 0.001007]
# PASSED
# tests/test_timing_intervals_ared_agreen_joined_hil.py::test_duration_intervals_within_expected_range[spec2]


# ==== Interval: gap_between_shutter_opened_and_agreen_on ====

# Durations: [0.0025360999861732125, 0.003003000048920512, 0.0030510000651702285, 0.00218990002758801, 0.005022799945436418, 0.0027264999225735664, 0.003877399954944849, 0.0018869000487029552, 0.002275099977850914, 0.002683900063857436, 0.003008199972100556, 0.0019348000641912222, 0.0022993000457063317, 0.005400100024417043, 0.0018841000273823738, 0.002652999944984913, 0.007961700088344514, 0.0019789000507444143, 0.00213489995803684, 0.0023641999578103423, 0.0020459999796003103, 0.005100299953483045, 0.002081400016322732, 0.0025900000473484397, 0.0026990000624209642]
# Expected:  0.002412 s
# Mean:      0.003016 s
# Std Dev:   0.001438 s
# 95% CI: [0.002422, 0.003609]
# Jitter-aware expected range (±2.064σ): [0.001223, 0.003601]
# PASSED
# tests/test_timing_intervals_ared_agreen_joined_hil.py::test_duration_intervals_within_expected_range[spec3]


# ==== Interval: gap_between_ared_off_and_agreen_on ====

# Durations: [0.003236299962736666, 0.0037444999907165766, 0.0035813000285997987, 0.002720499993301928, 0.006678099976852536, 0.0033947000047191978, 0.004496400011703372, 0.002489900100044906, 0.002873999997973442, 0.0030990000814199448, 0.0036455999361351132, 0.0023300000466406345, 0.0028188000433146954, 0.0071063999785110354, 0.0024352000327780843, 0.003805899992585182, 0.008515200112015009, 0.002409700071439147, 0.002768700011074543, 0.0028480999171733856, 0.0024850000627338886, 0.0064987000077962875, 0.002473599975928664, 0.003317599999718368, 0.003485799999907613]
# Expected:  0.004896 s
# Mean:      0.003730 s
# Std Dev:   0.001666 s
# 95% CI: [0.003043, 0.004418]
# Jitter-aware expected range (±2.064σ): [0.003542, 0.006250]
# PASSED
# tests/test_timing_intervals_ared_agreen_joined_hil.py::test_duration_intervals_within_expected_range[spec4]


# ==== Interval: agreen_duration ====

# Durations: [0.4979107000399381, 0.4994883999461308, 0.4934616999235004, 0.5005488999886438, 0.48937610001303256, 0.4983959000092, 0.4923184000654146, 0.498326399945654, 0.4962742000352591, 0.498318099998869, 0.49485070002265275, 0.5021945999469608, 0.4969664999516681, 0.4882735999999568, 0.4996273999568075, 0.4942400000290945, 0.4907608999637887, 0.4981381999095902, 0.4982313000364229, 0.497162300045602, 0.49702579993754625, 0.4938960999716073, 0.49702370003797114, 0.49426529998891056, 0.5034171999432147]
# Expected:  0.500000 s
# Mean:      0.496420 s
# Std Dev:   0.003720 s
# 95% CI: [0.494884, 0.497955]
# Jitter-aware expected range (±2.064σ): [0.492776, 0.507224]
# PASSED
# tests/test_timing_intervals_ared_agreen_joined_hil.py::test_duration_intervals_within_expected_range[spec5]


# ==== Interval: whole_protocol_duration ====

# Durations: [1.0014269000384957, 1.0019663999555632, 0.9982653999468312, 1.004135899944231, 0.9989665999310091, 1.0009179000044242, 0.997515800059773, 0.9990037999814376, 0.9981822000117972, 0.9985379000427201, 0.9981530000222847, 1.0029531000182033, 0.9984744000248611, 0.9995366999646649, 1.0002102999715135, 0.9977014999603853, 0.9987324000103399, 0.999137399950996, 0.999869600054808, 0.9987668000394478, 0.9984674999723211, 1.00093489990104, 0.9978399000829086, 0.9984897000249475, 1.0056240999838337]
# Expected:  1.007194 s
# Mean:      0.999752 s
# Std Dev:   0.002089 s
# 95% CI: [0.998890, 1.000615]
# Jitter-aware expected range (±2.064σ): [0.999432, 1.014956]
# PASSED

# ====================================== 6 passed in 62.85s (0:01:02) ======================================