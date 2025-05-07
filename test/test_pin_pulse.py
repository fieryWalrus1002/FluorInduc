"""
DWF Python Example
Author:  Digilent, Inc.
Revision:  2020-04-07

Requires:
    Python 2.7, 3
"""

from ctypes import *
from src.dwfconstants import *
import math
import time
import sys

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: " + str(version.value))

print("Opening first device")
hdwf = c_int()
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == 0:
    print("failed to open device")
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    quit()

hzSys = c_double()
pin = 0

# set up the clock frequency
dwf.FDwfDigitalOutInternalClockInfo(hdwf, byref(hzSys))

# Enable the pin for output
dwf.FDwfDigitalOutEnableSet(hdwf, c_int(pin), c_int(1))
dwf.FDwfDigitalOutEnableSet(hdwf, c_int(pin+1), c_int(1))
# pin loops on and off for three seconds
for i in range(3):

    dwf.FDwfDigitalOutCounterSet(hdwf, c_int(pin), c_int(0), c_int(1))
    time.sleep(0.25)
    dwf.FDwfDigitalOutCounterSet(hdwf, c_int(pin+1), c_int(0), c_int(1))
    time.sleep(0.5)
    dwf.FDwfDigitalOutCounterSet(hdwf, c_int(pin + 1), c_int(0), c_int(0))
    time.sleep(0.25)
    dwf.FDwfDigitalOutCounterSet(hdwf, c_int(pin), c_int(0), c_int(0))
    time.sleep(1.0)


dwf.FDwfDigitalOutReset(hdwf)
dwf.FDwfDeviceCloseAll()
