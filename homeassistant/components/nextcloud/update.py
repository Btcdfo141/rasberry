"""Summary data from Nextcoud."""
from __future__ import annotations

from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NextcloudDataUpdateCoordinator
from .entity import NextcloudEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Nextcloud update entity."""
    coordinator: NextcloudDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NextcloudUpdateSensor(coordinator, "Update", entry, None)])


class NextcloudUpdateSensor(NextcloudEntity, UpdateEntity):
    """Represents a Nextcloud update entity."""

    @property
    def installed_version(self) -> str | None:
        """Version installed and in use."""
        return self.coordinator.data.get("system version")

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self.coordinator.data.get(
            "system update available_version",
            self.installed_version
            # needed for Nextcloud serverinfo app pre 1.18.0
            if any(x.startswith("system update") for x in self.coordinator.data)
            else None,
        )

    @property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        if self.latest_version:
            ver = "-".join(self.latest_version.split(".")[:3])
            return f"https://nextcloud.com/changelog/#{ver}"
        return None
