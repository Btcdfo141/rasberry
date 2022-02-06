"""Tests for the SkyBell integration."""

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

USERNAME = "user"
PASSWORD = "password"

CONF_CONFIG_FLOW = {
    CONF_EMAIL: USERNAME,
    CONF_PASSWORD: PASSWORD,
}


def _patch_skybell():
    mocked_skybell = AsyncMock()
    mocked_skybell.user_id = "123456789012345678901234"
    return patch(
        "homeassistant.components.skybell.config_flow.Skybell.async_get_devices",
        return_value=[mocked_skybell],
    )
