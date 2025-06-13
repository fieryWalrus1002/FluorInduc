from ctypes import *
import time
from src import dwfconstants
import numpy as np
from src.event_logger import EventLogger


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
        self.dwf.FDwfAnalogInRecordLengthSet(self.hdwf, c_double(-1))

        hz_acq = c_double()
        self.dwf.FDwfAnalogInFrequencyGet(self.hdwf, byref(hz_acq))
        print(f"Confirmed acquisition frequency: {hz_acq.value}")

        channel_range = c_double()
        self.dwf.FDwfAnalogInChannelRangeGet(self.hdwf, c_int(self.channel), byref(channel_range))
        print(f"Channel {self.channel} range: {channel_range.value} V")

        self.dwf.FDwfAnalogInTriggerSourceSet(self.hdwf, c_int(0))  # 0 = trigsrcNone
        self.dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))

    def wait_for_data_start(self):
        """Block until data acquisition actually begins.

                    self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))
                        if cSamples == 0 and (
                            sts == dwfconstants.DwfStateConfig
                            or sts == dwfconstants.DwfStatePrefill
                            or sts == dwfconstants.DwfStateArmed
                        ):
                            # Acquisition not yet started, wait a bit
                            time.sleep(0.5)
                            continue

            typedef enum {
                DwfStateReady = 0,     // Ready to configure / start
                DwfStateConfig = 1,    // Configuring
                DwfStatePrefill = 2,   // Prefilling the buffer
                DwfStateArmed = 3,     // Ready and waiting for trigger
                DwfStateWait = 4,      // Waiting for trigger timeout
                DwfStateTriggered = 5, // Triggered, data incoming
                DwfStateRunning = 6,   // Running (streaming data)
                DwfStateDone = 7       // Acquisition complete
                } DwfState;

        """
        sts = c_byte()
        while True:
            self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))
            if sts.value not in (dwfconstants.DwfStateConfig, dwfconstants.DwfStatePrefill, dwfconstants.DwfStateArmed):
                break
            time.sleep(0.5)
        self.logger.log_event("recording_started")
        return time.perf_counter()

    def complete_recording(self, actions=None, debug=False):
        """
        Complete the recording process and return the recorded data.
        :param actions: A list of actions to execute during recording.
                        Each action is a tuple (sample_number, callable, label).
        :return: A tuple (rgdSamples, total_samples, lost_flag, corrupted_flag)
        """
        sts = c_byte()
        n_samples = self.n_samples
        rgdSamples = (c_double * n_samples)()
        cAvailable = c_int()
        cLost = c_int()
        cSamples = c_int()
        cCorrupted = c_int()
        fLost = 0
        fCorrupted = 0
        in_real_acquisition = False  # Track if we're in real acquisition yet

        self.logger.log_event("recording_loop_started")

        loopCounter = 0

        cSamples = 0
        while cSamples < n_samples:
            self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))

            if debug:
                if (loopCounter % 50) == 0:
                    print(f"[DEBUG] Loop {loopCounter}: Status={sts.value}, Samples={cSamples}/{n_samples}")
                loopCounter += 1

            if cSamples <= 0 and (
                sts == dwfconstants.DwfStateConfig
                or sts == dwfconstants.DwfStatePrefill
                or sts == dwfconstants.DwfStateArmed
            ):
                # Acquisition not yet started, wait a bit
                time.sleep(0.05)
                continue

            # Trigger actions when sample number reached
            # if actions:
            #     while actions and cSamples >= actions[0][0]:
            #         _, action_func, label = actions.pop(0)
            #         action_func()
            #         self.logger.log_event(f"action_{label}_executed_at_sample_{cSamples}")

            if actions:
                for action in actions[:]:  # iterate over copy
                    if cSamples >= action[0]:
                        print(f"Executing action at sample {cSamples}")
                        action[1]()
                        actions.remove(action)
                        self.logger.log_event(f"action_{action[2]}_executed_at_sample_{cSamples}")

            self.dwf.FDwfAnalogInStatusRecord(
                self.hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted)
            )

            # if there are any lost or corrupted samples, set the flags
            if cLost.value:
                fLost = 1
            if cCorrupted.value:
                fCorrupted = 1

            # adds lost samples to the count, if any
            cSamples += cLost.value

            # if no samples are available, continue to the next iteration
            if cAvailable.value == 0:
                continue

            # If the number of available samples exceeds the remaining samples to record, limit it
            if cSamples + cAvailable.value > n_samples:
                cAvailable = c_int(n_samples - cSamples)

            #         # Read the available samples into the rgdSamples array
            self.dwf.FDwfAnalogInStatusData(
                self.hdwf,
                c_int(self.channel),
                byref(rgdSamples, sizeof(c_double) * cSamples),
                cAvailable,
            )

            # add the number of available samples to the count
            cSamples += cAvailable.value

        self.logger.log_event("recording_completed")
        print(f"Recorded {cSamples} samples, lost {fLost}, corrupted {fCorrupted}")
        return rgdSamples[:cSamples], cSamples, fLost, fCorrupted

    def save_data(self, rgdSamples, hz_acq, start_time: float = None, filename="record.csv"):
        """
        Save the recorded data to a CSV file.
        :param rgdSamples: The recorded samples, as the ctype array.
        :param filename: Name of the CSV file to save the data.
        """
        if start_time is None:
            # If no start time is provided, use 0.0
            start_time = 0.0

        with open(filename, "w") as f:
            f.write("time,signal\n")
            for i, value in enumerate(rgdSamples):
                time_s = start_time + i * (1.0 / hz_acq)
                f.write(f"{time_s},{value}\n")


