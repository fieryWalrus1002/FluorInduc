from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
import os
import re


def get_event_time_by_pattern(events, pattern: str):
    """
    Search a list of (time, label) tuples for the first event matching the pattern.

    :param events: List of tuples (time, label) from event logger.
    :param pattern: Regex pattern to match label.
    :return: Time value for the first matching event, or raises AssertionError if not found.
    """
    for time_point, label in events:
        if re.search(pattern, label):
            return time_point
    raise AssertionError(f"No event label matched the pattern: '{pattern}'")


def get_relative_event_times(events, reference_label="recording_started"):
    """
    Given a list of (time, label) tuples, return a list of (delta_time, label) tuples,
    where delta_time is relative to the time of the reference event (e.g. 'recording_started').

    :param events: List of (time, label) tuples from event logger.
    :param reference_label: The label used as the zero point for relative timing.
    :return: List of (delta_time, label) tuples.
    :raises AssertionError: If the reference label is not found.
    """
    reference_time = None
    for time_point, label in events:
        if label == reference_label:
            reference_time = time_point
            break

    if reference_time is None:
        raise AssertionError(f"Reference event '{reference_label}' not found in events")

    return [(time_point - reference_time, label) for time_point, label in events]


def assert_label_matches(labels, pattern: str, *, message=None):
    """
    Assert that at least one label matches the given regex pattern.

    :param labels: List of label strings.
    :param pattern: Regex pattern to match against labels.
    :param message: Optional custom error message.
    """
    if not any(re.search(pattern, label) for label in labels):
        raise AssertionError(
            message or f"No label matched the pattern: '{pattern}'\nLabels: {labels}"
        )


@pytest.mark.hardware
def test_run_protocol_creates_output_files(tmp_path):
    io = IOController()

    filename = tmp_path / "test_output.csv"

    cfg = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_length_s=0.5,
        recording_hz=1000,
        ared_duration_s=0.01,
        wait_after_ared_s=0.005,
        agreen_delay_s=0.005,
        agreen_duration_s=0.02,
        filename=str(filename),
    )

    try:
        io.open_device()
        runner = ProtocolRunner(io, Recorder(io))

        result = runner.run_protocol(cfg)

        assert os.path.exists(cfg.filename), "CSV data file not created"
        assert os.path.exists(
            cfg.filename.replace(".csv", "_metadata.json")
        ), "Metadata file not created"

        with open(cfg.filename, "r") as f:
            lines = f.readlines()
        assert len(lines) > 2, "Not enough samples recorded"

        events = cfg.event_logger.get_events()
        labels = [label for _, label in events]

        # print all the labels out
        print("Logged events:")
        for label in labels:
            print(label)

        # match some basic events before recording
        assert_label_matches(
            labels, r"ared_on", message="Expected 'ared_on' event was not found"
        )
        assert_label_matches(
            labels, r"recording_started", message="Expected 'recording_started' event was not found"
        )
        assert_label_matches(
            labels, r"protocol_complete", message="Expected 'protocol_complete' event was not found"
        )

        # match action events that should be present in the recorded data
        assert_label_matches(labels, r"ared_on")
        assert_label_matches(labels, r"action_ared_off_executed_at_sample_\d+")
        assert_label_matches(labels, r"action_agreen_on_executed_at_sample_\d+")
        assert_label_matches(labels, r"action_shutter_opened_executed_at_sample_\d+")

    finally:
        io.cleanup()


@pytest.mark.hardware
def test_run_protocol_fails_when_green_duration_exceeds_limit(tmp_path):
    io = IOController()

    filename = tmp_path / "test_output.csv"

    cfg = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_length_s=2.0,
        recording_hz=1000,
        ared_duration_s=0.05,
        wait_after_ared_s=0.000,
        agreen_delay_s=0.002,
        agreen_duration_s=2.0,
        filename=str(filename),
    )

    io.open_device()
    runner = ProtocolRunner(io, Recorder(io))

    with pytest.raises(ValueError) as excinfo:
        runner.run_protocol(cfg)

    assert re.search(
        r"The Agreen LED duration plus delay exceeds the recording length",
        str(excinfo.value),
    ), f"Unexpected error message: {str(excinfo.value)}"
    
    io.cleanup()

