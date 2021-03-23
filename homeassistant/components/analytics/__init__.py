"""Send instance and usage analytics."""
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .analytics import Analytics
from .const import ATTR_HUUID, ATTR_PREFERENCES, DOMAIN, INTERVAL


async def async_setup(hass: HomeAssistant, _):
    """Set up the analytics integration."""
    analytics = Analytics(hass)

    # Load stored data
    await analytics.load()

    async def start_schedule(_event):
        """Start the send schedule after the started event."""
        # Wait 15 min after started
        async_call_later(hass, 900, analytics.send_analytics)

        # Send every day
        async_track_time_interval(hass, analytics.send_analytics, INTERVAL)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_schedule)

    websocket_api.async_register_command(hass, websocket_analytics_preferences)
    websocket_api.async_register_command(hass, websocket_analytics_preferences_update)

    hass.data[DOMAIN] = analytics
    return True


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "analytics"})
async def websocket_analytics_preferences(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict,
) -> None:
    """Return analytics preferences."""
    analytics: Analytics = hass.data[DOMAIN]
    huuid = await hass.helpers.instance_id.async_get()
    connection.send_result(
        msg["id"],
        {ATTR_PREFERENCES: analytics.preferences, ATTR_HUUID: huuid},
    )


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "analytics/preferences",
        vol.Required("preferences"): cv.ensure_list,
    }
)
async def websocket_analytics_preferences_update(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict,
) -> None:
    """Update analytics preferences."""
    preferences = msg[ATTR_PREFERENCES]
    analytics: Analytics = hass.data[DOMAIN]

    await analytics.save_preferences(preferences)
    await analytics.send_analytics()

    connection.send_result(
        msg["id"],
        {ATTR_PREFERENCES: analytics.preferences},
    )
