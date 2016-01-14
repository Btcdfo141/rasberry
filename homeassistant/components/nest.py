"""
homeassistant.components.thermostat.nest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Adds support for Nest thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermostat.nest/
"""
import logging

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)

REQUIREMENTS = ['python-nest==2.6.0']
DOMAIN = 'nest'

NEST = None


# pylint: disable=unused-argument
def setup(hass, config):
    """ Sets up the nest thermostat. """
    global NEST

    logger = logging.getLogger(__name__)
    print("nest config", config[DOMAIN])
    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)

    if username is None or password is None:
        logger.error("Missing required configuration items %s or %s",
                     CONF_USERNAME, CONF_PASSWORD)
        return

    try:
        import nest
    except ImportError:
        logger.exception(
            "Error while importing dependency nest. "
            "Did you maybe not install the python-nest dependency?")

        return

    NEST = nest.Nest(username, password)

    return True
