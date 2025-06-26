import pytest
from unittest.mock import MagicMock
from src.utils import calculate_samples_from_config, calculate_total_recording_length
from src.experiment_config import ExperimentConfig
from src.constants import PRE_BUFFER_SECONDS

def test_calculate_samples_from_config():
    """
    Ensure that the sample count is correctly calculated based on the total
    duration of the experiment, including a pre-buffer.
    """

    # Create a mock configuration object
    cfg = ExperimentConfig(
        recording_hz=10,
        ared_duration_s=1.0,
        wait_after_ared_s=0.5,
        agreen_delay_s=0.2,
        agreen_duration_s=0.8
    )

    # Calculate expected samples
    expected_samples = int(
        (PRE_BUFFER_SECONDS + cfg.ared_duration_s + cfg.wait_after_ared_s +
         cfg.agreen_delay_s + cfg.agreen_duration_s) * cfg.recording_hz
    )

    # Call the function and assert the result
    n_samples = calculate_samples_from_config(cfg)
    assert n_samples == expected_samples, f"Expected {expected_samples}, got {n_samples}"


def test_zero_duration_and_zero_hz_returns_at_least_one_sample():
    cfg = ExperimentConfig(
        recording_hz=0,
        ared_duration_s=0,
        wait_after_ared_s=0,
        agreen_delay_s=0,
        agreen_duration_s=0,
    )
    result = calculate_samples_from_config(cfg)
    assert result == 1, "Should return at least 1 sample"


@pytest.mark.parametrize(
    "hz,ared,wait,delay,green,expected",
    [
        (10, 1.0, 0.5, 0.2, 0.8, int((0.1 + 1.0 + 0.5 + 0.2 + 0.8) * 10)),
        (100, 0.0, 0.0, 0.0, 0.0, int(0.1 * 100)),  # just pre-buffer
        (0, 1.0, 1.0, 1.0, 1.0, 1),  # edge case: 0 Hz still returns at least 1
    ],
)

def test_calculate_samples_param(hz, ared, wait, delay, green, expected):
    cfg = ExperimentConfig(
        recording_hz=hz,
        ared_duration_s=ared,
        wait_after_ared_s=wait,
        agreen_delay_s=delay,
        agreen_duration_s=green,
    )
    result = calculate_samples_from_config(cfg)
    assert result == expected, f"Expected {expected}, got {result}"


def test_verbose_output_shows_debug_info(capfd):
    cfg = ExperimentConfig(
        recording_hz=10,
        ared_duration_s=1.0,
        wait_after_ared_s=0.5,
        agreen_delay_s=0.2,
        agreen_duration_s=0.8,
    )
    _ = calculate_samples_from_config(cfg, verbose=True)
    out, err = capfd.readouterr()
    assert "Pre-buffer" in out
    assert "Total duration" in out


def test_warning_for_short_total_duration():
    cfg = ExperimentConfig(
        recording_hz=1000,
        ared_duration_s=0,
        wait_after_ared_s=0,
        agreen_delay_s=0,
        agreen_duration_s=0,
    )
    # possibly raise or warn later, for now just ensure non-zero output
    result = calculate_samples_from_config(cfg)
    assert result == int(PRE_BUFFER_SECONDS * cfg.recording_hz)

def test_calculate_total_recording_length():
    cfg = ExperimentConfig(
        recording_hz=10,
        ared_duration_s=1.0,
        wait_after_ared_s=0.5,
        agreen_delay_s=0.2,
        agreen_duration_s=0.8
    )
    expected_length = (
        PRE_BUFFER_SECONDS
        + cfg.ared_duration_s
        + cfg.wait_after_ared_s
        + cfg.agreen_delay_s
        + cfg.agreen_duration_s
    )
    assert calculate_total_recording_length(cfg) == expected_length