"""Refoss devices platform loader."""
from __future__ import annotations

from collections.abc import Collection
from datetime import timedelta

from refoss_ha.const import (
    DEVICE_LIST_COORDINATOR,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    SOCKET_DISCOVER_UPDATE_INTERVAL,
)
from refoss_ha.http_device import HttpDeviceInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant

from .coordinator import RefossCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""
    if not config_entry.data.get(CONF_MAC):
        LOGGER.warning(
            (
                "The config entry %s probably comes from a custom integration, please"
                " remove it if you want to use core refoss integration"
            ),
            config_entry.title,
        )
        return False
    hass.data.setdefault(DOMAIN, {})

    refoss_coordinator = RefossCoordinator(
        hass=hass,
        update_interval=timedelta(seconds=SOCKET_DISCOVER_UPDATE_INTERVAL),
    )
    try:
        await refoss_coordinator.initial_setup()
    except ValueError as e:
        LOGGER.warning("Initial_setup failed: %s", e)
        return False

    hass.data[DOMAIN][config_entry.entry_id] = {
        DEVICE_LIST_COORDINATOR: refoss_coordinator,
        "ADDED_ENTITIES_IDS": set(),
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    def _poll_discovered_device():
        # Poll discovered devices.
        discovered_devices = refoss_coordinator.data
        known_devices = refoss_coordinator.find_devices()

        if _check_new_discovered_device(known_devices, discovered_devices.values()):
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
            )

    refoss_coordinator.async_add_listener(_poll_discovered_device)
    return True


def _check_new_discovered_device(
    known: Collection[HttpDeviceInfo], discovered: Collection[HttpDeviceInfo]
) -> bool:
    known_devices = {dev.uuid: dev for dev in known}
    for dev in discovered:
        if dev.uuid not in known_devices:
            LOGGER.debug(
                f"Add new device: device_type:{dev.device_type},ip: {dev.inner_ip}"
            )
            return True
        known_device = known_devices[dev.uuid]
        if known_device.inner_ip != dev.inner_ip:
            LOGGER.debug(
                f"device_type:{known_device.device_type}, update device, ip: {known_device.inner_ip} => {dev.inner_ip}"
            )
            return True
    return False


async def async_unload_entry(hass, entry):
    """Async unload hass config entry."""
    refoss_coordinator: RefossCoordinator = hass.data[DOMAIN][entry.entry_id][
        DEVICE_LIST_COORDINATOR
    ]
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        refoss_coordinator.socket.stopReveiveMsg()
        for task in refoss_coordinator.tasks:
            task.cancel()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
