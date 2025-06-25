from ctypes import *
import time
from src import dwfconstants
import numpy as np
from src.event_logger import EventLogger
from src.timed_action import TimedAction
import numpy as np
from numpy.ctypeslib import as_array
from src.constants import (
    ANALOG_IN_CHANNEL,
    ANALOG_TRIGGER_STATE,
    ANALOG_RECORD_FOREVER,)
from typing import Optional, Tuple


class Recorder:
    def __init__(self, controller):
        """
        Initialize the Recorder with a reference to the IOController.
        :param controller: An instance of the IOController class.
        """
        self.dwf = controller.dwf  # Reference to the DWF library
        self.hdwf = controller.hdwf  # Reference to the device handle
        self.logger = None
        self.channel = None
        self.n_samples = None
        self.hz_acq = None
        self.channel_range = None

    def prepare_recording(self, logger, channel, n_samples, hz_acq, channel_range):
        """
        Prepare the recording setup for the specified channel.
        :param logger: An instance of EventLogger for logging events.
        :param channel: The analog input channel to record from.
        :param n_samples: Number of samples to record.
        :param hz_acq: Acquisition frequency in Hz.
        :param channel_range: The range for the analog input channel in volts. Either 5 or 50.
        """
        self.logger = logger
        self.channel = channel
        self.n_samples = n_samples
        self.hz_acq = hz_acq
        self.channel_range = channel_range

        logger.log_event("setup_recording")

        # Declare ctype variables
        hzAcq = c_double(hz_acq)

        self.dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(channel), c_bool(True))
        self.dwf.FDwfAnalogInChannelRangeSet(
            self.hdwf, c_int(channel), c_double(channel_range)
        )
        self.dwf.FDwfAnalogInAcquisitionModeSet(self.hdwf, dwfconstants.acqmodeRecord)
        self.dwf.FDwfAnalogInFrequencySet(self.hdwf, hzAcq)
        self.dwf.FDwfAnalogInRecordLengthSet(self.hdwf, c_double(ANALOG_RECORD_FOREVER))

        hz_acq = c_double()
        self.dwf.FDwfAnalogInFrequencyGet(self.hdwf, byref(hz_acq))
        print(f"Confirmed acquisition frequency: {hz_acq.value}")

        channel_range = c_double()
        self.dwf.FDwfAnalogInChannelRangeGet(self.hdwf, c_int(self.channel), byref(channel_range))
        print(f"Channel {self.channel} range: {channel_range.value} V")

        self.dwf.FDwfAnalogInTriggerSourceSet(self.hdwf, c_int(ANALOG_TRIGGER_STATE))  # 0 = trigsrcNone
        self.dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))

    def flush_input_buffer(self):
        sts = c_byte()
        cAvailable = c_int()
        cLost = c_int()
        cCorrupted = c_int()

        self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))
        self.dwf.FDwfAnalogInStatusRecord(
            self.hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted)
        )
        if cAvailable.value > 0:
            dummy = (c_double * cAvailable.value)()
            self.dwf.FDwfAnalogInStatusData(
                self.hdwf, c_int(self.channel), dummy, cAvailable
            )

    def wait_for_data_start(self):
        """Wait until samples start flowing."""
        cAvailable = c_int()
        start_time = time.perf_counter()
        while True:
            sts = c_byte()
            self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))
            self.dwf.FDwfAnalogInStatusRecord(self.hdwf, byref(cAvailable), None, None)

            if cAvailable.value > 0:
                self.logger.log_event(f"data_available_at_sample_{cAvailable.value}")
                break
            time.sleep(0.005)

        return start_time

    def _execute_pending_actions(
        self,
        actions: list["TimedAction"],
        t_zero: Optional[float],
        start_time: float,
        hz_acq: int,
        data_index: Optional[int] = None,
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Check and execute any pending actions based on the current time.

        Returns:
        - t_zero: updated if initialized
        - dataIndex: sample index at which t_zero occurred
        """
        now = time.perf_counter()

        if t_zero is None and not any(a.label == "ared_on" and a.action_time_s == 0.0 for a in actions):
            raise RuntimeError("ared_on must be scheduled at 0.0s to initialize t_zero")

        if t_zero is None:
            for action in actions:
                if action.label == "ared_on" and action.action_time_s == 0.0:
                    if action.should_execute(now - start_time):  # this should be true nearly immediately
                        actual_time = action.execute(logger=self.logger, t_zero=None)
                        t_zero = actual_time
                        time_since_start = t_zero - start_time
                        data_index = int(time_since_start * hz_acq)
                        self.logger.log_event(
                            f"t_zero_initialized_from_actual_{action.label}_at_+{time_since_start:.6f}_s"
                        )
                    break  # Don't evaluate any other actions until t_zero is defined
        
        else:
            elapsed = now - t_zero
            for action in actions:
                if action.should_execute(elapsed):
                    action.execute(logger=self.logger, t_zero=t_zero)

        return t_zero, data_index            
            # else:
        #     t_action = now - t_zero

        # for action in actions:
        #     if action.should_execute(t_action):
        #         actual_time = action.execute(logger=self.logger, t_zero=t_zero)

        #         # we start our real timing at the ared_on action, so we set t_zero
        #         if t_zero is None and action.label == "ared_on":
        #             t_zero = actual_time
        #             time_since_start = t_zero - start_time
        #             if data_index is None:  # Only calculate once
        #                 data_index = int(time_since_start * hz_acq)
        #                 self.logger.log_event(
        #                     f"t_zero_initialized_from_actual_{action.label}_at_+{time_since_start:.6f}_s"
        #                 )
        # return t_zero, data_index

    def complete_recording(
        self, actions: list["TimedAction"] = None, stop_flag=None, debug=False
    ):
        """
        Complete the recording process and return the recorded data.
        :param actions: A list of TimedAction instances to execute during recording.
        :return: A tuple (rgdSamples, total_samples, lost_flag, corrupted_flag)
        """
        sts = c_byte()
        n_samples = self.n_samples
        max_total_samples = int(n_samples * 4)
        rgdSamples = (c_double * max_total_samples)()
        np_buffer = np.ctypeslib.as_array(rgdSamples)

        cAvailable = c_int()
        cLost = c_int()
        cSamples = 0
        cCorrupted = c_int()
        fLost = 0
        fCorrupted = 0
        loopCounter = 0

        # for tracking the time of the first action execution, and the first data point
        t_zero = None
        dataIndex = None

        debug_messages = []
        if stop_flag is None:
            stop_flag = {"stop": False}

        # clear the input buffer before starting
        self.logger.log_event("start_buffer_flush")
        self.dwf.FDwfAnalogInConfigure(self.hdwf, 0, 0)  # stop
        self.flush_input_buffer()
        self.dwf.FDwfAnalogInConfigure(self.hdwf, 0, 1)  # start cleanly

        # Wait for hardware to begin acquisition, this is important to ensure the recorder is ready
        # We won't actually start recording until we call complete_recording,
        # but we need to wait for the hardware to be ready to start recording
        start_time = self.wait_for_data_start()       
        self.logger.log_event(f"recording_loop_started_at_{start_time:.6f}")

        while not stop_flag.get("stop", False):
            self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))

            if debug and (loopCounter % 100 == 0 or loopCounter < 100):
                debug_messages.append(
                    f"{loopCounter}, {time.perf_counter() - start_time}, {cSamples}, {n_samples}"
                )

            loopCounter += 1

            self.dwf.FDwfAnalogInStatusRecord(
                self.hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted)
            )

            if cLost.value:
                fLost = 1
            if cCorrupted.value:
                fCorrupted = 1

            last_cSamples = cSamples
            cSamples += cLost.value  # Always account for lost samples

            if cAvailable.value == 0:
                continue
            remaining = n_samples - cSamples
            if remaining <= 0:
                self.logger.log_event("max_samples_reached")
                break
            cAvailable = c_int(min(cAvailable.value, remaining))

            self.dwf.FDwfAnalogInStatusData(
                self.hdwf,
                c_int(self.channel),
                byref(rgdSamples, sizeof(c_double) * cSamples),
                cAvailable,
            )
            
            if actions:
                updated_t_zero, updated_index = self._execute_pending_actions(
                    actions=actions, 
                    t_zero=t_zero, 
                    start_time=start_time, 
                    hz_acq=self.hz_acq, 
                    data_index=dataIndex
                )
                if t_zero is None and updated_t_zero is not None:
                    t_zero = updated_t_zero
                    dataIndex = updated_index

            cSamples += cAvailable.value

            # Sanity check for edge cases
            if np_buffer[cSamples - 1] == 0.0:
                debug_messages.append(
                    f"Warning: Last sample is 0.0 at index {cSamples - 1}. This may indicate an issue with the recording."
                )

            if cSamples > n_samples * 2:
                debug_messages.append("Overrun limit reached, forcing stop")
                break

        self.logger.log_event("recording_completed")

        # Final logging
        elapsed_time = time.perf_counter() - start_time

        if dataIndex is not None:
            trimmed, true_sample_count = self._trim_samples(rgdSamples, dataIndex)
        else:
            trimmed = rgdSamples[:cSamples]
            true_sample_count = self._get_true_sample_count(trimmed, cSamples, dataIndex)

        self.logger.log_event(f"acquired_{true_sample_count}_samples_in_{elapsed_time:.3f}_seconds")

        return trimmed, true_sample_count, fLost, fCorrupted, debug_messages

    def _get_true_sample_count(self, trimmed, cSamples, dataIndex):
        """Helper to determine the correct number of final samples acquired."""
        return len(trimmed) if dataIndex is not None else cSamples

    def _trim_samples(self, rgdSamples, dataIndex):
        """
        Return a trimmed view of the sample array starting from dataIndex to dataIndex + n_samples.
        """
        end_index = dataIndex + self.n_samples
        total_len = len(rgdSamples)

        if end_index > total_len:
            print(
                f"Warning: end_index {end_index} exceeds rgdSamples length {total_len}. Adjusting to fit."
            )
            end_index = total_len

        trimmed = rgdSamples[dataIndex:end_index]
        return trimmed, len(trimmed)

    def save_data(self, rgdSamples, hz_acq, start_time: float = None, filename = None):
        """
        Save the recorded data to a CSV file.
        :param rgdSamples: The recorded samples, as the ctype array.
        :param filename: Name of the CSV file to save the data.
        """
        if start_time is None:
            # If no start time is provided, use 0.0
            start_time = 0.0

        if filename:
            with open(filename, "w") as f:
                f.write("time,signal\n")
                for i, value in enumerate(rgdSamples):
                    time_s = start_time + i * (1.0 / hz_acq)
                    f.write(f"{time_s},{value}\n")
        else:
            print("No filename provided, skipping data save.")
