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
        self._stop_event = threading.Event()
        self.io = IOController()  # Initialize the IOController

    def run_task(self, cfg: ExperimentConfig):
        self.io.open_device()
        runner = ProtocolRunner(self.io, Recorder(self.io))
        runner.run_protocol(cfg)
    
    def cancel_task(self):
        """Signal the task to stop."""
        print("IOController: Cancellation requested.")
        self._stop_event.set()

    def cleanup(self):
        """Cleanup and release the device."""
        self.io.close_device()




if __name__ == "__main__":
    print("Starting WebApiController...")
    controller = WebApiController()
