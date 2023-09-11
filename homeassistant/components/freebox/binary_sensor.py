"""Support for Freebox devices (Freebox v6 and Freebox mini 4K)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FreeboxHomeCategory
from .home_base import FreeboxHomeEntity
from .router import FreeboxRouter

_LOGGER = logging.getLogger(__name__)


RAID_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="raid_degraded",
        name="degraded",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up binary sensors."""
    router: FreeboxRouter = hass.data[DOMAIN][entry.unique_id]
    binary_entities: list[BinarySensorEntity] = []

    _LOGGER.debug("%s - %s - %s raid(s)", router.name, router.mac, len(router.raids))

    binary_entities = [
        FreeboxRaidDegradedSensor(router, raid, description)
        for raid in router.raids.values()
        for description in RAID_SENSORS
    ]

    for node in router.home_devices.values():
        if node["category"] == FreeboxHomeCategory.PIR:
            binary_entities.append(FreeboxPirSensor(hass, router, node))
        elif node["category"] == FreeboxHomeCategory.DWS:
            binary_entities.append(FreeboxDwsSensor(hass, router, node))

        for endpoint in node["show_endpoints"]:
            if (
                endpoint["name"] == "cover"
                and endpoint["ep_type"] == "signal"
                and endpoint.get("value") is not None
            ):
                binary_entities.append(FreeboxCoverSensor(hass, router, node))

    if binary_entities:
        async_add_entities(binary_entities, True)


class FreeboxBinarySensor(FreeboxHomeEntity, BinarySensorEntity):
    """Representation of a Freebox binary sensor."""

    def __init__(
        self, hass: HomeAssistant, router: FreeboxRouter, node: dict[str, Any]
    ) -> None:
        """Initialize a Freebox binary sensor."""
        super().__init__(hass, router, node)
        self._command_trigger = self.get_command_id(
            node["type"]["endpoints"], "signal", "trigger"
        )

        self._detection = False

    async def async_update_signal(self):
        """Watch states."""
        detection = await self.get_home_endpoint_value(self._command_trigger)
        if detection is not None:
            if self._detection == detection:
                self._detection = not detection
                self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._detection


class FreeboxPirSensor(FreeboxBinarySensor):
    """Representation of a Freebox motion binary sensor."""

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.MOTION


class FreeboxDwsSensor(FreeboxBinarySensor):
    """Representation of a Freebox door opener binary sensor."""

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.DOOR


class FreeboxCoverSensor(FreeboxHomeEntity, BinarySensorEntity):
    """Representation of a cover Freebox plastic removal cover binary sensor (for some sensors: motion detector, door opener detector...)."""

    def __init__(
        self, hass: HomeAssistant, router: FreeboxRouter, node: dict[str, Any]
    ) -> None:
        """Initialize a cover for another device."""
        cover_node = next(
            filter(
                lambda x: (x["name"] == "cover" and x["ep_type"] == "signal"),
                node["type"]["endpoints"],
            ),
            None,
        )
        super().__init__(hass, router, node, cover_node)
        self._command_cover = self.get_command_id(
            node["type"]["endpoints"], "signal", "cover"
        )
        self._open = self.get_value("signal", "cover")

    @property
    def is_on(self) -> None:
        """Return true if the binary sensor is on."""
        return self._open

    async def async_update_node(self):
        """Update name & state."""
        self._open = self.get_value("signal", "cover")

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.SAFETY


class FreeboxRaidDegradedSensor(BinarySensorEntity):
    """Representation of a Freebox raid sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        router: FreeboxRouter,
        raid: dict[str, Any],
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a Freebox raid degraded sensor."""
        self.entity_description = description
        self._router = router
        self._attr_device_info = router.device_info
        self._raid = raid
        self._attr_name = f"Raid array {raid['id']} {description.name}"
        self._attr_unique_id = (
            f"{router.mac} {description.key} {raid['name']} {raid['id']}"
        )

    @callback
    def async_update_state(self) -> None:
        """Update the Freebox Raid sensor."""
        self._raid = self._router.raids[self._raid["id"]]

    @property
    def is_on(self) -> bool:
        """Return true if degraded."""
        return self._raid["degraded"]

    @callback
    def async_on_demand_update(self):
        """Update state."""
        self.async_update_state()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        self.async_update_state()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._router.signal_sensor_update,
                self.async_on_demand_update,
            )
        )
