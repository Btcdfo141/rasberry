"""Fixtures for System Bridge integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from systembridgeconnector.const import (
    EVENT_MODULES,
    TYPE_DATA_GET,
    TYPE_DATA_LISTENER_REGISTERED,
)
from systembridgemodels.media_directories import MediaDirectory
from systembridgemodels.media_files import MediaFile, MediaFiles
from systembridgemodels.modules import GetData, RegisterDataListener
from systembridgemodels.response import Response

from homeassistant.components.system_bridge.config_flow import SystemBridgeConfigFlow
from homeassistant.components.system_bridge.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant

from . import (
    FIXTURE_GENERIC_RESPONSE,
    FIXTURE_REQUEST_ID,
    FIXTURE_TITLE,
    FIXTURE_USER_INPUT,
    FIXTURE_UUID,
    mock_data_listener,
    setup_integration,
)

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock ConfigEntry."""
    return MockConfigEntry(
        title=FIXTURE_TITLE,
        domain=DOMAIN,
        unique_id=FIXTURE_UUID,
        version=SystemBridgeConfigFlow.VERSION,
        minor_version=SystemBridgeConfigFlow.MINOR_VERSION,
        data={
            CONF_HOST: FIXTURE_USER_INPUT[CONF_HOST],
            CONF_PORT: FIXTURE_USER_INPUT[CONF_PORT],
            CONF_TOKEN: FIXTURE_USER_INPUT[CONF_TOKEN],
        },
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setup entry."""
    with patch(
        "homeassistant.components.system_bridge.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(autouse=True)
def mock_setup_notify_platform() -> Generator[AsyncMock, None, None]:
    """Mock notify platform setup."""
    with patch(
        "homeassistant.helpers.discovery.async_load_platform",
    ) as mock_setup_notify_platform:
        yield mock_setup_notify_platform


@pytest.fixture
def mock_version() -> Generator[AsyncMock, None, None]:
    """Return a mocked Version class."""
    with patch(
        "homeassistant.components.system_bridge.Version",
        autospec=True,
    ) as mock_version:
        version = mock_version.return_value
        version.check_supported.return_value = True

        yield version


@pytest.fixture
def mock_websocket_client(
    get_data_model: GetData = GetData(
        modules=["system"],
    ),
    register_data_listener_model: RegisterDataListener = RegisterDataListener(
        modules=["system"]
    ),
) -> Generator[MagicMock, None, None]:
    """Return a mocked WebSocketClient client."""

    with (
        patch(
            "homeassistant.components.system_bridge.coordinator.WebSocketClient",
            autospec=True,
        ) as mock_websocket_client,
        patch(
            "homeassistant.components.system_bridge.config_flow.WebSocketClient",
            new=mock_websocket_client,
        ),
    ):
        websocket_client = mock_websocket_client.return_value
        websocket_client.connected = False
        websocket_client.get_data.return_value = Response(
            id=FIXTURE_REQUEST_ID,
            type=TYPE_DATA_GET,
            message="Getting data",
            data={EVENT_MODULES: get_data_model.modules},
        )
        websocket_client.register_data_listener.return_value = Response(
            id=FIXTURE_REQUEST_ID,
            type=TYPE_DATA_LISTENER_REGISTERED,
            message="Data listener registered",
            data={EVENT_MODULES: register_data_listener_model.modules},
        )
        # Trigger callback when listener is registered
        websocket_client.listen.side_effect = mock_data_listener

        websocket_client.get_directories.return_value = [
            MediaDirectory(
                key="testdirectory",
                path="testdirectory",
            )
        ]
        media_file = MediaFile(
            name="testfile.txt",
            path="testdirectory/testfile.txt",
            fullpath="/home/user/testdirectory/testfile.txt",
            size=100,
            last_accessed=1630000000,
            created=1630000000,
            modified=1630000000,
            is_directory=False,
            is_file=True,
            is_link=False,
            mime_type="text/plain",
        )
        websocket_client.get_files.return_value = MediaFiles(
            files=[media_file], path="testdirectory"
        )
        websocket_client.get_file.return_value = media_file

        websocket_client.open_path.return_value = FIXTURE_GENERIC_RESPONSE
        websocket_client.power_shutdown.return_value = FIXTURE_GENERIC_RESPONSE
        websocket_client.open_url.return_value = FIXTURE_GENERIC_RESPONSE
        websocket_client.keyboard_keypress.return_value = FIXTURE_GENERIC_RESPONSE
        websocket_client.keyboard_text.return_value = FIXTURE_GENERIC_RESPONSE

        yield websocket_client


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_version: MagicMock,
    mock_websocket_client: MagicMock,
) -> MockConfigEntry:
    """Initialize the System Bridge integration."""
    assert await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state == ConfigEntryState.LOADED

    return mock_config_entry
