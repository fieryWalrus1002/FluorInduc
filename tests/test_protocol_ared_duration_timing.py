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
N_REPEATS = 10
EXPECTED_DURATION_S = 1.0
CONFIDENCE_LEVEL = 0.95
MAX_ALLOWED_DEVIATION_S = 0.01  # 10ms max jitter tolerance


def get_event_time_by_pattern(events, pattern: str):
    compiled = re.compile(pattern)
    for time_point, label in events:
        if compiled.search(label):
            return time_point
    raise AssertionError(f"No event label matched the pattern: '{pattern}'")


def get_relative_event_times(events, reference_label="ared_on"):
    reference_time = None
    for time_point, label in events:
        if label == reference_label:
            reference_time = time_point
            break
    if reference_time is None:
        raise AssertionError(f"Reference event '{reference_label}' not found")
    return [(time_point - reference_time, label) for time_point, label in events]


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
            recording_length_s=2.0,
            recording_hz=1000,
            ared_duration_s=EXPECTED_DURATION_S,
            wait_after_ared_s=0.002,
            agreen_delay_s=0.002,
            agreen_duration_s=1.9,
            filename=str(filename),
        )

        runner = ProtocolRunner(io, Recorder(io))
        result = runner.run_protocol(cfg, debug=False)
        assert "Protocol completed successfully" in result

        events = cfg.event_logger.get_events()
        relative_events = get_relative_event_times(events, "ared_on")
        ared_on = get_event_time_by_pattern(relative_events, r"ared_on")
        action_ared_off = get_event_time_by_pattern(
            relative_events, r"action_ared_off_executed_at_"
        )

        duration = action_ared_off - ared_on
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


# # test to ensure that the protocol runner correctly handles timing of events
# @pytest.mark.hardware
# def test_run_protocol_timing_correct(tmp_path):
#     io = IOController()

#     filename = tmp_path / "test_output.csv"

#     cfg = ExperimentConfig(
#         actinic_led_intensity=75,
#         measurement_led_intensity=30,
#         recording_length_s=2.0,
#         recording_hz=1000,
#         ared_duration_s=1.0,
#         wait_after_ared_s=0.002,
#         agreen_delay_s=0.002,
#         agreen_duration_s=1.998,  # Ensure this is less than recording_length_s
#         filename=str(filename),
#     )

#     io.open_device()
#     runner = ProtocolRunner(io, Recorder(io))

#     result = runner.run_protocol(cfg, debug=True)
#     assert "Protocol completed successfully" in result, "Protocol did not complete successfully"

#     # verify that we created the appropriate files
#     assert os.path.exists(cfg.filename), "CSV data file not created"
#     assert os.path.exists(
#         cfg.filename.replace(".csv", "_metadata.json")
#     ), "Metadata file not created"

#     # verify the events
#     events = cfg.event_logger.get_events()

#     # print all the labels out
#     print("Logged events:")
#     for label, time_point in events:
#         print(time_point, label)

#     # match some basic events before recording
#     labels = [label for _, label in events]
#     # action_{self.label}_executed_at_
#     assert_label_matches(labels, r"action_ared_off_executed_at_")
#     assert_label_matches(labels, r"action_agreen_on_executed_at_")
#     assert_label_matches(labels, r"action_shutter_opened_executed_at_")

#     # look at the recorded data. Import the csv file and check the timing of the events
#     import pandas as pd
#     data = pd.read_csv(cfg.filename)

#     assert 'time' in data.columns, "Time column is missing from recorded data"
#     assert data['time'].notnull().all(), "Time column contains null values"
#     assert 'signal' in data.columns, "Signal column is missing from recorded data"
#     assert data['signal'].notnull().all(), "Signal column contains null values"

#     print(data.head())

#     # find the first sample where the signal is NOT zero
#     # this should be the first sample, but may not be if there is a delay in data
#     # acquisition or if the signal is not zero at the start
#     signal = data['signal'].values
#     first_signal_not_zero = next(
#         (i for i, s in enumerate(signal) if s != 0), None
#     )

#     assert first_signal_not_zero is not None, "No signal not zero found"
#     print(f"First signal not zero at sample: {first_signal_not_zero}")
#     assert first_signal_not_zero < 10, "The first signal not zero is too late, indicating a timing issue"

#     # now we dive into the timing of the events
#     # get the relative times of the events, relative to the first 'real' event, which is the ared_on event
#     relative_events = get_relative_event_times(events, "ared_on")

