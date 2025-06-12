from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
import json
import os

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
        assert "ared_on" in labels
        assert "recording_started" in labels
        assert any("action_[agreen_on]_executed" in label for label in labels)
        assert "protocol_complete" in labels

        print(result)

    except Exception as e:
        io.cleanup()
        return f"An error occurred: {str(e)}"
    finally:
        io.cleanup()
