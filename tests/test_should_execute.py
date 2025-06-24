import time
from src.recorder import Recorder
from src.event_logger import EventLogger
from src.timed_action import TimedAction


class DummyController:
    def __init__(self):
        self.dwf = None
        self.hdwf = None


class DummyAction(TimedAction):
    def __init__(self, label, action_time_s):
        def dummy_fn():
            print(f"Executed {label}")

        super().__init__(action_time_s=action_time_s, action_fn=dummy_fn, label=label)
        self.executed = False

    def execute(self, logger):
        self.executed = True
        logger.log_event(f"{self.label}_executed")
        return time.perf_counter()


    def should_execute(self, t_action):
        return not self.executed and t_action >= self.action_time_s


def test_execute_pending_actions_simulated_loop():
    controller = DummyController()
    recorder = Recorder(controller)
    logger = EventLogger()
    recorder.logger = logger
    logger.start_event("test")

    # Define two actions at 0.0s and 1.5s after t_zero
    actions = [
        DummyAction("ared_on", 0.0),
        DummyAction("agreen_on", 1.5),
    ]

    start_time = time.perf_counter()
    hz_acq = 1000.0  # Assume 1000 Hz for simulation
    t_zero = None
    data_index = None

    # Simulate loop for 2 seconds
    end_time = start_time + 2.1
    while time.perf_counter() < end_time:
        t_zero, data_index = recorder._execute_pending_actions(
            actions, t_zero, start_time, hz_acq, data_index
        )
        time.sleep(0.01)

    print(f"start_time: {start_time}, end_time: {end_time}, t_zero: {t_zero}, data_index: {data_index}")
    print(f"elapsed time: {time.perf_counter() - start_time:.3f} seconds")
    print(f"Expected elapsed time: {end_time - start_time:.3f} seconds")

    assert actions[0].executed, "ared_on should have executed"
    assert actions[1].executed, "agreen_on should have executed"
    print("Logged events:")
    print(logger)

    assert data_index is not None, "dataIndex should be set after ared_on"
