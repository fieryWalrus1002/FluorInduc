from src.io_controller import IOController
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig
import time


class ProtocolRunner:
    def __init__(self, io: IOController, recorder: Recorder):
        self.io = io
        self.recorder = recorder

    @staticmethod
    def calculate_sample_number_for_action(action_time, hz_acq=1000000):
        """
        Calculate the sample number for a given action time based on the acquisition frequency.
        :param action_time: Time in seconds when the action should be executed.
        :param hz_acq: Acquisition frequency in Hz.
        :return: Sample number corresponding to the action time.
        """
        return int(action_time * hz_acq)

    def run_protocol(self, cfg: ExperimentConfig):
        """
            Runs the revised LED + shutter + recording protocol with specified timing.
            All durations are in milliseconds.
            
            The protocol steps are as follows: 
            1	Pre-set intensity of Mgreen and Ared without switching them on.
            2	Shutter close (if it is not closed already)
            3	Ared on for X ms (range 1 to 3,000 ms)
            4	A red off
            5	Variable wait time (range 1 to 10,000 ms)
            6	Open shutter
            7	< turn on recording>
            8	Wait 2 ms.
            9	Agreen on for X ms (from 100 to 10,000 ms) <- still recording
            10	<turn off recording>
            11	Close shutter
            12	Turn off Agreen
        """

        # step 1: pre set the parameters for the recording and voltages
        self.io.open_device()

        green_trigger_point = self.calculate_sample_number_for_action(cfg.agreen_delay_s, cfg.recording_hz)
        print(f"Green trigger point (sample number): {green_trigger_point}")
        print(f"Recording length in samples: {cfg.recording_length_s * cfg.recording_hz}")

        # set up the actions that will be taken during recording
        actions = [
            (
                green_trigger_point,  # the acquisition number for Agreen ON
                lambda: self.io.set_led_intensity("green", cfg.measurement_led_intensity),  # the action to turn Agreen ON
            ),  # Step 9: Agreen ON
        ]

        n_samples = int(cfg.recording_hz * cfg.recording_length_s)

        # Set LEDs OFF
        self.io.set_led_intensity("red", 0)  # actinic channel off
        self.io.set_led_intensity("green", 0)  # measurement channel off

        # step 2: Close shutter if not already closed
        self.io.toggle_shutter(False)

        # step 3: Ared ON for specified duration
        self.io.set_led_intensity("red", cfg.actinic_led_intensity)
        time.sleep(cfg.ared_duration_s)

        # step 4: Ared OFF
        self.io.set_led_intensity("red", 0)

        # step 5: Wait for specified duration
        time.sleep(cfg.wait_after_ared_s)

        # step 6: Open shutter
        self.io.toggle_shutter(True)

        # step 7: Start recording
        # steps 8, 9, 10 are handled in the actions list above, during the recording process
        samples, count, lost, corrupted = self.recorder.record(
            channel=0, n_samples=n_samples, hz_acq=cfg.recording_hz, channel_range=cfg.channel_range, actions=actions
        )

        # step 11: Close shutter
        self.io.toggle_shutter(False)

        # step 12: Turn off Agreen
        self.io.set_led_intensity("green", 0)

        self.recorder.save_data(samples, cfg.recording_hz, cfg.filename)

        self.save_metadata(cfg)

        self.io.close_device()

        return f"Protocol completed successfully, saving data to CSV: {cfg.filename}"

    def make_json_filename(self, csv_filename):
        metadata_filename = csv_filename.replace(".csv", "_metadata.json")
        return metadata_filename

    def save_metadata(self, cfg: ExperimentConfig):
        """        Save metadata about the experiment to a file.
        :param cfg: Experiment configuration containing metadata.
        """
        # use the ExperimentConfig's to_json method to get the metadata or maybe ... its
        # #adataclass so does it have that ability already?

        metadata = cfg.to_dict()
        metadata_filename = self.make_json_filename(cfg.filename)

        with open(metadata_filename, "w") as f:
            f.write(cfg.to_json())
