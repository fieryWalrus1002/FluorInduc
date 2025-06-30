# constants.py
# This file contains constants used throughout the application. It lets me use meaningful
# names for pin numbers, voltage ranges, and other settings, making the code more readable
# and maintainable.
# While the use of these is mostly within the IOController class, it is useful to have them
# centralized here for easy reference and modification if we change hardware or settings,
# or need to use them in other parts of the codebase (such as the TimedActionFactory).

# Digital output pin configuration
PIN_GATE = 2
PIN_TRIGGER = 3

PIN_MASK_ALL_OUTPUT = 0xFF
PIN_STATE_ALL_LOW = 0x00
OUTPUT_MASK_ALL = 0xFF

# Analog output LED configuration
LED_RED_PIN = 0
LED_GREEN_PIN = 1

# analog input channel configuration
ANALOG_IN_CHANNEL = 0
ANALOG_TRIGGER_STATE = 0
ANALOG_RECORD_FOREVER = -1
DELAY_BEFORE_RECORDING_START = -0.065 # seconds, delay before recording starts
END_RECORDING_OFFSET_DELAY = 0.025 # small delay added to ensure the green LED is off first, as it was being skipped

# for error message retrieval from C API
STRING_BUFFER_SIZE = 524 

# define the minimum and maximum voltage ranges when setting intensities for the LEDs
# This will constrain the min and max current that can be set.
LED_VOLTAGE_RANGES = {
    "red": {"pin": LED_RED_PIN, "min": 0.0, "max": 5.0},
    "green": {"pin": LED_GREEN_PIN, "min": 1.0, "max": 5.0},
}

# Analog function generator settings
ANALOG_OUT_FREQUENCY = 0.0
ANALOG_OUT_OFFSET = 0.0
ANALOG_OUT_REPEAT = 1
ANALOG_OUT_WAIT = 0.0

# Pre-buffer time before the first action is recorded
PRE_BUFFER_SECONDS = 0.1
