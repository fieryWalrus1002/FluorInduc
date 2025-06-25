from ctypes import *
from src import dwfconstants
import time
import sys
from src.recorder import Recorder
from src.io_controller import IOController
from src.experiment_config import ExperimentConfig
from src.protocol_runner import ProtocolRunner
import threading

# Handles the web API, and delegates tasks to the IOController, Recorder, and ExperimentConfig.

class WebApiController:
    def __init__(self):
        self.io = IOController()  # Initialize the IOController

    def run_task(self, cfg: ExperimentConfig):
        try:
            self.io.open_device()
            runner = ProtocolRunner(self.io)
            result = runner.run_protocol(cfg)
            self.cleanup()
            return result
        except Exception as e:
            self.cleanup()
            return f"An error occurred: {str(e)}"

    def cancel_task(self):
        """Signal the task to stop."""
        self.io._stop_event.set()

    def cleanup(self):
        """Cleanup and release the device."""
        self.io.cleanup()
        print("Cleanup complete. Device released.")


if __name__ == "__main__":
    print("Starting WebApiController...")
    controller = WebApiController()
