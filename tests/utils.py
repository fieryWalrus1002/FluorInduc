import re
import numpy as np
from scipy.stats import t


def check_control_limits(data, target, tolerance):
    """
    Check if the data is within control limits defined by target and tolerance.

    :param data: list or np.array of measurements
    :param target: target value for the process
    :param tolerance: acceptable deviation from the target
    :return: True if all data points are within limits, False otherwise

    Prints out the control limits and whether the data is within those limits.
    """
    upper_limit = target + tolerance
    lower_limit = target - tolerance
    if isinstance(data, list):
        data = np.array(data)

    within_limits = np.all((data >= lower_limit) & (data <= upper_limit))

    print(f"Control Limits: LCL={lower_limit}, UCL={upper_limit}")
    print(f"Data within control limits: {within_limits}")

    if not within_limits:
        failures = [
            (i, val)
            for i, val in enumerate(data)
            if not (lower_limit <= val <= upper_limit)
        ]
        print("Out-of-control data points:")
        for idx, val in failures:
            print(f"  Index {idx}: {val:.6f} s")
    else:
        print("All data points are within control limits.")

    return within_limits


def process_capability_metrics(data, target, tolerance):
    """Calculate process capability metrics Cp and Cpk.
    param data: list or np.array of measurements
    param target: target value for the process
    param tolerance: acceptable deviation from the target

    Cp is the process capability index, which measures how well a process can produce output within specified limits.
    Cpk is the process capability index adjusted for the mean of the process.

    Good values for Cp and Cpk are typically above 1.33, indicating a capable process.
    1.0 is the minimum acceptable value, while values above 2.0 indicate an excellent process.

    Returns Cp, Cpk, mean, and standard deviation of the data.

    """
    mean = np.mean(data)
    stddev = np.std(data, ddof=1)

    USL = target + tolerance
    LSL = target - tolerance

    Cp = (USL - LSL) / (6 * stddev)
    Cpk = min((USL - mean), (mean - LSL)) / (3 * stddev)

    return Cp, Cpk, mean, stddev


def get_event_time_by_pattern(events, pattern: str):
    compiled = re.compile(pattern)
    for time_point, label in events:
        if compiled.search(label):
            return time_point
    raise AssertionError(f"No event label matched the pattern: '{pattern}'")


def compute_confidence_interval(data, confidence=0.95):
    arr = np.array(data)
    mean = arr.mean()
    std_err = arr.std(ddof=1) / np.sqrt(len(arr))
    ci = t.interval(confidence, len(arr) - 1, loc=mean, scale=std_err)
    return mean, std_err, ci


def pretty_print_events(events):
    print("----- Events ------")
    print("time       -     event")
    for time_point, label in events:
        print(f"{time_point:.6f}s - {label}")
