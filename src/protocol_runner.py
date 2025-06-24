from src.io_controller import IOController
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig
from src.timed_action_factory import TimedActionFactory
import time
from src.constants import ANALOG_IN_CHANNEL, DELAY_BEFORE_RECORDING_START, LED_GREEN_PIN, LED_RED_PIN
from src.utils import calculate_samples_from_config, intensity_to_voltage, calculate_total_recording_length

class ProtocolRunner:
    def __init__(self, io: IOController, recorder: Recorder):
        self.io = io
        self.recorder = recorder

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

        # get the green measurement voltage from the intensity
        meas_green_voltage = intensity_to_voltage("green", cfg.measurement_led_intensity)
        actinic_red_voltage = intensity_to_voltage("red", cfg.actinic_led_intensity)
        print(f"meas_green_intensity: {cfg.measurement_led_intensity}, voltage: {meas_green_voltage}V")
        print(f"actinic_red_intensity: {cfg.actinic_led_intensity}, voltage: {actinic_red_voltage}V")

        # initialize the IOController
        logger = cfg.event_logger
        logger.start_event("protocol_start")
        self.io.open_device()
        self.io.set_led_voltage(LED_RED_PIN, 0)  # actinic channel off
        self.io.set_led_voltage(LED_GREEN_PIN, 0)  # measurement channel off
        self.io.toggle_shutter(False)

        # do a stupid event logger check of how long it takes to open and close the shutter
        logger.log_event("test_shutter_opening")
        self.io.toggle_shutter(True)
        logger.log_event("test_shutter_opened")
        self.io.toggle_shutter(False)
        logger.log_event("test_shutter_closed")

        # Log the start of the recording loop
        n_samples = calculate_samples_from_config(cfg)
        logger.log_event(f"total_recording_length: {calculate_total_recording_length(cfg):.3f} seconds")
        logger.log_event(f"recording_hz: {cfg.recording_hz}")
        logger.log_event(f"n_samples_calculated: {n_samples}")

        # set up the actions that will be taken during recording
        if factory is None:
            # If no factory is provided, create a new one
            logger.log_event("creating_timed_action_factory")
            stop_flag = {"stop": False}
            factory = TimedActionFactory(self.io, cfg, stop_flag)
        else:
            logger.log_event("using_existing_timed_action_factory")

        actions = [
            factory.make_ared_on(voltage=actinic_red_voltage),
            factory.make_ared_off(),
            factory.make_wait_after_ared(),
            factory.make_shutter_opened(),
            factory.make_agreen_on(voltage=meas_green_voltage),
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

        # Record and apply timed actions
        samples, n, lost, corrupted, debug_messages = self.recorder.complete_recording(actions=actions, stop_flag=stop_flag, debug=debug)

        # Close shutter
        self.io.toggle_shutter(False)
        logger.log_event("shutter_closed_after_recording")

        # Log the completion of the protocol
        logger.log_event("protocol_complete")

        # we need to get the action_ared_on_executed_at_+0.000_s, as that is when data is important
        data_start_time = logger.get_event_time(
            "action_ared_on_executed_at_+0.000_s"
        )
        self.recorder.save_data(samples, cfg.recording_hz, data_start_time, cfg.filename)

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
