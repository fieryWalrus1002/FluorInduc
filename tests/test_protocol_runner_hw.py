from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
import json
import os
import re


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
        recording_length_s=0.05,
        recording_hz=10000,
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
