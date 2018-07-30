"""
Support for RitAssist Platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.ritassist/
"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    ATTR_SOURCE_TYPE, SOURCE_TYPE_GPS, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.entity import Entity


_LOGGER = logging.getLogger(__name__)

CLIENT_UUID_CONFIG_FILE = '.ritassist.conf'

CONF_CLIENT_ID = 'client_id'
CONF_CLIENT_SECRET = 'client_secret'
CONF_INCLUDE = 'include'
CONF_INTERVAL = 'interval'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_CLIENT_ID): cv.string,
    vol.Required(CONF_CLIENT_SECRET): cv.string,
    vol.Optional(CONF_INCLUDE, default=[]):
        vol.All(cv.ensure_list, [cv.string])
})


def setup_scanner(hass, config: dict, see, discovery_info=None):
    """Validate the configuration and return a RitAssist scanner."""
    RitAssistDeviceScanner(hass, config, see, discovery_info)
    return True


class RitAssistDeviceScanner:
    """Define a scanner for the RitAssist platform."""

    def __init__(self, hass, config, see, discovery_info):
        """Initialize RitAssistDeviceScanner."""
        from homeassistant.helpers.event import track_utc_time_change

        self._discovery_info = discovery_info
        self._hass = hass
        self._devices = []
        self._config = config
        self._see = see

        self._file = self._hass.config.path(CLIENT_UUID_CONFIG_FILE)
        self._authentication_info = RitAssistAuthentication.load(self._file)

        track_utc_time_change(self._hass,
                              lambda now: self._refresh(),
                              second=range(0, 60, 30))
        self._refresh()

    @property
    def devices(self):
        """Return the devices detected."""
        return self._devices

    def _get_access_token(self):
        """Retrieve an access token from API."""
        import requests

        data_url = "https://api.ritassist.nl/api/session/login"

        try:
            body = {
                'client_id': self._config.get(CONF_CLIENT_ID),
                'client_secret': self._config.get(CONF_CLIENT_SECRET),
                'username': self._config.get(CONF_USERNAME),
                'password': self._config.get(CONF_PASSWORD)
            }
            response = requests.post(data_url, json=body)

            self._authentication_info = RitAssistAuthentication()
            self._authentication_info.set_json(response.json())
            self._authentication_info.save(self._file)

        except requests.exceptions.ConnectionError:
            _LOGGER.error("ConnectionError: API is unavailable")
        except requests.exceptions.HTTPError:
            _LOGGER.error("HTTP Error: Please check configuration")

    def _refresh(self) -> None:
        """Refresh device information from the platform."""
        import requests

        if (self._authentication_info is None or
                not self._authentication_info.is_valid()):
            self._get_access_token()

        query = "?groupId=0&hasDeviceOnly=false"
        data_url = "https://api.ritassist.nl/api/equipment/Getfleet"

        try:
            header = self._authentication_info.create_header()
            response = requests.get(data_url + query, headers=header)
            data = response.json()
            self._devices = self.parse_devices(data)

            for device in self._devices:
                device.get_extra_vehicle_info(self._authentication_info)

                if self._see is not None:
                    self._see(dev_id=device.plate_as_id,
                              gps=(device.latitude, device.longitude),
                              attributes=device.state_attributes,
                              icon='mdi:car')

        except requests.exceptions.ConnectionError:
            _LOGGER.error('ConnectionError: Could not connect to RitAssist')

    def parse_devices(self, json):
        """Parse result from API."""
        result = []
        include = self._config.get(CONF_INCLUDE)

        for json_device in json:
            license_plate = json_device['EquipmentHeader']['SerialNumber']

            if (not include or license_plate in include):
                device = RitAssistDevice(self, license_plate)
                device.update_from_json(json_device)
                result.append(device)

        return result


class RitAssistDevice:
    """Entity used to store device information."""

    def __init__(self, data, license_plate):
        """Initialize a RitAssist device, also a vehicle."""
        self.attributes = {}
        self._data = data
        self._license_plate = license_plate

        self._identifier = None
        self._make = None
        self._model = None
        self._active = False
        self._odo = 0
        self._latitude = 0
        self._longitude = 0
        self._altitude = 0
        self._speed = 0
        self._last_seen = None
        self._equipment_id = None

        self._malfunction_light = False
        self._fuel_level = -1
        self._coolant_temperature = 0
        self._power_voltage = 0

    @property
    def identifier(self):
        """Return the internal identifier for this device."""
        return self._identifier

    @property
    def plate_as_id(self):
        """Format the license plate so it can be used as identifier."""
        return self._license_plate.replace('-', '')

    @property
    def license_plate(self):
        """Return the license plate of the vehicle."""
        return self._license_plate

    @property
    def equipment_id(self):
        """Return the equipment_id of the vehicle."""
        return self._equipment_id

    @property
    def latitude(self):
        """Return the latitude of the vehicle."""
        return self._latitude

    @property
    def longitude(self):
        """Return the longitude of the vehicle."""
        return self._longitude

    @property
    def state_attributes(self):
        """Return all attributes of the vehicle."""
        return {
            'id': self._identifier,
            'make': self._make,
            'model': self._model,
            'license_plate': self._license_plate,
            'active': self._active,
            'odo': self._odo,
            'latitude': self._latitude,
            'longitude': self._longitude,
            'altitude': self._altitude,
            'speed': self._speed,
            'last_seen': self._last_seen,
            'friendly_name': self._license_plate,
            'equipment_id': self._equipment_id,
            ATTR_SOURCE_TYPE: SOURCE_TYPE_GPS,
            'fuel_level': self._fuel_level,
            'malfunction_light': self._malfunction_light,
            'coolant_temperature': self._coolant_temperature,
            'power_voltage': self._power_voltage
        }

    def get_extra_vehicle_info(self, authentication_info):
        """Get extra data from the API."""
        import requests

        base_url = "https://secure.ritassist.nl/GenericServiceJSONP.ashx"
        query = "?f=CheckExtraVehicleInfo" \
                "&token={token}" \
                "&equipmentId={identifier}" \
                "&lastHash=null&padding=false"

        parameters = {
            'token': authentication_info.access_token,
            'identifier': str(self.identifier)
        }

        try:
            response = requests.get(base_url + query.format(**parameters))
            json = response.json()

            self._malfunction_light = json['MalfunctionIndicatorLight']
            self._fuel_level = json['FuelLevel']
            self._coolant_temperature = json['EngineCoolantTemperature']
            self._power_voltage = json['PowerVoltage']

        except requests.exceptions.ConnectionError:
            _LOGGER.error('ConnectionError: Could not connect to RitAssist')

    def update_from_json(self, json_device):
        """Set all attributes based on API response."""
        self._identifier = json_device['Id']
        self._license_plate = json_device['EquipmentHeader']['SerialNumber']
        self._make = json_device['EquipmentHeader']['Make']
        self._model = json_device['EquipmentHeader']['Model']
        self._equipment_id = json_device['EquipmentHeader']['EquipmentID']
        self._active = json_device['EngineRunning']
        self._odo = json_device['Odometer']
        self._latitude = json_device['Location']['Latitude']
        self._longitude = json_device['Location']['Longitude']
        self._altitude = json_device['Location']['Altitude']
        self._speed = json_device['Speed']
        self._last_seen = json_device['Location']['DateTime']


class RitAssistAuthentication(object):
    """Object used to store, load and validate authentication information."""

    def __init__(self):
        """Initialize RitAssistAuthentication object."""
        self.access_token = None
        self.refresh_token = None
        self.authenticated = None
        self.expires_in = None

    @property
    def token(self):
        """Return the access token."""
        return self.access_token

    def set_json(self, json):
        """Set all attributes based on JSON response."""
        import time

        self.access_token = json['access_token']
        self.refresh_token = json['refresh_token']
        self.expires_in = json['expires_in']

        if 'authenticated' in json:
            self.authenticated = json['authenticated']
        else:
            self.authenticated = time.time()

    def create_header(self):
        """Return an authorization header."""
        return {'Authorization': 'Bearer ' + self.access_token}

    def is_valid(self):
        """Check if the access token is still valid."""
        return self._check()

    def save(self, filename):
        """Save the authentication information to a file for caching."""
        from homeassistant.util.json import save_json

        json = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_in': self.expires_in,
            'authenticated': self.authenticated
        }
        if not save_json(filename, json):
            _LOGGER.error("Failed to save configuration file")

    @staticmethod
    def load(filename):
        """Load the authentication information from a file for caching."""
        from homeassistant.util.json import load_json

        data = load_json(filename)
        if data:
            result = RitAssistAuthentication()
            result.set_json(data)
            if not result.is_valid():
                return None

            return result
        else:
            return None

    def _check(self):
        """Check if the access token is expired or not."""
        import time

        if self.expires_in is None or self.authenticated is None:
            return False

        current = time.time()
        expire_time = self.authenticated + self.expires_in

        return expire_time > current
