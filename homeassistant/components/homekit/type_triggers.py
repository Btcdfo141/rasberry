"""Class to hold all sensor accessories."""
from __future__ import annotations

import logging
from typing import Any

from pyhap.const import CATEGORY_SENSOR

from homeassistant.core import CALLBACK_TYPE, Context
from homeassistant.helpers import entity_registry
from homeassistant.helpers.trigger import async_initialize_triggers

from .accessories import TYPES, HomeAccessory
from .aidmanager import get_system_unique_id
from .const import (
    CHAR_NAME,
    CHAR_PROGRAMMABLE_SWITCH_EVENT,
    CHAR_SERVICE_LABEL_INDEX,
    CHAR_SERVICE_LABEL_NAMESPACE,
    SERV_SERVICE_LABEL,
    SERV_STATELESS_PROGRAMMABLE_SWITCH,
)
from .util import cleanup_name_for_homekit

_LOGGER = logging.getLogger(__name__)


@TYPES.register("DeviceTriggerAccessory")
class DeviceTriggerAccessory(HomeAccessory):
    """Generate a Programmable switch."""

    def __init__(
        self,
        *args: Any,
        device_triggers: list[dict[str, Any]] | None = None,
        device_id: str | None = None,
    ) -> None:
        """Initialize a Programmable switch accessory object."""
        super().__init__(*args, category=CATEGORY_SENSOR, device_id=device_id)
        assert device_triggers is not None
        self._device_triggers = device_triggers
        self._remove_triggers: CALLBACK_TYPE | None = None
        self.triggers = []
        assert device_triggers is not None
        ent_reg = entity_registry.async_get(self.hass)
        for idx, trigger in enumerate(device_triggers):
            type_: str = trigger["type"]
            subtype: str | None = trigger.get("subtype")
            # Triggers don't really have a unique ID, so use the data in
            # the dict to build one to ensure we assign the same iid between
            # restarts. This is the best we can currently do.
            unique_id = f'{type_}-{subtype or ""}'
            if (entity_id := trigger.get("entity_id")) and (
                entry := ent_reg.async_get(entity_id)
            ):
                # Shouldn't be possible to it to not have an entry
                # since the device could not be created without it
                unique_id += f"-entity_unique_id:{get_system_unique_id(entry)}"
            if (metadata := trigger.get("metadata")) and (
                secondary := metadata.get("secondary")
            ) is not None:
                unique_id += f"-secondary:{secondary}"
            trigger_name_parts = [type_.replace("_", " ").title()]
            if subtype:
                trigger_name_parts.append(subtype.replace("_", " ").title())
            if entity_id and (state := self.hass.states.get(entity_id)):
                trigger_name_parts.append(state.name)
            if secondary is not None:
                trigger_name_parts.append(str(secondary))
            trigger_name = cleanup_name_for_homekit(" ".join(trigger_name_parts))
            serv_stateless_switch = self.add_preload_service(
                SERV_STATELESS_PROGRAMMABLE_SWITCH,
                [CHAR_NAME, CHAR_SERVICE_LABEL_INDEX],
                unique_id=unique_id,
            )
            self.triggers.append(
                serv_stateless_switch.configure_char(
                    CHAR_PROGRAMMABLE_SWITCH_EVENT,
                    value=0,
                    valid_values={"Trigger": 0},
                )
            )
            serv_stateless_switch.configure_char(CHAR_NAME, value=trigger_name)
            serv_stateless_switch.configure_char(
                CHAR_SERVICE_LABEL_INDEX, value=idx + 1
            )
            serv_service_label = self.add_preload_service(
                SERV_SERVICE_LABEL, unique_id=unique_id
            )
            serv_service_label.configure_char(CHAR_SERVICE_LABEL_NAMESPACE, value=1)
            serv_stateless_switch.add_linked_service(serv_service_label)

    async def async_trigger(
        self,
        run_variables: dict[str, Any],
        context: Context | None = None,
        skip_condition: bool = False,
    ) -> None:
        """Trigger button press.

        This method is a coroutine.
        """
        reason = ""
        if "trigger" in run_variables and "description" in run_variables["trigger"]:
            reason = f' by {run_variables["trigger"]["description"]}'
        _LOGGER.debug("Button triggered%s - %s", reason, run_variables)
        idx = int(run_variables["trigger"]["idx"])
        self.triggers[idx].set_value(0)

    # Attach the trigger using the helper in async run
    # and detach it in async stop
    async def run(self) -> None:
        """Handle accessory driver started event."""
        self._remove_triggers = await async_initialize_triggers(
            self.hass,
            self._device_triggers,
            self.async_trigger,
            "homekit",
            self.display_name,
            _LOGGER.log,
        )

    async def stop(self) -> None:
        """Handle accessory driver stop event."""
        if self._remove_triggers:
            self._remove_triggers()

    @property
    def available(self) -> bool:
        """Return available."""
        return True