#     # These are the key events we want to check
#     ared_on = get_event_time_by_pattern(relative_events, r"ared_on")
#     recording_loop_started = get_event_time_by_pattern(relative_events, r"recording_loop_started")
#     action_ared_off = get_event_time_by_pattern(relative_events, r"action_ared_off_executed_at_")
#     action_shutter_opened = get_event_time_by_pattern(relative_events, r"action_shutter_opened_executed_at_")
#     action_agreen_on = get_event_time_by_pattern(relative_events, r"action_agreen_on_executed_at_")
#     action_agreen_off = get_event_time_by_pattern(relative_events, r"agreen_off")
#     recording_complete = get_event_time_by_pattern(
#         relative_events, r"recording_completed"
#     )
#     buffer_flush_started = get_event_time_by_pattern(
#         relative_events, r"start_buffer_flush"
#     )

#     test_shutter_opening = get_event_time_by_pattern(
#         relative_events, r"test_shutter_opening"
#     )
#     test_shutter_opened = get_event_time_by_pattern(
#         relative_events, r"test_shutter_opened"
#     )
#     test_shutter_closed = get_event_time_by_pattern(
#         relative_events, r"test_shutter_closed"
#     )
#     # ensure that the test shutter transitions are less than 1ms apart
#     assert abs(test_shutter_opened - test_shutter_opening) < 0.001, (
#         f"Test shutter opening took too long: started at {test_shutter_opening:.3f}s, opened at {test_shutter_opened:.3f}s"
#     )
#     assert abs(test_shutter_closed - test_shutter_opened) < 0.001, (
#         f"Test shutter closing took too long: opened at {test_shutter_opened:.3f}s, closed at {test_shutter_closed:.3f}s"
#     )
#     assert abs(test_shutter_closed - test_shutter_opening) < 0.002, (
#         f"Test shutter total transition took too long: started at {test_shutter_opening:.3f}s, closed at {test_shutter_closed:.3f}s"
#     )

#     # Check that the buffer flush started and completed within a reasonable time
#     assert (
#         abs(recording_loop_started - buffer_flush_started) < 0.01
#     ), f"Buffer flush took too long: started at {buffer_flush_started:.3f}s, completed at {recording_loop_started:.3f}s"

#     # Expect a consistent timing for the ared_on event, within 1ms of the ared_duration_s based on the event logger
#     tolerance = 0.02 * cfg.ared_duration_s  # 2% of the ared duration expected on time
#     actual_on_time = action_ared_off - ared_on
#     assert abs(actual_on_time - cfg.ared_duration_s) < tolerance, (
#         f"Ared on timing is incorrect: expected around {cfg.ared_duration_s}s, "
#         f"but got {actual_on_time:.3f}s"
#     )

#     # So the shutter and the ared_off should be very close in timing, but then we have the wait
#     # We expect that the amount of time between the ared_off and the shutter_open is equal to the wait_after_ared_s
#     assert abs(action_shutter_opened - action_ared_off - cfg.wait_after_ared_s) <= 0.001, (
#         f"Action 'shutter_opened' timing is incorrect: expected around {cfg.wait_after_ared_s}s after 'ared_off', "
#         f"but got {action_shutter_opened - action_ared_off:.3f}s"
#     )

#     # # Check that the Agreen LED was turned on after the delay
#     assert abs(action_agreen_on - action_shutter_opened - cfg.agreen_delay_s) < 0.001, (
#         f"Action 'agreen_on' timing is incorrect: expected around {cfg.agreen_delay_s}s after 'shutter_opened', "
#         f"but got {action_agreen_on - action_shutter_opened:.3f}s"
#     )

#     # assert abs(recording_complete - action_agreen_on - cfg.agreen_duration_s) < 0.010, (
#     #     f"Action 'recording_complete' timing is incorrect: expected around {cfg.agreen_duration_s}s after 'agreen_on', "
#     #     f"but got {recording_complete - action_agreen_on:.3f}s"
#     # )

#     # # we expect the time from recording_loop_started to the recording_complete to be very close to the recording_length_s
#     # # Be within 25ms tolerance, as the recording may take a bit longer due to hardware delays
#     # assert abs(recording_complete - recording_loop_started - cfg.recording_length_s) < 0.010, (
#     #     f"Recording completion timing is incorrect: expected around {cfg.recording_length_s}s after 'recording_loop_started', "
#     #     f"but got {recording_complete - recording_loop_started:.3f}s"
#     # )

#     io.cleanup()
