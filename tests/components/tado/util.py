"""Tests for the tado integration."""

import requests_mock

from homeassistant.components.tado import DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import load_fixture


async def async_init_integration(
    hass: HomeAssistant, skip_setup: bool = False,
):
    """Set up the tado integration in Home Assistant."""

    token_fixture = "tado/token.json"
    devices_fixture = "tado/devices.json"
    me_fixture = "tado/me.json"
    zones_fixture = "tado/zones.json"
    # Water Heater 2
    zone_4_state_fixture = "tado/tadov2.water_heater.heating.json"
    zone_4_capabilities_fixture = "tado/water_heater_zone_capabilities.json"

    # Smart AC
    zone_3_state_fixture = "tado/smartac3.cool_mode.json"
    zone_3_capabilities_fixture = "tado/zone_capabilities.json"

    # Water Heater
    zone_2_state_fixture = "tado/tadov2.water_heater.auto_mode.json"
    zone_2_capabilities_fixture = "tado/water_heater_zone_capabilities.json"

    zone_1_state_fixture = "tado/tadov2.heating.manual_mode.json"
    zone_1_capabilities_fixture = "tado/tadov2.zone_capabilities.json"

    with requests_mock.mock() as m:
        m.post("https://auth.tado.com/oauth/token", text=load_fixture(token_fixture))
        m.get(
            "https://my.tado.com/api/v2/me", text=load_fixture(me_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/devices",
            text=load_fixture(devices_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones",
            text=load_fixture(zones_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/4/capabilities",
            text=load_fixture(zone_4_capabilities_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/3/capabilities",
            text=load_fixture(zone_3_capabilities_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/2/capabilities",
            text=load_fixture(zone_2_capabilities_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/1/capabilities",
            text=load_fixture(zone_1_capabilities_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/4/state",
            text=load_fixture(zone_4_state_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/3/state",
            text=load_fixture(zone_3_state_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/2/state",
            text=load_fixture(zone_2_state_fixture),
        )
        m.get(
            "https://my.tado.com/api/v2/homes/1/zones/1/state",
            text=load_fixture(zone_1_state_fixture),
        )
        if not skip_setup:
            assert await async_setup_component(
                hass, DOMAIN, {DOMAIN: {CONF_USERNAME: "mock", CONF_PASSWORD: "mock"}}
            )
            await hass.async_block_till_done()
