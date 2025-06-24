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


def test_clone_with_creates_modified_copy():
    cfg1 = ExperimentConfig(
        actinic_led_intensity=60, ared_duration_s=1.5, filename="original.csv"
    )

    cfg2 = cfg1.clone_with(ared_duration_s=2.5, filename="clone.csv")

    assert cfg2.ared_duration_s == 2.5
    assert cfg2.filename == "clone.csv"
    assert cfg2.actinic_led_intensity == 60  # retained from original

    # Original is unchanged
    assert cfg1.ared_duration_s == 1.5
    assert cfg1.filename == "original.csv"


def test_clone_with_creates_fresh_event_logger_by_default():
    cfg1 = ExperimentConfig()
    cfg1.event_logger.start_event("initial_test")
    cfg1.event_logger.log_event("test_event")

    cfg2 = cfg1.clone_with(filename="different.csv")

    assert cfg1.event_logger is not cfg2.event_logger
    assert len(cfg1.event_logger.get_events()) == 2  # start_event + log_event
    assert len(cfg2.event_logger.get_events()) == 0


def test_clone_with_preserves_custom_event_logger_if_provided():
    from src.event_logger import EventLogger

    shared_logger = EventLogger()
    shared_logger.start_event("shared_test")
    shared_logger.log_event("shared_event")

    cfg1 = ExperimentConfig(event_logger=shared_logger)
    cfg2 = cfg1.clone_with(filename="clone.csv", event_logger=shared_logger)

    assert cfg2.event_logger is shared_logger
    assert len(cfg2.event_logger.get_events()) == 2  # start_event + log_event
