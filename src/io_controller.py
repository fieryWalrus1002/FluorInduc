from ctypes import *
from src import dwfconstants
import time
import sys
from src.recorder import Recorder

import threading

# Uniblitz Model VMM-D1 shutter controller
# Unit state:
# Control mode set to remote
# Shutter mode set to N.O. (normally open)

class IOController:
    def __init__(self):
        self._stop_event = threading.Event()
        self.hwdf = None # device handle, set during open_device

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

        # Initialize system clock and pins
        self.hzSys = c_double()
        self.pin_measure_led = 0
        self.act_analog_out = 0
        self.pin_gate = 2
        self.pin_trigger = 3

        self.pin_mask = 0xFF  # Set all pins to output (0b11111111)
        self.pin_state = 0x00  # Initialize pin state to all low (0b00000000)
        self.output_mask = 0xFF  # Set all pins to output (0b11111111)

        # the channel we measure the signal from the analog out
        self.signal_channel = 0

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
        time.sleep(0.1)  # Optional short delay for hardware settling

    def toggle_measure_led(self, state):
        self.set_pin(self.pin_measure_led, state)

    def toggle_shutter(self, state=True):
        if state:
            self.set_pin(self.pin_gate, 1)
            self.set_pin(self.pin_trigger, 0)
        else:
            self.set_pin(self.pin_trigger, 1)
            self.set_pin(self.pin_gate, 0)

    def set_act_led(self, value):
        """
        # the device will be configured only when calling FDwfAnalogOutConfigure
        dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))

        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel, AnalogOutNodeCarrier, c_bool(True))
        dwf.FDwfAnalogOutIdleSet(hdwf, channel, DwfAnalogOutIdleOffset)
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel, AnalogOutNodeCarrier, funcSquare)
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel, AnalogOutNodeCarrier, c_double(0)) # low frequency
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel, AnalogOutNodeCarrier, c_double(3.3))
        dwf.FDwfAnalogOutNodeOffsetSet(hdwf, channel, AnalogOutNodeCarrier, c_double(0))
        dwf.FDwfAnalogOutRunSet(hdwf, channel, c_double(pulse)) # pulse length
        dwf.FDwfAnalogOutWaitSet(hdwf, channel, c_double(0)) # wait length
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel, c_int(1)) # repeat once

        print("Generating pulse")
        dwf.FDwfAnalogOutConfigure(hdwf, channel, c_bool(True))
        """
        # Set the analog output to the modulation value
        self.dwf.FDwfAnalogOutNodeEnableSet(
            self.hdwf, self.act_analog_out, dwfconstants.AnalogOutNodeCarrier, c_bool(True)
        )
        self.dwf.FDwfAnalogOutIdleSet(
            self.hdwf, self.act_analog_out, dwfconstants.DwfAnalogOutIdleOffset
        )
        self.dwf.FDwfAnalogOutNodeFunctionSet(
            self.hdwf,
            self.act_analog_out,
            dwfconstants.AnalogOutNodeCarrier,
            dwfconstants.funcSquare,
        )

        self.dwf.FDwfAnalogOutNodeFrequencySet(
            self.hdwf,
            self.act_analog_out,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(0),
        )  # low frequency
        self.dwf.FDwfAnalogOutNodeAmplitudeSet(
            self.hdwf,
            self.act_analog_out,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(value),
        )
        self.dwf.FDwfAnalogOutNodeOffsetSet(
            self.hdwf,
            self.act_analog_out,
            dwfconstants.AnalogOutNodeCarrier,
            c_double(0),
        )
        self.dwf.FDwfAnalogOutWaitSet(self.hdwf, self.act_analog_out, c_double(0)) # wait length
        self.dwf.FDwfAnalogOutRepeatSet(self.hdwf, self.act_analog_out, c_int(1)) # repeat once

        self.dwf.FDwfAnalogOutConfigure(self.hdwf, self.act_analog_out, c_bool(True))

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

    def run_task(self):
        """Perform a task with periodic checks for cancellation."""
        self.open_device()
        self._stop_event.clear()  # Ensure the stop event is reset
        print("IOController: Task started.")
        for i in range(10):

            if self._stop_event.is_set():
                print("IOController: Task canceled.")
                self.close_device()
                return "Task Canceled"

            print(f"IOController: Running step {i + 1}/10...")

            if i % 2 == 0:
                self.set_act_led(5.0)
            else:
                self.set_act_led(0.0)
                
            time.sleep(4)  # Simulate work (each step takes 4 seconds)

        print("IOController: Task completed.")
        self.close_device()
        return "Task Completed"

    def cancel_task(self):
        """Signal the task to stop."""
        print("IOController: Cancellation requested.")
        self._stop_event.set()

    def cleanup(self):
        """Cleanup and release the device."""
        self.close_device()

if __name__ == "__main__":
    print("Starting controller")
