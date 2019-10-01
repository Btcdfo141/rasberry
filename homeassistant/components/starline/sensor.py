"""Reads vehicle status from StarLine API."""
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from .const import DOMAIN

SENSOR_TYPES = {
    "battery": ["Battery", "V", "mdi:battery"],
    "balance": ["Balance", "$", "mdi:cash-multiple"],
    "ctemp": ["Inner Temperature", TEMP_CELSIUS, "mdi:thermometer"],
    "etemp": ["Engine Temperature", TEMP_CELSIUS, "mdi:thermometer"],
    "gsm_lvl": ["GSM Signal", "%", "mdi:signal"]
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the StarLine sensors."""
    api = hass.data[DOMAIN]
    entities = []
    for device_id, device in api.devices.items():
        for key, value in SENSOR_TYPES.items():
            # TODO: available method
            entities.append(StarlineSensor(api, device, key, *value))
    async_add_entities(entities)
    return True


class StarlineSensor(Entity):
    """Representation of a StarLine sensor."""
    def __init__(self, api, device, key, sensor_name, unit, icon):
        """Constructor."""
        self._api = api
        self._device = device
        self._key = key
        self._sensor_name = sensor_name
        self._unit = unit
        self._icon = icon

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return f"starline-{self._key}-{str(self._device.device_id)}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._device.name} {self._sensor_name}"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._key == "battery":
            return icon_for_battery_level(
                battery_level=self._device.battery_level_percent,
                charging=self._device.car_state["ign"]
            )
        elif self._key == "gsm_lvl":
            level = self._device.gsm_level_percent
            if level > 70:
                return "mdi:signal-cellular-3"
            if level > 30:
                return "mdi:signal-cellular-2"
            if level is not None:
                return "mdi:signal-cellular-1"
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._key == "battery":
            return self._device.battery_level
        elif self._key == "balance":
            return self._device.balance["value"]
        elif self._key == "ctemp":
            return self._device.temp_inner
        elif self._key == "etemp":
            return self._device.temp_engine
        elif self._key == "gsm_lvl":
            return self._device.gsm_level_percent
        return None

    @property
    def device_info(self):
        """Return the device info."""
        return self._device.device_info

    @property
    def unit_of_measurement(self):
        """Get the unit of measurement."""
        if self._key == "balance":
            return self._device.balance["currency"]
        return self._unit

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        if self._key == "balance":
            return {
                "operator": self._device.balance["operator"],
                "state": self._device.balance["state"],
                "updated": self._device.balance["ts"],
            }
        elif self._key == "gsm_lvl":
            return {
                "raw": self._device.gsm_level,
                "imei": self._device.imei,
                "phone": self._device.phone,
            }
        return None

    def update(self):
        """Read new state data."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Call when entity about to be added to Home Assistant."""
        await super().async_added_to_hass()
        self._api.add_update_listener(self.update)
