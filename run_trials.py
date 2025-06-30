# run_trials.py
# This script runs trials for an experiment by sending HTTP POST requests to a server.
# It takes a subject pattern and a list of intensities, randomizes the order of the intensities,
# and sends requests with the specified parameters.

import argparse
import requests
import random
import sys
import re
import time

def parse_pattern(pattern):
    """
    Parse a pattern like 'arab_1' into subject and subject_number.
    """
    match = re.match(r"^([a-zA-Z]+)_(\d+)", pattern)
    if not match:
        raise ValueError(f"Invalid pattern format: {pattern}")
    subject = match.group(1)
    subject_number = int(match.group(2))
    return subject, subject_number


def run_trials(subject, subject_number, intensities, base_url, sleep_time):
    """
    Randomizes the order of intensities and sends POST requests.
    """
    random.shuffle(intensities)
    print(f"Order of trials: {intensities}")

    for intensity in intensities:
        filename = f"{subject}_{subject_number}_{intensity}"
        payload = {
            "actinic_led_intensity": 0,
            "measurement_led_intensity": intensity,
            "recording_hz": 2000,
            "ared_duration_s": 0,
            "wait_after_ared_s": 0,
            "agreen_delay_s": 0.1,
            "agreen_duration_s": 1.5,
            "channel_range": 50,
            "filename": filename,
        }

        print(
            f"\nSending request for intensity {intensity} with filename '{filename}'..."
        )
        try:
            response = requests.post(
                f"{base_url}/start_task",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "User-Agent": "ExperimentRunner/1.0",
                },
            )
            response.raise_for_status()
            print(f"SUCCESS: Server response: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"ERROR sending request: {e}")
        print(f"Sleeping for {sleep_time} seconds...")
        sys.stdout.flush()
        time.sleep(sleep_time)


def main():
    parser = argparse.ArgumentParser(
        description="Run experiment trials by sending HTTP POST requests."
    )
    parser.add_argument(
        "--subject", help="Subject identifier, eg 'arab', '2xKimWipe', etc.",
        default="test"
    )
    parser.add_argument(
        "--subject_number", type=int, required=True, help="Subject number, e.g., 1",
        default=1
        
    )
    parser.add_argument(
        "--intensities",
        nargs="+",
        type=int,
        default=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        help="List of green intensities to use (default: 0 10 20 30 40 50 60 70 80 90 100)",
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:5000",
        help="Base server URL (default: http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--sleep",
        help="Amount of time to sleep between requests (default: 300 seconds)",
        type=int,
        default=300,
    )
    args = parser.parse_args()


    print(f"Running trials for subject='{args.subject}', subject_number={args.subject_number}")
    run_trials(args.subject, args.subject_number, args.intensities, args.server, args.sleep)


if __name__ == "__main__":
    main()
