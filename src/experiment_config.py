from dataclasses import dataclass, field
from typing import Optional

def ensure_file_suffix(filename: str, suffix: str = ".csv") -> str:
    """Ensure the filename ends with the specified suffix."""
    if not filename.endswith(suffix):
        return filename + suffix
    return filename

@dataclass
class ExperimentConfig:
    actinic_led_intensity: int = 50
    measurement_led_intensity: int = 50
    recording_length: int = 10
    recording_hz: int = 100000
    shutter_state: bool = False
    filename: str = "record.csv"

    # print the configuration in a readable format
    def __str__(self) -> str:
        return (
            f"ExperimentConfig(actinic_led_intensity={self.actinic_led_intensity}, "
            f"measurement_led_intensity={self.measurement_led_intensity}, "
            f"recording_length={self.recording_length}, "
            f"recording_hz={self.recording_hz}, "
            f"shutter_state={self.shutter_state}, "
            f"filename='{self.filename}')"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        """Safely populate the config from a dictionary, with validation."""

        def clamp(val, min_val, max_val):
            return max(min_val, min(max_val, val))

        try:
            actinic = int(data.get("actinic_led_intensity", 50))
            measurement = int(data.get("measurement_led_intensity", 50))
            rec_len = int(data.get("recording_length", 10))
            rec_hz = int(data.get("recording_hz", 100000))
            shutter = bool(data.get("shutter_state", False))
            filename = ensure_file_suffix(data.get("filename", "record.csv"))

            return cls(
                actinic_led_intensity=clamp(actinic, 0, 100),
                measurement_led_intensity=clamp(measurement, 0, 100),
                recording_length=clamp(rec_len, 1, 600),  # e.g. max 10 minutes
                recording_hz=clamp(rec_hz, 1000, 1000000),  # e.g. min 1kHz, max 1MHz
                shutter_state=shutter,
                filename=filename,
            )

        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid input in experiment config: {e}")