if __name__ == "__main__":
    print(
        "This module is not meant to be run directly. Use the IOController class to manage recording."
    )

    # def record(self, logger: EventLogger, channel, n_samples, hz_acq=1000000, channel_range=50, actions=None):
    #     """
    #     instead of record_and_save, this function is used to record the signal from the specified channel
    #     and return it as a tuple of lists (time, value).

    #     If there is a list of actions, it will execute them during the recording.
    #     :param channel: The analog input channel to record from.
    #     :param n_samples: Number of samples to record.
    #     :param hz_acq: Acquisition frequency in Hz.
    #     :param channel_range: The range for the analog input channel in volts.
    #     :param actions: A list of tuples (sample_number, action) where action is a callable to execute at that sample.
    #     """

    #     logger.log_event("setup_recording")

    #     # Declare ctype variables
    #     sts = c_byte()
    #     hzAcq = c_double(hz_acq)
    #     rgdSamples = (c_double * n_samples)()
    #     cAvailable = c_int()
    #     cLost = c_int()
    #     cCorrupted = c_int()
    #     fLost = 0
    #     fCorrupted = 0
    #     time_step = 1.0 / hzAcq.value

    #     # Configure the analog input channel
    #     self.dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(channel), c_bool(True))
    #     self.dwf.FDwfAnalogInChannelRangeSet(self.hdwf, c_int(channel), c_double(channel_range))
    #     self.dwf.FDwfAnalogInAcquisitionModeSet(self.hdwf, dwfconstants.acqmodeRecord)
    #     self.dwf.FDwfAnalogInFrequencySet(self.hdwf, hzAcq)
    #     self.dwf.FDwfAnalogInRecordLengthSet(
    #         self.hdwf, c_double(-1)
    #     )  # -1 for infinite record length

    #     # print out the acquisition frequency
    #     self.dwf.FDwfAnalogInFrequencyGet(self.hdwf, byref(hzAcq))
    #     print(f"Acquisition frequency: {hzAcq.value} Hz")

    #     # print out the number of samples
    #     print(f"Number of samples: {n_samples}")

    #     # set the channel in range
    #     channel_range = c_double()
    #     self.dwf.FDwfAnalogInChannelRangeGet(
    #         self.hdwf, c_int(channel), byref(channel_range)
    #     )
    #     print(f"Channel {channel} range: {channel_range.value} V")

    #     self.dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))
    #     logger.log_event("recording_started")
    #     cSamples = 0
    #     while cSamples < n_samples:

    #         self.dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(sts))
    #         if cSamples == 0 and (
    #             sts == dwfconstants.DwfStateConfig
    #             or sts == dwfconstants.DwfStatePrefill
    #             or sts == dwfconstants.DwfStateArmed
    #         ):
    #             # Acquisition not yet started, wait a bit
    #             time.sleep(0.5)
    #             continue

    #         # the actions in the list will be executed during the recording
    #         if actions is not None:
    #             for action in actions:
    #                 if cSamples >= action[0]:
    #                     print(f"Executing action at sample {cSamples}")
    #                     action[1]()
    #                     logger.log_event(f"action_{action[2]}_executed_at_sample_{cSamples}")
    #                     # now pop the action from the list so it does not get executed again
    #                     actions.pop(0)

    #         self.dwf.FDwfAnalogInStatusRecord(
    #             self.hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted)
    #         )

    #         # adds lost samples to the count, if any
    #         cSamples += cLost.value

    #         # if there are any lost or corrupted samples, set the flags
    #         if cLost.value:
    #             fLost = 1
    #         if cCorrupted.value:
    #             fCorrupted = 1

    #         # if no samples are available, continue to the next iteration
    #         if cAvailable.value == 0:
    #             continue

    #         # If the number of available samples exceeds the remaining samples to record, limit it
    #         if cSamples + cAvailable.value > n_samples:
    #             cAvailable = c_int(n_samples - cSamples)

    #         # Read the available samples into the rgdSamples array
    #         self.dwf.FDwfAnalogInStatusData(
    #             self.hdwf,
    #             c_int(channel),
    #             byref(rgdSamples, sizeof(c_double) * cSamples),
    #             cAvailable,
    #         )  # Get channel data

    #         # add the number of available samples to the count
    #         cSamples += cAvailable.value

    #     # self.dwf.FDwfAnalogOutReset(self.hdwf, c_int(channel))
    #     logger.log_event("recording_completed")
    #     print(f"Recorded {cSamples} samples, lost {cLost.value}, corrupted {cCorrupted.value}")
    #     return rgdSamples[:cSamples], cSamples, fLost, fCorrupted

    # def record_and_save(self, channel, n_samples, hz_acq=1000000, filename="record.csv", range=2):
    #     """
    #     Record the signal from the specified channel and save it to a CSV file.
    #     :param channel: The analog input channel to record from.
    #     :param n_samples: Number of samples to record.
    #     :param hz_acq: Acquisition frequency in Hz.
    #     :param filename: Name of the CSV file to save the data.
    #     """

    #     print(f"Recording {n_samples} samples at {hz_acq} Hz from channel {channel}...")
    #     print(f"Recording range: {range} V")
    #     rgdSamples, cSamples, fLost, fCorrupted = self.record(
    #         channel, n_samples, hz_acq, range
    #     )

    #     if fLost:
    #         print("Samples were lost! Reduce frequency")
    #     if fCorrupted:
    #         print("Samples could be corrupted! Reduce frequency")

    #     self.save_data(rgdSamples, hz_acq, filename)
