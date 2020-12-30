"""Tests for the WLED integration."""

import json

from homeassistant.components.wled.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_MAC, CONTENT_TYPE_JSON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker


async def init_integration(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    rgbw: bool = False,
    skip_setup: bool = False,
    device_registry: DeviceRegistry = None,
) -> MockConfigEntry:
    """Set up the WLED integration in Home Assistant."""

    fixture = "wled/rgb.json" if not rgbw else "wled/rgbw.json"
    data = json.loads(load_fixture(fixture))

    aioclient_mock.get(
        "http://192.168.1.123:80/json/",
        json=data,
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    aioclient_mock.post(
        "http://192.168.1.123:80/json/state",
        json=data["state"],
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    aioclient_mock.get(
        "http://192.168.1.123:80/json/info",
        json=data["info"],
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    aioclient_mock.get(
        "http://192.168.1.123:80/json/state",
        json=data["state"],
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.123", CONF_MAC: data["info"]["mac"]},
        title="WLED Mock Config Entry",
    )

    entry.add_to_hass(hass)

    if device_registry is not None:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.data.get("mac"))},
            name=data["info"]["name"],
        )

    if not skip_setup:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry
