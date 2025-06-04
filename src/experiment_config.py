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
    recording_length_s: float = 1.0  # Default recording length in seconds
    recording_hz: int = 100000
    ared_duration_s: float = 0.0
    wait_after_ared_s: float = 0.0
    agreen_delay_s: float = 0.002  # Delay after recording begins, before Agreen ON
    agreen_duration_s: float = 0.0
    channel_range: int = 2  # Default range for the channel, e.g., 2V
    filename: str = "record.csv"

    # print the configuration in a readable format
    def __str__(self) -> str:
        return (
            f"ExperimentConfig(actinic_led_intensity={self.actinic_led_intensity}, "
            f"measurement_led_intensity={self.measurement_led_intensity}, "
            f"recording_length_s={self.recording_length_s}, "
            f"recording_hz={self.recording_hz}, "
            f"filename='{self.filename}', "
            f"ared_duration_s={self.ared_duration_s}, "
            f"wait_after_ared_s={self.wait_after_ared_s}, "
            f"agreen_delay_s={self.agreen_delay_s}, "
            f"agreen_duration_s={self.agreen_duration_s}, "
            f"channel_range={self.channel_range}"
            f")"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        """Safely populate the config from a dictionary, with validation."""

        def clamp(val, min_val, max_val):
            return max(min_val, min(max_val, val))

        try:
            _actinic_led_intensity = int(data.get("actinic_led_intensity", 50))
            _measurement_led_intensity = int(data.get("measurement_led_intensity", 50))
            _recording_hz = int(data.get("recording_hz", 100000))
            _ared_duration_s = float(data.get("ared_duration_s", 0.0))
            _wait_after_ared_s = float(data.get("wait_after_ared_s", 0.0))
            _agreen_delay_s = float(data.get("agreen_delay_s", 0.002))  # Default delay
            _agreen_duration = float(data.get("agreen_duration_s", 0.0))
            _channel_range = int(data.get("channel_range", 2))    
            _filename = ensure_file_suffix(data.get("filename", "record.csv"))

            _recording_length = _agreen_delay_s + _agreen_duration

            return cls(
                actinic_led_intensity=clamp(_actinic_led_intensity, 0, 100),
                measurement_led_intensity=clamp(_measurement_led_intensity, 0, 100),
                recording_length_s=clamp(_recording_length, 0, 600),  # e.g. max 10 minutes
                recording_hz=clamp(_recording_hz, 1000, 1000000),  # e.g. min 1kHz, max 1MHz
                ared_duration_s=clamp(_ared_duration_s, 0.0, 10.0),  # max 10 seconds
                wait_after_ared_s=clamp(_wait_after_ared_s, 0.0, 10.0),  # max 10 seconds
                agreen_delay_s=clamp(_agreen_delay_s, 0.0, 10.0),  # max 10 seconds
                agreen_duration_s=clamp(_agreen_duration, 0.0, 10.0),  # max 10 seconds
                channel_range=_channel_range,
                filename=_filename
            )

        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid input in experiment config: {e}")
