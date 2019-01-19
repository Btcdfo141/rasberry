"""
Utility meter from sensors providing raw data.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.utility_meter/
"""
import logging

from decimal import Decimal, DecimalException

import homeassistant.util.dt as dt_util
from homeassistant.const import (
    CONF_NAME, ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START, STATE_UNKNOWN, STATE_UNAVAILABLE)
from homeassistant.core import callback
from homeassistant.helpers.event import (
    async_track_state_change, async_track_time_change)
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect)
from homeassistant.helpers.restore_state import RestoreEntity
from .const import (
    DATA_UTILITY, UTILITY_COMPONENT, SIGNAL_RESET_METER,
    HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY,
    CONF_SOURCE_SENSOR, CONF_METER_TYPE, CONF_METER_OFFSET,
    CONF_TARIFF, CONF_TARIFF_ENTITY, CONF_METER)

_LOGGER = logging.getLogger(__name__)

ATTR_SOURCE_ID = 'source'
ATTR_STATUS = 'status'
ATTR_PERIOD = 'meter_period'
ATTR_LAST_PERIOD = 'last_period'
ATTR_LAST_RESET = 'last_reset'
ATTR_TARIFF = 'tariff'

ICON = 'mdi:counter'

PRECISION = 3
PAUSED = 'paused'
COLLECTING = 'collecting'


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the utility meter sensor."""
    conf = discovery_info if discovery_info else config

    meter = conf[CONF_METER]
    conf_meter_source = hass.data[DATA_UTILITY][meter].get(CONF_SOURCE_SENSOR)
    conf_meter_type = hass.data[DATA_UTILITY][meter].get(CONF_METER_TYPE)
    conf_meter_offset = hass.data[DATA_UTILITY][meter].get(CONF_METER_OFFSET)
    conf_meter_tariff_entity = hass.data[DATA_UTILITY][meter].get(
        CONF_TARIFF_ENTITY)

    meter = UtilityMeterSensor(conf_meter_source,
                               conf.get(CONF_NAME),
                               conf_meter_type,
                               conf_meter_offset,
                               conf.get(CONF_TARIFF),
                               conf_meter_tariff_entity)

    async_add_entities([meter])


class UtilityMeterSensor(RestoreEntity):
    """Representation of an utility meter sensor."""

    def __init__(self, source_entity, name, meter_type, meter_offset=0,
                 tariff=None, tariff_entity=None):
        """Initialize the Utility Meter sensor."""
        self._sensor_source_id = source_entity
        self._state = 0
        self._last_period = 0
        self._last_reset = dt_util.now()
        self._collecting = None
        if name:
            self._name = name
        else:
            self._name = '{} meter'.format(source_entity)
        self._unit_of_measurement = None
        self._period = meter_type
        self._period_offset = meter_offset
        self._tariff = tariff
        self._tariff_entity = tariff_entity

    @callback
    def async_reading(self, entity, old_state, new_state):
        """Handle the sensor state changes."""
        if any([old_state is None,
                old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE],
                new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]]):
            return

        if self._unit_of_measurement is None and\
           new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) is not None:
            self._unit_of_measurement = new_state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT)

        try:
            diff = Decimal(new_state.state) - Decimal(old_state.state)

            if diff < 0:
                # Source sensor just rolled over for unknow reasons,
                return
            self._state += diff

        except ValueError as err:
            _LOGGER.warning("While processing state changes: %s", err)
        except DecimalException as err:
            _LOGGER.warning("Invalid state (%s > %s): %s",
                            old_state.state, new_state.state, err)
        self.async_schedule_update_ha_state()

    @callback
    def async_tariff_change(self, entity, old_state, new_state):
        """Handle tariff changes."""
        if self._tariff == new_state.state:
            self._collecting = async_track_state_change(
                self.hass, self._sensor_source_id, self.async_reading)
        else:
            self._collecting()
            self._collecting = None

        _LOGGER.debug("%s - %s - source <%s>", self._name,
                      COLLECTING if self._collecting is not None
                      else PAUSED, self._sensor_source_id)

        self.async_schedule_update_ha_state()

    async def _async_reset_meter(self, event):
        """Determine cycle - Helper function for larger then daily cycles."""
        now = dt_util.now()
        if self._period == WEEKLY and now.weekday() != self._period_offset:
            return
        if self._period == MONTHLY and\
                now.day != (1 + self._period_offset):
            return
        if self._period == YEARLY and\
                (now.month != (1 + self._period_offset) or now.day != 1):
            _LOGGER.error("%s / %s", now.month, now.day)
            return
        await self.async_reset_meter(self._tariff_entity)

    async def async_reset_meter(self, entity_id):
        """Reset meter."""
        if self._tariff_entity != entity_id:
            return
        _LOGGER.debug("Reset utility meter <%s>", self.entity_id)
        self._last_reset = dt_util.now()
        self._last_period = str(self._state)
        self._state = 0
        await self.async_update_ha_state()

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if self._period == HOURLY:
            async_track_time_change(self.hass, self._async_reset_meter,
                                    minute=self._period_offset, second=0)
        elif self._period == DAILY:
            async_track_time_change(self.hass, self._async_reset_meter,
                                    hour=self._period_offset, minute=0,
                                    second=0)
        elif self._period in [WEEKLY, MONTHLY, YEARLY]:
            async_track_time_change(self.hass, self._async_reset_meter,
                                    hour=0, minute=0, second=0)

        async_dispatcher_connect(
            self.hass, SIGNAL_RESET_METER, self.async_reset_meter)

        state = await self.async_get_last_state()
        if state:
            self._state = Decimal(state.state)
            self._unit_of_measurement = state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT)
            self._last_period = state.attributes.get(ATTR_LAST_PERIOD)
            self._last_reset = state.attributes.get(ATTR_LAST_RESET)
            await self.async_update_ha_state()
            if state.attributes.get(ATTR_STATUS) == PAUSED:
                # Fake cancelation function to init the meter paused
                self._collecting = lambda: None

        @callback
        def async_source_tracking(event):
            """Wait for source to be ready, then start meter."""
            if self._tariff_entity is not None:
                _LOGGER.debug("track %s", self._tariff_entity)
                async_track_state_change(self.hass, self._tariff_entity,
                                         self.async_tariff_change)

                component = self.hass.data[DATA_UTILITY][UTILITY_COMPONENT]
                tariff_entity = component.get_entity(self._tariff_entity)
                if self._tariff != tariff_entity.state:
                    return

            self._collecting = async_track_state_change(
                self.hass, self._sensor_source_id, self.async_reading)

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, async_source_tracking)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            ATTR_SOURCE_ID: self._sensor_source_id,
            ATTR_STATUS: PAUSED if self._collecting is None else COLLECTING,
            ATTR_LAST_PERIOD: self._last_period,
            ATTR_LAST_RESET: self._last_reset,
        }
        if self._period is not None:
            state_attr[ATTR_PERIOD] = self._period
        if self._tariff is not None:
            state_attr[ATTR_TARIFF] = self._tariff
        return state_attr

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON
