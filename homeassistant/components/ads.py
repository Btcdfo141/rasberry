"""
ADS Component.

For more details about this component, please refer to the documentation.

"""
import threading
import struct
import logging
import ctypes
from collections import namedtuple
import voluptuous as vol
from homeassistant.const import CONF_DEVICE, CONF_PORT, CONF_IP_ADDRESS, \
    EVENT_HOMEASSISTANT_STOP
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyads==2.2.6']

_LOGGER = logging.getLogger(__name__)

DATA_ADS = 'data_ads'

# Supported Types
ADSTYPE_INT = 'int'
ADSTYPE_UINT = 'uint'
ADSTYPE_BYTE = 'byte'
ADSTYPE_BOOL = 'bool'


ADS_PLATFORMS = ['switch', 'binary_sensor', 'light']
DOMAIN = 'ads'

# config variable names
CONF_ADSVAR = 'adsvar'
CONF_ADSTYPE = 'adstype'
CONF_ADS_USE_NOTIFY = 'use_notify'
CONF_ADS_POLL_INTERVAL = 'poll_interval'
CONF_ADS_FACTOR = 'factor'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICE): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Optional(CONF_IP_ADDRESS): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

MAX_RETRIES = 5
RETRY_SLEEPTIME_S = 0.1


def setup(hass, config):
    import pyads
    """ Set up the ADS component. """
    _LOGGER.info('created ADS client')
    conf = config[DOMAIN]

    net_id = conf.get(CONF_DEVICE)
    ip_address = conf.get(CONF_IP_ADDRESS)
    port = conf.get(CONF_PORT)

    client = pyads.Connection(net_id, port, ip_address)

    try:
        ads = AdsHub(client)
    except pyads.pyads.ADSError as e:
        _LOGGER.error('Could not connect to ADS host (netid={}, port={})'
                      .format(net_id, port))
        return False

    hass.data[DATA_ADS] = ads
    hass.bus.listen(EVENT_HOMEASSISTANT_STOP, ads.shutdown)

    return True


NotificationItem = namedtuple(
    'NotificationItem', 'hnotify huser name plc_datatype callback'
)


class AdsHub:
    """ Representation of a PyADS connection. """

    def __init__(self, ads_client):
        from pyads import PLCTYPE_BOOL, PLCTYPE_BYTE, PLCTYPE_INT, \
            PLCTYPE_UINT, ADSError

        self.ADS_TYPEMAP = {
            ADSTYPE_BOOL: PLCTYPE_BOOL,
            ADSTYPE_BYTE: PLCTYPE_BYTE,
            ADSTYPE_INT: PLCTYPE_INT,
            ADSTYPE_UINT: PLCTYPE_UINT,
        }

        self.PLCTYPE_BOOL = PLCTYPE_BOOL
        self.PLCTYPE_BYTE = PLCTYPE_BYTE
        self.PLCTYPE_INT = PLCTYPE_INT
        self.PLCTYPE_UINT = PLCTYPE_UINT
        self.ADSError = ADSError

        self._client = ads_client
        self._client.open()

        # all ADS devices are registered here
        self._devices = []
        self._notification_items = {}
        self._lock = threading.Lock()

    def shutdown(self, *args, **kwargs):
        _LOGGER.debug('Shutting down ADS')
        for key, notification_item in self._notification_items.items():
            self._client.del_device_notification(
                notification_item.hnotify,
                notification_item.huser
            )
            _LOGGER.debug('Deleting device notification {0}, {1}'
                          .format(notification_item.hnotify,
                                  notification_item.huser))
        self._client.close()

    def register_device(self, device):
        """ Register a new device. """
        self._devices.append(device)

    def write_by_name(self, name, value, plc_datatype):
        with self._lock:
            return self._client.write_by_name(name, value, plc_datatype)

    def read_by_name(self, name, plc_datatype):
        with self._lock:
            return self._client.read_by_name(name, plc_datatype)

    def add_device_notification(self, name, plc_datatype, callback):
        from pyads import NotificationAttrib
        """ Add a notification to the ADS devices. """
        attr = NotificationAttrib(ctypes.sizeof(plc_datatype))

        with self._lock:
            hnotify, huser = self._client.add_device_notification(
                name, attr, self._device_notification_callback
            )
            hnotify = int(hnotify)

        _LOGGER.debug('Added Device Notification {0} for variable {1}'
                      .format(hnotify, name))

        self._notification_items[hnotify] = NotificationItem(
            hnotify, huser, name, plc_datatype, callback
        )

    def _device_notification_callback(self, addr, notification, huser):
        from pyads import PLCTYPE_BOOL, PLCTYPE_INT, PLCTYPE_BYTE, PLCTYPE_UINT
        contents = notification.contents

        hnotify = int(contents.hNotification)
        _LOGGER.debug('Received Notification {0}'.format(hnotify))
        data = contents.data

        try:
            notification_item = self._notification_items[hnotify]
        except KeyError:
            _LOGGER.debug('Unknown Device Notification handle: {0}'
                          .format(hnotify))
            return

        # parse data to desired datatype
        if notification_item.plc_datatype == PLCTYPE_BOOL:
            value = bool(struct.unpack('<?', bytearray(data)[:1])[0])
        elif notification_item.plc_datatype == PLCTYPE_INT:
            value = struct.unpack('<h', bytearray(data)[:2])[0]
        elif notification_item.plc_datatype == PLCTYPE_BYTE:
            value = struct.unpack('<B', bytearray(data)[:1])[0]
        elif notification_item.plc_datatype == PLCTYPE_UINT:
            value = struct.unpack('<H', bytearray(data)[:2])[0]
        else:
            value = bytearray(data)
            _LOGGER.warning('No callback available for this datatype.')

        # execute callback
        notification_item.callback(notification_item.name, value)
