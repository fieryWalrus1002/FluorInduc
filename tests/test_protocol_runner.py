from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig


def test_calculate_sample_number_for_action():
    assert ProtocolRunner.calculate_sample_number_for_action(0.002, 1000000) == 2000


def test_run_protocol_calls_all_steps(tmp_path):
    # Mock IOController and Recorder
    io = MagicMock()
    recorder = MagicMock()

    # Stub the record function to return dummy data
    dummy_samples = [0] * 1000
    recorder.record.return_value = (dummy_samples, 1000, 0, 0)

    # Create a config with known parameters
    cfg = ExperimentConfig(
        actinic_led_intensity=75,
        measurement_led_intensity=33,
        recording_length_s=0.01,
        recording_hz=1000,
        ared_duration_s=0.001,
        wait_after_ared_s=0.001,
        agreen_delay_s=0.001,
        agreen_duration_s=0.005,
        channel_range=2,
        filename=str(tmp_path / "output.csv"),
    )

    runner = ProtocolRunner(io, recorder)
    result_msg = runner.run_protocol(cfg)

    # Check recording was called
    recorder.record.assert_called_once()
    io.open_device.assert_called_once()
    io.close_device.assert_called_once()
    assert "Protocol completed successfully" in result_msg

    # Metadata should be saved
    metadata_file = tmp_path / "output_metadata.json"
    assert metadata_file.exists()


def test_event_logger_logs_events():
    io = MagicMock()
    recorder = MagicMock()
    recorder.record.return_value = ([0] * 1000, 1000, 0, 0)

    cfg = ExperimentConfig(
        actinic_led_intensity=50,
        measurement_led_intensity=50,
        recording_length_s=0.01,
        recording_hz=1000,
        ared_duration_s=0.001,
        wait_after_ared_s=0.001,
        agreen_delay_s=0.001,
        agreen_duration_s=0.005,
        channel_range=2,
        filename="test.csv",
    )

    runner = ProtocolRunner(io, recorder)
    runner.run_protocol(cfg)

    events = cfg.event_logger.get_events()
    assert events[0][1] == "protocol_start"
    assert len(events) >= 1
