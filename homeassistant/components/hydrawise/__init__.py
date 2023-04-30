"""Support for Hydrawise cloud."""

from typing import Any

from hydrawiser.core import Hydrawiser
from requests.exceptions import ConnectTimeout, HTTPError
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DATA_HYDRAWISE,
    DOMAIN,
    LOGGER,
    NOTIFICATION_ID,
    NOTIFICATION_TITLE,
    SCAN_INTERVAL,
)
from .coordinator import HydrawiseDataUpdateCoordinator

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hunter Hydrawise component."""
    conf = config[DOMAIN]
    access_token = conf[CONF_ACCESS_TOKEN]
    scan_interval = conf.get(CONF_SCAN_INTERVAL)

    try:
        hydrawise = await hass.async_add_executor_job(Hydrawiser, access_token)
        hass.data[DATA_HYDRAWISE] = HydrawiseDataUpdateCoordinator(
            hass, hydrawise, scan_interval
        )
    except (ConnectTimeout, HTTPError) as ex:
        LOGGER.error("Unable to connect to Hydrawise cloud service: %s", str(ex))
        persistent_notification.create(
            hass,
            f"Error: {ex}<br />You will need to restart hass after fixing.",
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID,
        )
        return False

    # NOTE: We don't need to call async_config_entry_first_refresh() because
    # data is fetched when the Hydrawiser object is instantiated.

    return True


class HydrawiseEntity(CoordinatorEntity):
    """Entity class for Hydrawise devices."""

    _attr_attribution = "Data provided by hydrawise.com"

    def __init__(
        self,
        *,
        data: dict[str, Any],
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Hydrawise entity."""
        super().__init__(coordinator=coordinator)
        self.data = data
        self.api = self.coordinator.api
        self.entity_description = description
        self._attr_name = f"{self.data['name']} {description.name}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"identifier": self.data.get("relay")}
