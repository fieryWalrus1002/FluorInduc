import pytest
from src.timed_action_factory import TimedActionFactory
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.timed_action import TimedAction
from src.event_logger import EventLogger
import time

ARED_DURATION = 1.0  # seconds
WAIT_AFTER_ARED = 0.002  # seconds
AGREEN_DELAY = 0.002  # seconds
AGREEN_DURATION = 1.2  # seconds
END_RECORDING_DELAY = 0.025  # seconds

class MockIOController:
    def set_led_voltage(self, led_number, value):
        print(f"[Mock] Set LED {led_number} to {value} V")


class CustomTimedActionFactory(TimedActionFactory):
    def get_test_actions(self, actinic_red_voltage: float, meas_green_voltage: float, logger: EventLogger = None) -> list[TimedAction]:
        """
        Get a list of all actions for production.
        """
        return [
            self.make_ared_on(voltage=actinic_red_voltage),
            self.make_ared_off(),
            self.make_wait_after_ared(),
            self.make_shutter_opened(),
            self.make_agreen_on(voltage=meas_green_voltage),
            self.make_agreen_off(),
            self.end_recording()
        ]

    def create_full_protocol(
        self, red_voltage: float = 0.0, green_voltage: float = 0.0, logger: EventLogger = None
    ) -> list[TimedAction]:
        return self.get_test_actions(red_voltage, green_voltage, logger=logger)


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
def test_factory(test_config):
    io = MockIOController()
    stop_flag = {"stop": False}
    return CustomTimedActionFactory(io, test_config, stop_flag)

def test_ared_on_delay(test_factory, test_config):
    action = test_factory.make_ared_on(3.3)
    assert isinstance(action, TimedAction)
    assert action.action_time_s == 0.0
    assert action.label == "ared_on"
    assert action.epsilon == test_config.action_epsilon_s


def test_ared_off_delay(test_factory, test_config):
    action = test_factory.make_ared_off()
    assert action.action_time_s == ARED_DURATION
    assert action.label == "ared_off"
    assert action.epsilon == test_config.action_epsilon_s

def test_wait_after_ared_delay(test_factory):
    action = test_factory.make_wait_after_ared()
    expected = ARED_DURATION + WAIT_AFTER_ARED
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "wait_after_ared"


def test_shutter_opened_delay(test_factory):
    action = test_factory.make_shutter_opened()
    expected = ARED_DURATION + WAIT_AFTER_ARED
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "shutter_opened"


def test_agreen_on_delay(test_factory):
    action = test_factory.make_agreen_on(voltage=1.2)
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_on"


def test_agreen_off_delay(test_factory):
    action = test_factory.make_agreen_off()
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "agreen_off"


def test_end_recording_delay(test_factory):
    action = test_factory.end_recording()
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + AGREEN_DURATION + END_RECORDING_DELAY
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected
    assert action.label == "end_recording"

def test_end_recording_sets_stop_flag(test_factory):
    action = test_factory.end_recording()
    assert not test_factory.stop_flag["stop"]  # Make sure it's initially False
    action.action_fn()  # Execute the stop signal function
    assert test_factory.stop_flag["stop"] is True  # It should now be set

def test_capture_and_verify_event_logs(test_config):
    logger = EventLogger()
    io = MockIOController()
    test_factory = CustomTimedActionFactory(io, test_config, {"stop": False})
    test_factory.event_logger = logger
    ared = test_factory.make_ared_off()
    ared.execute(logger, t_zero=time.perf_counter())
    assert any("ared_off" in msg for _, msg in logger.events)


def test_full_protocol(test_factory):
    actions = test_factory.create_full_protocol()
    assert len(actions) == 7  # Should include all actions in the full protocol

    expected_labels = [
        "ared_on",
        "ared_off",
        "wait_after_ared",
        "shutter_opened",
        "agreen_on",
        "agreen_off",
        "end_recording"
    ]

    for action, expected_label in zip(actions, expected_labels):
        assert action.label == expected_label


def test_all_actions_have_epsilon(test_factory, test_config):
    actions = test_factory.create_full_protocol()
    for action in actions:
        assert action.epsilon == test_config.action_epsilon_s

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
    io = MockIOController()
    stop_flag = {"stop": False}
    overrides = {"agreen_on": 0.005}
    test_factory = CustomTimedActionFactory(io, config, stop_flag, delay_overrides=overrides)

    action = test_factory.make_agreen_on(1.2)
    expected = ARED_DURATION + WAIT_AFTER_ARED + AGREEN_DELAY + overrides["agreen_on"]
    assert action.label == "agreen_on"
    assert pytest.approx(action.action_time_s, abs=1e-6) == expected


def test_capture_and_verify_event_logs(test_factory):
    logger = EventLogger()
    logger.start_event("test_event")
    test_factory.event_logger = logger
    ared = test_factory.make_ared_off()
    ared.execute(logger, t_zero=time.perf_counter())

    assert any("ared_off" in msg for _, msg in logger.get_events())
