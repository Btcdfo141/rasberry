"""Test emulated_roku component setup process."""
from unittest.mock import Mock, patch

from homeassistant.components import emulated_roku

from tests.common import mock_coro


async def test_setup_entry(hass):
    """Test setup entry is successful."""
    entry = Mock()
    entry.data = {
        emulated_roku.CONF_NAME: 'Emulated Roku Test',
        emulated_roku.CONF_LISTEN_PORT: 8060,
        emulated_roku.CONF_HOST_IP: '1.2.3.5',
        emulated_roku.CONF_ADVERTISE_IP: '1.2.3.4',
        emulated_roku.CONF_ADVERTISE_PORT: 8071,
        emulated_roku.CONF_UPNP_BIND_MULTICAST: False
    }
    with patch('emulated_roku.make_roku_api',
               return_value=mock_coro(((None, None), None))) as make_roku_api:
        assert await emulated_roku.async_setup_entry(hass, entry) is True

    assert len(make_roku_api.mock_calls) == 1
    assert hass.data[emulated_roku.DOMAIN]

    roku_instance = hass.data[emulated_roku.DOMAIN]['emulated_roku_test']

    assert roku_instance.roku_usn == 'Emulated Roku Test'
    assert roku_instance.host_ip == '1.2.3.5'
    assert roku_instance.listen_port == 8060
    assert roku_instance.advertise_ip == '1.2.3.4'
    assert roku_instance.advertise_port == 8071
    assert roku_instance.bind_multicast is False


async def test_unload_entry(hass):
    """Test being able to unload an entry."""
    entry = Mock()
    entry.data = {'name': 'Emulated Roku Test', 'listen_port': 8060}
    with patch('emulated_roku.make_roku_api',
               return_value=mock_coro(((None, None), None))):
        assert await emulated_roku.async_setup_entry(hass, entry) is True

    assert emulated_roku.DOMAIN in hass.data

    assert await emulated_roku.async_unload_entry(hass, entry)
    assert len(hass.data[emulated_roku.DOMAIN]) == 0
