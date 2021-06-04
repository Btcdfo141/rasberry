"""The Netio switch component."""
from __future__ import annotations

import logging
from typing import Any, Final

from aiohttp import web
from pynetio import Netio
import voluptuous as vol
from voluptuous.schema_builder import Schema

from homeassistant import util
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.switch import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    STATE_ON,
)
from homeassistant.core import Event, HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_START_DATE,
    ATTR_TOTAL_CONSUMPTION_KWH,
    CONF_OUTLETS,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    MIN_TIME_BETWEEN_SCANS,
    URL_API_NETIO_EP,
)
from .model import Device

_LOGGER: Final = logging.getLogger(__name__)

DEVICES: dict[str, Device] = {}

PLATFORM_SCHEMA: Final[Schema] = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_OUTLETS): {cv.string: cv.string},
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> bool:
    """Set up the Netio platform."""

    host: str = config[CONF_HOST]
    username: str = config.get(CONF_USERNAME, DEFAULT_USERNAME)
    password: str = config[CONF_PASSWORD]
    port: int = config.get(CONF_PORT, DEFAULT_PORT)

    if not DEVICES:
        hass.http.register_view(NetioApiView())

    dev = Netio(host, port, username, password)

    DEVICES[host] = Device(dev, [])

    # Throttle the update for all Netio switches of one Netio
    dev.update = util.Throttle(MIN_TIME_BETWEEN_SCANS)(dev.update)

    for key in config[CONF_OUTLETS]:
        switch = NetioSwitch(DEVICES[host].netio, key, config[CONF_OUTLETS][key])
        DEVICES[host].entities.append(switch)

    add_entities(DEVICES[host].entities)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, dispose)
    return True


def dispose(event: Event) -> None:
    """Close connections to Netio Devices."""
    for value in DEVICES.values():
        value.netio.stop()


class NetioApiView(HomeAssistantView):
    """WSGI handler class."""

    url = URL_API_NETIO_EP
    name = "api:netio"

    @callback
    def get(self, request: web.Request, host: str) -> web.Response:
        """Request handler."""
        data = request.query
        states: list[bool] = []
        consumptions: list[float] = []
        cumulated_consumptions: list[float] = []
        start_dates: list[str] = []

        for i in range(1, 5):
            out = "output%d" % i
            states.append(data.get("%s_state" % out) == STATE_ON)
            consumptions.append(float(data.get("%s_consumption" % out, 0)))
            cumulated_consumptions.append(
                float(data.get("%s_cumulatedConsumption" % out, 0)) / 1000
            )
            start_dates.append(data.get("%s_consumptionStart" % out, ""))

        _LOGGER.debug(
            "%s: %s, %s, %s since %s",
            host,
            states,
            consumptions,
            cumulated_consumptions,
            start_dates,
        )

        ndev: Netio = DEVICES[host].netio
        ndev.consumptions = consumptions
        ndev.cumulated_consumptions = cumulated_consumptions
        ndev.states = states
        ndev.start_dates = start_dates

        for dev in DEVICES[host].entities:
            dev.async_write_ha_state()

        return self.json(True)


class NetioSwitch(SwitchEntity):
    """Provide a Netio linked switch."""

    def __init__(self, netio: Netio, outlet: str, name: str) -> None:
        """Initialize the Netio switch."""
        self._name = name
        self.outlet = outlet
        self.netio = netio

    @property
    def name(self) -> str:
        """Return the device's name."""
        return self._name

    @property
    def available(self) -> bool:
        """Return true if entity is available."""
        return not hasattr(self, "telnet")

    def turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        self._set(True)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        self._set(False)

    def _set(self, value: bool) -> None:
        val = list("uuuu")
        val[int(self.outlet) - 1] = "1" if value else "0"
        self.netio.get("port list %s" % "".join(val))
        self.netio.states[int(self.outlet) - 1] = value
        self.schedule_update_ha_state()

    @property
    def is_on(self) -> bool:
        """Return the switch's status."""
        return self.netio.states[int(self.outlet) - 1]  # type: ignore[no-any-return]

    def update(self) -> None:
        """Update the state."""
        self.netio.update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return optional state attributes."""
        return {
            ATTR_TOTAL_CONSUMPTION_KWH: self.cumulated_consumption_kwh,
            ATTR_START_DATE: self.start_date.split("|")[0],
        }

    @property
    def current_power_w(self) -> int:
        """Return actual power."""
        return self.netio.consumptions[int(self.outlet) - 1]  # type: ignore[no-any-return]

    @property
    def cumulated_consumption_kwh(self) -> int:
        """Return the total enerygy consumption since start_date."""
        return self.netio.cumulated_consumptions[int(self.outlet) - 1]  # type: ignore[no-any-return]

    @property
    def start_date(self) -> str:
        """Point in time when the energy accumulation started."""
        return self.netio.start_dates[int(self.outlet) - 1]  # type: ignore[no-any-return]
