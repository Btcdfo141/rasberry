"""Support for Tellstick sensors."""
from collections import namedtuple
import logging

from tellcore import telldus
import tellcore.constants as tellcore_constants
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_ID, CONF_NAME, CONF_PROTOCOL, TEMP_CELSIUS
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DatatypeDescription = namedtuple("DatatypeDescription", ["name", "unit"])

CONF_DATATYPE_MASK = "datatype_mask"
CONF_ONLY_NAMED = "only_named"
CONF_TEMPERATURE_SCALE = "temperature_scale"
CONF_MODEL = "model"

DEFAULT_DATATYPE_MASK = 127
DEFAULT_TEMPERATURE_SCALE = TEMP_CELSIUS

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(
            CONF_TEMPERATURE_SCALE, default=DEFAULT_TEMPERATURE_SCALE
        ): cv.string,
        vol.Optional(
            CONF_DATATYPE_MASK, default=DEFAULT_DATATYPE_MASK
        ): cv.positive_int,
        vol.Optional(CONF_ONLY_NAMED, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_ID): cv.positive_int,
                        vol.Required(CONF_NAME): cv.string,
                        vol.Optional(CONF_PROTOCOL): cv.string,
                        vol.Optional(CONF_MODEL): cv.string,
                    }
                )
            ],
        ),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tellstick sensors."""

    sensor_value_descriptions = {
        tellcore_constants.TELLSTICK_TEMPERATURE: DatatypeDescription(
            "temperature", config.get(CONF_TEMPERATURE_SCALE)
        ),
        tellcore_constants.TELLSTICK_HUMIDITY: DatatypeDescription("humidity", "%"),
        tellcore_constants.TELLSTICK_RAINRATE: DatatypeDescription("rain rate", ""),
        tellcore_constants.TELLSTICK_RAINTOTAL: DatatypeDescription("rain total", ""),
        tellcore_constants.TELLSTICK_WINDDIRECTION: DatatypeDescription(
            "wind direction", ""
        ),
        tellcore_constants.TELLSTICK_WINDAVERAGE: DatatypeDescription(
            "wind average", ""
        ),
        tellcore_constants.TELLSTICK_WINDGUST: DatatypeDescription("wind gust", ""),
    }

    try:
        tellcore_lib = telldus.TelldusCore()
    except OSError:
        _LOGGER.exception("Could not initialize Tellstick")
        return

    sensors = []
    datatype_mask = config.get(CONF_DATATYPE_MASK)

    if config[CONF_ONLY_NAMED]:
        named_sensors = {}
        for named_sensor in config[CONF_ONLY_NAMED]:
            name = named_sensor[CONF_NAME]
            proto = named_sensor.get(CONF_PROTOCOL)
            model = named_sensor.get(CONF_MODEL)
            id_ = named_sensor[CONF_ID]
            if proto is not None:
                if model is not None:
                    named_sensors["{}{}{}".format(proto, model, id_)] = name
                else:
                    named_sensors["{}{}".format(proto, id_)] = name
            else:
                named_sensors[id_] = name

    for tellcore_sensor in tellcore_lib.sensors():
        if not config[CONF_ONLY_NAMED]:
            sensor_name = str(tellcore_sensor.id)
        else:
            proto_id = "{}{}".format(tellcore_sensor.protocol, tellcore_sensor.id)
            proto_model_id = "{}{}{}".format(
                tellcore_sensor.protocol, tellcore_sensor.model, tellcore_sensor.id
            )
            if tellcore_sensor.id in named_sensors:
                sensor_name = named_sensors[tellcore_sensor.id]
            elif proto_id in named_sensors:
                sensor_name = named_sensors[proto_id]
            elif proto_model_id in named_sensors:
                sensor_name = named_sensors[proto_model_id]
            else:
                continue

        for datatype in sensor_value_descriptions:
            if datatype & datatype_mask and tellcore_sensor.has_value(datatype):
                sensor_info = sensor_value_descriptions[datatype]
                sensors.append(
                    TellstickSensor(sensor_name, tellcore_sensor, datatype, sensor_info)
                )

    add_entities(sensors)


class TellstickSensor(Entity):
    """Representation of a Tellstick sensor."""

    def __init__(self, name, tellcore_sensor, datatype, sensor_info):
        """Initialize the sensor."""
        self._datatype = datatype
        self._tellcore_sensor = tellcore_sensor
        self._unit_of_measurement = sensor_info.unit or None
        self._value = None

        self._name = f"{name} {sensor_info.name}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self):
        """Update tellstick sensor."""
        self._value = self._tellcore_sensor.value(self._datatype).value
