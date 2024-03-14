"""Tests for the Sonos Media Player platform."""

import pytest

from homeassistant.components.media_player import (
    DOMAIN as MP_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerEnqueue,
)
from homeassistant.components.media_player.const import ATTR_MEDIA_ENQUEUE
from homeassistant.components.sonos.media_player import LONG_SERVICE_TIMEOUT
from homeassistant.const import STATE_IDLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    CONNECTION_UPNP,
    DeviceRegistry,
)

from .conftest import SoCoMockFactory


async def test_device_registry(
    hass: HomeAssistant, device_registry: DeviceRegistry, async_autosetup_sonos, soco
) -> None:
    """Test sonos device registered in the device registry."""
    reg_device = device_registry.async_get_device(
        identifiers={("sonos", "RINCON_test")}
    )
    assert reg_device is not None
    assert reg_device.model == "Model Name"
    assert reg_device.sw_version == "13.1"
    assert reg_device.connections == {
        (CONNECTION_NETWORK_MAC, "00:11:22:33:44:55"),
        (CONNECTION_UPNP, "uuid:RINCON_test"),
    }
    assert reg_device.manufacturer == "Sonos"
    assert reg_device.name == "Zone A"
    # Default device provides battery info, area should not be suggested
    assert reg_device.suggested_area is None


async def test_device_registry_not_portable(
    hass: HomeAssistant, device_registry: DeviceRegistry, async_setup_sonos, soco
) -> None:
    """Test non-portable sonos device registered in the device registry to ensure area suggested."""
    soco.get_battery_info.return_value = {}
    await async_setup_sonos()

    reg_device = device_registry.async_get_device(
        identifiers={("sonos", "RINCON_test")}
    )
    assert reg_device is not None
    assert reg_device.suggested_area == "Zone A"


async def test_entity_basic(
    hass: HomeAssistant, async_autosetup_sonos, discover
) -> None:
    """Test basic state and attributes."""
    state = hass.states.get("media_player.zone_a")
    assert state.state == STATE_IDLE
    attributes = state.attributes
    assert attributes["friendly_name"] == "Zone A"
    assert attributes["is_volume_muted"] is False
    assert attributes["volume_level"] == 0.19


@pytest.mark.parametrize(
    ("media_content_type", "media_content_id", "enqueue", "test_result"),
    [
        (
            "artist",
            "A:ALBUMARTIST/Beatles",
            MediaPlayerEnqueue.REPLACE,
            {
                "title": "All",
                "item_id": "A:ALBUMARTIST/Beatles/",
                "clear_queue": 1,
                "position": None,
                "play": 1,
                "play_pos": 0,
            },
        ),
        (
            "genre",
            "A:GENRE/Classic%20Rock",
            MediaPlayerEnqueue.ADD,
            {
                "title": "All",
                "item_id": "A:GENRE/Classic%20Rock/",
                "clear_queue": 0,
                "position": None,
                "play": 0,
                "play_pos": 0,
            },
        ),
        (
            "album",
            "A:ALBUM/Abbey%20Road",
            MediaPlayerEnqueue.NEXT,
            {
                "title": "Abbey Road",
                "item_id": "A:ALBUM/Abbey%20Road",
                "clear_queue": 0,
                "position": 1,
                "play": 0,
                "play_pos": 0,
            },
        ),
        (
            "composer",
            "A:COMPOSER/Carlos%20Santana",
            MediaPlayerEnqueue.PLAY,
            {
                "title": "All",
                "item_id": "A:COMPOSER/Carlos%20Santana/",
                "clear_queue": 0,
                "position": 1,
                "play": 1,
                "play_pos": 9,
            },
        ),
        (
            "artist",
            "A:ALBUMARTIST/Beatles/Abbey%20Road",
            MediaPlayerEnqueue.REPLACE,
            {
                "title": "Abbey Road",
                "item_id": "A:ALBUMARTIST/Beatles/Abbey%20Road",
                "clear_queue": 1,
                "position": None,
                "play": 1,
                "play_pos": 0,
            },
        ),
    ],
)
async def test_play_media_library(
    hass: HomeAssistant,
    soco_factory: SoCoMockFactory,
    async_autosetup_sonos,
    media_content_type,
    media_content_id,
    enqueue,
    test_result,
) -> None:
    """Test playing local library with a variety of options."""
    sock_mock = soco_factory.mock_list.get("192.168.42.2")
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.zone_a",
            "media_content_type": media_content_type,
            "media_content_id": media_content_id,
            ATTR_MEDIA_ENQUEUE: enqueue,
        },
        blocking=True,
    )
    assert sock_mock.clear_queue.call_count == test_result["clear_queue"]
    assert sock_mock.add_to_queue.call_count == 1
    assert (
        sock_mock.add_to_queue.call_args_list[0].args[0].title == test_result["title"]
    )
    assert (
        sock_mock.add_to_queue.call_args_list[0].args[0].item_id
        == test_result["item_id"]
    )
    if test_result["position"] is not None:
        assert (
            sock_mock.add_to_queue.call_args_list[0].kwargs["position"]
            == test_result["position"]
        )
    else:
        assert "position" not in sock_mock.add_to_queue.call_args_list[0].kwargs
    assert (
        sock_mock.add_to_queue.call_args_list[0].kwargs["timeout"]
        == LONG_SERVICE_TIMEOUT
    )
    assert sock_mock.play_from_queue.call_count == test_result["play"]
    if test_result["play"] != 0:
        assert (
            sock_mock.play_from_queue.call_args_list[0].args[0]
            == test_result["play_pos"]
        )
