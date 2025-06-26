import time
import pytest
from unittest.mock import MagicMock
from src.event_logger import EventLogger
from src.timed_action import TimedAction  # Or wherever TimedAction is defined
from src.timed_action_factory import TimedActionFactory


def test_should_execute_when_time_reached():
    action = TimedAction(action_time_s=0.5, action_fn=lambda: None, label="test")
    assert not action.should_execute(0.49)
    assert action.should_execute(0.5)
    assert action.should_execute(1.0)


def test_should_not_execute_twice():
    mock_fn = MagicMock()
    logger = EventLogger()
    logger.start_event("start")

    action = TimedAction(action_time_s=0.1, action_fn=mock_fn, label="test")
    action.execute(logger)

    # After execution, it should not execute again
    assert not action.should_execute(0.2)
    action.execute(logger)
    mock_fn.assert_called_once()  # should not call it twice


def test_execute_calls_function_and_logs_event():
    mock_fn = MagicMock()
    logger = EventLogger()
    logger.start_event("recording_loop_started")

    action = TimedAction(action_time_s=0.1, action_fn=mock_fn, label="green_on")
    action.execute(logger)

    events = logger.get_events()
    assert any("action_green_on" in e[1] for e in events)
    mock_fn.assert_called_once()


def test_multiple_actions_trigger_independently():
    mock_fn1 = MagicMock()
    mock_fn2 = MagicMock()
    logger = EventLogger()
    logger.start_event()

    action1 = TimedAction(0.1, mock_fn1, "led1")
    action2 = TimedAction(0.2, mock_fn2, "led2")

    assert action1.should_execute(0.11)
    action1.execute(logger)
    assert not action2.should_execute(0.15)
    assert action2.should_execute(0.21)
    action2.execute(logger)

    mock_fn1.assert_called_once()
    mock_fn2.assert_called_once()


def test_execute_does_not_crash_without_logger():
    mock_fn = MagicMock()
    logger = EventLogger()
    logger.start_event("recording_loop_started")  # Important!

    action = TimedAction(0.01, mock_fn, "noop")
    action.execute(logger)

    mock_fn.assert_called_once()


def test_no_execute_if_already_executed():
    mock_fn = MagicMock()
    action = TimedAction(0.1, mock_fn, "single_run")
    logger = EventLogger()
    logger.start_event("start")

    action.execute(logger)
    assert not action.should_execute(0.5)

    # Attempt to execute again
    action.execute(logger)
    mock_fn.assert_called_once()
