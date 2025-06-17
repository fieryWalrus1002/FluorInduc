from src.timed_action import TimedAction
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.event_logger import EventLogger
import time

class TimedActionFactory:
    """
    Factory class to create the timed actions used in the protocol. This class encapsulates
    the logic for creating actions that control the LED voltages and shutter states based on
    the provided configuration.

    time zero is "recording_loop_started", which is the time when the recording starts. All
    other times are relative to this point

    """

    def __init__(self, io: IOController, cfg: ExperimentConfig):
        self.io = io
        self.cfg = cfg

    def make_ared_off(self) -> TimedAction:
        return TimedAction(0.0, lambda: self.io.set_led_voltage(0, 0), "ared_off")

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
        time_s = self.cfg.wait_after_ared_s + 0.002  # same as shutter open time
        if voltage < 0 or voltage > 5:
            raise ValueError("Voltage must be between 0 and 5V")
        return TimedAction(
            time_s,
            lambda: self.io.set_led_voltage(1, voltage),
            "agreen_on",
        )
