"""Test HomematicIP Cloud accesspoint."""

from asynctest import Mock, patch
from homematicip.aio.auth import AsyncAuth
from homematicip.base.base_connection import HmipConnectionError
import pytest

from homeassistant.components.homematicip_cloud import (
    DOMAIN as HMIPC_DOMAIN,
    const,
    errors,
    hap as hmipc,
)
from homeassistant.components.homematicip_cloud.hap import (
    HomematicipAuth,
    HomematicipHAP,
)
from homeassistant.exceptions import ConfigEntryNotReady

from .helper import HAPID, HAPPIN

from tests.common import mock_coro, mock_coro_func


async def test_auth_setup(hass):
    """Test auth setup for client registration."""
    config = {
        const.HMIPC_HAPID: "ABC123",
        const.HMIPC_PIN: "123",
        const.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipAuth(hass, config)
    with patch.object(hap, "get_auth", return_value=mock_coro()):
        assert await hap.async_setup() is True


async def test_auth_setup_connection_error(hass):
    """Test auth setup connection error behaviour."""
    config = {
        const.HMIPC_HAPID: "ABC123",
        const.HMIPC_PIN: "123",
        const.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipAuth(hass, config)
    with patch.object(hap, "get_auth", side_effect=errors.HmipcConnectionError):
        assert await hap.async_setup() is False


async def test_auth_auth_check_and_register(hass):
    """Test auth client registration."""
    config = {
        const.HMIPC_HAPID: "ABC123",
        const.HMIPC_PIN: "123",
        const.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipAuth(hass, config)
    hap.auth = Mock()
    with patch.object(
        hap.auth, "isRequestAcknowledged", return_value=mock_coro(True)
    ), patch.object(
        hap.auth, "requestAuthToken", return_value=mock_coro("ABC")
    ), patch.object(
        hap.auth, "confirmAuthToken", return_value=mock_coro()
    ):
        assert await hap.async_checkbutton() is True
        assert await hap.async_register() == "ABC"


async def test_auth_auth_check_and_register_with_exception(hass):
    """Test auth client registration."""
    config = {
        const.HMIPC_HAPID: "ABC123",
        const.HMIPC_PIN: "123",
        const.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipAuth(hass, config)
    hap.auth = Mock(spec=AsyncAuth)
    with patch.object(
        hap.auth, "isRequestAcknowledged", side_effect=HmipConnectionError
    ), patch.object(hap.auth, "requestAuthToken", side_effect=HmipConnectionError):
        assert await hap.async_checkbutton() is False
        assert await hap.async_register() is False


async def test_hap_setup_works(aioclient_mock):
    """Test a successful setup of a accesspoint."""
    hass = Mock()
    entry = Mock()
    home = Mock()
    entry.data = {
        hmipc.HMIPC_HAPID: "ABC123",
        hmipc.HMIPC_AUTHTOKEN: "123",
        hmipc.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipHAP(hass, entry)
    with patch.object(hap, "get_hap", return_value=mock_coro(home)):
        assert await hap.async_setup() is True

    assert hap.home is home
    assert len(hass.config_entries.async_forward_entry_setup.mock_calls) == 8
    assert hass.config_entries.async_forward_entry_setup.mock_calls[0][1] == (
        entry,
        "alarm_control_panel",
    )
    assert hass.config_entries.async_forward_entry_setup.mock_calls[1][1] == (
        entry,
        "binary_sensor",
    )


async def test_hap_setup_connection_error():
    """Test a failed accesspoint setup."""
    hass = Mock()
    entry = Mock()
    entry.data = {
        hmipc.HMIPC_HAPID: "ABC123",
        hmipc.HMIPC_AUTHTOKEN: "123",
        hmipc.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipHAP(hass, entry)
    with patch.object(
        hap, "get_hap", side_effect=errors.HmipcConnectionError
    ), pytest.raises(ConfigEntryNotReady):
        await hap.async_setup()

    assert not hass.async_add_job.mock_calls
    assert not hass.config_entries.flow.async_init.mock_calls


async def test_hap_reset_unloads_entry_if_setup():
    """Test calling reset while the entry has been setup."""
    hass = Mock()
    entry = Mock()
    home = Mock()
    home.disable_events = mock_coro_func()
    entry.data = {
        hmipc.HMIPC_HAPID: "ABC123",
        hmipc.HMIPC_AUTHTOKEN: "123",
        hmipc.HMIPC_NAME: "hmip",
    }
    hap = hmipc.HomematicipHAP(hass, entry)
    with patch.object(hap, "get_hap", return_value=mock_coro(home)):
        assert await hap.async_setup() is True

    assert hap.home is home
    assert not hass.services.async_register.mock_calls
    assert len(hass.config_entries.async_forward_entry_setup.mock_calls) == 8

    hass.config_entries.async_forward_entry_unload.return_value = mock_coro(True)
    await hap.async_reset()

    assert len(hass.config_entries.async_forward_entry_unload.mock_calls) == 8


@patch("homematicip.aio.home.AsyncHome.__init__", Mock(return_value=None))
@patch("homematicip.aio.home.AsyncHome.init", Mock(return_value=mock_coro(None)))
@patch(
    "homematicip.aio.home.AsyncHome.get_current_state",
    Mock(return_value=mock_coro(None)),
)
@patch(
    "homematicip.aio.home.AsyncHome.download_configuration",
    Mock(return_value=mock_coro("")),
)
@patch(
    "homematicip.aio.home.AsyncHome.set_auth_token", Mock(return_value=mock_coro(None))
)
@patch("homematicip.aio.home.AsyncHome.on_update", Mock())
@patch("homematicip.aio.home.AsyncHome.on_create", Mock())
@patch("homematicip.aio.home.AsyncHome.on_remove", Mock())
@patch("homematicip.aio.home.AsyncHome.devices", new=[], create=True)
@patch("homematicip.aio.home.AsyncHome.groups", new=[], create=True)
@patch("homematicip.aio.home.AsyncHome.location", Mock(), create=True)
@patch("homematicip.aio.home.AsyncHome.weather", Mock(), create=True)
@patch("homematicip.aio.home.AsyncHome.id", Mock(), create=True)
@patch("homematicip.aio.home.AsyncHome.connected", Mock(), create=True)
@patch("homematicip.aio.home.AsyncHome.dutyCycle", Mock(), create=True)
@patch("homeassistant.helpers.temperature.display_temp", Mock(return_value=12))
@patch("homeassistant.components.weather.WeatherEntity.state_attributes", new={})
@patch(
    "homeassistant.helpers.storage.Store._async_callback_stop_write",
    Mock(return_value=mock_coro(None)),
)
@patch(
    "homeassistant.helpers.storage.Store._async_handle_write_data",
    Mock(return_value=mock_coro(None)),
)
async def test_hap_create(hass, hmip_config_entry):
    """Mock AsyncHome to execute get_hap."""
    hass.config.components.add(HMIPC_DOMAIN)
    hap = HomematicipHAP(hass, hmip_config_entry)
    assert hap
    hap.async_connect = Mock(return_value=mock_coro(None))
    hass.data[HMIPC_DOMAIN] = {HAPID: hap}
    assert await hap.async_setup()
    await hass.async_block_till_done()


@patch("homematicip.aio.auth.AsyncAuth.__init__", Mock(return_value=None))
@patch("homematicip.aio.auth.AsyncAuth.init", Mock(return_value=mock_coro(None)))
@patch("homematicip.aio.auth.AsyncAuth.pin", Mock(), create=True)
@patch(
    "homematicip.aio.auth.AsyncAuth.connectionRequest",
    Mock(return_value=mock_coro(None)),
)
async def test_auth_create(hass, hmip_config):
    """Mock AsyncAuth to execute get_auth."""
    auth = HomematicipAuth(hass, hmip_config)
    assert auth
    assert await auth.async_setup()

    await hass.async_block_till_done()

    res = await auth.get_auth(hass, HAPID, HAPPIN)
    assert res.pin == HAPPIN


@patch("homematicip.aio.auth.AsyncAuth.__init__", Mock(return_value=None))
@patch("homematicip.aio.auth.AsyncAuth.init", Mock(return_value=mock_coro(None)))
@patch("homematicip.aio.auth.AsyncAuth.pin", Mock(), create=True)
@patch(
    "homematicip.aio.auth.AsyncAuth.connectionRequest",
    Mock(side_effect=HmipConnectionError),
)
async def test_auth_create_exception(hass, hmip_config):
    """Mock AsyncAuth to execute get_auth."""
    auth = HomematicipAuth(hass, hmip_config)
    assert auth
    assert await auth.async_setup()

    await hass.async_block_till_done()

    assert not await auth.get_auth(hass, HAPID, HAPPIN)
