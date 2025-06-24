import pytest
from src.timed_action_factory import TimedActionFactory
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.timed_action import TimedAction


@pytest.fixture
def test_config():
    return ExperimentConfig(
        actinic_led_intensity=100,
        measurement_led_intensity=50,
        recording_hz=1000,
        ared_duration_s=1.0,
        wait_after_ared_s=0.005,
        agreen_delay_s=0.002,
        agreen_duration_s=0.998,
        filename="dummy.csv",
    )


@pytest.fixture
def factory(test_config):
    io = IOController()
    stop_flag = {"stop": False}
    return TimedActionFactory(io, test_config, stop_flag)


def test_ared_on_delay(factory):
    action = factory.make_ared_on(3.3)
    assert isinstance(action, TimedAction)
    assert action.action_time_s == 0.0
    assert action.label == "ared_on"


def test_ared_off_delay(factory):
    action = factory.make_ared_off()
    assert action.action_time_s == 1.0
    assert action.label == "ared_off"


def test_wait_after_ared_delay(factory):
    action = factory.make_wait_after_ared()
    expected = 1.0 + 0.005
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "wait_after_ared"


def test_shutter_opened_delay(factory):
    action = factory.make_shutter_opened()
    expected = 1.0 + 0.005
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "shutter_opened"


def test_agreen_on_delay(factory):
    action = factory.make_agreen_on(voltage=1.2, delay_from_shutter_open=0.002)
    expected = 1.0 + 0.005 + 0.002 + 0.002
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_on"


def test_agreen_off_delay(factory):
    action = factory.make_agreen_off(delay_from_shutter_open=0.002)
    expected = 1.0 + 0.005 + 0.002 + 0.002 + 0.998
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_off"


def test_end_recording_delay(factory):
    action = factory.end_recording(delay_from_shutter_open=0.002)
    expected = 1.0 + 0.005 + 0.002 + 0.002 + 0.998
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "end_recording"
