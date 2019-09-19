"""Support for SolarEdge-local Monitoring API."""
import logging
from datetime import timedelta
import statistics

from requests.exceptions import HTTPError, ConnectTimeout
from solaredge_local import SolarEdge
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    POWER_WATT,
    ENERGY_WATT_HOUR
 )
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

DOMAIN = "solaredge_local"
UPDATE_DELAY = timedelta(seconds=10)

# Supported sensor types:
# Key: ['json_key', 'name', unit, icon]
SENSOR_TYPES = {
    "current_power": [
        "currentPower",
        "Current Power",
        POWER_WATT,
        "mdi:solar-power"
    ],
    "energy_this_month": [
        "energyThisMonth",
        "Energy this month",
        ENERGY_WATT_HOUR,
        "mdi:solar-power",
    ],
    "energy_this_year": [
        "energyThisYear",
        "Energy this year",
        ENERGY_WATT_HOUR,
        "mdi:solar-power",
    ],
    "energy_today": [
        "energyToday",
        "Energy today",
        ENERGY_WATT_HOUR,
        "mdi:solar-power",
    ],
    "inverter_temperature": [
        "invertertemperature",
        "Inverter Temperature",
        'C',
        "mdi:thermometer"
    ],
    "lifetime_energy": [
        "energyTotal",
        "Lifetime energy",
        ENERGY_WATT_HOUR,
        "mdi:solar-power",
    ],
    "optimizer_current": [
        "optimizercurrent",
        "Avrage Optimizer Current",
        'A',
        "mdi:solar-panel"
    ],
    "optimizer_power": [
        "optimizerpower",
        "Avrage Optimizer Power",
        POWER_WATT,
        "mdi:solar-panel"
    ],
    "optimizer_temperature": [
        "optimizertemperature",
        "Avrage Optimizer Temperature",
        'C',
        "mdi:solar-panel"
    ],
    "optimizer_voltage": [
        "optimizervoltage",
        "Avrage Optimizer Voltage",
        'V',
        "mdi:solar-panel"
    ]
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default="SolarEdge"): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Create the SolarEdge Monitoring API sensor."""
    ip_address = config[CONF_IP_ADDRESS]
    platform_name = config[CONF_NAME]

    # Create new SolarEdge object to retrieve data.
    api = SolarEdge(f"http://{ip_address}/")

    # Check if api can be reached and site is active.
    try:
        status = api.get_status()
        _LOGGER.debug("Credentials correct and site is active")
    except AttributeError:
        _LOGGER.error("Missing details data in solaredge status")
        _LOGGER.debug("status is: %s", status)
        return
    except (ConnectTimeout, HTTPError):
        _LOGGER.error("Could not retrieve details from SolarEdge API")
        return

    # Create solaredge data service which will retrieve and update the data.
    data = SolarEdgeData(hass, api)

    # Create a new sensor for each sensor type.
    entities = []
    for sensor_key in SENSOR_TYPES:
        sensor = SolarEdgeSensor(platform_name, sensor_key, data)
        entities.append(sensor)

    add_entities(entities, True)


class SolarEdgeSensor(Entity):
    """Representation of an SolarEdge Monitoring API sensor."""

    def __init__(self, platform_name, sensor_key, data):
        """Initialize the sensor."""
        self.platform_name = platform_name
        self.sensor_key = sensor_key
        self.data = data
        self._state = None

        self._json_key = SENSOR_TYPES[self.sensor_key][0]
        self._unit_of_measurement = SENSOR_TYPES[self.sensor_key][2]

    @property
    def name(self):
        """Return the name."""
        return f"{self.platform_name} ({SENSOR_TYPES[self.sensor_key][1]})"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the sensor icon."""
        return SENSOR_TYPES[self.sensor_key][3]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Get the latest data from the sensor and update the state."""
        self.data.update()
        self._state = self.data.data[self._json_key]


class SolarEdgeData:
    """Get and update the latest data."""

    def __init__(self, hass, api):
        """Initialize the data object."""
        self.hass = hass
        self.api = api
        self.data = {}

    @Throttle(UPDATE_DELAY)
    def update(self):
        """Update the data from the SolarEdge Monitoring API."""
        try:
            status = self.api.get_status()
            _LOGGER.debug("status from SolarEdge: %s", status)
        except (ConnectTimeout):
            _LOGGER.error("Connection timeout, skipping update")
            return
        except (HTTPError):
            _LOGGER.error("Could not retrieve status, skipping update")
            return

        try:
            maintenance = self.api.get_maintenance()
            _LOGGER.debug("maintenance from SolarEdge: %s", maintenance)
        except (ConnectTimeout):
            _LOGGER.error("Connection timeout, skipping update")
            return
        except (HTTPError):
            _LOGGER.error("Could not retrieve maintenance, skipping update")
            return

        temperature = []
        voltage = []
        current = []
        data = maintenance.diagnostics.inverters.primary
        stringlength = len(data.optimizer)
        power = 0

        for x in range(stringlength):
            if data.optimizer[x].online is True:
                temperature.append(data.optimizer[x].temperature.value)
                voltage.append(data.optimizer[x].inputV)
                current.append(data.optimizer[x].inputC)

        if len(voltage) == 0:
            temperature.append(0)
            voltage.append(0)
            current.append(0)            
        else:
            power = statistics.mean(voltage) * statistics.mean(current)
        self.data["energyTotal"] = status.energy.total
        self.data["energyThisYear"] = status.energy.thisYear
        self.data["energyThisMonth"] = status.energy.thisMonth
        self.data["energyToday"] = status.energy.today
        self.data["currentPower"] = status.powerWatt
        self.data["invertertemperature"] = status.inverters.primary.temperature.value
        self.data["optimizertemperature"] = \
        statistics.mean(temperature)
        self.data["optimizervoltage"] = statistics.mean(voltage)
        self.data["optimizercurrent"] = statistics.mean(current)
        self.data["optimizerpower"] = power
