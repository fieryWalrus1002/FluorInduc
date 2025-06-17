import os
import pandas as pd
import pytest

from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.recorder import Recorder


@pytest.mark.hardware
def test_acquisition_rate_and_zero_buffer(tmp_path):
    io = IOController()

    filename = tmp_path / "rate_and_zero_check.csv"

    cfg = ExperimentConfig(
        actinic_led_intensity=50,
        measurement_led_intensity=0,
        recording_length_s=2.0,
        recording_hz=1000,
        ared_duration_s=1.0,
        wait_after_ared_s=0.005,
        agreen_delay_s=0.002,
        agreen_duration_s=1.998,
        filename=str(filename),
    )

    try:
        io.open_device()
        runner = ProtocolRunner(io, Recorder(io))
        result = runner.run_protocol(cfg, debug=False)
        assert "Protocol completed successfully" in result

        # Check output file was created
        assert os.path.exists(cfg.filename), "CSV data file not created"
        data = pd.read_csv(cfg.filename)

        assert "time" in data.columns, "Time column is missing"
        assert "signal" in data.columns, "Signal column is missing"
        assert data["time"].notnull().all(), "Missing time values"
        assert data["signal"].notnull().all(), "Missing signal values"

        # ------------------------------------------
        # Verify expected acquisition rate
        # ------------------------------------------
        actual_duration = data["time"].iloc[-1] - data["time"].iloc[0]
        actual_sample_count = len(data)
        expected_rate = cfg.recording_hz

        actual_rate = actual_sample_count / actual_duration
        print(f"Expected rate: {expected_rate} Hz, Actual rate: {actual_rate:.2f} Hz")

        assert (
            abs(actual_rate - expected_rate) < 50
        ), f"Sample rate error too large: expected {expected_rate} Hz, got {actual_rate:.2f} Hz"

        # ------------------------------------------
        # Check for excessive initial zeros
        # ------------------------------------------
        signal = data["signal"].values
        zero_threshold = 0.01
        zero_run_limit = 1

        initial_zeros = next(
            (i for i, v in enumerate(signal) if abs(v) >= zero_threshold), len(signal)
        )
        print(f"Initial zeros before signal activity: {initial_zeros}")

        assert (
            initial_zeros <= zero_run_limit
        ), f"Too many initial zeros ({initial_zeros}). Data may include pre-buffered artifacts."

    finally:
        io.cleanup()
