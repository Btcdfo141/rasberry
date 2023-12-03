"""Test the FastdotcomDataUpdateCoordindator."""
from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory

from homeassistant.components.fastdotcom.const import DOMAIN
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_fastdotcom_data_update_coordinator(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Test the update coordinator."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UNIQUE_TEST_ID",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    with patch(
        "homeassistant.components.fastdotcom.coordinator.fast_com",
    ):
        await hass.async_block_till_done()

    state = hass.states.get("sensor.fast_com_download")
    assert state is not None

    coordinator = hass.data[config_entry.domain][config_entry.entry_id]
    assert coordinator.last_update_success is True

    with patch(
        "homeassistant.components.fastdotcom.coordinator.fast_com",
        side_effect=Exception("Test error"),
    ):
        freezer.tick(timedelta(minutes=5, seconds=1))
        async_fire_time_changed(hass)
        await coordinator.async_refresh()

    state = hass.states.get("sensor.fast_com_download")
    assert state.state is STATE_UNAVAILABLE
