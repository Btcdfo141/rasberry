"""
Support for Paradox Alarm area/partition states.

 - represented as an alarm control panel.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.paradox/
"""
import logging
import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.paradox import (PARADOX_CONTROLLER,
                                              PARTITION_SCHEMA,
                                              CONF_PARTITIONNAME)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED, STATE_UNKNOWN)

# Mandatory items specified in configuration.yaml file
PANEL_TYPE = 'panel_type'
PORT = 'port'
SPEED = 'speed'

DEPENDENCIES = ['paradox']
_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """
    Set up the Paradox alarm control panel platform.

    Based on configuration file contents, not auto discovered.
    """
    def update_alarm_armed_cb(area_number):
        """Process the area armed event received from alarm panel."""
        # Area in use on alarm panel might not be setup/defined in HA
        try:
            _affected_area = PARTITION_SCHEMA(_partitions[area_number])
            _LOGGER.debug('HA area %s to be armed.',
                          _affected_area[CONF_PARTITIONNAME])
            _area = ('alarm_control_panel.' +
                     _affected_area[CONF_PARTITIONNAME])
            _area.update_ha_state(True)
        except KeyError:
            _LOGGER.debug('Area %d not defined in HA.', area_number)

    def update_alarm_stay_armed_cb(area_number):
        """Process area stay armed event received from alarm panel."""
        # Area in use on alarm panel might not be setup/defined in HA
        try:
            _affected_area = PARTITION_SCHEMA(_partitions[area_number])
            _LOGGER.debug('HA area %s to be stay armed.',
                          _affected_area[CONF_PARTITIONNAME])
            _area = ('alarm_control_panel.' +
                     _affected_area[CONF_PARTITIONNAME])
            _area.update_ha_state(True)
        except KeyError:
            _LOGGER.debug('Area %d not defined in HA.', area_number)

    def update_alarm_disarmed_cb(area_number):
        """Process area/partition disarmed event received from alarm panel."""
        # Area in use on alarm panel might not be setup/defined in HA
        try:
            _affected_area = PARTITION_SCHEMA(_partitions[area_number])
            _LOGGER.debug('HA area %s to be disarmed.',
                          _affected_area[CONF_PARTITIONNAME])
            _area = ('alarm_control_panel.' +
                     _affected_area[CONF_PARTITIONNAME])
            _area.update_ha_state(True)
        except KeyError:
            _LOGGER.debug('Area %d not defined in HA.', area_number)

    # Overwrite the controllers default callback to call the hass functions
    PARADOX_CONTROLLER.callback_area_armed = update_alarm_armed_cb
    PARADOX_CONTROLLER.callback_area_stay_armed = update_alarm_stay_armed_cb
    PARADOX_CONTROLLER.callback_area_disarmed = update_alarm_disarmed_cb

    # Get the area information specified in the configuration/yaml file.
    _yaml_partitions = discovery_info['partitions']
    for area_number in _yaml_partitions:
        # For each area specified, get the detail for that area.
        _device_config_data = PARTITION_SCHEMA(_yaml_partitions[area_number])
        # Add the partition as a HA device.
        # Each area is represented as an alarm control panel in HA
        add_devices(
            [ParadoxAlarm(
                hass,
                area_number,
                _device_config_data[CONF_PARTITIONNAME],
                PARADOX_CONTROLLER.alarm_state['partition'][area_number]
                )])
    return True


class ParadoxAlarm(alarm.AlarmControlPanel):
    """Representation of an Paradox area as a alarm control panel."""

    def __init__(self, hass, area_number, area_name, area_info):
        """Initialize the Paradox area as a alarm control panel."""
        # from pyparadox_alarm import paradox_defaults

        self._area_info = area_info  # As defined in Alarm State dictionary
        # self._hass = hass
        self._area_number = area_number
        if area_name in '':
            # When no name provided request area label from the panel.
            # PARADOX_CONTROLLER.submit_area_label_request(self._area_number)
            # but it is asynchronous so set default name in the mean time
            self._name = self._area_info['name']  # Alarm state default label
        else:
            self._name = area_name  # Name in configuration/yaml file

        # At startup the area status should be requested from the alarm panel.
        # Request the area status from the alarm panel
        PARADOX_CONTROLLER.submit_area_status_request(self._area_number)
        # No need to wait or call self.update() as status will be 
        # updated when it returns from controller.

        _LOGGER.debug('HA added area: ' + area_name)

    @property
    def name(self):
        """
        Return the name of the alarm control panel device.

        (Area/Partition name/label)
        """
        _LOGGER.debug('HA reports area name as ' + self._name)
        return self._name

    @property
    def should_poll(self):
        """Alarm status is pushed by alarm panel, so no polling needed."""
        return False

    @property
    def state(self):
        """Return the state of the area/partition."""
        # Status is available/mirrored in alarm state dictionary.
        if self._area_info['status']['alarm']:
            return STATE_ALARM_TRIGGERED
        elif self._area_info['status']['armed_away']:
            return STATE_ALARM_ARMED_AWAY
        elif self._area_info['status']['armed_stay']:
            return STATE_ALARM_ARMED_HOME
        elif self._area_info['status']['alpha']:
            return STATE_ALARM_DISARMED
        else:
            return STATE_UNKNOWN

    def alarm_disarm(self, code=None):
        """Send disarm command. Planned for next version."""
        raise NotImplementedError()

    def alarm_arm_home(self, code=None):
        """Send arm home command. Planned for next version."""
        raise NotImplementedError()

    def alarm_arm_away(self, code=None):
        """Send arm away command. Planned for next version."""
        raise NotImplementedError()

    def alarm_trigger(self, code=None):
        """Send alarm trigger command. Planned for next version."""
        raise NotImplementedError()
