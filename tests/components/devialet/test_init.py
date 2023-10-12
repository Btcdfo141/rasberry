"""Test the Devialet init."""
from homeassistant.components.devialet.const import DOMAIN
from homeassistant.components.media_player import DOMAIN as MP_DOMAIN, MediaPlayerState
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from . import SERIAL, setup_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_load_unload_config_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the Devialet configuration entry loading and unloading."""
    entry = await setup_integration(hass, aioclient_mock)

    assert entry.entry_id in hass.data[DOMAIN]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id is not None

    state = hass.states.get(f"{MP_DOMAIN}.{DOMAIN}_{SERIAL.lower()}")
    assert state.state == MediaPlayerState.PLAYING

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data[DOMAIN]
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_load_unload_config_entry_when_device_offline(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the Devialet configuration entry loading and unloading when the device is offline."""
    entry = await setup_integration(hass, aioclient_mock, state=MediaPlayerState.OFF)

    assert entry.entry_id in hass.data[DOMAIN]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id is not None

    state = hass.states.get(f"{MP_DOMAIN}.{DOMAIN}_{SERIAL.lower()}")
    assert state.state == MediaPlayerState.OFF

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data[DOMAIN]
    assert entry.state is ConfigEntryState.NOT_LOADED
