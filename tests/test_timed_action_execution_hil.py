# tests/test_timed_action_execution_hil.py
import pytest
import time
import statistics
from src.io_controller import IOController
from src.experiment_config import ExperimentConfig
from src.timed_action_factory import TimedActionFactory
from src.event_logger import EventLogger
from src.constants import LED_RED_PIN, LED_GREEN_PIN


@pytest.fixture(scope="module")
def io_controller():
    io = IOController()
    io.open_device()
    yield io
    io.cleanup()


def measure_execution(label, timed_action_factory, build_fn, logger=None, n_repeats=10):
    durations = []
    for _ in range(n_repeats):
        action = build_fn(timed_action_factory)
        start = time.perf_counter()
        action.execute(logger)
        end = time.perf_counter()
        durations.append(end - start)
    mean = statistics.mean(durations)
    stddev = statistics.stdev(durations)
    print(f"{label:30} Mean: {mean:.6f} s, StdDev: {stddev:.6f} s")
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
    measure_execution("ared_on", factory, lambda f: f.make_ared_on(3.3), logger)
    measure_execution("ared_off", factory, lambda f: f.make_ared_off(), logger)
    measure_execution(
        "shutter_opened", factory, lambda f: f.make_shutter_opened(), logger
    )
    measure_execution("agreen_on", factory, lambda f: f.make_agreen_on(2.5), logger)
    measure_execution("agreen_off", factory, lambda f: f.make_agreen_off(), logger)

    # For wait_after_ared and combined actions, expect longer durations
    measure_execution(
        "wait_after_ared", factory, lambda f: f.make_wait_after_ared(), logger
    )
    measure_execution(
        "combined_ared_off_and_shutter_opened",
        factory,
        lambda f: f.make_combined_ared_off_and_shutter_opened(logger),
        logger,
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
"""