"""SensorPush session fixtures."""

import pytest


@pytest.fixture(autouse=True)
def mock_bluetooth(mock_bleak_scanner_start, enable_bluetooh):
    """Auto mock bluetooth."""
