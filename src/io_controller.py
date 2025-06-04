from ctypes import *
from src import dwfconstants
import time
import sys
from src.recorder import Recorder
from src.experiment_config import ExperimentConfig
import threading

# Uniblitz Model VMM-D1 shutter controller
# Unit state:
# Control mode set to remote
# Shutter mode set to N.O. (normally open)
"""
Device Lifecycle:
    open_device()  # Load DWF library, open device, set up pins
    close_device()  # Reset digital output, close device
    cleanup()  # Close device and clear stop event
    cancel_task()  # Signal the task to stop
    
Hardware I/O:
    set_pin(pin, value)  # Set a digital output pin to a specific value (0 or 1)
    toggle_shutter(state)  # Toggle the shutter state (open/close)
    set_led_voltage(led_number, value)  # Set analog output voltage for a specific LED
    get_voltage_from_intensity(intensity)  # Convert intensity percentage to voltage
    print_io_status()  # Print the status of digital I/O pins

Recording:
    record_and_save(channel, n_samples, hz_acq=100000, filename="record_1.csv")  # Record data and save to file
"""

class IOController:
    def __init__(self):
        self._stop_event = threading.Event()
        self.hwdf = None # self.dwfdevice handle, set during open_device
        self.dwf = None  # DWF library handle, set during open_device
        # Initialize system clock and pins
        self.hzSys = c_double()
        self.act_led_pin = 0 # analog out w1
        self.meas_led_pin = 1 # analog out w2
        self.pin_gate = 2
        self.pin_trigger = 3

        self.pin_mask = 0xFF  # Set all pins to output (0b11111111)
        self.pin_state = 0x00  # Initialize pin state to all low (0b00000000)
        self.output_mask = 0xFF  # Set all pins to output (0b11111111)

        # the channel we measure the signal from the analog out
        self.signal_channel = 0

        # self.open_device()  # Automatically open the device on initialization

    @staticmethod
    def intensity_to_voltage(intensity: int) -> float:
        return 5.0 * max(0, min(100, intensity)) / 100.0

    def open_device(self):
        if self.hwdf:
            print("Device already opened.")
            return

        # Load the DWF library
        if sys.platform.startswith("win"):
            self.dwf = cdll.dwf
        elif sys.platform.startswith("darwin"):
            self.dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        else:
            self.dwf = cdll.LoadLibrary("libdwf.so")

        if self.dwf == None:
            raise RuntimeError("Failed to load DWF library. Ensure it is installed correctly.")

        version = create_string_buffer(16)
        self.dwf.FDwfGetVersion(version)
        print("DWF Version: " + str(version.value))

        # Open the device
        print("Opening first device")
        self.hdwf = c_int()
        self.dwf.FDwfDeviceOpen(c_int(-1), byref(self.hdwf))

        if self.hdwf.value == 0:
            print("Failed to open device")
            szerr = create_string_buffer(512)
            self.dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            self.hdwf = None
            raise RuntimeError("Failed to open device")

        # set up the clock frequency
        self.dwf.FDwfDigitalOutInternalClockInfo(self.hdwf, byref(self.hzSys))

        # # Enable pins for output
        self.dwf.FDwfDigitalIOOutputEnableSet(self.hdwf, c_int(self.pin_mask), c_int(self.output_mask))

        # ensure that the trigger pin is set to high to begin with
        self.set_pin(self.pin_trigger, 1)

    def close_device(self):
        """Close the device properly."""
        if self.hdwf:
            print("Closing device...")
            self.dwf.FDwfDigitalOutReset(self.hdwf)

            self.dwf.FDwfDeviceCloseAll()
            self.hdwf = None
            print("Device closed.")

            self._stop_event.clear()  # Clear the stop event to allow for future tasks
        else:
            print("Device is not open. Nothing to close.")

    def print_io_status(self):
        """
                FDwfDigitalIOStatus(HDWF hdwf)
        Description: Reads the status and input values, of the device DigitalIO to the PC. The status and values are
        accessed from the FDwfDigitalIOInputStatus function.
        Parameters:
        - hdwf – Open interface handle on a device.
        
        Then we use FDwfDigitalIOInputStatus to read the status of the digital I/O pins.
        and print the status of the pins.
        """
        dwRead = c_uint32()

        # fetch digital IO information from the device
        self.dwf.FDwfDigitalIOStatus(self.hdwf)

        # read state of all pins, regardless of output enable
        self.dwf.FDwfDigitalIOInputStatus(self.hdwf, byref(dwRead))

        # print(dwRead as bitfield (32 digits, removing 0b at the front)
        print("Digital IO Pins: ", bin(dwRead.value)[2:].zfill(16))

    def set_pin(self, pin, value):
        """
        Set a digital output pin to a specific value (0 or 1), preserving all other pin states.
        """
        if value:
            self.pin_state |= 1 << pin  # Set the pin high
        else:
            self.pin_state &= ~(1 << pin)  # Set the pin low

        self.dwf.FDwfDigitalIOOutputSet(self.hdwf, c_int(self.pin_state))
        # time.sleep(0.1)  # Optional short delay for hardware settling

    def toggle_shutter(self, state=True):
        if state:
            self.set_pin(self.pin_gate, 1)
            self.set_pin(self.pin_trigger, 0)
        else:
            self.set_pin(self.pin_trigger, 1)
            self.set_pin(self.pin_gate, 0)

    def set_led_voltage(self, led_number, value):
        """
        Set the analog output voltage for a specific LED.
        Parameters:
        - led_number: The LED number (0-1) for the w1 and w2 pins.
        - value: The voltage value to set (0-5V).
        Raises:
        - ValueError: If the LED number is not between 0 and 5, or if the value is not between 0 and 5.
        - TypeError: If the led_number is not an integer.
        """

        led_int = int(led_number)
        if led_int < 0 or led_int > 5:
            raise ValueError("LED number must be between 0 and 5.")

        # Set the analog output to the modulation value
        self.dwf.FDwfAnalogOutNodeEnableSet(
            self.hdwf, led_int, dwfconstants.AnalogOutNodeCarrier, c_bool(True)
        )
        self.dwf.FDwfAnalogOutIdleSet(
            self.hdwf, led_int, dwfconstants.DwfAnalogOutIdleOffset
        )
        self.dwf.FDwfAnalogOutNodeFunctionSet(
            self.hdwf,
            led_int,
            dwfconstants.AnalogOutNodeCarrier,
            dwfconstants.funcSquare,
        )

        self.dwf.FDwfAnalogOutNodeFrequencySet(
            self.hdwf,
            led_int,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(0),
        )  # low frequency
        self.dwf.FDwfAnalogOutNodeAmplitudeSet(
            self.hdwf,
            led_int,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(value),
        )
        self.dwf.FDwfAnalogOutNodeOffsetSet(
            self.hdwf,
            led_int,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(0),
        )
        self.dwf.FDwfAnalogOutWaitSet(self.hdwf, led_int, c_double(0))  # wait length
        self.dwf.FDwfAnalogOutRepeatSet(self.hdwf, led_int, c_int(1))  # repeat once

        self.dwf.FDwfAnalogOutConfigure(self.hdwf, led_int, c_bool(True))

    # Should this take a Recorder instance as an argument? It would get it from the ProtocolRunner.
    # and do we need the various parameters like hz_acq, n_samples, etc.?
    # or can we just send in the ExperimentConfig object?
    def record_and_save(
        self, channel, n_samples, hz_acq=100000, filename="record_1.csv"
    ):
        """
        Test the recording functionality using the Recorder class.
        
        Parameters:
        - channel: The channel to record from.
        - n_samples: The number of samples to record.
        - hz_acq: The acquisition frequency in Hz.
        - filename: The name of the file to save the recorded data.
        """
        recorder = Recorder(self)  # Pass the IOController instance to the Recorder

        recorder.record_and_save(channel, n_samples, hz_acq, filename)

    # def recording_task(
    #     self,
    #     cfg: ExperimentConfig = ExperimentConfig(),
    # ):
    #     """Perform a task with periodic checks for cancellation."""

    #     print(cfg)

    #     act_voltage = self.intensity_to_voltage(cfg.actinic_led_intensity)
    #     meas_voltage = self.intensity_to_voltage(cfg.measurement_led_intensity)
    #     channel = self.signal_channel  # Use the signal channel for recording
    #     n_samples = (cfg.recording_length + 1) * cfg.recording_hz

    #     self.open_device()
    #     self._stop_event.clear()  # Ensure the stop event is reset
    #     print("IOController: Task started.")

    #     # turn on the measuring LED and the actinic LED
    #     self.set_led_voltage(self.meas_led_pin, meas_voltage)
    #     self.set_led_voltage(self.act_led_pin, act_voltage)
    #     self.toggle_shutter(cfg.shutter_state)

    #     self.record_and_save(
    #         channel, n_samples, hz_acq=cfg.recording_hz, filename=cfg.filename
    #     )

    #     self.toggle_shutter(False)

    #     print("IOController: Task completed.")
    #     self.close_device()
    #     return "Task Completed"

    def cancel_task(self):
        """Signal the task to stop."""
        print("IOController: Cancellation requested.")
        self._stop_event.set()

    def cleanup(self):
        """Cleanup and release the device."""
        self.close_device()


if __name__ == "__main__":
    print("Starting controller")
