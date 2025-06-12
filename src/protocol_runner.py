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

    @staticmethod
    def calculate_samples_from_config(cfg: ExperimentConfig):
        """

        Calculate the number of samples to record based on the configuration.
        :param cfg: ExperimentConfig object containing recording parameters.
        :return: Number of samples to record.

        # we need to take into account a few factors:
        - The requested recording length in seconds from the user
        - the length of various periods that aren't assumed by the user to be part of the recording,
            such as the time it takes to open the shutter, turn on the LEDs, etc.
            These are not part of the recording length in seconds that the user specifies,
        but are part of the period that we have to measure in order to ensure the timing is correct.
        - The recording frequency in Hz, which determines how many samples we will record per second.

        So the user thinks that they are recording the following:
        - start recording, will record for cfg.recording_length_s seconds
        - for the first cfg.agreen_delay_s seconds, the Agreen LED is off
        - then at cfg.agreen_delay_s seconds, the Agreen LED is turned on
        - it stays on for cfg.agreen_duration_s seconds, which might be longer than the recording length?!?
        - so we need to check that the recording length is long enough to cover the Agreen ON period
        """
        # Calculate the total recording length in seconds
        if (cfg.agreen_duration_s + cfg.agreen_delay_s) > cfg.recording_length_s:
            raise ValueError(
                "The Agreen LED duration plus delay exceeds the recording length. "
                "Please adjust the recording length or the Agreen LED parameters."
            )
    
        total_recording_length = cfg.wait_after_ared_s + cfg.recording_length_s

        # Calculate the number of samples based on the recording frequency
        n_samples = int(total_recording_length * cfg.recording_hz)

        # Ensure we have at least 1 sample to record
        return max(n_samples, 1)

    def run_protocol(self, cfg: ExperimentConfig):
        """
        Runs the revised LED + shutter + recording protocol with specified timing.
        All durations are in milliseconds.

        The protocol steps are as follows:
        - set LED voltages to 0 (pre-set)
        - set shutter to closed (pre-set)
        - prepare the recorder
        - wait for the recorder to be ready
        - turn on the actinic LED, "ared_on"
        - wait for the actinic LED to be on for a specified duration
        - begin recording
        - turn off the actinic LED, "ared_off"
        - open the shutter, "shutter_opened"
        - wait for green_delay_s
        - turn on the Agreen LED, "agreen_on"
        - wait for the Agreen LED to be on for a specified duration
        - turn off the Agreen LED, "agreen_off"
        - close the shutter, "shutter_closed"

        """

        # initialize the IOController
        logger = cfg.event_logger
        logger.start_event("protocol_start")
        self.io.open_device()
        self.io.set_led_intensity("red", 0)  # actinic channel off
        self.io.set_led_intensity("green", 0)  # measurement channel off
        self.io.toggle_shutter(False)

        n_samples = self.calculate_samples_from_config(cfg)

        # set up the actions that will be taken during recording
        # Calculate the sample numbers for the actions based on the recording frequency
        # As checking the time in the loop is not accurate enough, we will use sample numbers
        # and then record the time of the action in the event logger to verify the timing
        ared_off_sample = 0
        wait_after_ared_sample = int(cfg.wait_after_ared_s * cfg.recording_hz)
        shutter_open_sample = wait_after_ared_sample + int(0.002 * cfg.recording_hz)
        agreen_on_sample = shutter_open_sample + int(cfg.agreen_delay_s * cfg.recording_hz)

        actions = [
            (ared_off_sample,
            lambda: self.io.set_led_intensity("red", 0),
            "ared_off"),
            
            (wait_after_ared_sample,
            lambda: time.sleep(cfg.wait_after_ared_s),
            "wait_after_ared"),
            
            (shutter_open_sample,
            lambda: self.io.toggle_shutter(True),
            "shutter_opened"),
            
            (agreen_on_sample,
            lambda: self.io.set_led_intensity("green", cfg.measurement_led_intensity),
            "agreen_on"),
        ]

        # Prepare recording now that we know how many samples we will record
        logger.log_event("preparing_recorder")
        self.recorder.prepare_recording(
            logger=logger,
            channel=0,
            n_samples=n_samples,
            hz_acq=cfg.recording_hz,
            channel_range=cfg.channel_range,
        )
        logger.log_event("recorder_prepared")

        # Wait for hardware to begin acquisition, this is important to ensure the recorder is ready
        # We won't actually start recording until we call complete_recording,
        # but we need to wait for the hardware to be ready to start recording
        self.recorder.wait_for_data_start()
        logger.log_event("recorder_wait_for_data_start_complete")

        # turn on the actinic LED. We'll switch it off after the recording starts
        logger.log_event("ared_on")
        self.io.set_led_intensity("red", cfg.actinic_led_intensity)
        time.sleep(cfg.ared_duration_s)

        # Record and apply timed actions
        samples, count, lost, corrupted = self.recorder.complete_recording(actions=actions)

        # Close shutter
        self.io.toggle_shutter(False)
        logger.log_event("shutter_closed_after_recording")

        # Turn off Agreen, after recording is complete
        self.io.set_led_intensity("green", 0)
        logger.log_event("agreen_off_after_recording")

        # Log the completion of the protocol
        logger.log_event("protocol_complete")
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
