"""
Sensor for data from Austrian "Zentralanstalt für Meteorologie und Geodynamik".

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.zamg/
"""
import csv
import logging
from datetime import datetime, timedelta

import pytz
import requests
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.weather import (
    ATTR_WEATHER_HUMIDITY, ATTR_WEATHER_ATTRIBUTION, ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE, ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_SPEED)
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, CONF_NAME, __version__)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

ATTR_STATION = 'station'
ATTR_UPDATED = 'updated'
ATTRIBUTION = 'Data provided by ZAMG'

CONF_STATION_ID = 'station_id'

DEFAULT_NAME = 'zamg'

# Data source updates once per hour, so we do nothing if it's been less time
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

SENSOR_TYPES = {
    ATTR_WEATHER_PRESSURE: ('Pressure', 'hPa', 'LDstat hPa', float),
    'pressure_sealevel': ('Pressure at Sea Level', 'hPa', 'LDred hPa', float),
    ATTR_WEATHER_HUMIDITY: ('Humidity', '%', 'RF %', int),
    ATTR_WEATHER_WIND_SPEED: ('Wind Speed', 'km/h', 'WG km/h', float),
    ATTR_WEATHER_WIND_BEARING: ('Wind Bearing', '°', 'WR °', int),
    'wind_max_speed': ('Top Wind Speed', 'km/h', 'WSG km/h', float),
    'wind_max_bearing': ('Top Wind Bearing', '°', 'WSR °', int),
    'sun_last_hour': ('Sun Last Hour', '%', 'SO %', int),
    ATTR_WEATHER_TEMPERATURE: ('Temperature', '°C', 'T °C', float),
    'precipitation': ('Precipitation', 'l/m²', 'N l/m²', float),
    'dewpoint': ('Dew Point', '°C', 'TP °C', float),
    # The following probably not useful for general consumption,
    # but we need them to fill in internal attributes
    'station_name': ('Station Name', None, 'Name', str),
    'station_elevation': ('Station Elevation', 'm', 'Höhe m', int),
    'update_date': ('Update Date', None, 'Datum', str),
    'update_time': ('Update Time', None, 'Zeit', str),
}

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Required(CONF_STATION_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZAMG sensor platform."""
    station_id = config.get(CONF_STATION_ID)
    name = config.get(CONF_NAME, DEFAULT_NAME)

    logger = logging.getLogger(__name__)
    probe = ZamgData(station_id=station_id, logger=logger)
    try:
        probe.update()
    except ValueError as err:
        logger.error("Received error from ZAMG: %s", err)
        return False

    sensors = [ZamgSensor(probe, variable, name)
               for variable in config[CONF_MONITORED_CONDITIONS]]

    add_devices(sensors, True)


class ZamgSensor(Entity):
    """Implementation of a ZAMG sensor."""

    def __init__(self, probe, variable, name):
        """Initialize the sensor."""
        self.probe = probe
        self.client_name = name
        self.variable = variable
        self.update()

    def update(self):
        """Delegate update to probe."""
        self.probe.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self.client_name, self.variable)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.probe.get_data(self.variable)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return SENSOR_TYPES[self.variable][1]

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_WEATHER_ATTRIBUTION: ATTRIBUTION,
            ATTR_STATION: self.probe.get_data('station_name'),
            ATTR_UPDATED: self.probe.last_update.isoformat(),
        }


class ZamgData(object):
    """The class for handling the data retrieval."""

    API_URL = 'http://www.zamg.ac.at/ogd/'
    API_HEADERS = {
        'User-Agent': '{} {}'.format('home-assistant.zamg/', __version__),
    }

    def __init__(self, logger, station_id):
        """Initialize the probe."""
        self._logger = logger
        self._station_id = station_id
        self.data = {}

    @property
    def last_update(self):
        """Return the timestamp of the most recent data."""
        date, time = self.data.get('update_date'), self.data.get('update_time')
        if date is not None and time is not None:
            return datetime.strptime(date + time, '%d-%m-%Y%H:%M').replace(
                tzinfo=pytz.timezone('Europe/Vienna'))

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from ZAMG."""
        if self.last_update and (self.last_update + timedelta(hours=1) >
                                 datetime.utcnow().replace(tzinfo=pytz.utc)):
            return  # Not time to update yet; data is only hourly

        try:
            response = requests.get(
                self.API_URL, headers=self.API_HEADERS, timeout=15)
        except requests.exceptions.RequestException:
            self._logger.exception("While fetching data from server")
            return

        if response.status_code != 200:
            self._logger.error("API call returned with status %s",
                               response.status_code)
            return

        content_type = response.headers.get('Content-Type', 'whatever')
        if content_type != 'text/csv':
            self._logger.error("Expected text/csv but got %s", content_type)
            return

        response.encoding = 'UTF8'
        content = response.text
        data = (line for line in content.split('\n'))
        reader = csv.DictReader(data, delimiter=';', quotechar='"')
        for row in reader:
            if row.get('Station') == self._station_id:
                api_fields = {col_heading: (standard_name, dtype)
                              for standard_name, (_, _, col_heading, dtype)
                              in SENSOR_TYPES.items()}
                self.data = {
                    api_fields.get(col_heading)[0]:
                        api_fields.get(col_heading)[1](v.replace(',', '.'))
                    for col_heading, v in row.items()
                    if col_heading in self.API_FIELDS and v}
                break
        else:
            raise ValueError('No weather data for station {}'
                             .format(self._station_id))


    def get_data(self, variable):
        """Generic accessor for data."""
        return self.data.get(variable)
