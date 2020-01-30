"""Test Axis component setup process."""
from unittest.mock import Mock, patch

from homeassistant.components import axis
from homeassistant.setup import async_setup_component

from .test_device import ENTRY_CONFIG, MAC, setup_axis_integration

from tests.common import MockConfigEntry, mock_coro


async def test_setup_device_already_configured(hass):
    """Test already configured device does not configure a second."""
    with patch.object(hass, "config_entries") as mock_config_entries:

        assert await async_setup_component(
            hass,
            axis.DOMAIN,
            {axis.DOMAIN: {"device_name": {axis.CONF_HOST: "1.2.3.4"}}},
        )

    assert not mock_config_entries.flow.mock_calls


async def test_setup_no_config(hass):
    """Test setup without configuration."""
    assert await async_setup_component(hass, axis.DOMAIN, {})
    assert axis.DOMAIN not in hass.data


async def test_setup_entry(hass):
    """Test successful setup of entry."""
    await setup_axis_integration(hass)
    assert len(hass.data[axis.DOMAIN]) == 1
    assert MAC in hass.data[axis.DOMAIN]


async def test_setup_entry_fails(hass):
    """Test successful setup of entry."""
    entry = MockConfigEntry(
        domain=axis.DOMAIN, data={axis.CONF_MAC: "0123"}, options=True
    )

    mock_device = Mock()
    mock_device.async_setup.return_value = mock_coro(False)

    with patch.object(axis, "AxisNetworkDevice") as mock_device_class:
        mock_device_class.return_value = mock_device

        assert not await axis.async_setup_entry(hass, entry)

    assert not hass.data[axis.DOMAIN]


async def test_unload_entry(hass):
    """Test successful unload of entry."""
    device = await setup_axis_integration(hass)
    assert hass.data[axis.DOMAIN]

    assert await axis.async_unload_entry(hass, device.config_entry)
    assert not hass.data[axis.DOMAIN]


async def test_populate_options(hass):
    """Test successful populate options."""
    entry = MockConfigEntry(domain=axis.DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_hass(hass)

    with patch.object(axis, "get_device", return_value=mock_coro(Mock())):

        await axis.async_populate_options(hass, entry)

    assert entry.options == {
        axis.CONF_CAMERA: True,
        axis.CONF_EVENTS: True,
        axis.CONF_TRIGGER_TIME: axis.DEFAULT_TRIGGER_TIME,
    }


async def test_migrate_entry(hass):
    """Test successful migration of entry data."""
    legacy_config = {
        axis.CONF_DEVICE: {
            axis.CONF_HOST: "1.2.3.4",
            axis.CONF_USERNAME: "username",
            axis.CONF_PASSWORD: "password",
            axis.CONF_PORT: 80,
        },
        axis.CONF_MAC: "mac",
        axis.device.CONF_MODEL: "model",
        axis.device.CONF_NAME: "name",
    }
    entry = MockConfigEntry(domain=axis.DOMAIN, data=legacy_config)

    assert entry.data == legacy_config
    assert entry.version == 1

    await entry.async_migrate(hass)

    assert entry.data == {
        axis.CONF_DEVICE: {
            axis.CONF_HOST: "1.2.3.4",
            axis.CONF_USERNAME: "username",
            axis.CONF_PASSWORD: "password",
            axis.CONF_PORT: 80,
        },
        axis.CONF_HOST: "1.2.3.4",
        axis.CONF_USERNAME: "username",
        axis.CONF_PASSWORD: "password",
        axis.CONF_PORT: 80,
        axis.CONF_MAC: "mac",
        axis.device.CONF_MODEL: "model",
        axis.device.CONF_NAME: "name",
    }
    assert entry.version == 2
