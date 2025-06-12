# tests/test_experiment_config.py

import pytest
from src.experiment_config import ExperimentConfig
import json

import time

def test_default_config_values():
    cfg = ExperimentConfig()
    assert cfg.actinic_led_intensity == 50
    assert cfg.recording_hz == 100000


def test_to_json_and_back():

    cfg1 = ExperimentConfig()
    cfg1.event_logger.start_event("protocol_start")
    cfg1.event_logger.log_event("ared_on")

    # Save
    json_str = cfg1.to_json()

    # Later...
    cfg2 = ExperimentConfig.from_dict(json.loads(json_str))
    assert cfg2.event_logger.get_events() == cfg1.event_logger.get_events()