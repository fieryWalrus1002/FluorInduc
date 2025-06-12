# conftest.py
import pytest

# pytest                 # hardware tests skipped
# pytest --run-hardware  # hardware tests run

def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-hardware"):
        return  # Don't skip anything

    skip_hw = pytest.mark.skip(reason="Need --run-hardware to run")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hw)


def pytest_addoption(parser):
    parser.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="Run tests marked as hardware",
    )
