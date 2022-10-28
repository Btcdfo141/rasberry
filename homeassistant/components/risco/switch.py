"""Support for bypassing Risco alarm zones."""
from __future__ import annotations

from pyrisco.common import Zone

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LocalData, RiscoDataUpdateCoordinator, is_local
from .const import DATA_COORDINATOR, DOMAIN
from .entity import RiscoCloudZoneEntity, RiscoLocalZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Risco alarm control panel."""
    if is_local(config_entry):
        local_data: LocalData = hass.data[DOMAIN][config_entry.entry_id]
        async_add_entities(
            RiscoLocalSwitch(local_data.system.id, zone_id, zone)
            for zone_id, zone in local_data.system.zones.items()
        )
    else:
        coordinator: RiscoDataUpdateCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
        ][DATA_COORDINATOR]
        async_add_entities(
            RiscoCloudSwitch(coordinator, zone_id, zone)
            for zone_id, zone in coordinator.data.zones.items()
        )


class RiscoCloudSwitch(SwitchEntity, RiscoCloudZoneEntity):
    """Representation of a bypass switch for a Risco cloud zone."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: RiscoDataUpdateCoordinator, zone_id: int, zone: Zone
    ) -> None:
        """Init the zone."""
        super().__init__(
            coordinator=coordinator,
            name="Bypassed",
            suffix="_bypassed",
            zone_id=zone_id,
            zone=zone,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the zone is bypassed."""
        return self._zone.bypassed

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._bypass(True)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._bypass(False)

    async def _bypass(self, bypass: bool) -> None:
        alarm = await self._risco.bypass_zone(self._zone_id, bypass)
        self._zone = alarm.zones[self._zone_id]
        self.async_write_ha_state()


class RiscoLocalSwitch(SwitchEntity, RiscoLocalZoneEntity):
    """Representation of a bypass switch for a Risco local zone."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, system_id: str, zone_id: int, zone: Zone) -> None:
        """Init the zone."""
        super().__init__(
            system_id=system_id,
            name="Bypassed",
            suffix="_bypassed",
            zone_id=zone_id,
            zone=zone,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the zone is bypassed."""
        return self._zone.bypassed

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._bypass(True)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._bypass(False)

    async def _bypass(self, bypass: bool) -> None:
        await self._zone.bypass(bypass)
