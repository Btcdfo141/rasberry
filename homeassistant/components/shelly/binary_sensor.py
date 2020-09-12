"""Binary sensor for Shelly."""
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_VIBRATION,
    BinarySensorEntity,
)

from .entity import (
    BlockAttributeDescription,
    ShellyBlockAttributeEntity,
    async_setup_entry_attribute_entities,
)

SENSORS = {
    ("device", "overtemp"): BlockAttributeDescription(
        name="Overheating",
        device_class=DEVICE_CLASS_PROBLEM,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("device", "overpower"): BlockAttributeDescription(
        name="Over Power",
        device_class=DEVICE_CLASS_PROBLEM,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("light", "overpower"): BlockAttributeDescription(
        name="Over Power",
        device_class=DEVICE_CLASS_PROBLEM,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("relay", "overpower"): BlockAttributeDescription(
        name="Over Power",
        device_class=DEVICE_CLASS_PROBLEM,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("sensor", "dwIsOpened"): BlockAttributeDescription(
        name="Door",
        device_class=DEVICE_CLASS_OPENING,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("sensor", "flood"): BlockAttributeDescription(
        name="flood",
        device_class=DEVICE_CLASS_MOISTURE,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("sensor", "gas"): BlockAttributeDescription(
        name="gas",
        device_class=DEVICE_CLASS_GAS,
        value=lambda value: value in ["mild", "heavy"],
        device_state_attributes=lambda block: {"detected": block.gas},
    ),
    ("sensor", "smoke"): BlockAttributeDescription(
        name="smoke",
        device_class=DEVICE_CLASS_SMOKE,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
    ("sensor", "vibration"): BlockAttributeDescription(
        name="vibration",
        device_class=DEVICE_CLASS_VIBRATION,
        device_state_attributes=lambda wrapper: {
            "ip address": wrapper.device.ip,
            "Shelly id": wrapper.device.id,
        },
    ),
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors for device."""
    await async_setup_entry_attribute_entities(
        hass, config_entry, async_add_entities, SENSORS, ShellyBinarySensor
    )


class ShellyBinarySensor(ShellyBlockAttributeEntity, BinarySensorEntity):
    """Shelly binary sensor entity."""

    @property
    def is_on(self):
        """Return true if sensor state is on."""
        return bool(self.attribute_value)
