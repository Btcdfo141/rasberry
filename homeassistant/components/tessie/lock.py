"""Lock platform for Tessie integration."""

from __future__ import annotations

from typing import Any

from tessie_api import (
    disable_speed_limit,
    enable_speed_limit,
    lock,
    open_unlock_charge_port,
    unlock,
)

from homeassistant.components.automation import automations_with_entity
from homeassistant.components.lock import ATTR_CODE, LockEntity
from homeassistant.components.script import scripts_with_entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieChargeCableLockStates
from .coordinator import TessieStateUpdateCoordinator
from .entity import TessieEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie sensor platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        klass(vehicle.state_coordinator)
        for klass in (TessieLockEntity, TessieCableLockEntity, TessieSpeedLimitEntity)
        for vehicle in data
    )


class TessieLockEntity(TessieEntity, LockEntity):
    """Lock entity for Tessie."""

    def __init__(
        self,
        coordinator: TessieStateUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "vehicle_state_locked")

    @property
    def is_locked(self) -> bool | None:
        """Return the state of the Lock."""
        return self._value

    async def async_lock(self, **kwargs: Any) -> None:
        """Set new value."""
        await self.run(lock)
        self.set((self.key, True))

    async def async_unlock(self, **kwargs: Any) -> None:
        """Set new value."""
        await self.run(unlock)
        self.set((self.key, False))


class TessieSpeedLimitEntity(TessieEntity, LockEntity):
    """Speed Limit with PIN entity for Tessie."""

    _attr_code_format = r"^\d\d\d\d$"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: TessieStateUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "vehicle_state_speed_limit_mode_active")

    @property
    def is_locked(self) -> bool | None:
        """Return the state of the Lock."""
        return self._value

    async def async_lock(self, **kwargs: Any) -> None:
        """Enable speed limit with pin."""
        ir.async_create_issue(
            self.coordinator.hass,
            DOMAIN,
            "deprecated_speed_limit_locked",
            breaks_in_ha_version="2024.10.0",
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_speed_limit_locked",
        )
        code: str | None = kwargs.get(ATTR_CODE)
        if code:
            await self.run(enable_speed_limit, pin=code)
            self.set((self.key, True))

    async def async_unlock(self, **kwargs: Any) -> None:
        """Disable speed limit with pin."""
        ir.async_create_issue(
            self.coordinator.hass,
            DOMAIN,
            "deprecated_speed_limit_unlocked",
            breaks_in_ha_version="2024.10.0",
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_speed_limit_unlocked",
        )
        code: str | None = kwargs.get(ATTR_CODE)
        if code:
            await self.run(disable_speed_limit, pin=code)
            self.set((self.key, False))

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        entity_automations = automations_with_entity(self.hass, self.entity_id)
        entity_scripts = scripts_with_entity(self.hass, self.entity_id)
        for item in entity_automations + entity_scripts:
            ir.async_create_issue(
                self.coordinator.hass,
                DOMAIN,
                "deprecated_speed_limit_entity",
                breaks_in_ha_version="2024.10.0",
                is_fixable=True,
                is_persistent=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="deprecated_speed_limit_entity",
                translation_placeholders={"entity": self.entity_id, "item": item},
            )


class TessieCableLockEntity(TessieEntity, LockEntity):
    """Cable Lock entity for Tessie."""

    def __init__(
        self,
        coordinator: TessieStateUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charge_state_charge_port_latch")

    @property
    def is_locked(self) -> bool | None:
        """Return the state of the Lock."""
        return self._value == TessieChargeCableLockStates.ENGAGED

    async def async_lock(self, **kwargs: Any) -> None:
        """Charge cable Lock cannot be manually locked."""
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_cable",
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock charge cable lock."""
        await self.run(open_unlock_charge_port)
        self.set((self.key, TessieChargeCableLockStates.DISENGAGED))
