# utils.py
from src.experiment_config import ExperimentConfig
from src.constants import PRE_BUFFER_SECONDS, LED_VOLTAGE_RANGES



def calculate_total_recording_length(cfg: ExperimentConfig) -> float:
    """
    Calculate the total recording length based on the experiment configuration.
    """
    return (
        PRE_BUFFER_SECONDS
        + cfg.ared_duration_s
        + cfg.wait_after_ared_s
        + cfg.agreen_delay_s
        + cfg.agreen_duration_s
    )

def calculate_samples_from_config(cfg: ExperimentConfig, verbose=False) -> int:
    """
    Calculate the number of samples required to fully capture the experiment,
    including a small pre-buffer before the first action.

    Parameters:
    - cfg (ExperimentConfig): configuration object with timing and Hz fields
    - verbose (bool): if True, prints detailed timing breakdown

    Returns:
    - int: number of samples to record
    """

    total_recording_length = calculate_total_recording_length(cfg)

    n_samples = int(total_recording_length * cfg.recording_hz)

    if verbose:
        print(f"[calculate_samples_from_config]")
        print(f"  Pre-buffer:         {PRE_BUFFER_SECONDS:.3f} s")
        print(f"  ARed duration:      {cfg.ared_duration_s:.3f} s")
        print(f"  Wait after ARed:    {cfg.wait_after_ared_s:.3f} s")
        print(f"  Agreen delay:       {cfg.agreen_delay_s:.3f} s")
        print(f"  Agreen duration:    {cfg.agreen_duration_s:.3f} s")
        print(f"  Total duration:     {total_recording_length:.3f} s")
        print(f"  Sampling rate:      {cfg.recording_hz} Hz")
        print(f"  Samples calculated: {n_samples}")

    return max(n_samples, 1)


def intensity_to_voltage(led: str, intensity: int = 50) -> float:
    """
    Convert LED intensity percentage to voltage based on the LED's min and max voltage range.
    
    Parameters:
    - led (str): The LED type, e.g., "red" or "green".
    - intensity (int): The intensity percentage (0-100).
    Returns:
    - float: The corresponding voltage value.
    Raises:
    - ValueError: If the LED is not recognized or if the intensity is out of range
    """


    if led not in LED_VOLTAGE_RANGES:
        raise ValueError(f"LED '{led}' is not recognized. Valid options are: {list(LED_VOLTAGE_RANGES.keys())}")
    if not isinstance(intensity, int):
        raise TypeError("Intensity must be an integer.")
    if not (0 <= intensity <= 100):
        raise ValueError("Intensity must be between 0 and 100.")

    if intensity <= 0:
        return 0.0 # return 0V for 0% intensity

    voltage = LED_VOLTAGE_RANGES[led]["min"] + (LED_VOLTAGE_RANGES[led]["max"] - LED_VOLTAGE_RANGES[led]["min"]) * (intensity / 100.0)
    if voltage < LED_VOLTAGE_RANGES[led]["min"] or voltage > LED_VOLTAGE_RANGES[led]["max"]:
        raise ValueError(f"Calculated voltage {voltage}V is out of range for {led} LED.")
    return voltage
