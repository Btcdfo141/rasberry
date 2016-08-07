"""
Component to create an interface to a Pilight daemon (https://pilight.org/).
Pilight can be used to send and receive signals from a radio frequency module (RF receiver).

RF commands received by the daemon are put on the HA event bus.
RF commands can also be send with a pilight.send service call.
"""
# pylint: disable=import-error
import logging
import socket

from homeassistant.helpers import validate_config
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START
from homeassistant.const import CONF_HOST, CONF_PORT

REQUIREMENTS = ['pilight']

DOMAIN = "pilight"
_LOGGER = logging.getLogger(__name__)
ICON = 'mdi:remote'
EVENT = 'pilight_received'
SERVICE_NAME = 'send'
TIMEOUT = 1

CONNECTED = False

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    from pilight import pilight

    if not validate_config(config,
                       {DOMAIN: [CONF_HOST, CONF_PORT]},
                       _LOGGER):
        return None

    try:
        pilight_client = pilight.Client(host=config[DOMAIN][CONF_HOST],
                                        port=config[DOMAIN][CONF_PORT])
    except (socket.error, socket.timeout) as err:
        _LOGGER.error(
                "Unable to connect to %s on port %s: %s",
                config[CONF_HOST], config[CONF_PORT], err)
        return None
    
    # Start / stop pilight-daemon connection with HA start/stop
    def start_pilight_client(event):
        pilight_client.start()
    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_pilight_client)
    def stop_pilight_client(event):
        pilight_client.stop()
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_pilight_client)
        
    # Send RF code to the pilight-daemon
    def send_code(call):
        message_data = call.data

        if not "protocol" in message_data:
            _LOGGER.error('Pilight data to send does not contain a protocol info. Check the pilight-send doku!', str(call.data))
            return
        
        # Patch data because of bug: https://github.com/pilight/pilight/issues/296
        message_data = message_data.copy()
        message_data["protocol"] = [message_data["protocol"]]  # Protocol has to be in a list otherwise segfault
        
        try:
            pilight_client.send_code(message_data)
        except IOError:
            _LOGGER.error('Pilight send failed for %s', str(message_data))
    hass.services.register(DOMAIN, SERVICE_NAME, send_code)
        
    # Publish received codes on the HA event bus
    def handle_received_code(data):
        data = dict({'protocol': data['protocol'], 'uuid': data['uuid']}, **data['message'])  # Unravel dict of dicts to make event_data cut in automation rule possible
        _LOGGER.info(data)
        hass.bus.fire(EVENT, data)
    pilight_client.set_callback(handle_received_code)
    
    global CONNECTED
    CONNECTED = True

    return True