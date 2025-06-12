from dataclasses import dataclass, field
from typing import Optional
import os
import json
from src.event_logger import EventLogger

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
    event_logger: EventLogger = field(default_factory=EventLogger)

    # print the configuration in a readable format
    def print_config(self):
        print(self)

    def __str__(self) -> str:
        return (
            f"Experiment Setup:\n"
            f"  - Actinic LED Intensity: {self.actinic_led_intensity}%\n"
            f"  - Measurement LED Intensity: {self.measurement_led_intensity}%\n"
            f"  - Ared Duration: {self.ared_duration_s:.3f} s\n"
            f"  - Wait After Ared: {self.wait_after_ared_s:.3f} s\n"
            f"  - Agreen Delay: {self.agreen_delay_s:.3f} s\n"
            f"  - Agreen Duration: {self.agreen_duration_s:.3f} s\n"
            f"  - Total Recording Length: {self.recording_length_s:.3f} s\n"
            f"  - Sampling Rate: {self.recording_hz:,} Hz\n"
            f"  - Input Range: ±{self.channel_range/2:.1f} V\n"
            f"  - Output File: {os.path.basename(self.filename)}"
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

            cfg = cls(
                actinic_led_intensity=clamp(_actinic_led_intensity, 0, 100),
                measurement_led_intensity=clamp(_measurement_led_intensity, 0, 100),
                recording_length_s=clamp(
                    _recording_length, 0, 600
                ),  # e.g. max 10 minutes
                recording_hz=clamp(
                    _recording_hz, 1000, 1000000
                ),  # e.g. min 1kHz, max 1MHz
                ared_duration_s=clamp(_ared_duration_s, 0.0, 10.0),  # max 10 seconds
                wait_after_ared_s=clamp(
                    _wait_after_ared_s, 0.0, 10.0
                ),  # max 10 seconds
                agreen_delay_s=clamp(_agreen_delay_s, 0.0, 10.0),  # max 10 seconds
                agreen_duration_s=clamp(_agreen_duration, 0.0, 10.0),  # max 10 seconds
                channel_range=_channel_range,
                filename=_filename
                )

            # Handle event_logger if present
            if "event_logger" in data:
                cfg.event_logger = EventLogger.from_dict(data["event_logger"])

            return cfg
        
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid input in experiment config: {e}")

    def to_dict(self) -> dict:
        return {
            "actinic_led_intensity": self.actinic_led_intensity,
            "measurement_led_intensity": self.measurement_led_intensity,
            "recording_length_s": self.recording_length_s,
            "recording_hz": self.recording_hz,
            "ared_duration_s": self.ared_duration_s,
            "wait_after_ared_s": self.wait_after_ared_s,
            "agreen_delay_s": self.agreen_delay_s,
            "agreen_duration_s": self.agreen_duration_s,
            "channel_range": self.channel_range,
            "filename": self.filename,
            "event_logger": self.event_logger.to_dict() if self.event_logger else None
        }

    def to_json(self, indent: int = 4) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent)


