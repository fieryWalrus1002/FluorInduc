from src.timed_action import TimedAction
from src.experiment_config import ExperimentConfig
from src.io_controller import IOController
from src.event_logger import EventLogger
import time
from src.constants import LED_RED_PIN, LED_GREEN_PIN, END_RECORDING_OFFSET_DELAY


class TimedActionFactory:
    """
    Factory class to create TimedAction instances for a fluorescence protocol,
    where each action (e.g., turning on LEDs, opening shutter) is scheduled relative to a common time zero.

    - "t_zero" is defined as the time the "ared_on" action is executed.
    - All subsequent actions are scheduled relative to this t_zero using action_time_s values.

    This class:
      - Uses the experiment configuration (`ExperimentConfig`) for base durations.
      - Accepts optional `delay_overrides`, allowing fine-grained adjustment of the protocol timing.
      - Propagates delays cumulatively: if one step is delayed, all downstream steps shift accordingly.
      - Constructs a `timeline` dictionary mapping each label to its scheduled execution time.

    Example Timing Schedule (relative to t_zero):

        ared_on         → t_zero + 0.000
        ared_off        → t_zero + ared_duration_s + delay("ared_off")
        wait_after_ared → ared_off_time + wait_after_ared_s + delay("wait_after_ared")
        shutter_opened  → wait_after_ared_time + delay("shutter_opened")
        agreen_on       → shutter_opened_time + agreen_delay_s + delay("agreen_on")
        agreen_off      → agreen_on_time + agreen_duration_s + delay("agreen_off")
        end_recording   → agreen_off_time + END_RECORDING_OFFSET_DELAY + delay("end_recording")

    Each `make_*()` method returns a TimedAction scheduled at the appropriate time.
    The Recorder is responsible for executing actions when their scheduled time (relative to t_zero) is reached.
    """


    def __init__(
        self,
        io: IOController,
        cfg: ExperimentConfig,
        stop_flag: dict = None,
        delay_overrides: dict = None,
    ):
        self.io = io
        self.cfg = cfg
        self.stop_flag = stop_flag or {"stop": False}
        self.delay_overrides = delay_overrides or {}
        self.timeline = {}
        self._build_base_timeline()

    # def _expand_composite_delays(self, original):
    #     """
    #     Converts composite interval overrides (like 'delay_after_ared') into
    #     overrides for the specific TimedAction labels that implement those intervals.
    #     """
    #     out = dict(original)  # copy to avoid mutating caller's dict

    #     # If the user provides a "delay_after_ared" override, apply it to "ared_off" or "agreen_on" depending on your convention
    #     if "delay_after_ared" in original:
    #         delta = original["delay_after_ared"]

    #         # Option 1: Adjust agreen_on to include the composite delay
    #         out["agreen_on"] = out.get("agreen_on", 0.0) + delta

    #         # Option 2 (less preferred): Split delay over both ared_off and agreen_on
    #         # out["ared_off"] = out.get("ared_off", 0.0) - delta / 2
    #         # out["agreen_on"] = out.get("agreen_on", 0.0) + delta / 2

    #         del out["delay_after_ared"]  # don't pass unknown label to other parts

    #     return out

    def _build_base_timeline(self):
        cfg = self.cfg
        d = lambda k: self.delay_overrides.get(k, 0.0)

        self.timeline["ared_on"] = 0.0

        self.timeline["ared_off"] = (
            self.timeline["ared_on"] + cfg.ared_duration_s + d("ared_off")
        )

        self.timeline["wait_after_ared"] = (
            self.timeline["ared_off"] + cfg.wait_after_ared_s + d("wait_after_ared")
        )

        self.timeline["shutter_opened"] = self.timeline["wait_after_ared"] + d(
            "shutter_opened"
        )

        self.timeline["agreen_on"] = (
            self.timeline["shutter_opened"] + cfg.agreen_delay_s + d("agreen_on")
        )

        self.timeline["agreen_off"] = (
            self.timeline["agreen_on"] + cfg.agreen_duration_s + d("agreen_off")
        )

        self.timeline["end_recording"] = (
            self.timeline["agreen_off"] + END_RECORDING_OFFSET_DELAY + d("end_recording")
        )

    def _get_delay(self, label: str, default: float = 0.0) -> float:
        return self.delay_overrides.get(label, default)

    def make_ared_on(self, voltage: float) -> TimedAction:
        return TimedAction(
            action_time_s=self.timeline["ared_on"],
            action_fn=lambda: self.io.set_led_voltage(LED_RED_PIN, voltage),
            label="ared_on",    
            epsilon=self.cfg.action_epsilon_s,
        )

    def make_ared_off(self) -> TimedAction:
        return TimedAction(
            action_time_s=self.timeline["ared_off"],
            action_fn=lambda: self.io.set_led_voltage(LED_RED_PIN, 0),
            label="ared_off",
            epsilon=self.cfg.action_epsilon_s
        )

    def make_wait_after_ared(self) -> TimedAction:
        return TimedAction(
            action_time_s=self.timeline["wait_after_ared"],
            action_fn=lambda: time.sleep(self.cfg.wait_after_ared_s),
            label="wait_after_ared",
            epsilon=self.cfg.action_epsilon_s
        )

    def make_shutter_opened(self) -> TimedAction:
        def shutter_open():
            start = time.perf_counter()
            self.io.toggle_shutter(True)
            end = time.perf_counter()
            print(f"[DEBUG] Shutter open took {(end - start)*1000:.3f} ms")

        return TimedAction(
            action_time_s=self.timeline["shutter_opened"],
            action_fn=shutter_open,
            label="shutter_opened",
            epsilon=self.cfg.action_epsilon_s
        )

    def make_agreen_on(self, voltage: float = 0.0) -> TimedAction:
        return TimedAction(
            action_time_s=self.timeline["agreen_on"],
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, voltage),
            label="agreen_on",
            epsilon=self.cfg.action_epsilon_s
        )

    def make_agreen_off(self) -> TimedAction:
        return TimedAction(
            action_time_s=self.timeline["agreen_off"],
            action_fn=lambda: self.io.set_led_voltage(LED_GREEN_PIN, 0),
            label="agreen_off",
            epsilon=self.cfg.action_epsilon_s
        )

    def end_recording(self) -> TimedAction:
        def signal_stop():
            self.stop_flag["stop"] = True

        return TimedAction(
            action_time_s=self.timeline["end_recording"],
            action_fn=signal_stop,
            label="end_recording",
            epsilon=self.cfg.action_epsilon_s
        )

    def print_timeline(self):
        """
        Print the scheduled execution times of all actions in the timeline
        for visual verification. Times are shown relative to t_zero.
        """
        print("\n--- Scheduled Action Timeline (relative to t_zero) ---")
        for label, time_s in sorted(self.timeline.items(), key=lambda item: item[1]):
            print(f"{label:<20} @ +{time_s:.6f} s")
        print("------------------------------------------------------\n")
