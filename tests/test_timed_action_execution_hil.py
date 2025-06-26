# tests/test_timed_action_execution_hil.py
import pytest
import time
import statistics
from src.io_controller import IOController
from src.experiment_config import ExperimentConfig
from src.timed_action_factory import TimedActionFactory
from src.event_logger import EventLogger
from src.constants import LED_RED_PIN, LED_GREEN_PIN

N_REPEATS = 60

@pytest.fixture(scope="module")
def io_controller():
    io = IOController()
    io.open_device()
    yield io
    io.cleanup()


def measure_execution(label, timed_action_factory, build_fn, logger=None, n_repeats=100):
    durations = []
    for _ in range(n_repeats):
        action = build_fn(timed_action_factory)
        start = time.perf_counter()
        action.execute(logger)
        end = time.perf_counter()
        durations.append(end - start)
    mean = statistics.mean(durations)
    stddev = statistics.stdev(durations)
    print(f"{label:30} n: {n_repeats} Mean: {mean:.6f} s, StdDev: {stddev:.6f} s")
    return durations


def measure_combined_execution(
    label, factory, build_fn1, build_fn2, logger=None, n_repeats=10
):
    """ I wanted to capture the timing of two actions executed in sequence,
    which is common in the protocol runner.
    """
    durations = []
    for _ in range(n_repeats):
        action1 = build_fn1(factory)
        action2 = build_fn2(factory)
        start = time.perf_counter()
        action1.execute(logger)
        action2.execute(logger)
        end = time.perf_counter()
        durations.append(end - start)
    mean = statistics.mean(durations)
    stddev = statistics.stdev(durations)

    print(f"{label:30} n: {n_repeats} Mean: {mean:.6f} s, StdDev: {stddev:.6f} s")
    return durations


@pytest.mark.hardware
def test_timed_action_execution(io_controller):
    print("Running TimedAction execution timing tests")

    cfg = ExperimentConfig(
        recording_hz=0,
        ared_duration_s=0,
        wait_after_ared_s=0,
        agreen_delay_s=0,
        agreen_duration_s=0,
    )
    factory = TimedActionFactory(io_controller, cfg)
    logger = EventLogger(begin="test_timed_action_execution")

    # Use basic actions that don't include intentional sleeps
    measure_execution("ared_on", factory, lambda f: f.make_ared_on(3.3), logger, n_repeats=N_REPEATS)
    measure_execution("ared_off", factory, lambda f: f.make_ared_off(), logger, n_repeats=N_REPEATS)
    measure_execution(
        "shutter_opened", factory, lambda f: f.make_shutter_opened(), logger, n_repeats=N_REPEATS
    )
    measure_execution("agreen_on", factory, lambda f: f.make_agreen_on(2.5), logger, n_repeats=N_REPEATS)
    measure_execution("agreen_off", factory, lambda f: f.make_agreen_off(), logger, n_repeats=N_REPEATS)

    # For wait_after_ared and combined actions, expect longer durations
    measure_execution(
        "wait_after_ared", factory, lambda f: f.make_wait_after_ared(), logger, n_repeats=N_REPEATS
    )
    measure_execution(
        "combined_ared_off_and_shutter_opened",
        factory,
        lambda f: f.make_combined_ared_off_and_shutter_opened(logger),
        logger,
        n_repeats=N_REPEATS
    )

    measure_execution(
        "combined_ared_off_and_agreen_on",
        factory,
        lambda f: f.make_combined_ared_off_and_agreen_on(2.5, logger),
        logger,
        n_repeats=N_REPEATS,
    )

    measure_combined_execution(
        "combined_ared_off_and_shutter_opened_followed_by_agreen_on",
        factory,
        lambda f: f.make_combined_ared_off_and_shutter_opened(logger),
        lambda f: f.make_agreen_on(2.5),
        logger,
        n_repeats=N_REPEATS
    )


"""
6-25-25
bare actions, no logging and 0 delays
tests\test_io_controller_hil.py DWF Version: b'3.23.4'
Opening first device
Running IO timing tests
toggle_shutter(True)           Mean: 0.000380 s, StdDev: 0.000022 s
toggle_shutter(False)          Mean: 0.000494 s, StdDev: 0.000169 s
set_led_voltage RED            Mean: 0.002140 s, StdDev: 0.000452 s
set_led_voltage GREEN          Mean: 0.002158 s, StdDev: 0.000281 s
.Closing device...
Device closed.

TimedAction execution with no delays
tests\test_timed_action_execution_hil.py DWF Version: b'3.23.4'
Opening first device
Running TimedAction execution timing tests
ared_on                        Mean: 0.002194 s, StdDev: 0.000093 s
ared_off                       Mean: 0.002524 s, StdDev: 0.000536 s
shutter_opened                 Mean: 0.000427 s, StdDev: 0.000010 s
agreen_on                      Mean: 0.002588 s, StdDev: 0.000898 s
agreen_off                     Mean: 0.002413 s, StdDev: 0.000465 s
wait_after_ared                Mean: 0.000005 s, StdDev: 0.000002 s
combined_ared_off_and_shutter_opened Mean: 0.002611 s, StdDev: 0.000264 s
.Closing device...
Device closed.

No change to the time taken by the ared_on, agreen_on, etc. Shutter opening is very fast, 
at ~0.0004 seconds, which is expected.
The wait_after_ared is very fast, at ~0.000005 seconds, which is expected since it is 
executed with 0.0 sleep and is essentially a no-op in this test setup.


6-26-25
Running TimedAction execution timing tests
ared_on                        n: 60 Mean: 0.002080 s, StdDev: 0.000358 s
ared_off                       n: 60 Mean: 0.002335 s, StdDev: 0.000583 s
shutter_opened                 n: 60 Mean: 0.000375 s, StdDev: 0.000011 s
agreen_on                      n: 60 Mean: 0.002487 s, StdDev: 0.001882 s
agreen_off                     n: 60 Mean: 0.002209 s, StdDev: 0.000776 s
wait_after_ared                n: 60 Mean: 0.000004 s, StdDev: 0.000002 s
combined_ared_off_and_shutter_opened n: 60 Mean: 0.002722 s, StdDev: 0.000674 s
combined_ared_off_and_agreen_on n: 60 Mean: 0.004832 s, StdDev: 0.000638 s
combined_ared_off_and_shutter_opened_followed_by_agreen_on n: 60 Mean: 0.006109 s, StdDev: 0.003597 s
"""
