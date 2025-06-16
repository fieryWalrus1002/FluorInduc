from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder
import os
import re


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