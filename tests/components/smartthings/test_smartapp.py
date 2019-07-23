"""Tests for the smartapp module."""
from uuid import uuid4

from asynctest import CoroutineMock, Mock, patch
from pysmartthings import AppEntity, Capability

from homeassistant.components.smartthings import smartapp
from homeassistant.components.smartthings.const import (
    CONF_INSTALLED_APP_ID, CONF_INSTALLED_APPS, CONF_LOCATION_ID,
    CONF_REFRESH_TOKEN, DATA_MANAGER, DOMAIN)

from tests.common import MockConfigEntry


async def test_update_app(hass, app):
    """Test update_app does not save if app is current."""
    await smartapp.update_app(hass, app)
    assert app.save.call_count == 0


async def test_update_app_updated_needed(hass, app):
    """Test update_app updates when an app is needed."""
    mock_app = Mock(AppEntity)
    mock_app.app_name = 'Test'

    await smartapp.update_app(hass, mock_app)

    assert mock_app.save.call_count == 1
    assert mock_app.app_name == 'Test'
    assert mock_app.display_name == app.display_name
    assert mock_app.description == app.description
    assert mock_app.webhook_target_url == app.webhook_target_url
    assert mock_app.app_type == app.app_type
    assert mock_app.single_instance == app.single_instance
    assert mock_app.classifications == app.classifications


async def test_smartapp_install_store_if_no_other(
        hass, smartthings_mock, device_factory):
    """Test aborts if no other app was configured already."""
    # Arrange
    app = Mock()
    app.app_id = uuid4()
    request = Mock()
    request.installed_app_id = str(uuid4())
    request.auth_token = str(uuid4())
    request.location_id = str(uuid4())
    request.refresh_token = str(uuid4())
    # Act
    await smartapp.smartapp_install(hass, request, None, app)
    # Assert
    entries = hass.config_entries.async_entries('smartthings')
    assert not entries
    data = hass.data[DOMAIN][CONF_INSTALLED_APPS][0]
    assert data[CONF_REFRESH_TOKEN] == request.refresh_token
    assert data[CONF_LOCATION_ID] == request.location_id
    assert data[CONF_INSTALLED_APP_ID] == request.installed_app_id


async def test_smartapp_install_creates_flow(
        hass, smartthings_mock, config_entry, location, device_factory):
    """Test installation creates flow."""
    # Arrange
    config_entry.add_to_hass(hass)
    app = Mock()
    app.app_id = config_entry.data['app_id']
    request = Mock()
    request.installed_app_id = str(uuid4())
    request.auth_token = str(uuid4())
    request.refresh_token = str(uuid4())
    request.location_id = location.location_id
    devices = [
        device_factory('', [Capability.battery, 'ping']),
        device_factory('', [Capability.switch, Capability.switch_level]),
        device_factory('', [Capability.switch])
    ]
    smartthings_mock.devices.return_value = devices
    # Act
    await smartapp.smartapp_install(hass, request, None, app)
    # Assert
    await hass.async_block_till_done()
    entries = hass.config_entries.async_entries('smartthings')
    assert len(entries) == 2
    assert entries[1].data['app_id'] == app.app_id
    assert entries[1].data['installed_app_id'] == request.installed_app_id
    assert entries[1].data['location_id'] == request.location_id
    assert entries[1].data['access_token'] == \
        config_entry.data['access_token']
    assert entries[1].data['refresh_token'] == request.refresh_token
    assert entries[1].data['client_secret'] == \
        config_entry.data['client_secret']
    assert entries[1].data['client_id'] == config_entry.data['client_id']
    assert entries[1].title == location.name


async def test_smartapp_update_saves_token(
        hass, smartthings_mock, location, device_factory):
    """Test update saves token."""
    # Arrange
    entry = MockConfigEntry(domain=DOMAIN, data={
        'installed_app_id': str(uuid4()),
        'app_id': str(uuid4())
    })
    entry.add_to_hass(hass)
    app = Mock()
    app.app_id = entry.data['app_id']
    request = Mock()
    request.installed_app_id = entry.data['installed_app_id']
    request.auth_token = str(uuid4())
    request.refresh_token = str(uuid4())
    request.location_id = location.location_id

    # Act
    await smartapp.smartapp_update(hass, request, None, app)
    # Assert
    assert entry.data[CONF_REFRESH_TOKEN] == request.refresh_token


