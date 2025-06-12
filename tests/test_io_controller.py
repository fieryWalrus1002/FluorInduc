# tests/test_io_controller_hil.py
import time
import pytest
from src.io_controller import IOController


@pytest.fixture(scope="module")
def io_controller():
    io = IOController()
    io.open_device()
    yield io
    io.cleanup()


def test_shutter_toggle(io_controller):
    io_controller.toggle_shutter(False)
    time.sleep(0.5)
    io_controller.toggle_shutter(True)
    time.sleep(0.5)
    io_controller.toggle_shutter(False)


def test_led_voltage_range(io_controller):
    for led in ["red", "green"]:
        for intensity in [0, 25, 50, 75, 100]:
            io_controller.set_led_intensity(led, intensity)
            print(f"Set {led} LED to {intensity}% intensity")
            time.sleep(0.2)