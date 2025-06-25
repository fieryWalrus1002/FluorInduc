import pytest
from src.timed_action_factory import TimedActionFactory
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.timed_action import TimedAction


ARED_DURATION = 1.0  # seconds
WAIT_AFTER_ARED = 0.005  # seconds
AGREEN_DELAY = 0.002  # seconds
AGREEN_DURATION = 0.998  # seconds
END_RECORDING_DELAY = 0.025  # seconds

@pytest.fixture
def test_config():
    return ExperimentConfig(
        actinic_led_intensity=100,
        measurement_led_intensity=50,
        recording_hz=1000,
        ared_duration_s=ARED_DURATION,
        wait_after_ared_s=WAIT_AFTER_ARED,
        agreen_delay_s=AGREEN_DELAY,
        agreen_duration_s=AGREEN_DURATION,
        filename="dummy.csv",
        action_epsilon_s=0.001,
    )


@pytest.fixture
def factory(test_config):
    io = IOController()
    stop_flag = {"stop": False}
    return TimedActionFactory(io, test_config, stop_flag)


def test_ared_on_delay(factory, test_config):
    action = factory.make_ared_on(3.3)
    assert isinstance(action, TimedAction)
    assert action.action_time_s == 0.0
    assert action.label == "ared_on"
    assert action.epsilon == test_config.action_epsilon_s


def test_ared_off_delay(factory, test_config):
    action = factory.make_ared_off()
    assert action.action_time_s == 1.0
    assert action.label == "ared_off"
    assert action.epsilon == test_config.action_epsilon_s


def test_wait_after_ared_delay(factory):
    action = factory.make_wait_after_ared()
    expected = ARED_DURATION + WAIT_AFTER_ARED
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "wait_after_ared"


def test_shutter_opened_delay(factory):
    action = factory.make_shutter_opened()
    expected = ARED_DURATION + WAIT_AFTER_ARED
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "shutter_opened"


def test_agreen_on_delay(factory):
    action = factory.make_agreen_on(voltage=1.2)
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_on"


def test_agreen_off_delay(factory):
    action = factory.make_agreen_off()
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_off"


def test_end_recording_delay(factory):
    action = factory.end_recording()
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION + END_RECORDING_DELAY
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "end_recording"


def test_all_actions_have_epsilon(factory, test_config):
    actions = [
        factory.make_ared_on(3.3),
        factory.make_ared_off(),
        factory.make_wait_after_ared(),
        factory.make_shutter_opened(),
        factory.make_agreen_on(1.0),
        factory.make_agreen_off(),
        factory.end_recording(),
    ]
    for action in actions:
        assert action.epsilon == test_config.action_epsilon_s


def test_end_recording_sets_stop_flag(factory):
    action = factory.end_recording()
    assert not factory.stop_flag["stop"]  # Make sure it's initially False
    action.action_fn()  # Execute the stop signal function
    assert factory.stop_flag["stop"] is True  # It should now be set


def test_delay_override_applied():
    
    TEST_AGREEN_DURATION = 1.2  # seconds
    
    config = ExperimentConfig(
        actinic_led_intensity=100,
        measurement_led_intensity=50,
        recording_hz=1000,
        ared_duration_s=ARED_DURATION,
        wait_after_ared_s=WAIT_AFTER_ARED,
        agreen_delay_s=AGREEN_DELAY,
        agreen_duration_s=TEST_AGREEN_DURATION,
        filename="dummy.csv",
        action_epsilon_s=0.001,
    )
    io = IOController()
    stop_flag = {"stop": False}
    overrides = {"agreen_on": 0.005}
    factory = TimedActionFactory(io, config, stop_flag, delay_overrides=overrides)

    action = factory.make_agreen_on(1.2)
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + overrides["agreen_on"]
    assert action.label == "agreen_on"
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
