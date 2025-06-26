import unittest
from unittest.mock import MagicMock
import time

from src.recorder import Recorder
from src.timed_action import TimedAction
from src.event_logger import EventLogger


class TestRecorderActions(unittest.TestCase):
    def test_execute_pending_actions_initializes_t_zero(self):
        # Arrange
        fake_logger = EventLogger()
        fake_logger.start_event("test")

        recorder = Recorder(controller=MagicMock())
        recorder.logger = fake_logger

        # Mock action that should be executed immediately
        executed_flag = {"called": False}

        def fake_action_fn():
            executed_flag["called"] = True

        mock_action = TimedAction(
            action_time_s=0.0, action_fn=fake_action_fn, label="ared_on"
        )

        # Fake should_execute to always return True
        mock_action.should_execute = MagicMock(return_value=True)
        mock_action.execute = MagicMock(
            side_effect=lambda logger, t_zero=None: time.perf_counter()
        )

        actions = [mock_action]

        # Act
        start_time = time.perf_counter()
        t_zero, data_index = recorder._execute_pending_actions(
            actions=actions,
            t_zero=None,
            start_time=start_time,
            hz_acq=1000.0,  # 1000 Hz
            data_index=None,
        )

        # Assert
        self.assertIsNotNone(t_zero)
        self.assertIsNotNone(data_index)
        self.assertTrue(mock_action.execute.called)
        self.assertTrue(mock_action.should_execute.called)
        self.assertGreaterEqual(data_index, 0)
        self.assertIn(
            "t_zero_initialized_from_actual_ared_on",
            "\n".join([e[1] for e in fake_logger.get_events()]),
        )

    def test_execute_pending_actions_skips_unready_actions(self):
        recorder = Recorder(controller=MagicMock())
        recorder.logger = EventLogger()
        recorder.logger.start_event("test")

        mock_action = TimedAction(
            action_time_s=1.0, action_fn=lambda: None, label="ared_on"
        )
        mock_action.should_execute = MagicMock(return_value=False)
        mock_action.execute = MagicMock()

        with self.assertRaises(RuntimeError) as cm:
            recorder._execute_pending_actions(
                actions=[mock_action],
                t_zero=None,
                start_time=time.perf_counter(),
                hz_acq=1000.0,
                data_index=None,
            )

        self.assertIn("ared_on must be scheduled at 0.0s", str(cm.exception))

    def test_future_actions_skipped_but_valid_ared_on_executes(self):
        recorder = Recorder(controller=MagicMock())
        recorder.logger = EventLogger()
        recorder.logger.start_event("test")

        # Valid ared_on at t=0.0
        ared_action = TimedAction(
            action_time_s=0.0, action_fn=lambda: None, label="ared_on"
        )
        ared_action.should_execute = MagicMock(return_value=True)
        ared_action.execute = MagicMock(
            side_effect=lambda logger, t_zero=None: time.perf_counter()
        )

        # Future action far in the future (won’t trigger)
        future_action = TimedAction(
            action_time_s=999.0, action_fn=lambda: None, label="agreen_on"
        )
        future_action.should_execute = MagicMock(return_value=False)
        future_action.execute = MagicMock()

        start_time = time.perf_counter()
        t_zero, data_index = recorder._execute_pending_actions(
            actions=[ared_action, future_action],
            t_zero=None,
            start_time=start_time,
            hz_acq=1000,
            data_index=None,
        )

        self.assertIsNotNone(t_zero)
        self.assertIsNotNone(data_index)
        ared_action.execute.assert_called_once()
        future_action.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
