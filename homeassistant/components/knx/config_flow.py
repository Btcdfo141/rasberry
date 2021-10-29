"""Config flow for KNX."""
from __future__ import annotations

from collections import OrderedDict
from typing import Final

import voluptuous as vol
from xknx import XKNX
from xknx.io import DEFAULT_MCAST_GRP, DEFAULT_MCAST_PORT
from xknx.io.gateway_scanner import GatewayDescriptor, GatewayScanner

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_KNX_AUTOMATIC,
    CONF_KNX_CONNECTION_TYPE,
    CONF_KNX_INDIVIDUAL_ADDRESS,
    CONF_KNX_ROUTING,
    CONF_KNX_TUNNELING,
    DOMAIN,
)
from .schema import ConnectionSchema

CONF_KNX_GATEWAY: Final = "gateway"


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a KNX config flow."""

    VERSION = 1

    _tunnels: list = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self._tunnels = []
        return await self.async_step_type()

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle connection type configuration."""
        errors: dict = {}
        supported_connection_types = [CONF_KNX_TUNNELING, CONF_KNX_ROUTING]

        if user_input is None:
            gateways = await scan_for_gateways()

            if gateways:
                supported_connection_types.insert(0, CONF_KNX_AUTOMATIC)
                for gateway in gateways:
                    if gateway.supports_tunnelling:
                        self._tunnels.append(gateway)

        if user_input is not None:
            connection_type = user_input[CONF_KNX_CONNECTION_TYPE]
            if connection_type == CONF_KNX_AUTOMATIC:
                return self.async_create_entry(
                    title=CONF_KNX_AUTOMATIC, data=user_input
                )

            if connection_type == CONF_KNX_ROUTING:
                return await self.async_step_routing()

            if connection_type == CONF_KNX_TUNNELING and self._tunnels:
                return await self.async_step_tunnel()

            return await self.async_step_manual_tunnel(user_input)

        fields = OrderedDict()
        fields[vol.Required(CONF_KNX_CONNECTION_TYPE)] = vol.In(
            supported_connection_types
        )

        return self.async_show_form(
            step_id="type", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_manual_tunnel(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """General setup."""
        errors: dict = {}

        # prefill data for frontend
        _gateway_ip: str = ""
        _gateway_port: int = 3675
        if user_input is not None and CONF_HOST in user_input:
            _gateway_ip = user_input[CONF_HOST]
            _gateway_port = user_input[CONF_PORT]

        if user_input is not None and CONF_KNX_INDIVIDUAL_ADDRESS in user_input:
            return self.async_create_entry(
                title=user_input[CONF_HOST],
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_KNX_INDIVIDUAL_ADDRESS: user_input[
                        CONF_KNX_INDIVIDUAL_ADDRESS
                    ],
                    ConnectionSchema.CONF_KNX_ROUTE_BACK: user_input[
                        ConnectionSchema.CONF_KNX_ROUTE_BACK
                    ],
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_TUNNELING,
                },
            )

        fields = OrderedDict()
        fields[vol.Required(CONF_HOST, default=_gateway_ip)] = str
        fields[vol.Required(CONF_PORT, default=_gateway_port)] = vol.Coerce(int)
        fields[
            vol.Required(CONF_KNX_INDIVIDUAL_ADDRESS, default=XKNX.DEFAULT_ADDRESS)
        ] = str
        fields[
            vol.Required(ConnectionSchema.CONF_KNX_ROUTE_BACK, default=False)
        ] = vol.Coerce(bool)

        return self.async_show_form(
            step_id="manual_tunnel", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_tunnel(self, user_input: dict | None = None) -> FlowResult:
        """Select a tunnel from a list. Will be skipped if the gateway scan was unsuccessful or if only one gateway was found."""
        errors: dict = {}

        if user_input is not None:
            gateway: GatewayDescriptor = next(
                filter(
                    lambda _gateway: gateway_descriptor_to_string(_gateway)
                    == user_input[CONF_KNX_GATEWAY],  # type: ignore
                    self._tunnels,
                )
            )

            return await self.async_step_manual_tunnel(
                {
                    CONF_HOST: gateway.ip_addr,
                    CONF_PORT: gateway.port,
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_TUNNELING,
                }
            )

        # GatewayScanner returns a gateway for each physical interface, we only need to show it once,
        # thus set() is called.
        tunnel_repr = {
            gateway_descriptor_to_string(tunnel)
            for tunnel in self._tunnels
            if tunnel.supports_tunnelling
        }

        #  skip this step if the user has only one unique gateway.
        if len(tunnel_repr) == 1:
            _gateway: GatewayDescriptor = self._tunnels[0]
            return await self.async_step_manual_tunnel(
                {
                    CONF_HOST: _gateway.ip_addr,
                    CONF_PORT: _gateway.port,
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_TUNNELING,
                }
            )

        fields = OrderedDict()

        fields[vol.Required(CONF_KNX_GATEWAY)] = vol.In(tunnel_repr)

        return self.async_show_form(
            step_id="tunnel", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_routing(self, user_input: dict | None = None) -> FlowResult:
        """Routing setup."""
        errors: dict = {}

        if user_input is not None:
            return self.async_create_entry(
                title=CONF_KNX_ROUTING,
                data={
                    ConnectionSchema.CONF_KNX_MCAST_GRP: user_input[
                        ConnectionSchema.CONF_KNX_MCAST_GRP
                    ],
                    ConnectionSchema.CONF_KNX_MCAST_PORT: user_input[
                        ConnectionSchema.CONF_KNX_MCAST_PORT
                    ],
                    CONF_KNX_INDIVIDUAL_ADDRESS: user_input[
                        CONF_KNX_INDIVIDUAL_ADDRESS
                    ],
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_ROUTING,
                },
            )

        fields = OrderedDict()
        fields[
            vol.Required(CONF_KNX_INDIVIDUAL_ADDRESS, default=XKNX.DEFAULT_ADDRESS)
        ] = str
        fields[
            vol.Required(ConnectionSchema.CONF_KNX_MCAST_GRP, default=DEFAULT_MCAST_GRP)
        ] = str
        fields[
            vol.Required(
                ConnectionSchema.CONF_KNX_MCAST_PORT, default=DEFAULT_MCAST_PORT
            )
        ] = vol.Coerce(int)

        return self.async_show_form(
            step_id="routing", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_import(self, config: dict | None = None) -> FlowResult:
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries() or not config:
            return self.async_abort(reason="single_instance_allowed")

        if CONF_KNX_TUNNELING in config:
            return self.async_create_entry(
                title=config[CONF_KNX_TUNNELING][CONF_HOST],
                data={
                    CONF_HOST: config[CONF_KNX_TUNNELING][CONF_HOST],
                    CONF_PORT: config[CONF_KNX_TUNNELING][CONF_PORT],
                    CONF_KNX_INDIVIDUAL_ADDRESS: config[CONF_KNX_INDIVIDUAL_ADDRESS],
                    ConnectionSchema.CONF_KNX_ROUTE_BACK: config[CONF_KNX_TUNNELING][
                        ConnectionSchema.CONF_KNX_ROUTE_BACK
                    ],
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_TUNNELING,
                },
            )

        if CONF_KNX_ROUTING in config:
            return self.async_create_entry(
                title=CONF_KNX_ROUTING,
                data={
                    ConnectionSchema.CONF_KNX_MCAST_GRP: config[
                        ConnectionSchema.CONF_KNX_MCAST_GRP
                    ],
                    ConnectionSchema.CONF_KNX_MCAST_PORT: config[
                        ConnectionSchema.CONF_KNX_MCAST_PORT
                    ],
                    CONF_KNX_INDIVIDUAL_ADDRESS: config[CONF_KNX_INDIVIDUAL_ADDRESS],
                    CONF_KNX_CONNECTION_TYPE: CONF_KNX_ROUTING,
                },
            )

        return self.async_create_entry(
            title=CONF_KNX_AUTOMATIC,
            data={
                CONF_KNX_CONNECTION_TYPE: CONF_KNX_AUTOMATIC,
                CONF_KNX_INDIVIDUAL_ADDRESS: config[CONF_KNX_INDIVIDUAL_ADDRESS],
                ConnectionSchema.CONF_KNX_MCAST_GRP: config[
                    ConnectionSchema.CONF_KNX_MCAST_GRP
                ],
                ConnectionSchema.CONF_KNX_MCAST_PORT: config[
                    ConnectionSchema.CONF_KNX_MCAST_PORT
                ],
            },
        )


def gateway_descriptor_to_string(descriptor: GatewayDescriptor) -> str:
    """Return the string representation of the gateway descriptor."""
    return f"{descriptor.name} - {descriptor.ip_addr}:{descriptor.port}"


async def scan_for_gateways() -> list:
    """Scan for gateways within the network."""
    xknx = XKNX()
    gatewayscanner = GatewayScanner(xknx, timeout_in_seconds=4)
    return await gatewayscanner.scan()
