"""Config flow for SeventeenTrack."""
from py17track import Client
from py17track.errors import SeventeenTrackError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_SHOW_ARCHIVED,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_ARCHIVED,
    DOMAIN,
)
from .errors import AuthenticationError, UnknownError

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def get_client(hass: HomeAssistant, entry):
    """Return SeventeenTrack client."""
    session = aiohttp_client.async_get_clientsession(hass)
    try:
        client = Client(session=session)
        login_result = await client.profile.login(
            entry[CONF_USERNAME], entry[CONF_PASSWORD]
        )
        if not login_result:
            raise AuthenticationError
    except SeventeenTrackError as err:
        raise UnknownError from err
    return client


class SeventeenTrackFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle SeventeenTrack config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return SeventeenTrackOptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Start the config flow."""
        self._reauth_unique_id = None

    async def _async_validate_input(self, user_input):
        """Validate the user input allows us to connect."""
        errors = {}
        try:
            await get_client(self.hass, user_input)

        except AuthenticationError:
            errors["base"] = "invalid_auth"
        except UnknownError:
            errors["base"] = "cannot_connect"

        return errors

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:

            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            errors = await self._async_validate_input(user_input)

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self._reauth_unique_id = self.context["unique_id"]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        errors = {}
        existing_entry = await self.async_set_unique_id(self._reauth_unique_id)
        if user_input is not None:
            user_input[CONF_USERNAME] = existing_entry.data[CONF_USERNAME]
            errors = await self._async_validate_input(user_input)

            if not errors:
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={
                        **existing_entry.data,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            description_placeholders={
                CONF_USERNAME: existing_entry.data[CONF_USERNAME]
            },
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class SeventeenTrackOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle SeventeenTrack options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): int,
            vol.Optional(
                CONF_SHOW_ARCHIVED,
                default=self.config_entry.options.get(
                    CONF_SHOW_ARCHIVED, DEFAULT_SHOW_ARCHIVED
                ),
            ): bool,
        }
        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
