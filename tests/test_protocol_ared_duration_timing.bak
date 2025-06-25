import os
import re
import pytest
import numpy as np
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
from scipy.stats import t

# Settings
N_REPEATS = 3
EXPECTED_DURATION_S = 1.0
CONFIDENCE_LEVEL = 0.95
MAX_ALLOWED_DEVIATION_S = 0.01  # 10ms max jitter tolerance


def get_event_time_by_pattern(events, pattern: str):
    compiled = re.compile(pattern)
    for time_point, label in events:
        if compiled.search(label):
            return time_point
    raise AssertionError(f"No event label matched the pattern: '{pattern}'")


# def get_relative_event_times(
#     events, reference_label="action_ared_on_executed_at_0.000_s"
# ):
#     reference_time = None
#     for time_point, label in events:
#         if label == reference_label:
#             reference_time = time_point
#             break
#     if reference_time is None:
#         raise AssertionError(f"Reference event '{reference_label}' not found")
#     return [(time_point - reference_time, label) for time_point, label in events]


@pytest.mark.hardware
def test_timing_statistics_for_ared_off(tmp_path):
    io = IOController()

    durations = []

    for i in range(N_REPEATS):
        io = IOController()
        io.open_device()
        print(f"Running protocol iteration {i + 1}/{N_REPEATS}...")
        filename = tmp_path / f"run_{i}_output.csv"
        cfg = ExperimentConfig(
            actinic_led_intensity=75,
            measurement_led_intensity=30,
            recording_hz=1000,
            ared_duration_s=EXPECTED_DURATION_S,
            wait_after_ared_s=0.002,
            agreen_delay_s=0.002,
            agreen_duration_s=1.998, # agreen_delay_s + agreen_duration_s should be 2.0s total
            filename=str(filename),
        )

        runner = ProtocolRunner(io, Recorder(io))
        result = runner.run_protocol(cfg, debug=False)
        assert "Protocol completed successfully" in result

        events = cfg.event_logger.get_events()
        print("Logged events:")
        print("Time (s) - Event Label")
        for time_point, label in events:
            print(f"{time_point:.3f} - {label}")


        action_ared_on = get_event_time_by_pattern(events, r"action_ared_on")
        action_ared_off = get_event_time_by_pattern(
            events, r"action_ared_off_executed_at_"
        )

        duration = action_ared_off - action_ared_on
        durations.append(duration)

        io.cleanup()

    io.cleanup()

    # Analyze results
    durations_np = np.array(durations)
    mean_dur = durations_np.mean()
    std_dev = durations_np.std(ddof=1)
    conf_interval = t.interval(
        CONFIDENCE_LEVEL,
        len(durations_np) - 1,
        loc=mean_dur,
        scale=std_dev / np.sqrt(len(durations_np)),
    )

    print(f"\nResults from {N_REPEATS} protocol runs:")
    print(f"Mean duration: {mean_dur:.6f} s")
    print(f"Std Dev: {std_dev:.6f} s")
    print(
        f"{int(CONFIDENCE_LEVEL*100)}% Confidence Interval: {conf_interval[0]:.6f} to {conf_interval[1]:.6f} s"
    )

    # Final assertion: ensure the confidence interval is centered around the expected duration
    assert (
        abs(mean_dur - EXPECTED_DURATION_S) < MAX_ALLOWED_DEVIATION_S
    ), f"Mean Ared duration deviated too much: expected {EXPECTED_DURATION_S:.3f}s, got {mean_dur:.3f}s"
