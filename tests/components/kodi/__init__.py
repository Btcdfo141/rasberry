"""Tests for the Kodi integration."""
from homeassistant.components.kodi.const import CONF_WS_PORT, DOMAIN
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

from .util import MockConnection

from tests.async_mock import patch
from tests.common import MockConfigEntry


async def init_integration(hass) -> MockConfigEntry:
    """Set up the Kodi integration in Home Assistant."""
    entry_data = {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 8080,
        CONF_WS_PORT: 9090,
        CONF_USERNAME: "user",
        CONF_PASSWORD: "pass",
        CONF_SSL: False,
    }
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    with patch("homeassistant.components.kodi.Kodi.ping", return_value=True,), patch(
        "homeassistant.components.kodi.Kodi.get_application_properties",
        return_value={"version": {"major": 18, "minor": 18}},
    ), patch(
        "homeassistant.components.kodi.Kodi.get_application_properties",
        return_value={"version": {"major": 1, "minor": 1}},
    ), patch(
        "homeassistant.components.kodi.get_kodi_connection",
        return_value=MockConnection(),
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry
