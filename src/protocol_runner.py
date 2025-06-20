from src.io_controller import IOController
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig
from src.timed_action_factory import TimedActionFactory
import time
from src.constants import ANALOG_IN_CHANNEL, DELAY_BEFORE_RECORDING_START


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

    def run_protocol(self, cfg: ExperimentConfig, factory: TimedActionFactory = None, debug: bool = False) -> str:
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

        # do a stupid event logger check of how long it takes to open and close the shutter
        logger.log_event("test_shutter_opening")
        self.io.toggle_shutter(True)
        logger.log_event("test_shutter_opened")
        self.io.toggle_shutter(False)
        logger.log_event("test_shutter_closed")

        n_samples = self.calculate_samples_from_config(cfg)

        # set up the actions that will be taken during recording
        if factory is None:
            # If no factory is provided, create a new one
            logger.log_event("creating_timed_action_factory")
            stop_flag = {"stop": False}
            factory = TimedActionFactory(self.io, cfg, stop_flag)
        else:
            logger.log_event("using_existing_timed_action_factory")

        actions = [
            factory.make_ared_off(),
            factory.make_wait_after_ared(),
            factory.make_shutter_opened(),
            factory.make_agreen_on(),
            factory.make_agreen_off(),
            factory.end_recording()
        ]

        # Prepare recording now that we know how many samples we will record
        logger.log_event("preparing_recorder")
        self.recorder.prepare_recording(
            logger=logger,
            channel=ANALOG_IN_CHANNEL,
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
        logger.log_event(f"ared_on_for_{cfg.ared_duration_s:.3f}_seconds")
        
        # wait for the actinic LED to be on for the specified duration
        time.sleep(
            cfg.ared_duration_s if cfg.ared_duration_s > 0 else 0
        )  # wait for the actinic LED to be on for the specified duration

        # Record and apply timed actions
        samples, n, lost, corrupted, debug_messages = self.recorder.complete_recording(actions=actions, stop_flag=stop_flag, debug=debug)

        # Close shutter
        self.io.toggle_shutter(False)
        logger.log_event("shutter_closed_after_recording")

        # Log the completion of the protocol
        logger.log_event("protocol_complete")

        # we need to get the recording_loop_started time to calculate the time of the actions
        recording_loop_started_time = logger.get_event_time("recording_loop_started")
        self.recorder.save_data(samples, cfg.recording_hz, recording_loop_started_time, cfg.filename)

        self.save_metadata(cfg)

        self.io.close_device()

        if debug:
            for message in debug_messages:
                print(message)

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
