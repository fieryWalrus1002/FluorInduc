"""
DWF Python Example
Author:  Digilent, Inc.
Revision:  2018-07-19

Requires:
    Python 2.7, 3
"""

from ctypes import *
from src.dwfconstants import *
import math
import time
import sys
import numpy

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

# declare ctype variables
hdwf = c_int()
sts = c_byte()
hzAcq = c_double(1000000)
nSamples = 300000
rgdSamples = (c_double * nSamples)()
cAvailable = c_int()
cLost = c_int()
cCorrupted = c_int()
fLost = 0
fCorrupted = 0
time_step = 1.0 / hzAcq.value

# print(DWF version
version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: " + str(version.value))

# open device
print("Opening first device")
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == hdwfNone.value:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    print("failed to open device")
    quit()

# enabling the power supply
# set up analog IO channel nodes
# enable positive supply
# dwf.FDwfAnalogIOChannelNodeSet(hdwf, 0, 0, 1)
# # enable negative supply
# # dwf.FDwfAnalogIOChannelNodeSet(hdwf, 1, 0, 1)
# # master enable
# dwf.FDwfAnalogIOEnableSet(hdwf, True)

# enable positive supply
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(0), c_double(True))
# set voltage between 0 and 9V
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(1), c_double(3.0))
# set current limitation 0 and 1.5A
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(2), c_double(0.5))


# creating the analog output signal
print("Generating sine wave...")
dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_bool(True))
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSine)
dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(60))
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(0.8))
dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_bool(True))

# set up acquisition
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(2))
dwf.FDwfAnalogInAcquisitionModeSet(hdwf, acqmodeRecord)
dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq)
dwf.FDwfAnalogInRecordLengthSet(
    hdwf, c_double(nSamples / hzAcq.value)
)  # -1 infinite record length

# wait at least 2 seconds for the offset to stabilize
time.sleep(2)

print("Starting oscilloscope")
dwf.FDwfAnalogInConfigure(hdwf, c_int(0), c_int(1))

cSamples = 0

while cSamples < nSamples:
    dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
    if cSamples == 0 and (
        sts == DwfStateConfig or sts == DwfStatePrefill or sts == DwfStateArmed
    ):
        # Acquisition not yet started.
        continue

    dwf.FDwfAnalogInStatusRecord(
        hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted)
    )

    cSamples += cLost.value

    if cLost.value:
        fLost = 1
    if cCorrupted.value:
        fCorrupted = 1

    if cAvailable.value == 0:
        continue

    if cSamples + cAvailable.value > nSamples:
        cAvailable = c_int(nSamples - cSamples)

    dwf.FDwfAnalogInStatusData(
        hdwf, c_int(0), byref(rgdSamples, sizeof(c_double) * cSamples), cAvailable
    )  # get channel 1 data
    # dwf.FDwfAnalogInStatusData(hdwf, c_int(1), byref(rgdSamples, sizeof(c_double)*cSamples), cAvailable) # get channel 2 data
    cSamples += cAvailable.value

dwf.FDwfAnalogOutReset(hdwf, c_int(0))
dwf.FDwfDeviceCloseAll()

print("Recording done")
if fLost:
    print("Samples were lost! Reduce frequency")
if fCorrupted:
    print("Samples could be corrupted! Reduce frequency")

# Open the CSV file and write the time and sample data
with open("record.csv", "w") as f:
    f.write("Time (s),Sample Value\n")  # Add a header for clarity
    for i, v in enumerate(rgdSamples):
        time = i * time_step  # Calculate the time for each sample
        f.write(f"{time},{v}\n")

print("Data with time axis saved to record.csv")

# turn off the power supply
dwf.FDwfAnalogIOEnableSet(hdwf, False)
