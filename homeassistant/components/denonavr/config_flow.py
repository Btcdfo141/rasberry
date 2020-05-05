"""Config flow to configure Denon AVR receivers using their HTTP interface."""
import logging
from urllib.parse import urlparse

import denonavr
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.const import CONF_HOST, CONF_TIMEOUT

from .receiver import ConnectDenonAVR

_LOGGER = logging.getLogger(__name__)

DOMAIN = "denonavr"

SUPPORTED_MANUFACTURERS = ["Denon", "DENON", "Marantz"]

CONF_SHOW_ALL_SOURCES = "show_all_sources"
CONF_ZONE2 = "zone2"
CONF_ZONE3 = "zone3"
CONF_RECEIVER_ID = "receiver_id"

DEFAULT_SHOW_SOURCES = False
DEFAULT_TIMEOUT = 2
DEFAULT_ZONE2 = False
DEFAULT_ZONE3 = False

CONFIG_SCHEMA = vol.Schema({vol.Optional(CONF_HOST): str})

SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            int, vol.Range(min=1)
        ),
        vol.Optional(CONF_SHOW_ALL_SOURCES, default=DEFAULT_SHOW_SOURCES): bool,
        vol.Optional(CONF_ZONE2, default=DEFAULT_ZONE2): bool,
        vol.Optional(CONF_ZONE3, default=DEFAULT_ZONE3): bool,
    }
)


class DenonAvrFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Denon AVR config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Denon AVR flow."""
        self.host = None
        self.timeout = DEFAULT_TIMEOUT
        self.show_all_sources = DEFAULT_SHOW_SOURCES
        self.zone2 = DEFAULT_ZONE2
        self.zone3 = DEFAULT_ZONE3
        self.d_receivers = []

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            # check if IP address is set manually
            host = user_input.get(CONF_HOST)
            if host:
                self.host = host
                return await self.async_step_settings()

            # discovery using denonavr library
            self.d_receivers = await self.hass.async_add_executor_job(denonavr.discover)
            # More than one receiver could be discovered by that method
            if len(self.d_receivers) == 1:
                self.host = self.d_receivers[0]["host"]
                return await self.async_step_settings()
            if len(self.d_receivers) > 1:
                # show selection form
                return await self.async_step_select()

            errors["base"] = "discovery_error"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def async_step_select(self, user_input=None):
        """Handle multiple receivers found."""
        errors = {}
        if user_input is not None:
            self.host = user_input["select_host"]
            return await self.async_step_settings()

        select_scheme = vol.Schema(
            {
                vol.Required("select_host"): vol.In(
                    [d_receiver["host"] for d_receiver in self.d_receivers]
                )
            }
        )

        return self.async_show_form(
            step_id="select", data_schema=select_scheme, errors=errors
        )

    async def async_step_settings(self, user_input=None):
        """Allow the user to specify settings."""
        if user_input is not None:
            # Get config option that have defaults
            self.timeout = user_input[CONF_TIMEOUT]
            self.show_all_sources = user_input[CONF_SHOW_ALL_SOURCES]
            self.zone2 = user_input[CONF_ZONE2]
            self.zone3 = user_input[CONF_ZONE3]

            return await self.async_step_connect()

        return self.async_show_form(step_id="settings", data_schema=SETTINGS_SCHEMA)

    async def async_step_connect(self, user_input=None):
        """Connect to the receiver."""
        connect_denonavr = ConnectDenonAVR(
            self.hass,
            self.host,
            self.timeout,
            self.show_all_sources,
            self.zone2,
            self.zone3,
        )
        if not await connect_denonavr.async_connect_receiver():
            return self.async_abort(reason="connection_error")
        receiver = connect_denonavr.receiver

        unique_id = self.construct_unique_id(
            receiver.model_name, receiver.serial_number
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=receiver.name,
            data={
                CONF_HOST: self.host,
                CONF_TIMEOUT: self.timeout,
                CONF_SHOW_ALL_SOURCES: self.show_all_sources,
                CONF_ZONE2: self.zone2,
                CONF_ZONE3: self.zone3,
                CONF_RECEIVER_ID: unique_id,
            },
        )

    async def async_step_ssdp(self, discovery_info):
        """Handle a discovered Denon AVR.

        This flow is triggered by the SSDP component. It will check if the
        host is already configured and delegate to the import step if not.
        """
        # Filter out non-Denon AVRs#1
        if (
            discovery_info.get(ssdp.ATTR_UPNP_MANUFACTURER)
            not in SUPPORTED_MANUFACTURERS
        ):
            return self.async_abort(reason="not_denonavr_manufacturer")

        # Check if required information is present to set the unique_id
        if (
            ssdp.ATTR_UPNP_MODEL_NAME not in discovery_info
            or ssdp.ATTR_UPNP_SERIAL not in discovery_info
        ):
            return self.async_abort(reason="not_denonavr_missing")

        model_name = discovery_info[ssdp.ATTR_UPNP_MODEL_NAME]
        serial_number = discovery_info[ssdp.ATTR_UPNP_SERIAL]
        self.host = urlparse(discovery_info[ssdp.ATTR_SSDP_LOCATION]).hostname

        unique_id = self.construct_unique_id(model_name, serial_number)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return await self.async_step_settings()

    @staticmethod
    def construct_unique_id(model_name, serial_number):
        """Construct the unique id from the ssdp discovery or user_step."""
        return f"{model_name}-{serial_number}"
