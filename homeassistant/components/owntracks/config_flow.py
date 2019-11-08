"""Config flow for OwnTracks."""
from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.auth.util import generate_secret

from .const import DOMAIN

CONF_SECRET = "secret"
CONF_CLOUDHOOK = "cloudhook"


def supports_encryption():
    """Test if we support encryption."""
    try:
        import nacl  # noqa pylint: disable=unused-import

        return True
    except OSError:
        return False


class OwnTracksFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up OwnTracks."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a user initiated set up flow to create OwnTracks webhook."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="one_instance_allowed")

        if user_input is None:
            return self.async_show_form(step_id="user")

        webhook_id, webhook_url, cloudhook = await self._get_webhook_id()

        secret = generate_secret(16)

        if supports_encryption():
            secret_desc = f"The encryption key is {secret} (on Android under preferences -> advanced)"
        else:
            secret_desc = "Encryption is not supported because nacl is not installed."

        return self.async_create_entry(
            title="OwnTracks",
            data={
                CONF_WEBHOOK_ID: webhook_id,
                CONF_SECRET: secret,
                CONF_CLOUDHOOK: cloudhook,
            },
            description_placeholders={
                "secret": secret_desc,
                "webhook_url": webhook_url,
                "android_url": "https://play.google.com/store/apps/details?id=org.owntracks.android",
                "ios_url": "https://itunes.apple.com/us/app/owntracks/id692424691?mt=8",
                "docs_url": "https://www.home-assistant.io/integrations/owntracks/",
            },
        )

    async def async_step_import(self, user_input):
        """Import a config flow from configuration."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="one_instance_allowed")
        webhook_id, _webhook_url, cloudhook = await self._get_webhook_id()
        secret = generate_secret(16)
        return self.async_create_entry(
            title="OwnTracks",
            data={
                CONF_WEBHOOK_ID: webhook_id,
                CONF_SECRET: secret,
                CONF_CLOUDHOOK: cloudhook,
            },
        )

    async def _get_webhook_id(self):
        """Generate webhook ID."""
        webhook_id = self.hass.components.webhook.async_generate_id()
        if (
            "cloud" in self.hass.config.components
            and self.hass.components.cloud.async_active_subscription()
        ):
            webhook_url = await self.hass.components.cloud.async_create_cloudhook(
                webhook_id
            )
            cloudhook = True
        else:
            webhook_url = self.hass.components.webhook.async_generate_url(webhook_id)
            cloudhook = False

        return webhook_id, webhook_url, cloudhook
