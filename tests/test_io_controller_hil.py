# tests/test_io_controller_hil.py
import pytest
import time
import statistics
from src.io_controller import IOController
from src.constants import LED_RED_PIN, LED_GREEN_PIN

N_SAMPLES = 1000  # Number of samples to average over for timing

@pytest.fixture(scope="module")
def io_controller():
    """Fixture that opens and cleans up the IOController once per module."""
    io = IOController()
    io.open_device()
    yield io
    io.cleanup()


def measure_timing(label, func, *args, n_repeats=100):
    """Utility to time execution of a hardware command."""
    durations = []
    for _ in range(n_repeats):
        start = time.perf_counter()
        func(*args)
        end = time.perf_counter()
        durations.append(end - start)
    mean = statistics.mean(durations)
    stddev = statistics.stdev(durations)
    print(f"{label:30} Mean: {mean:.6f} s, StdDev: {stddev:.6f} s")
    return durations


@pytest.mark.hardware
def test_io_timing_suite(io_controller):
    """Hardware-in-the-loop test measuring IO timing."""
    print("Running IO timing tests")
    print(f"n= {N_SAMPLES}")
    results = {}
    results["toggle_shutter_on"] = measure_timing(
        "toggle_shutter(True)", io_controller.toggle_shutter, True, n_repeats=N_SAMPLES
    )
    results["toggle_shutter_off"] = measure_timing(
        "toggle_shutter(False)", io_controller.toggle_shutter, False, n_repeats=N_SAMPLES
    )
    results["set_led_voltage_red"] = measure_timing(
        "set_led_voltage RED", io_controller.set_led_voltage, LED_RED_PIN, 3.3, n_repeats=N_SAMPLES
    )
    results["set_led_voltage_green"] = measure_timing(
        "set_led_voltage GREEN", io_controller.set_led_voltage, LED_GREEN_PIN, 2.5, n_repeats=N_SAMPLES
    )

    # Optionally assert timing ranges or export to CSV here
    
    
    for label, times in results.items():
        assert all(t > 0 for t in times), f"{label} contains non-positive durations"

# tests\test_io_controller_hil.py DWF Version: b'3.23.4'
# Opening first device
# Running IO timing tests
# toggle_shutter(True)           Mean: 0.000380 s, StdDev: 0.000022 s
# toggle_shutter(False)          Mean: 0.000494 s, StdDev: 0.000169 s
# set_led_voltage RED            Mean: 0.002140 s, StdDev: 0.000452 s
# set_led_voltage GREEN          Mean: 0.002158 s, StdDev: 0.000281 s
# .Closing device...
# Device closed.

# 6-25-25
# tests\test_timed_action_execution_hil.py DWF Version: b'3.23.4'
# Opening first device
# Running TimedAction execution timing tests
# ared_on                        Mean: 0.002194 s, StdDev: 0.000093 s
# ared_off                       Mean: 0.002524 s, StdDev: 0.000536 s
# shutter_opened                 Mean: 0.000427 s, StdDev: 0.000010 s
# agreen_on                      Mean: 0.002588 s, StdDev: 0.000898 s
# agreen_off                     Mean: 0.002413 s, StdDev: 0.000465 s
# wait_after_ared                Mean: 0.000005 s, StdDev: 0.000002 s
# combined_ared_off_and_shutter_opened Mean: 0.002611 s, StdDev: 0.000264 s
# .Closing device...
# Device closed.

# 6-26-25
# Running IO timing tests
# n= 1000
# toggle_shutter(True)           Mean: 0.000421 s, StdDev: 0.000051 s
# toggle_shutter(False)          Mean: 0.000521 s, StdDev: 0.000074 s
# set_led_voltage RED            Mean: 0.002367 s, StdDev: 0.000294 s
# set_led_voltage GREEN          Mean: 0.002430 s, StdDev: 0.000413 s