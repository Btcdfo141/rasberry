"""Fixtures for IntelliFire integration tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from aiohttp.client_reqrep import ConnectionKey
import pytest


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.intellifire.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_intellifire_config_flow() -> Generator[None, MagicMock, None]:
    """Return a mocked IntelliFire client."""
    data_mock = Mock()
    data_mock.serial = "12345"

    with patch(
        "homeassistant.components.intellifire.config_flow.IntellifireAsync",
        autospec=True,
    ) as intellifire_mock:
        intellifire = intellifire_mock.return_value
        intellifire.data = data_mock

        yield intellifire


@pytest.fixture
def mock_intellifire_config_flow_with_local_error() -> Generator[None, MagicMock, None]:
    """Return a mocked IntelliFire client."""
    data_mock = Mock()
    data_mock.serial = "12345"

    with patch(
        "homeassistant.components.intellifire.config_flow.IntellifireAsync",
        autospec=True,
    ) as intellifire_mock:
        intellifire_mock.side_effect = ConnectionError()
        yield ConnectionError()


@pytest.fixture
def mock_intellifire_config_flow_with_api_error() -> Generator[None, MagicMock, None]:
    """Return a mocked IntelliFire client."""
    data_mock = Mock()
    data_mock.serial = "12345"

    with patch(
        "homeassistant.components.intellifire.config_flow.IntellifireControlAsync",
        autospec=True,
    ), patch(
        "homeassistant.components.intellifire.config_flow.IntellifireAsync",
        autospec=True,
    ) as intellifire_mock:
        intellifire = intellifire_mock.return_value
        intellifire.data = data_mock
        yield intellifire


def mock_api_connection_error() -> ConnectionError:
    """Return a fake a ConnectionError for iftapi.net."""
    ret = ConnectionError()
    ret.args = [ConnectionKey("iftapi.net", 443, False, None, None, None, None)]
    return ret
