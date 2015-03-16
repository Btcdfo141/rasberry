"""
Helper methods for components within Home Assistant.
"""
from datetime import datetime

from homeassistant.loader import get_component
from homeassistant.const import ATTR_ENTITY_ID, CONF_PLATFORM
from homeassistant.util import ensure_unique_string, slugify

# Deprecated 3/5/2015 - Moved to homeassistant.helpers.device
# pylint: disable=unused-import
from .device import Device, ToggleDevice  # noqa


def generate_entity_id(entity_id_format, name, current_ids=None, hass=None):
    """ Generate a unique entity ID based on given entity IDs or used ids. """
    if current_ids is None:
        if hass is None:
            raise RuntimeError("Missing required parameter currentids or hass")

        current_ids = hass.states.entity_ids()

    return ensure_unique_string(
        entity_id_format.format(slugify(name.lower())), current_ids)


def extract_entity_ids(hass, service):
    """
    Helper method to extract a list of entity ids from a service call.
    Will convert group entity ids to the entity ids it represents.
    """
    if not (service.data and ATTR_ENTITY_ID in service.data):
        return []

    group = get_component('group')

    # Entity ID attr can be a list or a string
    service_ent_id = service.data[ATTR_ENTITY_ID]

    if isinstance(service_ent_id, str):
        return group.expand_entity_ids(hass, [service_ent_id.lower()])

    return [ent_id for ent_id in group.expand_entity_ids(hass, service_ent_id)]


# pylint: disable=too-few-public-methods, attribute-defined-outside-init
class TrackStates(object):
    """
    Records the time when the with-block is entered. Will add all states
    that have changed since the start time to the return list when with-block
    is exited.
    """
    def __init__(self, hass):
        self.hass = hass
        self.states = []

    def __enter__(self):
        self.now = datetime.now()
        return self.states

    def __exit__(self, exc_type, exc_value, traceback):
        self.states.extend(self.hass.states.get_since(self.now))


def validate_config(config, items, logger):
    """
    Validates if all items are available in the configuration.

    config is the general dictionary with all the configurations.
    items is a dict with per domain which attributes we require.
    logger is the logger from the caller to log the errors to.

    Returns True if all required items were found.
    """
    errors_found = False
    for domain in items.keys():
        config.setdefault(domain, {})

        errors = [item for item in items[domain] if item not in config[domain]]

        if errors:
            logger.error(
                "Missing required configuration items in {}: {}".format(
                    domain, ", ".join(errors)))

            errors_found = True

    return not errors_found


def get_configs_for_domain(config, domain, logger):
    """
    Generator to get the different configurations for specified domain.
    For example, will find 'switch', 'switch 2', 'switch 3', .. etc
    """
    config_key = domain
    found = 1

    while config_key in config:
        yield config_key, config[config_key]
        found += 1
        config_key = "{} {}".format(domain, found)


def config_per_platform(config, domain, logger):
    """
    Generator to break a component config into different platforms.
    For example, will find 'switch', 'switch 2', 'switch 3', .. etc
    """
    for config_key, platform_config in get_configs_for_domain(config, domain,
                                                              logger):
        if not isinstance(platform_config, list):
            platform_config = [platform_config]

        for item in platform_config:
            platform_type = item.get(CONF_PLATFORM)

            if platform_type is None:
                logger.warning('No platform specified for %s', config_key)
                continue

            yield platform_type, item