async def test_smartapp_uninstall(hass, config_entry):
    """Test the config entry is unloaded when the app is uninstalled."""
    config_entry.add_to_hass(hass)
    app = Mock()
    app.app_id = config_entry.data['app_id']
    request = Mock()
    request.installed_app_id = config_entry.data['installed_app_id']

    with patch.object(hass.config_entries, 'async_remove') as remove:
        await smartapp.smartapp_uninstall(hass, request, None, app)
        assert remove.call_count == 1


async def test_smartapp_webhook(hass):
    """Test the smartapp webhook calls the manager."""
    manager = Mock()
    manager.handle_request = CoroutineMock(return_value={})
    hass.data[DOMAIN][DATA_MANAGER] = manager
    request = Mock()
    request.headers = []
    request.json = CoroutineMock(return_value={})
    result = await smartapp.smartapp_webhook(hass, '', request)

    assert result.body == b'{}'


async def test_smartapp_sync_subscriptions(
        hass, smartthings_mock, device_factory, subscription_factory):
    """Test synchronization adds and removes."""
    smartthings_mock.subscriptions.return_value = [
        subscription_factory(Capability.thermostat),
        subscription_factory(Capability.switch),
        subscription_factory(Capability.switch_level)
    ]
    devices = [
        device_factory('', [Capability.battery, 'ping']),
        device_factory('', [Capability.switch, Capability.switch_level]),
        device_factory('', [Capability.switch])
    ]

    await smartapp.smartapp_sync_subscriptions(
        hass, str(uuid4()), str(uuid4()), str(uuid4()), devices)

    assert smartthings_mock.subscriptions.call_count == 1
    assert smartthings_mock.delete_subscription.call_count == 1
    assert smartthings_mock.create_subscription.call_count == 1


async def test_smartapp_sync_subscriptions_up_to_date(
        hass, smartthings_mock, device_factory, subscription_factory):
    """Test synchronization does nothing when current."""
    smartthings_mock.subscriptions.return_value = [
        subscription_factory(Capability.battery),
        subscription_factory(Capability.switch),
        subscription_factory(Capability.switch_level)
    ]
    devices = [
        device_factory('', [Capability.battery, 'ping']),
        device_factory('', [Capability.switch, Capability.switch_level]),
        device_factory('', [Capability.switch])
    ]

    await smartapp.smartapp_sync_subscriptions(
        hass, str(uuid4()), str(uuid4()), str(uuid4()), devices)

    assert smartthings_mock.subscriptions.call_count == 1
    assert smartthings_mock.delete_subscription.call_count == 0
    assert smartthings_mock.create_subscription.call_count == 0


async def test_smartapp_sync_subscriptions_handles_exceptions(
        hass, smartthings_mock, device_factory, subscription_factory):
    """Test synchronization does nothing when current."""
    smartthings_mock.delete_subscription.side_effect = Exception
    smartthings_mock.create_subscription.side_effect = Exception
    smartthings_mock.subscriptions.return_value = [
        subscription_factory(Capability.battery),
        subscription_factory(Capability.switch),
        subscription_factory(Capability.switch_level)
    ]
    devices = [
        device_factory('', [Capability.thermostat, 'ping']),
        device_factory('', [Capability.switch, Capability.switch_level]),
        device_factory('', [Capability.switch])
    ]

    await smartapp.smartapp_sync_subscriptions(
        hass, str(uuid4()), str(uuid4()), str(uuid4()), devices)

    assert smartthings_mock.subscriptions.call_count == 1
    assert smartthings_mock.delete_subscription.call_count == 1
    assert smartthings_mock.create_subscription.call_count == 1
