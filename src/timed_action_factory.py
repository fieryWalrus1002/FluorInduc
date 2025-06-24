from src.timed_action import TimedAction
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.event_logger import EventLogger
import time
from src.constants import LED_RED_PIN, LED_GREEN_PIN
class TimedActionFactory:
    """
    Factory class to create the timed actions used in the protocol. This class encapsulates
    the logic for creating actions that control the LED voltages and shutter states based on
    the provided configuration.

    time zero is "ared_on", which is that first action that is executed
    in the protocol. All other actions are scheduled relative to this time.
    We set the t_zero in the Recorder.complete_recording() method when the
    Recorder has finished executing the "ared_on" action.

    The Recorder will check each loop to see if the current time from t_zero is greater than
    the action's action_time_s, and if so, it will execute the action's action_fn.

    If an action has already been executed, it will not be executed again.


    Timed Action Timeline (relative to t_zero = time of "ared_on"):

    - ared_on          → t_zero + 0.0
    - ared_off         → t_zero + ared_duration_s
    - wait_after_ared  → t_zero + ared_duration_s + wait_after_ared_s
    - shutter_opened   → t_zero + ared_duration_s + wait_after_ared_s
    - agreen_on        → t_zero + ared_duration_s + wait_after_ared_s + agreen_delay_s
    - agreen_off       → t_zero + ared_duration_s + wait_after_ared_s + agreen_delay_s + agreen_duration_s
    - end_recording    → same as agreen_off (with optional small offset)


    """

    def __init__(self, io: IOController, cfg: ExperimentConfig, stop_flag: dict):
        self.io = io
        self.cfg = cfg
        self.stop_flag = stop_flag

    def make_ared_on(self, voltage: float) -> TimedAction:
        return TimedAction(
            action_time_s=0.0,
            action_fn=lambda: self.io.set_led_voltage(LED_RED_PIN, voltage),
            label="ared_on",
        )

    def make_ared_off(self, addtl_delay: float = 0.0) -> TimedAction:
        return TimedAction(
            action_time_s=self.cfg.ared_duration_s + addtl_delay,
            action_fn=lambda: self.io.set_led_voltage(LED_RED_PIN, 0),
            label="ared_off"
        )

    def make_wait_after_ared(self, addtl_delay: float = 0.0) -> TimedAction:
        delay = self.cfg.ared_duration_s + self.cfg.wait_after_ared_s + addtl_delay
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: time.sleep(self.cfg.wait_after_ared_s),
            label="wait_after_ared"
        )

    def make_shutter_opened(self, addtl_delay: float = 0.0) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s 
            + addtl_delay
        )
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.toggle_shutter(True),
            label="shutter_opened"
        )

    def make_agreen_on(self, voltage: float = 0.0, addtl_delay: float = 0.0) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + self.cfg.agreen_delay_s
            + addtl_delay
        )
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, voltage),
            label="agreen_on"
        )

    def make_agreen_off(self, addtl_delay: float = 0.002) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + addtl_delay
            + self.cfg.agreen_delay_s
            + self.cfg.agreen_duration_s
        )
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, 0),
            label="agreen_off"
        )

    def end_recording(self, addtl_delay: float = 0.002) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + addtl_delay
            + self.cfg.agreen_delay_s
            + self.cfg.agreen_duration_s
        )

        def signal_stop():
            self.stop_flag["stop"] = True

        return TimedAction(action_time_s=delay, action_fn=signal_stop, label="end_recording")