# test to ensure that the protocol runner correctly handles timing of events
@pytest.mark.hardware
def test_run_protocol_timing_correct(tmp_path):
    io = IOController()

    filename = tmp_path / "test_output.csv"

    cfg = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=30,
        recording_length_s=2.0,
        recording_hz=1000,
        ared_duration_s=1.0,
        wait_after_ared_s=0.002,
        agreen_delay_s=0.002,
        agreen_duration_s=1.998,  # Ensure this is less than recording_length_s
        filename=str(filename),
    )

    io.open_device()
    runner = ProtocolRunner(io, Recorder(io))

    result = runner.run_protocol(cfg, debug=True)
    assert "Protocol completed successfully" in result, "Protocol did not complete successfully"

    # verify that we created the appropriate files
    assert os.path.exists(cfg.filename), "CSV data file not created"
    assert os.path.exists(
        cfg.filename.replace(".csv", "_metadata.json")
    ), "Metadata file not created"

    # verify the events
    events = cfg.event_logger.get_events()

    # print all the labels out
    print("Logged events:")
    for label, time_point in events:
        print(time_point, label)

    # match some basic events before recording
    labels = [label for _, label in events]
    assert_label_matches(labels, r"action_ared_off_executed_at_sample_\d+")
    assert_label_matches(labels, r"action_agreen_on_executed_at_sample_\d+")
    assert_label_matches(labels, r"action_shutter_opened_executed_at_sample_\d+")

    # look at the recorded data. Import the csv file and check the timing of the events
    import pandas as pd
    data = pd.read_csv(cfg.filename)

    assert 'time' in data.columns, "Time column is missing from recorded data"
    assert data['time'].notnull().all(), "Time column contains null values"
    assert 'signal' in data.columns, "Signal column is missing from recorded data"
    assert data['signal'].notnull().all(), "Signal column contains null values"

    print(data.head())

    # find the first sample where the signal is NOT zero
    # this should be the first sample, but may not be if there is a delay in data
    # acquisition or if the signal is not zero at the start
    signal = data['signal'].values
    first_signal_not_zero = next(
        (i for i, s in enumerate(signal) if s != 0), None
    )

    assert first_signal_not_zero is not None, "No signal not zero found"
    print(f"First signal not zero at sample: {first_signal_not_zero}")
    assert first_signal_not_zero < 10, "The first signal not zero is too late, indicating a timing issue"

    # now we dive into the timing of the events
    # get the relative times of the events, relative to the first 'real' event, which is the ared_on event
    relative_events = get_relative_event_times(events, "ared_on")

    # These are the key events we want to check
    ared_on = get_event_time_by_pattern(relative_events, r"ared_on")
    recording_loop_started = get_event_time_by_pattern(relative_events, r"recording_loop_started")
    action_ared_off = get_event_time_by_pattern(relative_events, r"action_ared_off_executed_at_sample_\d+")
    action_shutter_opened = get_event_time_by_pattern(relative_events, r"action_shutter_opened_executed_at_sample_\d+")
    action_agreen_on = get_event_time_by_pattern(relative_events, r"action_agreen_on_executed_at_sample_\d+")
    action_agreen_off = get_event_time_by_pattern(relative_events, r"agreen_off")
    recording_complete = get_event_time_by_pattern(
        relative_events, r"recording_completed"
    )
    buffer_flush_started = get_event_time_by_pattern(
        relative_events, r"start_buffer_flush"
    )
    
    test_shutter_opening = get_event_time_by_pattern(
        relative_events, r"test_shutter_opening"
    )
    test_shutter_opened = get_event_time_by_pattern(
        relative_events, r"test_shutter_opened"
    )
    test_shutter_closed = get_event_time_by_pattern(
        relative_events, r"test_shutter_closed"
    )
    # ensure that the test shutter transitions are less than 1ms apart
    assert abs(test_shutter_opened - test_shutter_opening) < 0.001, (
        f"Test shutter opening took too long: started at {test_shutter_opening:.3f}s, opened at {test_shutter_opened:.3f}s"
    )
    assert abs(test_shutter_closed - test_shutter_opened) < 0.001, (
        f"Test shutter closing took too long: opened at {test_shutter_opened:.3f}s, closed at {test_shutter_closed:.3f}s"
    )
    assert abs(test_shutter_closed - test_shutter_opening) < 0.002, (
        f"Test shutter total transition took too long: started at {test_shutter_opening:.3f}s, closed at {test_shutter_closed:.3f}s"
    )

    # Check that the buffer flush started and completed within a reasonable time
    assert (
        abs(recording_loop_started - buffer_flush_started) < 0.001
    ), f"Buffer flush took too long: started at {buffer_flush_started:.3f}s, completed at {recording_loop_started:.3f}s"

    # Expect a consistent timing for the ared_on event, within 1ms of the ared_duration_s based on the event logger
    assert abs(action_ared_off - ared_on - cfg.ared_duration_s) < 0.003, (
        f"Action 'ared_off' timing is incorrect: expected around {cfg.ared_duration_s}s after 'ared_on', "
        f"but got {action_ared_off - ared_on:.3f}s"
    )

    # So the shutter and the ared_off should be very close in timing, but then we have the wait
    # We expect that the amount of time between the ared_off and the shutter_open is equal to the wait_after_ared_s
    assert abs(action_shutter_opened - action_ared_off - cfg.wait_after_ared_s) <= 0.001, (
        f"Action 'shutter_opened' timing is incorrect: expected around {cfg.wait_after_ared_s}s after 'ared_off', "
        f"but got {action_shutter_opened - action_ared_off:.3f}s"
    )

    # # Check that the Agreen LED was turned on after the delay
    assert abs(action_agreen_on - action_shutter_opened - cfg.agreen_delay_s) < 0.001, (
        f"Action 'agreen_on' timing is incorrect: expected around {cfg.agreen_delay_s}s after 'shutter_opened', "
        f"but got {action_agreen_on - action_shutter_opened:.3f}s"
    )
    
    
    # assert abs(recording_complete - action_agreen_on - cfg.agreen_duration_s) < 0.010, (
    #     f"Action 'recording_complete' timing is incorrect: expected around {cfg.agreen_duration_s}s after 'agreen_on', "
    #     f"but got {recording_complete - action_agreen_on:.3f}s"
    # )

    # # we expect the time from recording_loop_started to the recording_complete to be very close to the recording_length_s
    # # Be within 25ms tolerance, as the recording may take a bit longer due to hardware delays
    # assert abs(recording_complete - recording_loop_started - cfg.recording_length_s) < 0.010, (
    #     f"Recording completion timing is incorrect: expected around {cfg.recording_length_s}s after 'recording_loop_started', "
    #     f"but got {recording_complete - recording_loop_started:.3f}s"
    # )

    io.cleanup()
