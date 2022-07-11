"""Switches for the Elexa Guardian integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aioguardian.errors import GuardianError

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GuardianData, ValveControllerEntity, ValveControllerEntityDescription
from .const import API_VALVE_STATUS, API_WIFI_STATUS, DOMAIN

ATTR_AVG_CURRENT = "average_current"
ATTR_CONNECTED_CLIENTS = "connected_clients"
ATTR_INST_CURRENT = "instantaneous_current"
ATTR_INST_CURRENT_DDT = "instantaneous_current_ddt"
ATTR_STATION_CONNECTED = "station_connected"
ATTR_TRAVEL_COUNT = "travel_count"

SWITCH_KIND_ONBOARD_AP = "onboard_ap"
SWITCH_KIND_VALVE = "valve"


@dataclass
class ValveControllerSwitchDescription(
    SwitchEntityDescription, ValveControllerEntityDescription
):
    """Describe a Guardian valve controller switch."""


VALVE_CONTROLLER_DESCRIPTIONS = (
    ValveControllerSwitchDescription(
        key=SWITCH_KIND_ONBOARD_AP,
        name="Onboard AP",
        icon="mdi:wifi",
        entity_category=EntityCategory.CONFIG,
        api_category=API_WIFI_STATUS,
    ),
    ValveControllerSwitchDescription(
        key=SWITCH_KIND_VALVE,
        name="Valve controller",
        icon="mdi:water",
        api_category=API_VALVE_STATUS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Guardian switches based on a config entry."""
    data: GuardianData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ValveControllerSwitch(entry, data, description)
        for description in VALVE_CONTROLLER_DESCRIPTIONS
    )


class ValveControllerSwitch(ValveControllerEntity, SwitchEntity):
    """Define a base Guardian switch."""

    ON_STATES = {
        "start_opening",
        "opening",
        "finish_opening",
        "opened",
    }

    entity_description: ValveControllerSwitchDescription

    def __init__(
        self,
        entry: ConfigEntry,
        data: GuardianData,
        description: ValveControllerSwitchDescription,
    ) -> None:
        """Initialize."""
        super().__init__(entry, data.valve_controller_coordinators, description)

        self._client = data.client

    @callback
    def _async_update_from_latest_data(self) -> None:
        """Update the entity."""
        if self.entity_description.key == SWITCH_KIND_ONBOARD_AP:
            self._attr_extra_state_attributes.update(
                {
                    ATTR_CONNECTED_CLIENTS: self.coordinator.data.get("ap_clients"),
                    ATTR_STATION_CONNECTED: self.coordinator.data["station_connected"],
                }
            )
            self._attr_is_on = self.coordinator.data["ap_enabled"]
        elif self.entity_description.key == SWITCH_KIND_VALVE:
            self._attr_is_on = self.coordinator.data["state"] in self.ON_STATES
            self._attr_extra_state_attributes.update(
                {
                    ATTR_AVG_CURRENT: self.coordinator.data["average_current"],
                    ATTR_INST_CURRENT: self.coordinator.data["instantaneous_current"],
                    ATTR_INST_CURRENT_DDT: self.coordinator.data[
                        "instantaneous_current_ddt"
                    ],
                    ATTR_TRAVEL_COUNT: self.coordinator.data["travel_count"],
                }
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.entity_description.key == SWITCH_KIND_ONBOARD_AP:
            coro_func = self._client.wifi.disable_ap
        else:
            coro_func = self._client.valve.close

        try:
            async with self._client:
                await coro_func()
        except GuardianError as err:
            raise HomeAssistantError(
                f'Error while turning "{self.entity_id}" off: {err}'
            ) from err

        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.entity_description.key == SWITCH_KIND_ONBOARD_AP:
            coro_func = self._client.wifi.enable_ap
        else:
            coro_func = self._client.valve.open

        try:
            async with self._client:
                await coro_func()
        except GuardianError as err:
            raise HomeAssistantError(
                f'Error while turning "{self.entity_id}" on: {err}'
            ) from err

        self._attr_is_on = True
        self.async_write_ha_state()
