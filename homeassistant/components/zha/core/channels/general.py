"""
General channels module for Zigbee Home Automation.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/zha/
"""
import logging

import zigpy.zcl.clusters.general as general

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later

from . import AttributeListeningChannel, ZigbeeChannel, parse_and_log_command
from .. import registries
from ..const import (
    REPORT_CONFIG_ASAP,
    REPORT_CONFIG_BATTERY_SAVE,
    REPORT_CONFIG_DEFAULT,
    REPORT_CONFIG_IMMEDIATE,
    SIGNAL_ATTR_UPDATED,
    SIGNAL_MOVE_LEVEL,
    SIGNAL_SET_LEVEL,
)
from ..helpers import get_attr_id_by_name

_LOGGER = logging.getLogger(__name__)


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Alarms(ZigbeeChannel):
    """Alarms channel."""

    CLUSTER_ID = general.Alarms.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class AnalogInput(AttributeListeningChannel):
    """Analog Input channel."""

    CLUSTER_ID = general.AnalogInput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class AnalogOutput(AttributeListeningChannel):
    """Analog Output channel."""

    CLUSTER_ID = general.AnalogOutput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class AnalogValue(AttributeListeningChannel):
    """Analog Value channel."""

    CLUSTER_ID = general.AnalogValue.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class ApplianceContorl(ZigbeeChannel):
    """Appliance Control channel."""

    CLUSTER_ID = general.ApplianceControl.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class BasicChannel(ZigbeeChannel):
    """Channel to interact with the basic cluster."""

    CLUSTER_ID = general.Basic.cluster_id
    UNKNOWN = 0
    BATTERY = 3

    POWER_SOURCES = {
        UNKNOWN: "Unknown",
        1: "Mains (single phase)",
        2: "Mains (3 phase)",
        BATTERY: "Battery",
        4: "DC source",
        5: "Emergency mains constantly powered",
        6: "Emergency mains and transfer switch",
    }

    def __init__(self, cluster, device):
        """Initialize BasicChannel."""
        super().__init__(cluster, device)
        self._power_source = None

    async def async_configure(self):
        """Configure this channel."""
        await super().async_configure()
        await self.async_initialize(False)

    async def async_initialize(self, from_cache):
        """Initialize channel."""
        self._power_source = await self.get_attribute_value(
            "power_source", from_cache=from_cache
        )
        await super().async_initialize(from_cache)

    def get_power_source(self):
        """Get the power source."""
        return self._power_source


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class BinaryInput(AttributeListeningChannel):
    """Binary Input channel."""

    CLUSTER_ID = general.BinaryInput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class BinaryOutput(AttributeListeningChannel):
    """Binary Output channel."""

    CLUSTER_ID = general.BinaryOutput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class BinaryValue(AttributeListeningChannel):
    """Binary Value channel."""

    CLUSTER_ID = general.BinaryValue.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Commissioning(ZigbeeChannel):
    """Commissioning channel."""

    CLUSTER_ID = general.Commissioning.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class DeviceTemperature(ZigbeeChannel):
    """Device Temperature channel."""

    CLUSTER_ID = general.DeviceTemperature.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class GreenPowerProxy(ZigbeeChannel):
    """Green Power Proxy channel."""

    CLUSTER_ID = general.GreenPowerProxy.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Groups(ZigbeeChannel):
    """Groups channel."""

    CLUSTER_ID = general.Groups.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Identify(ZigbeeChannel):
    """Identify channel."""

    CLUSTER_ID = general.Identify.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class LevelControlChannel(ZigbeeChannel):
    """Channel for the LevelControl Zigbee cluster."""

    CLUSTER_ID = general.LevelControl.cluster_id
    CURRENT_LEVEL = 0
    REPORT_CONFIG = ({"attr": "current_level", "config": REPORT_CONFIG_ASAP},)

    @callback
    def cluster_command(self, tsn, command_id, args):
        """Handle commands received to this cluster."""
        cmd = parse_and_log_command(self, tsn, command_id, args)

        if cmd in ("move_to_level", "move_to_level_with_on_off"):
            self.dispatch_level_change(SIGNAL_SET_LEVEL, args[0])
        elif cmd in ("move", "move_with_on_off"):
            # We should dim slowly -- for now, just step once
            rate = args[1]
            if args[0] == 0xFF:
                rate = 10  # Should read default move rate
            self.dispatch_level_change(SIGNAL_MOVE_LEVEL, -rate if args[0] else rate)
        elif cmd in ("step", "step_with_on_off"):
            # Step (technically may change on/off)
            self.dispatch_level_change(
                SIGNAL_MOVE_LEVEL, -args[1] if args[0] else args[1]
            )

    @callback
    def attribute_updated(self, attrid, value):
        """Handle attribute updates on this cluster."""
        self.debug("received attribute: %s update with value: %s", attrid, value)
        if attrid == self.CURRENT_LEVEL:
            self.dispatch_level_change(SIGNAL_SET_LEVEL, value)

    def dispatch_level_change(self, command, level):
        """Dispatch level change."""
        async_dispatcher_send(
            self._zha_device.hass, "{}_{}".format(self.unique_id, command), level
        )

    async def async_initialize(self, from_cache):
        """Initialize channel."""
        await self.get_attribute_value(self.CURRENT_LEVEL, from_cache=from_cache)
        await super().async_initialize(from_cache)


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class MultistateInput(AttributeListeningChannel):
    """Multistate Input channel."""

    CLUSTER_ID = general.MultistateInput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class MultistateOutput(AttributeListeningChannel):
    """Multistate Output channel."""

    CLUSTER_ID = general.MultistateOutput.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class MultistateValue(AttributeListeningChannel):
    """Multistate Value channel."""

    CLUSTER_ID = general.MultistateValue.cluster_id
    REPORT_CONFIG = [{"attr": "present_value", "config": REPORT_CONFIG_DEFAULT}]


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class OnOffChannel(ZigbeeChannel):
    """Channel for the OnOff Zigbee cluster."""

    CLUSTER_ID = general.OnOff.cluster_id
    ON_OFF = 0
    REPORT_CONFIG = ({"attr": "on_off", "config": REPORT_CONFIG_IMMEDIATE},)

    def __init__(self, cluster, device):
        """Initialize OnOffChannel."""
        super().__init__(cluster, device)
        self._state = None
        self._off_listener = None

    @callback
    def cluster_command(self, tsn, command_id, args):
        """Handle commands received to this cluster."""
        cmd = parse_and_log_command(self, tsn, command_id, args)

        if cmd in ("off", "off_with_effect"):
            self.attribute_updated(self.ON_OFF, False)
        elif cmd in ("on", "on_with_recall_global_scene"):
            self.attribute_updated(self.ON_OFF, True)
        elif cmd == "on_with_timed_off":
            should_accept = args[0]
            on_time = args[1]
            # 0 is always accept 1 is only accept when already on
            if should_accept == 0 or (should_accept == 1 and self._state):
                if self._off_listener is not None:
                    self._off_listener()
                    self._off_listener = None
                self.attribute_updated(self.ON_OFF, True)
                if on_time > 0:
                    self._off_listener = async_call_later(
                        self.device.hass,
                        (on_time / 10),  # value is in 10ths of a second
                        self.set_to_off,
                    )
        elif cmd == "toggle":
            self.attribute_updated(self.ON_OFF, not bool(self._state))

    @callback
    def set_to_off(self, *_):
        """Set the state to off."""
        self._off_listener = None
        self.attribute_updated(self.ON_OFF, False)

    @callback
    def attribute_updated(self, attrid, value):
        """Handle attribute updates on this cluster."""
        if attrid == self.ON_OFF:
            async_dispatcher_send(
                self._zha_device.hass,
                "{}_{}".format(self.unique_id, SIGNAL_ATTR_UPDATED),
                value,
            )
            self._state = bool(value)

    async def async_initialize(self, from_cache):
        """Initialize channel."""
        self._state = bool(
            await self.get_attribute_value(self.ON_OFF, from_cache=from_cache)
        )
        await super().async_initialize(from_cache)

    async def async_update(self):
        """Initialize channel."""
        from_cache = not self.device.is_mains_powered
        self.debug("attempting to update onoff state - from cache: %s", from_cache)
        self._state = bool(
            await self.get_attribute_value(self.ON_OFF, from_cache=from_cache)
        )
        await super().async_update()


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class OnOffConfiguration(ZigbeeChannel):
    """OnOff Configuration channel."""

    CLUSTER_ID = general.OnOffConfiguration.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Ota(ZigbeeChannel):
    """OTA Channel."""

    CLUSTER_ID = general.Ota.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Partition(ZigbeeChannel):
    """Partition channel."""

    CLUSTER_ID = general.Partition.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class PollControl(ZigbeeChannel):
    """Poll Control channel."""

    CLUSTER_ID = general.PollControl.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class PowerConfigurationChannel(ZigbeeChannel):
    """Channel for the zigbee power configuration cluster."""

    CLUSTER_ID = general.PowerConfiguration.cluster_id
    REPORT_CONFIG = (
        {"attr": "battery_voltage", "config": REPORT_CONFIG_BATTERY_SAVE},
        {"attr": "battery_percentage_remaining", "config": REPORT_CONFIG_BATTERY_SAVE},
    )

    @callback
    def attribute_updated(self, attrid, value):
        """Handle attribute updates on this cluster."""
        attr = self._report_config[1].get("attr")
        if isinstance(attr, str):
            attr_id = get_attr_id_by_name(self.cluster, attr)
        else:
            attr_id = attr
        if attrid == attr_id:
            async_dispatcher_send(
                self._zha_device.hass,
                "{}_{}".format(self.unique_id, SIGNAL_ATTR_UPDATED),
                value,
            )

    async def async_initialize(self, from_cache):
        """Initialize channel."""
        await self.async_read_state(from_cache)
        await super().async_initialize(from_cache)

    async def async_update(self):
        """Retrieve latest state."""
        await self.async_read_state(True)

    async def async_read_state(self, from_cache):
        """Read data from the cluster."""
        await self.get_attribute_value("battery_size", from_cache=from_cache)
        await self.get_attribute_value(
            "battery_percentage_remaining", from_cache=from_cache
        )
        await self.get_attribute_value("battery_voltage", from_cache=from_cache)
        await self.get_attribute_value("battery_quantity", from_cache=from_cache)


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class PowerProfile(ZigbeeChannel):
    """Power Profile channel."""

    CLUSTER_ID = general.PowerProfile.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class RSSILocation(ZigbeeChannel):
    """RSSI Location channel."""

    CLUSTER_ID = general.RSSILocation.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Scenes(ZigbeeChannel):
    """Scenes channel."""

    CLUSTER_ID = general.Scenes.cluster_id
    pass


@registries.ZIGBEE_CHANNEL_REGISTRY.register
class Time(ZigbeeChannel):
    """Time channel."""

    CLUSTER_ID = general.Time.cluster_id
    pass
