"""Class to hold all sensor accessories."""
import logging

from pyhap.const import CATEGORY_SWITCH

from homeassistant.helpers.trigger import async_initialize_triggers

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_NAME,
    CHAR_PROGRAMMABLE_SWITCH_EVENT,
    CHAR_SERVICE_LABEL_INDEX,
    CHAR_SERVICE_LABEL_NAMESPACE,
    SERV_SERVICE_LABEL,
    SERV_STATELESS_PROGRAMMABLE_SWITCH,
)

_LOGGER = logging.getLogger(__name__)


@TYPES.register("DeviceTriggerAccessory")
class DeviceTriggerAccessory(HomeAccessory):
    """Generate a Programmable switch."""

    def __init__(self, *args, device_triggers=None, device_id=None):
        """Initialize a TemperatureSensor accessory object."""
        super().__init__(*args, category=CATEGORY_SWITCH, device_id=device_id)
        self._device_triggers = device_triggers
        self._remove_triggers = None
        self._triggers = []
        for idx, trigger in enumerate(device_triggers):
            _LOGGER.warning("Set up up trigger: %s", trigger)
            serv_service_label = self.add_preload_service(
                SERV_SERVICE_LABEL, [CHAR_NAME]
            )
            serv_service_label.configure_char(CHAR_SERVICE_LABEL_NAMESPACE, value=1)
            serv_stateless_switch = self.add_preload_service(
                SERV_STATELESS_PROGRAMMABLE_SWITCH,
                [CHAR_NAME, CHAR_SERVICE_LABEL_INDEX],
            )
            self._triggers.append(
                serv_stateless_switch.configure_char(
                    CHAR_PROGRAMMABLE_SWITCH_EVENT,
                    value=0,
                    valid_values={"Press": 0},
                )
            )
            type_ = trigger.get("type")
            subtype = trigger.get("subtype")
            serv_stateless_switch.configure_char(CHAR_NAME, value=f"{type_} {subtype}")
            serv_stateless_switch.configure_char(CHAR_SERVICE_LABEL_INDEX, value=idx)
            serv_service_label.configure_char(CHAR_NAME, value=f"{type_} {subtype}")

    async def async_trigger(self, run_variables, context=None, skip_condition=False):
        """Trigger button press.

        This method is a coroutine.
        """
        reason = ""
        if "trigger" in run_variables and "description" in run_variables["trigger"]:
            reason = f' by {run_variables["trigger"]["description"]}'
        _LOGGER.warning("Button triggered%s - %s", reason, run_variables)

    # Attach the trigger using the helper in async run
    # and detach it in async stop
    async def run(self):
        """Handle accessory driver started event."""
        self._remove_triggers = await async_initialize_triggers(
            self.hass,
            self._device_triggers,
            self.async_trigger,
            "homekit",
            self.name,
            _LOGGER,
        )

    async def stop(self):
        """Handle accessory driver stop event."""
        if self._remove_triggers:
            self._remove_triggers()

    @property
    def available(self):
        """Return available."""
        return True
