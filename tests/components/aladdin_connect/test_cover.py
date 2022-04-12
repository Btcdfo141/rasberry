"""Test the Aladdin Connect Cover."""
from unittest.mock import MagicMock, patch

from homeassistant.components.aladdin_connect.const import DOMAIN
import homeassistant.components.aladdin_connect.cover as cover
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

YAML_CONFIG = {"username": "test-user", "password": "test-password"}
DEVICE_CONFIG = {
    "device_id": 533255,
    "door_number": 1,
    "name": "home",
    "status": "open",
    "link_status": "Connected",
}


async def test_setup_component_authfailed(hass: HomeAssistant) -> None:
    """Test component setup."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_component_typeerror(hass: HomeAssistant) -> None:
    """Test component setup TypeError."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        side_effect=TypeError,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_component_keyerror(hass: HomeAssistant) -> None:
    """Test component setup KeyError."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        side_effect=KeyError,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_component_nameerror(hass: HomeAssistant) -> None:
    """Test component setup Namerror."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        side_effect=NameError,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_component_valueerror(hass: HomeAssistant) -> None:
    """Test component setup ValueError."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        side_effect=ValueError,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_component_noerror(hass: HomeAssistant) -> None:
    """Test component setup KeyError."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        return_value=True,
    ), patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_doors",
        return_value=[DEVICE_CONFIG],
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_import(hass: HomeAssistant) -> None:
    """Testing the import function of Aladdin Connect entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        return_value=True,
    ), patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_doors",
        return_value=[DEVICE_CONFIG],
    ):
        await async_setup_component(hass, DOMAIN, config_entry)


async def test_load_and_unload(hass: HomeAssistant) -> None:
    """Test loading and unloading Aladdin Connect entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        return_value=True,
    ), patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_doors",
        return_value=[DEVICE_CONFIG],
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1

    entities = hass.states.async_entity_ids(Platform.COVER)
    for entity in entities:
        assert hass.states.get(entity).state != STATE_UNAVAILABLE

    assert await config_entry.async_unload(hass)
    await hass.async_block_till_done()
    assert config_entry.state == ConfigEntryState.NOT_LOADED

    entities = hass.states.async_entity_ids(Platform.COVER)
    for entity in entities:
        assert hass.states.get(entity).state == STATE_UNAVAILABLE


async def test_open_cover(hass: HomeAssistant) -> None:
    """Test component setup KeyError."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=YAML_CONFIG,
        unique_id="test-id",
    )
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.login",
        return_value=True,
    ), patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_doors",
        return_value=[DEVICE_CONFIG],
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert COVER_DOMAIN in hass.config.components

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.open_door",
        return_value=True,
    ):
        await hass.services.async_call(
            "cover", "open_cover", {"entity_id": "cover.home"}, blocking=True
        )

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.close_door",
        return_value=True,
    ):
        await hass.services.async_call(
            "cover", "close_cover", {"entity_id": "cover.home"}, blocking=True
        )
    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_door_status",
        return_value=STATE_CLOSED,
    ):
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": "cover.home"}, blocking=True
        )
    assert hass.states.get("cover.home").state == STATE_CLOSED

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_door_status",
        return_value=STATE_OPEN,
    ):
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": "cover.home"}, blocking=True
        )
    assert hass.states.get("cover.home").state == STATE_OPEN

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_door_status",
        return_value=STATE_OPENING,
    ):
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": "cover.home"}, blocking=True
        )
    assert hass.states.get("cover.home").state == STATE_OPENING

    with patch(
        "homeassistant.components.aladdin_connect.cover.AladdinConnectClient.get_door_status",
        return_value=STATE_CLOSING,
    ):
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": "cover.home"}, blocking=True
        )
    assert hass.states.get("cover.home").state == STATE_CLOSING


async def test_yaml_info_cover(hass):
    """Test setup YAML import."""
    assert COVER_DOMAIN not in hass.config.components
    hass.async_create_task = MagicMock()
    await cover.async_setup_platform(hass, YAML_CONFIG, None)
    await hass.async_block_till_done()
