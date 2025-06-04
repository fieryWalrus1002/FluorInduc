from src.io_controller import IOController
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig

class ProtocolRunner:
    def __init__(self, io: IOController, recorder: Recorder):
        self.io = io
        self.recorder = recorder

    def run_protocol(self, cfg: ExperimentConfig):
        # logic from old run_protocol(), adapted to cleanly call io.set_led_with_analog_voltage(), etc.
        self.io.open_device()
        self.io.set_led_voltage(self.io.act_led_pin, cfg.actinic_led_intensity)
        self.io.set_led_voltage(self.io.meas_led_pin, cfg.measurement_led_intensity)

    # def run_protocol(self, ExperimentConfig: ExperimentConfig):
    #     """
    #     Runs the revised LED + shutter + recording protocol with specified timing.
    #     All durations are in milliseconds.
    #     """
    #     # Convert to seconds for timing logic
    #     ared_duration = ared_duration_ms / 1000.0
    #     wait_after_ared = wait_after_ared_ms / 1000.0
    #     agreen_duration = agreen_duration_ms / 1000.0

    #     # Set intensities — these voltages can be adjusted per your calibration
    #     v_ared = self.get_voltage_from_intensity(80)
    #     v_agreen = controller.get_voltage_from_intensity(60)
    #     controller.open_device()

    #     print("[Protocol] Step 1: Set Mgreen and Ared intensities (no output)")
    #     controller.set_led_voltage(0, 0)  # actinic channel off
    #     controller.set_led_voltage(1, 0)  # measurement channel off

    #     print("[Protocol] Step 2: Ensure shutter is closed")
    #     controller.toggle_shutter(False)

    #     print("[Protocol] Step 3: Ared ON")
    #     controller.set_led_voltage(0, v_ared)
    #     time.sleep(ared_duration)

    #     print("[Protocol] Step 4: Ared OFF")
    #     controller.set_led_voltage(0, 0)

    #     print(f"[Protocol] Step 5: Wait {wait_after_ared_ms} ms")
    #     time.sleep(wait_after_ared)

    #     print("[Protocol] Step 6: Open shutter")
    #     controller.toggle_shutter(True)

    #     print("[Protocol] Step 7: Start recording + Step 8: Wait 2 ms")
    #     actions = [
    #         (
    #             0.002,
    #             lambda: controller.set_led_voltage(1, v_agreen),
    #         ),  # Step 9: Agreen ON
    #         (
    #             0.002 + agreen_duration,
    #             lambda: controller.set_led_voltage(1, 0),
    #         ),  # Step 12: Agreen OFF
    #         (
    #             0.002 + agreen_duration,
    #             lambda: controller.toggle_shutter(False),
    #         ),  # Step 11: Close shutter
    #     ]

    #     total_duration = 0.002 + agreen_duration + 0.01  # Add 10 ms padding
    #     n_samples = int(hz_acq * total_duration)

    #     samples, count, lost, corrupted = recorder.record(
    #         channel=0, n_samples=n_samples, hz_acq=hz_acq, range=2, actions=actions
    #     )

    #     print("[Protocol] Step 10: Recording completed.")
    #     controller.close_device()
    #     return samples, count, lost, corrupted
