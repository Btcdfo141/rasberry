"""The Tomorrow.io integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from math import ceil
from typing import Any

from pytomorrowio import TomorrowioV4
from pytomorrowio.const import CURRENT, FORECASTS
from pytomorrowio.exceptions import (
    CantConnectException,
    InvalidAPIKeyException,
    RateLimitedException,
    UnknownException,
)

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.weather import DOMAIN as WEATHER_DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ATTRIBUTION,
    CONF_MAX_REQUESTS_PER_DAY,
    CONF_TIMESTEP,
    DEFAULT_MAX_REQUESTS_PER_DAY,
    DOMAIN,
    INTEGRATION_NAME,
    TMRW_ATTR_CARBON_MONOXIDE,
    TMRW_ATTR_CHINA_AQI,
    TMRW_ATTR_CHINA_HEALTH_CONCERN,
    TMRW_ATTR_CHINA_PRIMARY_POLLUTANT,
    TMRW_ATTR_CLOUD_BASE,
    TMRW_ATTR_CLOUD_CEILING,
    TMRW_ATTR_CLOUD_COVER,
    TMRW_ATTR_CONDITION,
    TMRW_ATTR_DEW_POINT,
    TMRW_ATTR_EPA_AQI,
    TMRW_ATTR_EPA_HEALTH_CONCERN,
    TMRW_ATTR_EPA_PRIMARY_POLLUTANT,
    TMRW_ATTR_FEELS_LIKE,
    TMRW_ATTR_FIRE_INDEX,
    TMRW_ATTR_HUMIDITY,
    TMRW_ATTR_NITROGEN_DIOXIDE,
    TMRW_ATTR_OZONE,
    TMRW_ATTR_PARTICULATE_MATTER_10,
    TMRW_ATTR_PARTICULATE_MATTER_25,
    TMRW_ATTR_POLLEN_GRASS,
    TMRW_ATTR_POLLEN_TREE,
    TMRW_ATTR_POLLEN_WEED,
    TMRW_ATTR_PRECIPITATION,
    TMRW_ATTR_PRECIPITATION_PROBABILITY,
    TMRW_ATTR_PRECIPITATION_TYPE,
    TMRW_ATTR_PRESSURE,
    TMRW_ATTR_PRESSURE_SURFACE_LEVEL,
    TMRW_ATTR_SOLAR_GHI,
    TMRW_ATTR_SULPHUR_DIOXIDE,
    TMRW_ATTR_TEMPERATURE,
    TMRW_ATTR_TEMPERATURE_HIGH,
    TMRW_ATTR_TEMPERATURE_LOW,
    TMRW_ATTR_VISIBILITY,
    TMRW_ATTR_WIND_DIRECTION,
    TMRW_ATTR_WIND_GUST,
    TMRW_ATTR_WIND_SPEED,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [SENSOR_DOMAIN, WEATHER_DOMAIN]


def _other_config_entries_same_api_key(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> list[ConfigEntry]:
    """Return all other config entries that use the same API key."""
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != config_entry.entry_id
        and entry.data[CONF_API_KEY] == config_entry.data[CONF_API_KEY]
    ]


@callback
def _set_update_interval(hass: HomeAssistant, current_entry: ConfigEntry) -> timedelta:
    """Recalculate update_interval based on existing Tomorrow.io instances and update them."""
    api_calls = 2
    # We check how many Tomorrow.io configured instances are using the same API key and
    # calculate interval to not exceed allowed numbers of requests. Divide 90% of
    # max requests per day by the number of API calls because we want a buffer in the
    # number of API calls left at the end of the day.
    other_instance_entries = _other_config_entries_same_api_key(hass, current_entry)

    interval = timedelta(
        minutes=(
            ceil(
                (24 * 60 * (len(other_instance_entries) + 1) * api_calls)
                / (current_entry.options[CONF_MAX_REQUESTS_PER_DAY] * 0.9)
            )
        )
    )

    for entry in other_instance_entries:
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id].update_interval = interval

    return interval


async def _update_handler(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle the update of a config entry."""
    max_requests = config_entry.options[CONF_MAX_REQUESTS_PER_DAY]
    api_key = config_entry.data[CONF_API_KEY]
    # If this is the first config entry to be updated, we need to update all of the
    # other config entries that use the same API key
    if max_requests != hass.data[DOMAIN][CONF_MAX_REQUESTS_PER_DAY][api_key]:
        # Update the master requests value so that updates to other entries don't
        # trigger an infinite loop
        hass.data[DOMAIN][CONF_MAX_REQUESTS_PER_DAY][api_key] = max_requests

        # Update all other config entries that use the same API key
        other_instance_entries = _other_config_entries_same_api_key(hass, config_entry)
        for entry in other_instance_entries:
            hass.config_entries.async_update_entry(
                entry,
                options={**entry.options, CONF_MAX_REQUESTS_PER_DAY: max_requests},
            )

        # Update the coordinator's update interval
        hass.data[DOMAIN][config_entry.entry_id].update_interval = _set_update_interval(
            hass, config_entry
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tomorrow.io API from a config entry."""
    # Let's precreate the device so that if this is a first time setup for a config
    # entry imported from a ClimaCell entry, we can apply customizations from the old
    # device.
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_API_KEY])},
        name=INTEGRATION_NAME,
        manufacturer=INTEGRATION_NAME,
        sw_version="v4",
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    # If this is an import and we still have the old config entry ID in the entry data,
    # it means we are setting this entry up for the first time after a migration from
    # ClimaCell to Tomorrow.io. In order to preserve any customizations on the ClimaCell
    # entities, we need to remove each old entity, creating a new entity in its place
    # but attached to this entry.
    if entry.source == SOURCE_IMPORT and "old_config_entry_id" in entry.data:
        # Remove the old config entry ID from the entry data so we don't try this again
        # on the next setup
        data = entry.data.copy()
        old_config_entry_id = data.pop("old_config_entry_id")
        hass.config_entries.async_update_entry(entry, data=data)
        _LOGGER.debug(
            (
                "Setting up imported climacell entry %s for the first time as "
                "tomorrowio entry %s"
            ),
            old_config_entry_id,
            entry.entry_id,
        )

        ent_reg = er.async_get(hass)
        for entity_entry in er.async_entries_for_config_entry(
            ent_reg, old_config_entry_id
        ):
            _LOGGER.debug("Removing %s", entity_entry.entity_id)
            ent_reg.async_remove(entity_entry.entity_id)
            # In case the API key has changed due to a V3 -> V4 change, we need to
            # generate the new entity's unique ID
            new_unique_id = (
                f"{entry.data[CONF_API_KEY]}_"
                f"{'_'.join(entity_entry.unique_id.split('_')[1:])}"
            )
            _LOGGER.debug(
                "Re-creating %s for the new config entry", entity_entry.entity_id
            )
            # We will precreate the entity so that any customizations can be preserved
            new_entity_entry = ent_reg.async_get_or_create(
                entity_entry.domain,
                DOMAIN,
                new_unique_id,
                suggested_object_id=entity_entry.entity_id.split(".")[1],
                disabled_by=entity_entry.disabled_by,
                config_entry=entry,
                original_name=entity_entry.original_name,
                original_icon=entity_entry.original_icon,
            )
            _LOGGER.debug("Re-created %s", new_entity_entry.entity_id)
            # If there are customizations on the old entity, apply them to the new one
            if entity_entry.name or entity_entry.icon:
                ent_reg.async_update_entity(
                    new_entity_entry.entity_id,
                    name=entity_entry.name,
                    icon=entity_entry.icon,
                )

        # We only have one device in the registry but we will do a loop just in case
        for old_device in dr.async_entries_for_config_entry(
            dev_reg, old_config_entry_id
        ):
            if old_device.name_by_user:
                dev_reg.async_update_device(
                    device.id, name_by_user=old_device.name_by_user
                )

        # Remove the old config entry and now the entry is fully migrated
        hass.async_create_task(hass.config_entries.async_remove(old_config_entry_id))

    if CONF_MAX_REQUESTS_PER_DAY not in entry.options:
        hass.config_entries.async_update_entry(
            entry,
            options={
                **entry.options,
                CONF_MAX_REQUESTS_PER_DAY: DEFAULT_MAX_REQUESTS_PER_DAY,
            },
        )

    api_key = entry.data[CONF_API_KEY]
    hass.data.setdefault(DOMAIN, {}).setdefault(CONF_MAX_REQUESTS_PER_DAY, {})
    hass.data[DOMAIN][CONF_MAX_REQUESTS_PER_DAY][api_key] = entry.options[
        CONF_MAX_REQUESTS_PER_DAY
    ]

    api = TomorrowioV4(
        api_key,
        entry.data[CONF_LOCATION][CONF_LATITUDE],
        entry.data[CONF_LOCATION][CONF_LONGITUDE],
        session=async_get_clientsession(hass),
    )

    coordinator = TomorrowioDataUpdateCoordinator(
        hass,
        entry,
        api,
        _set_update_interval(hass, entry),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_update_handler))

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    hass.data[DOMAIN].pop(config_entry.entry_id)
    if not _other_config_entries_same_api_key(hass, config_entry):
        hass.data[DOMAIN][CONF_MAX_REQUESTS_PER_DAY].pop(
            config_entry.data[CONF_API_KEY]
        )
    if not hass.data[DOMAIN][CONF_MAX_REQUESTS_PER_DAY]:
        hass.data[DOMAIN].pop(CONF_MAX_REQUESTS_PER_DAY)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok


class TomorrowioDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold Tomorrow.io data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: TomorrowioV4,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""

        self._config_entry = config_entry
        self._api = api
        self.name = config_entry.data[CONF_NAME]
        self.data = {CURRENT: {}, FORECASTS: {}}

        super().__init__(
            hass,
            _LOGGER,
            name=config_entry.data[CONF_NAME],
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            return await self._api.realtime_and_all_forecasts(
                [
                    TMRW_ATTR_TEMPERATURE,
                    TMRW_ATTR_HUMIDITY,
                    TMRW_ATTR_PRESSURE,
                    TMRW_ATTR_WIND_SPEED,
                    TMRW_ATTR_WIND_DIRECTION,
                    TMRW_ATTR_CONDITION,
                    TMRW_ATTR_VISIBILITY,
                    TMRW_ATTR_OZONE,
                    TMRW_ATTR_WIND_GUST,
                    TMRW_ATTR_CLOUD_COVER,
                    TMRW_ATTR_PRECIPITATION_TYPE,
                    *(
                        TMRW_ATTR_CARBON_MONOXIDE,
                        TMRW_ATTR_CHINA_AQI,
                        TMRW_ATTR_CHINA_HEALTH_CONCERN,
                        TMRW_ATTR_CHINA_PRIMARY_POLLUTANT,
                        TMRW_ATTR_CLOUD_BASE,
                        TMRW_ATTR_CLOUD_CEILING,
                        TMRW_ATTR_CLOUD_COVER,
                        TMRW_ATTR_DEW_POINT,
                        TMRW_ATTR_EPA_AQI,
                        TMRW_ATTR_EPA_HEALTH_CONCERN,
                        TMRW_ATTR_EPA_PRIMARY_POLLUTANT,
                        TMRW_ATTR_FEELS_LIKE,
                        TMRW_ATTR_FIRE_INDEX,
                        TMRW_ATTR_NITROGEN_DIOXIDE,
                        TMRW_ATTR_OZONE,
                        TMRW_ATTR_PARTICULATE_MATTER_10,
                        TMRW_ATTR_PARTICULATE_MATTER_25,
                        TMRW_ATTR_POLLEN_GRASS,
                        TMRW_ATTR_POLLEN_TREE,
                        TMRW_ATTR_POLLEN_WEED,
                        TMRW_ATTR_PRECIPITATION_TYPE,
                        TMRW_ATTR_PRESSURE_SURFACE_LEVEL,
                        TMRW_ATTR_SOLAR_GHI,
                        TMRW_ATTR_SULPHUR_DIOXIDE,
                        TMRW_ATTR_WIND_GUST,
                    ),
                ],
                [
                    TMRW_ATTR_TEMPERATURE_LOW,
                    TMRW_ATTR_TEMPERATURE_HIGH,
                    TMRW_ATTR_WIND_SPEED,
                    TMRW_ATTR_WIND_DIRECTION,
                    TMRW_ATTR_CONDITION,
                    TMRW_ATTR_PRECIPITATION,
                    TMRW_ATTR_PRECIPITATION_PROBABILITY,
                ],
                nowcast_timestep=self._config_entry.options[CONF_TIMESTEP],
            )
        except (
            CantConnectException,
            InvalidAPIKeyException,
            RateLimitedException,
            UnknownException,
        ) as error:
            raise UpdateFailed from error


class TomorrowioEntity(CoordinatorEntity[TomorrowioDataUpdateCoordinator]):
    """Base Tomorrow.io Entity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: TomorrowioDataUpdateCoordinator,
        api_version: int,
    ) -> None:
        """Initialize Tomorrow.io Entity."""
        super().__init__(coordinator)
        self.api_version = api_version
        self._config_entry = config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.data[CONF_API_KEY])},
            name="Tomorrow.io",
            manufacturer="Tomorrow.io",
            sw_version=f"v{self.api_version}",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    def _get_current_property(self, property_name: str) -> int | str | float | None:
        """
        Get property from current conditions.

        Used for V4 API.
        """
        return self.coordinator.data.get(CURRENT, {}).get(property_name)

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION
