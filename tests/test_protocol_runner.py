from unittest.mock import MagicMock
import pytest
from src.protocol_runner import ProtocolRunner
from src.experiment_config import ExperimentConfig


def test_calculate_sample_number_for_action():
    assert ProtocolRunner.calculate_sample_number_for_action(0.002, 1000000) == 2000

def test_run_protocol_calls_all_steps(tmp_path):
    io = MagicMock()
    recorder = MagicMock()

    # Updated mocks for the new recording interface
    recorder.prepare_recording.return_value = None
    recorder.wait_for_data_start.return_value = 0.0
    recorder.complete_recording.return_value = ([0.0] * 1000, 1000, 0, 0, [])

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
    result_msg = runner.run_protocol(cfg, debug=True)

    assert "Protocol completed successfully" in result_msg


def test_event_logger_logs_events():
    io = MagicMock()
    recorder = MagicMock()
    recorder.prepare_recording.return_value = None
    recorder.wait_for_data_start.return_value = 0.0
    recorder.complete_recording.return_value = ([0.0] * 1000, 1000, 0, 0, [])

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
