"""Fixtures for Jellyfin integration tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from jellyfin_apiclient_python import JellyfinClient
from jellyfin_apiclient_python.api import API
from jellyfin_apiclient_python.configuration import Config
from jellyfin_apiclient_python.connection_manager import ConnectionManager
import pytest

from .const import (
    MOCK_SUCCESFUL_CONNECTION_STATE,
    MOCK_SUCCESFUL_LOGIN_RESPONSE,
    MOCK_USER_SETTINGS,
)


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.jellyfin.async_setup_entry", return_value=True
    ) as setup_mock:
        yield setup_mock


@pytest.fixture
def mock_client_device_id() -> Generator[None, MagicMock, None]:
    """Mock generating device id."""
    with patch(
        "homeassistant.components.jellyfin.config_flow._generate_client_device_id"
    ) as id_mock:
        id_mock.return_value = "TEST-UUID"
        yield id_mock


@pytest.fixture
def mock_auth() -> MagicMock:
    """Return a mocked ConnectionManager."""
    jf_auth = create_autospec(ConnectionManager)
    jf_auth.connect_to_address.return_value = MOCK_SUCCESFUL_CONNECTION_STATE
    jf_auth.login.return_value = MOCK_SUCCESFUL_LOGIN_RESPONSE

    return jf_auth


@pytest.fixture
def mock_api() -> MagicMock:
    """Return a mocked API."""
    jf_api = create_autospec(API)
    jf_api.get_user_settings.return_value = MOCK_USER_SETTINGS

    return jf_api


@pytest.fixture
def mock_config() -> MagicMock:
    """Return a mocked JellyfinClient."""
    jf_config = create_autospec(Config)
    jf_config.data = {}

    return jf_config


@pytest.fixture
def mock_client(
    mock_config: MagicMock, mock_auth: MagicMock, mock_api: MagicMock
) -> MagicMock:
    """Return a mocked JellyfinClient."""
    jf_client = create_autospec(JellyfinClient)
    jf_client.auth = mock_auth
    jf_client.config = mock_config
    jf_client.jellyfin = mock_api

    return jf_client


@pytest.fixture
def mock_jellyfin(mock_client: MagicMock) -> Generator[None, MagicMock, None]:
    """Return a mocked Jellyfin."""
    with patch(
        "homeassistant.components.jellyfin.client_wrapper.Jellyfin", autospec=True
    ) as jellyfin_mock:
        jf = jellyfin_mock.return_value
        jf.get_client.return_value = mock_client

        yield jf
