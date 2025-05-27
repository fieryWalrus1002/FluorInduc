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

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        """Safely populate the config from a dictionary, with defaults."""
        return cls(
            actinic_led_intensity=int(data.get("actinic_led_intensity", 50)),
            measurement_led_intensity=int(data.get("measurement_led_intensity", 50)),
            recording_length=int(data.get("recording_length", 10)),
            shutter_state=bool(data.get("shutter_state", False)),
            filename=ensure_file_suffix(data.get("filename", "record.csv")),
            recording_hz=int(data.get("recording_hz", 100000)),
        )
        
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
