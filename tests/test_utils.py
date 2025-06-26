import pytest
from src.utils import precise_sleep
from src.constants import PRE_BUFFER_SECONDS
import time

def test_precise_sleep():
    start_time = time.perf_counter()
    precise_sleep(1.0)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    assert abs(elapsed_time - 1.0) < 0.1, f"Expected sleep duration ~1.0s, got {elapsed_time:.3f}s"