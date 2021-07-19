"""Config flow for Modem Caller ID integration."""
from phone_modem import PhoneModem
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE

from .const import DEFAULT_DEVICE, DEFAULT_NAME, DOMAIN, EXCEPTIONS

DATA_SCHEMA = vol.Schema({"name": str, "device": str})


class PhoneModemFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Phone Modem."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            device = user_input[CONF_DEVICE]

            await self.async_set_unique_id(device)
            self._abort_if_unique_id_configured()
            try:
                api = PhoneModem()
                await api.test(device)

            except EXCEPTIONS:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={CONF_DEVICE: device},
                )

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE,
                        default=user_input.get(CONF_DEVICE) or DEFAULT_DEVICE,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, config):
        """Import a config entry from configuration.yaml."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if "sensor" in config:
            for entry in config["sensor"]:
                if CONF_DEVICE not in entry:
                    config[CONF_DEVICE] = DEFAULT_DEVICE

        return await self.async_step_user(config)
