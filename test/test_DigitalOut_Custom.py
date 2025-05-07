"""
   DWF Python Example
   Author:  Digilent, Inc.
   Revision:  2019-09-02

   Requires:                       
       Python 2.7, 3
   Description:
   Generates a custom pattern
"""

# 10Hz pulse of the first pin

from ctypes import *
from dwfconstants import *
import sys
import time

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

hdwf = c_int()

version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))


print("Opening first device")
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == 0:
    print("failed to open device")
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    quit()

print("Configuring Digital Out")

hzSys = c_double()
dwf.FDwfDigitalOutInternalClockInfo(hdwf, byref(hzSys))


data_py=[0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]

# how many bytes we need to fit this many bits, (+7)/8
rgbdata=(c_ubyte*((len(data_py)+7)>>3))(0) 

# array to bits in byte array
for i in range(len(data_py)):
    if data_py[i] != 0:
        rgbdata[i>>3] |= 1<<(i&7)
        
        
pin=0
# generate pattern
dwf.FDwfDigitalOutEnableSet(hdwf, c_int(pin), c_int(1))
dwf.FDwfDigitalOutTypeSet(hdwf, c_int(pin), DwfDigitalOutTypeCustom)
# 100kHz sample rate
dwf.FDwfDigitalOutDividerSet(hdwf, c_int(pin), c_int(int(hzSys.value/10))) # set sample rate
dwf.FDwfDigitalOutDataSet(hdwf, c_int(pin), byref(rgbdata), c_int(len(data_py)))


print("Generating pattern...")
dwf.FDwfDigitalOutConfigure(hdwf, c_int(1))

time.sleep(10)

dwf.FDwfDigitalOutReset(hdwf)
dwf.FDwfDeviceCloseAll()
