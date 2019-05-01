"""Support for Repetier-Server sensors."""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (
    CONF_API_KEY, CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_PORT,
    CONF_SENSORS, TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import slugify as util_slugify

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'RepetierServer'
DOMAIN = 'repetier'
REPETIER_API = 'repetier_api'
SCAN_INTERVAL = timedelta(seconds=10)
UPDATE_SIGNAL = 'repetier_update_signal'

TEMP_DATA = {
    'tempset': 'temp_set',
    'tempread': 'state',
    'output': 'output',
}


API_PRINTER_METHODS = {
    'bed_temperature': {
        'offline': {'heatedbeds': None, 'state': 'off'},
        'state': {'heatedbeds': 'temp_data'},
        'temp_data': TEMP_DATA,
    },
    'extruder_temperature': {
        'offline': {'extruder': None, 'state': 'off'},
        'state': {'extruder': 'temp_data'},
        'temp_data': TEMP_DATA,
    },
    'chamber_temperature': {
        'offline': {'heatedchambers': None, 'state': 'off'},
        'state': {'heatedchambers': 'temp_data'},
        'temp_data': TEMP_DATA,
    },
    'current_state': {
        'offline': {'state': None},
        'state': {
            'state': 'state',
            'activeextruder': 'active_extruder',
            'hasxhome': 'x_homed',
            'hasyhome': 'y_homed',
            'haszhome': 'z_homed',
            'firmware': 'firmware',
            'firmwareurl': 'firmware_url',
        },
    },
    'current_job': {
        'offline': {'job': None, 'state': 'off'},
        'state': {
            'done': 'state',
            'job': 'job_name',
            'jobid': 'job_id',
            'totallines': 'total_lines',
            'linessent': 'lines_sent',
            'oflayer': 'total_layers',
            'layer': 'current_layer',
            'speedmultiply': 'feed_rate',
            'flowmultiply': 'flow',
            'x': 'x',
            'y': 'y',
            'z': 'z',
        },
    },
    'job_end': {
        'offline': {
            'job': None, 'state': 'off', 'start': None, 'printtime': None},
        'state': {
            'job': 'job_name',
            'start': 'start',
            'printtime': 'print_time',
            'printedtimecomp': 'from_start',
        },
    },
    'job_start': {
        'offline': {
            'job': None,
            'state': 'off',
            'start': None,
            'printedtimecomp': None
        },
        'state': {
            'job': 'job_name',
            'start': 'start',
            'printedtimecomp': 'from_start',
        },
    },
}


def has_all_unique_names(value):
    """Validate that printers have an unique name."""
    names = [util_slugify(printer[CONF_NAME]) for printer in value]
    vol.Schema(vol.Unique())(names)
    return value


SENSOR_TYPES = {
    # Type, Unit, Icon
    'bed_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                        '_bed_'],
    'extruder_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                             '_extruder_'],
    'chamber_temperature': ['temperature', TEMP_CELSIUS, 'mdi:thermometer',
                            '_chamber_'],
    'current_state': ['state', None, 'mdi:printer-3d', ''],
    'current_job': ['progress', '%', 'mdi:file-percent', '_current_job'],
    'job_end': ['progress', None, 'mdi:clock-end', '_job_end'],
    'job_start': ['progress', None, 'mdi:clock-start', '_job_start'],
}

SENSOR_SCHEMA = vol.Schema({
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=3344): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SENSORS, default={}): SENSOR_SCHEMA,
    })], has_all_unique_names),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Repetier Server component."""
    import pyrepetier

    hass.data[REPETIER_API] = {}
    sensor_info = []

    for repetier in config[DOMAIN]:
        _LOGGER.debug("Repetier server config %s", repetier[CONF_HOST])

        url = "http://{}".format(repetier[CONF_HOST])
        port = repetier[CONF_PORT]
        api_key = repetier[CONF_API_KEY]

        client = pyrepetier.Repetier(
            url=url,
            port=port,
            apikey=api_key)

        printers = client.getprinters()

        if not printers:
            return False

        api = PrinterAPI(hass, client, printers)
        api.update()
        track_time_interval(hass, api.update, SCAN_INTERVAL)

        hass.data[REPETIER_API][repetier[CONF_NAME]] = api

        sensors = repetier[CONF_SENSORS][CONF_MONITORED_CONDITIONS]
        for pidx, printer in enumerate(printers):
            for sensor_type in sensors:
                info = {}
                info['sensor_type'] = sensor_type
                info['printer_id'] = pidx
                info['name'] = printer.slug
                info['printer_name'] = repetier[CONF_NAME]

                if sensor_type == 'bed_temperature':
                    if printer.heatedbeds is None:
                        continue
                    for idx, _ in enumerate(printer.heatedbeds):
                        info['temp_id'] = idx
                        sensor_info.append(info)
                elif sensor_type == 'extruder_temperature':
                    if printer.extruder is None:
                        continue
                    for idx, _ in enumerate(printer.extruder):
                        info['temp_id'] = idx
                        sensor_info.append(info)
                elif sensor_type == 'chamber_temperature':
                    if printer.heatedchambers is None:
                        continue
                    for idx, _ in enumerate(printer.heatedchambers):
                        info['temp_id'] = idx
                        sensor_info.append(info)
                else:
                    info['temp_id'] = None
                    sensor_info.append(info)

    load_platform(hass, 'sensor', DOMAIN, sensor_info, config)

    return True


class PrinterAPI:
    """Handle the printer API."""

    def __init__(self, hass, client, printers):
        """Set up instance."""
        self._hass = hass
        self._client = client
        self.printers = printers

    def get_data(self, printer_id, sensor_type, temp_id):
        """Get data from the state cache."""
        printer = self.printers[printer_id]
        methods = API_PRINTER_METHODS[sensor_type]
        for prop, offline in methods['offline'].items():
            state = getattr(printer, prop)
            if state == offline:
                # if state matches offline, sensor is offline
                return None

        data = {}
        for prop, attr in methods['state'].items():
            prop_data = getattr(printer, prop)
            if attr == 'temp_data':
                temp_methods = methods['temp_data']
                for temp_prop, temp_attr in temp_methods.items():
                    data[temp_attr] = getattr(prop_data[temp_id], temp_prop)
            else:
                data[attr] = prop_data
        return data

    def update(self, now=None):
        """Update the state cache from the printer API."""
        for printer in self.printers:
            printer.get_data()
        dispatcher_send(self._hass, UPDATE_SIGNAL)
