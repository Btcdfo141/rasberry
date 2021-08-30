"""Test setup of zeversolar local integration."""
from unittest.mock import patch

from zeversolarlocal.api import SolarData

from homeassistant.components.zeversolar_local import async_unload_entry
from homeassistant.components.zeversolar_local.const import DOMAIN, ZEVER_INVERTER_ID
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_setup(hass: HomeAssistant):
    """Test a successful setup."""
    inverter_id = "abcd"
    entry_data = {
        CONF_URL: "http://1.1.1.1/home.cgi",
        ZEVER_INVERTER_ID: inverter_id,
        "title": "Zeversolar invertor.",
    }

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id="1234", data=entry_data)

    mock_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.zeversolar_local.config_flow.api.solardata",
        return_value=SolarData(daily_energy=1, current_power=2),
    ):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)

    total_energy_entity = registry.async_get("sensor.total_generated_energy")
    assert total_energy_entity
    assert inverter_id in total_energy_entity.unique_id
    generated_energy = hass.states.get("sensor.total_generated_energy")
    assert generated_energy.state == "1"

    current_power_entity = registry.async_get("sensor.current_solar_power_production")
    assert current_power_entity
    assert inverter_id in total_energy_entity.unique_id
    current_power = hass.states.get("sensor.current_solar_power_production")
    assert current_power.state == "2"


async def test_unload_entry(hass: HomeAssistant):
    """Test unloading the entry."""
    inverter_id = "abcd"
    entry_data = {
        CONF_URL: "http://1.1.1.1/home.cgi",
        ZEVER_INVERTER_ID: inverter_id,
        "title": "Zeversolar invertor.",
    }
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id="1234", data=entry_data)
    mock_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.zeversolar_local.config_flow.api.solardata",
        return_value=SolarData(daily_energy=1, current_power=2),
    ):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    result = await async_unload_entry(hass, mock_entry)
    assert result is True
