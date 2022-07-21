"""The Govee Bluetooth integration."""
from __future__ import annotations

import logging

from govee_ble import GoveeBluetoothDeviceData

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothDataUpdateCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from .const import DOMAIN
from .sensor import sensor_update_to_bluetooth_data_update

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Govee BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None

    data = GoveeBluetoothDeviceData()

    @callback
    def _async_update_data(
        service_info: BluetoothServiceInfo,
    ) -> PassiveBluetoothDataUpdate:
        """Update data from Govee Bluetooth."""
        return sensor_update_to_bluetooth_data_update(data.update(service_info))

    hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = PassiveBluetoothDataUpdateCoordinator(
        hass,
        _LOGGER,
        update_method=_async_update_data,
        address=address,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
