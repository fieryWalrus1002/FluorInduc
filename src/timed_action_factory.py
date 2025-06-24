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

    time zero is "recording_loop_started", which is the time when the recording starts. All
    other times are relative to this point

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

    def make_ared_off(self) -> TimedAction:
        return TimedAction(
            action_time_s=self.cfg.ared_duration_s,
            action_fn=lambda: self.io.set_led_voltage(LED_RED_PIN, 0),
            label="ared_off"
        )

    def make_wait_after_ared(self) -> TimedAction:
        delay = self.cfg.ared_duration_s + self.cfg.wait_after_ared_s
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: time.sleep(self.cfg.wait_after_ared_s),
            label="wait_after_ared"
        )

    def make_shutter_opened(self) -> TimedAction:
        delay = self.cfg.ared_duration_s + self.cfg.wait_after_ared_s
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.toggle_shutter(True),
            label="shutter_opened"
        )

    def make_agreen_on(self, voltage: float = 0.0, delay_from_shutter_open: float = 0.002) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + delay_from_shutter_open
            + self.cfg.agreen_delay_s
        )
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, voltage),
            label="agreen_on"
        )

    def make_agreen_off(self, delay_from_shutter_open: float = 0.002) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + delay_from_shutter_open
            + self.cfg.agreen_delay_s
            + self.cfg.agreen_duration_s
        )
        return TimedAction(
            action_time_s=delay,
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, 0),
            label="agreen_off"
        )

    def end_recording(self, delay_from_shutter_open: float = 0.002) -> TimedAction:
        delay = (
            self.cfg.ared_duration_s
            + self.cfg.wait_after_ared_s
            + delay_from_shutter_open
            + self.cfg.agreen_delay_s
            + self.cfg.agreen_duration_s
        )

        def signal_stop():
            self.stop_flag["stop"] = True

        return TimedAction(action_time_s=delay, action_fn=signal_stop, label="end_recording")
