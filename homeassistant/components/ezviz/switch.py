"""Support for EZVIZ Switch sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyezviz.constants import DeviceSwitchType, SupportExt
from pyezviz.exceptions import HTTPError, PyEzvizError

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import EzvizDataUpdateCoordinator
from .entity import EzvizEntity


@dataclass
class EzvizSwitchEntityDescriptionMixin:
    """Mixin values for EZVIZ Switch entities."""

    supported_ext: str | None


@dataclass
class EzvizSwitchEntityDescription(
    SwitchEntityDescription, EzvizSwitchEntityDescriptionMixin
):
    """Describe a EZVIZ switch."""


SWITCH_TYPES: dict[int, EzvizSwitchEntityDescription] = {
    3: EzvizSwitchEntityDescription(
        key="3",
        name="Status light",
        translation_key="status_light",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=None,
    ),
    7: EzvizSwitchEntityDescription(
        key="7",
        name="Privacy",
        translation_key="privacy",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportPtzPrivacy.value),
    ),
    10: EzvizSwitchEntityDescription(
        key="10",
        name="Infrared light",
        translation_key="infrared_light",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportCloseInfraredLight.value),
    ),
    21: EzvizSwitchEntityDescription(
        key="21",
        name="Sleep",
        translation_key="sleep",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportSleep.value),
    ),
    22: EzvizSwitchEntityDescription(
        key="22",
        name="Audio",
        translation_key="audio",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportAudioOnoff.value),
    ),
    25: EzvizSwitchEntityDescription(
        key="25",
        name="Motion Tracking",
        translation_key="motion_tracking",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportIntelligentTrack.value),
    ),
    29: EzvizSwitchEntityDescription(
        key="29",
        name="All day video recording",
        translation_key="all_day_video_recording",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportFulldayRecord.value),
    ),
    32: EzvizSwitchEntityDescription(
        key="32",
        name="Auto sleep",
        translation_key="auto_sleep",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportAutoSleep.value),
    ),
    301: EzvizSwitchEntityDescription(
        key="301",
        name="Flicker light on movement",
        translation_key="flicker_light_on_movement",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportActiveDefense.value),
    ),
    305: EzvizSwitchEntityDescription(
        key="305",
        name="PIR motion activated light",
        translation_key="pir_motion_activated_light",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportLightRelate.value),
    ),
    306: EzvizSwitchEntityDescription(
        key="306",
        name="Tamper Alarm",
        translation_key="tamper_alarm",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportTamperAlarm.value),
    ),
    650: EzvizSwitchEntityDescription(
        key="650",
        name="Follow movement",
        translation_key="follow_movement",
        device_class=SwitchDeviceClass.SWITCH,
        supported_ext=str(SupportExt.SupportTracking.value),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up EZVIZ switch based on a config entry."""
    coordinator: EzvizDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    async_add_entities(
        [
            EzvizSwitch(coordinator, camera, switch_number)
            for camera in coordinator.data
            for switch_number in coordinator.data[camera].get("switches")
            if switch_number in SWITCH_TYPES
            if SWITCH_TYPES[switch_number].supported_ext
            in coordinator.data[camera]["supportExt"]
            or SWITCH_TYPES[switch_number].supported_ext is None
        ]
    )


class EzvizSwitch(EzvizEntity, SwitchEntity):
    """Representation of a EZVIZ sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EzvizDataUpdateCoordinator, serial: str, switch_number: int
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, serial)
        self._switch_number = switch_number
        self._attr_unique_id = (
            f"{serial}_{self._camera_name}.{DeviceSwitchType(switch_number).name}"
        )
        self.entity_description = SWITCH_TYPES[switch_number]
        self._attr_is_on = self.data["switches"][switch_number]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Change a device switch on the camera."""
        try:
            update_ok = await self.hass.async_add_executor_job(
                self.coordinator.ezviz_client.switch_status,
                self._serial,
                self._switch_number,
                1,
            )

        except (HTTPError, PyEzvizError) as err:
            raise HomeAssistantError(f"Failed to turn on switch {self.name}") from err

        if update_ok:
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Change a device switch on the camera."""
        try:
            update_ok = await self.hass.async_add_executor_job(
                self.coordinator.ezviz_client.switch_status,
                self._serial,
                self._switch_number,
                0,
            )

        except (HTTPError, PyEzvizError) as err:
            raise HomeAssistantError(f"Failed to turn off switch {self.name}") from err

        if update_ok:
            self._attr_is_on = False
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.data["switches"].get(self._switch_number):
            return

        self._attr_is_on = self.data["switches"][self._switch_number]
        super()._handle_coordinator_update()
