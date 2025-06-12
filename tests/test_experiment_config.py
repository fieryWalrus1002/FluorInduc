# tests/test_experiment_config.py
import pytest
import json
import math
from src.experiment_config import ExperimentConfig


def test_default_config_values():
    cfg = ExperimentConfig()
    assert cfg.actinic_led_intensity == 50
    assert cfg.recording_hz == 100000


def test_to_json_and_back():
    cfg1 = ExperimentConfig()
    cfg1.event_logger.start_event("protocol_start")
    cfg1.event_logger.log_event("ared_on")

    json_str = cfg1.to_json()

    cfg2 = ExperimentConfig.from_dict(json.loads(json_str))

    events1 = cfg1.event_logger.get_events()
    events2 = cfg2.event_logger.get_events()

    assert len(events1) == len(events2)

    for (t1, label1), (t2, label2) in zip(events1, events2):
        assert label1 == label2
        assert math.isclose(t1, t2, rel_tol=1e-5, abs_tol=1e-6)
