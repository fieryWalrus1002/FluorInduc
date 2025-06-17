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

    def make_ared_off(self) -> TimedAction:
        return TimedAction(0.0, lambda: self.io.set_led_voltage(LED_RED_PIN, 0), "ared_off")

    def make_wait_after_ared(self) -> TimedAction:
        return TimedAction(
            self.cfg.wait_after_ared_s,
            lambda: time.sleep(self.cfg.wait_after_ared_s),
            "wait_after_ared",
        )

    def make_shutter_opened(self) -> TimedAction:
        time_s = self.cfg.wait_after_ared_s  # fixed 2ms after wait
        return TimedAction(
            time_s, lambda: self.io.toggle_shutter(True), "shutter_opened"
        )

    def make_agreen_on(
        self, voltage: float = 0.0, delay_from_shutter_open: float = 0.0
    ) -> TimedAction:
        time_s = self.cfg.wait_after_ared_s + 0.002  # just after shutter opened
        if voltage < 0 or voltage > 5:
            raise ValueError("Voltage must be between 0 and 5V")
        return TimedAction(
            time_s,
            lambda: self.io.set_led_voltage(LED_GREEN_PIN, voltage),
            "agreen_on",
        )

    def make_agreen_off(self) -> TimedAction:
        time_s = self.cfg.wait_after_ared_s + 0.002 + self.cfg.agreen_duration_s
        if time_s < 0:
            raise ValueError("Time for Agreen off must be non-negative")
        if time_s > 10:
            raise ValueError("Time for Agreen off must be less than 10 seconds")
        return TimedAction(
            time_s, lambda: self.io.set_led_voltage(LED_GREEN_PIN, 0), "agreen_off"
        )

    def end_recording(self) -> TimedAction:
        time_s = self.cfg.wait_after_ared_s + 0.002 + self.cfg.agreen_duration_s
        if time_s < 0:
            raise ValueError("Time for end recording must be non-negative")
        if time_s > 10:
            raise ValueError("Time for end recording must be less than 10 seconds")

        def signal_stop():
            self.stop_flag["stop"] = True

        return TimedAction(time_s, signal_stop, "end_recording")