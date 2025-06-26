import pytest
from src.utils import intensity_to_voltage
from src.constants import LED_VOLTAGE_RANGES


@pytest.mark.parametrize(
    "led,intensity,expected",
    [
        ("red", 0, 0.0),
        ("red", 100, LED_VOLTAGE_RANGES["red"]["max"]),
        (
            "red",
            50,
            (LED_VOLTAGE_RANGES["red"]["max"] - LED_VOLTAGE_RANGES["red"]["min"]) * 0.5,
        ),
        ("green", 0, 0.0),
        ("green", 100, LED_VOLTAGE_RANGES["green"]["max"]),
        (
            "green",
            50,
            (LED_VOLTAGE_RANGES["green"]["max"] - LED_VOLTAGE_RANGES["green"]["min"])
            * 0.5,
        ),
    ],
)
def test_intensity_to_voltage_valid(led, intensity, expected):
    voltage = intensity_to_voltage(led, intensity)
    assert (
        abs(voltage - expected) < 1e-6
    ), f"{led} LED at {intensity}% should be ~{expected}, got {voltage}"


def test_intensity_to_voltage_invalid_led():
    with pytest.raises(ValueError, match="LED 'blue' is not recognized"):
        intensity_to_voltage("blue", 50)


def test_intensity_to_voltage_out_of_range_intensity():
    with pytest.raises(ValueError, match="Intensity must be between 0 and 100"):
        intensity_to_voltage("red", -10)

    with pytest.raises(ValueError, match="Intensity must be between 0 and 100"):
        intensity_to_voltage("green", 101)


def test_intensity_to_voltage_invalid_type():
    with pytest.raises(TypeError, match="Intensity must be an integer"):
        intensity_to_voltage("red", "50")
