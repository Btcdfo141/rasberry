"""Integration tests for the auth component."""
from datetime import timedelta
from unittest.mock import patch

from homeassistant.auth.models import Credentials
from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow
from homeassistant.components import auth

from . import async_setup_auth

from tests.common import CLIENT_ID, CLIENT_REDIRECT_URI


async def test_login_new_user_and_trying_refresh_token(hass, aiohttp_client):
    """Test logging in with new user and refreshing tokens."""
    client = await async_setup_auth(hass, aiohttp_client, setup_api=True)
    resp = await client.post('/auth/login_flow', json={
        'client_id': CLIENT_ID,
        'handler': ['insecure_example', None],
        'redirect_uri': CLIENT_REDIRECT_URI,
    })
    assert resp.status == 200
    step = await resp.json()

    resp = await client.post(
        '/auth/login_flow/{}'.format(step['flow_id']), json={
            'client_id': CLIENT_ID,
            'username': 'test-user',
            'password': 'test-pass',
        })

    assert resp.status == 200
    step = await resp.json()
    code = step['result']

    # Exchange code for tokens
    resp = await client.post('/auth/token', data={
        'client_id': CLIENT_ID,
        'grant_type': 'authorization_code',
        'code': code
    })

    # User is not active
    assert resp.status == 403
    data = await resp.json()
    assert data['error'] == 'access_denied'
    assert data['error_description'] == 'User is not active'


def test_credential_store_expiration():
    """Test that the credential store will not return expired tokens."""
    store, retrieve = auth._create_cred_store()
    client_id = 'bla'
    credentials = 'creds'
    now = utcnow()

    with patch('homeassistant.util.dt.utcnow', return_value=now):
        code = store(client_id, credentials)

    with patch('homeassistant.util.dt.utcnow',
               return_value=now + timedelta(minutes=10)):
        assert retrieve(client_id, code) is None

    with patch('homeassistant.util.dt.utcnow', return_value=now):
        code = store(client_id, credentials)

    with patch('homeassistant.util.dt.utcnow',
               return_value=now + timedelta(minutes=9, seconds=59)):
        assert retrieve(client_id, code) == credentials


async def test_ws_current_user(hass, hass_ws_client, hass_access_token):
    """Test the current user command with homeassistant creds."""
    assert await async_setup_component(hass, 'auth', {
        'http': {
            'api_password': 'bla'
        }
    })

    user = hass_access_token.refresh_token.user
    credential = Credentials(auth_provider_type='homeassistant',
                             auth_provider_id=None,
                             data={}, id='test-id')
    user.credentials.append(credential)
    assert len(user.credentials) == 1

    with patch('homeassistant.auth.AuthManager.active', return_value=True):
        client = await hass_ws_client(hass, hass_access_token)

    await client.send_json({
        'id': 5,
        'type': auth.WS_TYPE_CURRENT_USER,
    })

    result = await client.receive_json()
    assert result['success'], result

    user_dict = result['result']

    assert user_dict['name'] == user.name
    assert user_dict['id'] == user.id
    assert user_dict['is_owner'] == user.is_owner
    assert len(user_dict['credentials']) == 1

    hass_cred = user_dict['credentials'][0]
    assert hass_cred['auth_provider_type'] == 'homeassistant'
    assert hass_cred['auth_provider_id'] is None
    assert 'data' not in hass_cred


async def test_cors_on_token(hass, aiohttp_client):
    """Test logging in with new user and refreshing tokens."""
    client = await async_setup_auth(hass, aiohttp_client)

    resp = await client.options('/auth/token', headers={
        'origin': 'http://example.com',
        'Access-Control-Request-Method': 'POST',
    })
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://example.com'
    assert resp.headers['Access-Control-Allow-Methods'] == 'POST'

    resp = await client.post('/auth/token', headers={
        'origin': 'http://example.com'
    })
    assert resp.headers['Access-Control-Allow-Origin'] == 'http://example.com'
