#!/usr/bin/env python3

# run_trials.py
# This script runs trials for an experiment by sending HTTP POST requests to a server.
# It takes a subject and intensities, randomizes their order,
# sends requests with specified parameters, and logs the entire session.

import argparse
import requests
import random
import sys
import re
import time
import datetime
import os


def get_timestamp():
    """Return current datetime as a formatted string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_log_filename():
    """Return a log filename with current date and time."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"experiment_log_{timestamp}.txt"


def write_log_header(log_file, args, randomized_order):
    """Write the header section to the log file."""
    log_file.write("=== Experiment Log ===\n")
    log_file.write(f"Date: {get_timestamp()}\n")
    log_file.write(f"Subject: {args.subject}\n")
    log_file.write(f"Subject Number: {args.subject_number}\n")
    log_file.write(f"Server URL: {args.server}\n")
    log_file.write(f"Sleep Time Between Requests: {args.sleep} seconds\n")
    log_file.write(f"Original Intensities: {args.intensities}\n")
    log_file.write(f"Randomized Order: {randomized_order}\n")
    log_file.write("======================\n\n")
    log_file.flush()


def log_trial(log_file, trial_info):
    """Append a single trial's info to the log file."""
    log_file.write(f"--- Trial at {get_timestamp()} ---\n")
    for key, value in trial_info.items():
        log_file.write(f"{key}: {value}\n")
    log_file.write("\n")
    log_file.flush()


def run_trials(subject, subject_number, intensities, base_url, sleep_time, log_path):
    """
    Randomizes the order of intensities, sends POST requests, and logs results.
    """
    randomized_order = intensities.copy()
    random.shuffle(randomized_order)
    print(f"Order of trials: {randomized_order}")

    # Open the log file
    with open(log_path, "a") as log_file:
        # Write header once
        write_log_header(
            log_file,
            argparse.Namespace(
                subject=subject,
                subject_number=subject_number,
                server=base_url,
                sleep=sleep_time,
                intensities=intensities,
            ),
            randomized_order,
        )

        for intensity in randomized_order:
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
            trial_info = {
                "Intensity": intensity,
                "Filename": filename,
                "Payload": payload,
            }

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
                trial_info["Response"] = response.text
                print(f"SUCCESS: Server response: {response.text}")
            except requests.exceptions.RequestException as e:
                trial_info["Error"] = str(e)
                print(f"ERROR sending request: {e}")

            # Log this trial
            log_trial(log_file, trial_info)

            # Wait before next trial
            print(f"Sleeping for {sleep_time} seconds...")
            sys.stdout.flush()
            time.sleep(sleep_time)


def main():
    parser = argparse.ArgumentParser(
        description="Run experiment trials by sending HTTP POST requests."
    )
    parser.add_argument(
        "--subject",
        help="Subject identifier, eg 'arab', '2xKimWipe', etc.",
        default="test",
    )
    parser.add_argument(
        "--subject_number",
        type=int,
        help="Subject number, e.g., 1",
        default=1,
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
    parser.add_argument(
        "--logdir",
        help="Directory to save log file (default: current directory)",
        default=".",
    )
    args = parser.parse_args()

    # Create log file path
    log_filename = get_log_filename()
    log_path = os.path.join(args.logdir, log_filename)

    print(f"Logging all trials to: {log_path}")
    print(
        f"Running trials for subject='{args.subject}', subject_number={args.subject_number}"
    )
    run_trials(
        args.subject,
        args.subject_number,
        args.intensities,
        args.server,
        args.sleep,
        log_path,
    )


if __name__ == "__main__":
    main()
