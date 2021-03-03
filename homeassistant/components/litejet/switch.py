"""Support for LiteJet switch."""
import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN

ATTR_NUMBER = "number"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""

    system = hass.data[DOMAIN]

    def get_entities(system):
        entities = []
        for i in system.button_switches():
            name = system.get_switch_name(i)
            entities.append(LiteJetSwitch(config_entry.entry_id, system, i, name))
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities, system), True)


class LiteJetSwitch(SwitchEntity):
    """Representation of a single LiteJet switch."""

    def __init__(self, entry_id, lj, i, name):
        """Initialize a LiteJet switch."""
        self._entry_id = entry_id
        self._lj = lj
        self._index = i
        self._state = False
        self._name = name

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._lj.on_switch_pressed(self._index, self._on_switch_pressed)
        self._lj.on_switch_released(self._index, self._on_switch_released)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._lj.unsubscribe(self._on_switch_pressed)
        self._lj.unsubscribe(self._on_switch_released)

    def _on_switch_pressed(self):
        _LOGGER.debug("Updating pressed for %s", self._name)
        self._state = True
        self.schedule_update_ha_state()

    def _on_switch_released(self):
        _LOGGER.debug("Updating released for %s", self._name)
        self._state = False
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique identifier for this switch."""
        return f"{self._entry_id}_{self._index}"

    @property
    def is_on(self):
        """Return if the switch is pressed."""
        return self._state

    @property
    def should_poll(self):
        """Return that polling is not necessary."""
        return False

    @property
    def device_state_attributes(self):
        """Return the device-specific state attributes."""
        return {ATTR_NUMBER: self._index}

    def turn_on(self, **kwargs):
        """Press the switch."""
        self._lj.press_switch(self._index)

    def turn_off(self, **kwargs):
        """Release the switch."""
        self._lj.release_switch(self._index)

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Switches are only enabled by explicit user choice."""
        return False
