"""
Support for WeMo device discovery.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/wemo/
"""
import logging

import voluptuous as vol
import requests

from homeassistant.components.discovery import SERVICE_WEMO
from homeassistant.helpers import discovery
from homeassistant.helpers import config_validation as cv

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['pywemo==0.4.20']

DOMAIN = 'wemo'

# Mapping from Wemo model_name to component.
WEMO_MODEL_DISPATCH = {
    'Bridge':  'light',
    'Insight': 'switch',
    'Maker':   'switch',
    'Sensor':  'binary_sensor',
    'Motion':  'binary_sensor',
    'Socket':  'switch',
    'LightSwitch': 'switch',
    'Switch': 'switch',
    'CoffeeMaker': 'switch'
}

SUBSCRIPTION_REGISTRY = None
KNOWN_DEVICES = []

_LOGGER = logging.getLogger(__name__)

CONF_STATIC = 'static'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_STATIC, default=[]): vol.Schema([cv.string])
    }),
}, extra=vol.ALLOW_EXTRA)


# pylint: disable=unused-argument, too-many-function-args
def setup(hass, config):
    """Set up for WeMo devices."""
    import pywemo
    from pywemo.ouimeaux_device.api.xsd import device as deviceParser

    global SUBSCRIPTION_REGISTRY
    SUBSCRIPTION_REGISTRY = pywemo.SubscriptionRegistry()
    SUBSCRIPTION_REGISTRY.start()

    def stop_wemo(event):
        """Shutdown Wemo subscriptions and subscription thread on exit."""
        _LOGGER.info("Shutting down subscriptions.")
        SUBSCRIPTION_REGISTRY.stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_wemo)

    def discovery_dispatch(service, discovery_info):
        """Dispatcher for WeMo discovery events."""
        # name, model, location, mac
        model_name = discovery_info.get('model_name')
        serial = discovery_info.get('serial')

        # Only register a device once
        if serial in KNOWN_DEVICES:
            return
        _LOGGER.debug('Discovered unique device %s', serial)
        KNOWN_DEVICES.append(serial)

        component = WEMO_MODEL_DISPATCH.get(model_name, 'switch')

        discovery.load_platform(hass, component, DOMAIN, discovery_info,
                                config)

    def get_model_from_uuid(uuid):
        if uuid is None:
            return 'Socket'
        for model in WEMO_MODEL_DISPATCH:
            if uuid.startswith('uuid:{}'.format(model)):
                return model
        return None

    discovery.listen(hass, SERVICE_WEMO, discovery_dispatch)

    _LOGGER.info("Scanning for WeMo devices.")
    devices = [(device.host, device) for device in pywemo.discover_devices()]

    # Add static devices from the config file.
    devices.extend((address, None)
                   for address in config.get(DOMAIN, {}).get(CONF_STATIC, []))

    for address, device in devices:
        port = pywemo.ouimeaux_device.probe_wemo(address)
        if not port:
            _LOGGER.warning('Unable to probe wemo at %s', address)
            continue
        _LOGGER.info('Adding wemo at %s:%i', address, port)

        url = 'http://%s:%i/setup.xml' % (address, port)
        if device is None:
            device = pywemo.discovery.device_from_description(url, None)

        xml = requests.get(url, timeout=10)
        uuid = deviceParser.parseString(xml.content).device.UDN

        _LOGGER.debug("Device UUID is %s, this makes it a %s ",
                      uuid, get_model_from_uuid(uuid))

        discovery_info = {
            'model_name': get_model_from_uuid(uuid),
            'serial': device.serialnumber,
            'mac_address': device.mac,
            'ssdp_description': url,
        }

        discovery.discover(hass, SERVICE_WEMO, discovery_info)
    return True
