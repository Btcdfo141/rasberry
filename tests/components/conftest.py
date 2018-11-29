"""Fixtures for component testing."""
from unittest.mock import patch

import pytest

from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_READ_ONLY
from homeassistant.auth.providers import legacy_api_password, homeassistant
from homeassistant.setup import async_setup_component
from homeassistant.components.websocket_api.http import URL
from homeassistant.components.websocket_api.auth import (
    TYPE_AUTH, TYPE_AUTH_OK, TYPE_AUTH_REQUIRED)

from tests.common import MockUser, CLIENT_ID, mock_coro


@pytest.fixture(autouse=True)
def prevent_io():
    """Fixture to prevent certain I/O from happening."""
    with patch('homeassistant.components.http.ban.async_load_ip_bans_config',
               side_effect=lambda *args: mock_coro([])):
        yield


@pytest.fixture
def hass_ws_client(aiohttp_client):
    """Websocket client fixture connected to websocket server."""
    async def create_client(hass, access_token=None):
        """Create a websocket client."""
        assert await async_setup_component(hass, 'websocket_api')

        client = await aiohttp_client(hass.http.app)

        patches = []

        if access_token is None:
            patches.append(patch(
                'homeassistant.auth.AuthManager.active', return_value=False))
            patches.append(patch(
                'homeassistant.auth.AuthManager.support_legacy',
                return_value=True))
            patches.append(patch(
                'homeassistant.components.websocket_api.auth.'
                'validate_password', return_value=True))
        else:
            patches.append(patch(
                'homeassistant.auth.AuthManager.active', return_value=True))
            patches.append(patch(
                'homeassistant.components.http.auth.setup_auth'))

        for p in patches:
            p.start()

        try:
            websocket = await client.ws_connect(URL)
            auth_resp = await websocket.receive_json()
            assert auth_resp['type'] == TYPE_AUTH_REQUIRED

            if access_token is None:
                await websocket.send_json({
                    'type': TYPE_AUTH,
                    'api_password': 'bla'
                })
            else:
                await websocket.send_json({
                    'type': TYPE_AUTH,
                    'access_token': access_token
                })

            auth_ok = await websocket.receive_json()
            assert auth_ok['type'] == TYPE_AUTH_OK

        finally:
            for p in patches:
                p.stop()

        # wrap in client
        websocket.client = client
        return websocket

    return create_client


@pytest.fixture
def hass_access_token(hass, hass_admin_user):
    """Return an access token to access Home Assistant."""
    refresh_token = hass.loop.run_until_complete(
        hass.auth.async_create_refresh_token(hass_admin_user, CLIENT_ID))
    yield hass.auth.async_create_access_token(refresh_token)


@pytest.fixture
def hass_admin_user(hass, local_auth):
    """Return a Home Assistant admin user."""
    admin_group = hass.loop.run_until_complete(hass.auth.async_get_group(
        GROUP_ID_ADMIN))
    return MockUser(groups=[admin_group]).add_to_hass(hass)


@pytest.fixture
def hass_read_only_user(hass, local_auth):
    """Return a Home Assistant read only user."""
    read_only_group = hass.loop.run_until_complete(hass.auth.async_get_group(
        GROUP_ID_READ_ONLY))
    return MockUser(groups=[read_only_group]).add_to_hass(hass)


@pytest.fixture
def legacy_auth(hass):
    """Load legacy API password provider."""
    prv = legacy_api_password.LegacyApiPasswordAuthProvider(
        hass, hass.auth._store, {
            'type': 'legacy_api_password'
        }
    )
    hass.auth._providers[(prv.type, prv.id)] = prv


@pytest.fixture
def local_auth(hass):
    """Load local auth provider."""
    prv = homeassistant.HassAuthProvider(
        hass, hass.auth._store, {
            'type': 'homeassistant'
        }
    )
    hass.auth._providers[(prv.type, prv.id)] = prv


@pytest.fixture
def hass_client(hass, aiohttp_client, hass_access_token):
    """Return an authenticated HTTP client."""
    async def auth_client():
        """Return an authenticated client."""
        return await aiohttp_client(hass.http.app, headers={
            'Authorization': "Bearer {}".format(hass_access_token)
        })

    return auth_client
