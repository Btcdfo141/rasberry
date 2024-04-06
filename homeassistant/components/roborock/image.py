"""Support for Roborock image."""

import asyncio
import io
from itertools import chain

from roborock import RoborockCommand
from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify
import homeassistant.util.dt as dt_util

from .const import DOMAIN, IMAGE_CACHE_INTERVAL, IMAGE_DRAWABLES, MAP_SLEEP
from .coordinator import RoborockDataUpdateCoordinator
from .device import RoborockCoordinatedEntity
from .roborock_storage import RoborockStorage, get_roborock_storage


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Roborock image platform."""

    coordinators: dict[str, RoborockDataUpdateCoordinator] = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    entities = list(
        chain.from_iterable(
            await asyncio.gather(
                *(
                    create_coordinator_maps(coord, hass)
                    for coord in coordinators.values()
                )
            )
        )
    )
    async_add_entities(entities)


class RoborockMap(RoborockCoordinatedEntity, ImageEntity, RestoreEntity):
    """A class to let you visualize the map."""

    _attr_has_entity_name = True

    def __init__(
        self,
        unique_id: str,
        coordinator: RoborockDataUpdateCoordinator,
        map_flag: int,
        starting_map: bytes,
        map_name: str,
        roborock_storage: RoborockStorage,
        create_map: bool,
    ) -> None:
        """Initialize a Roborock map."""
        RoborockCoordinatedEntity.__init__(self, unique_id, coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_name: str = map_name
        self.parser = RoborockMapDataParser(
            ColorsPalette(), Sizes(), IMAGE_DRAWABLES, ImageConfig(), []
        )
        self._attr_image_last_updated = dt_util.utcnow()
        self.map_flag = map_flag
        if create_map:
            try:
                self.cached_map = self._create_image(starting_map)
            except HomeAssistantError:
                # If we failed to update the image on init, we set cached_map to None so that we are unavailable and can try again later.
                self.cached_map = b""
        else:
            # Map was cached - so we can load it directly.
            self.cached_map = starting_map
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._roborock_storage = roborock_storage

    @property
    def available(self):
        """Determines if the entity is available."""
        return self.cached_map == b""

    @property
    def is_selected(self) -> bool:
        """Return if this map is the currently selected map."""
        return self.map_flag == self.coordinator.current_map

    def is_map_valid(self) -> bool:
        """Update this map if it is the current active map, and the vacuum is cleaning."""
        return self.cached_map == b"" or (
            self.is_selected
            and self.image_last_updated is not None
            and self.coordinator.roborock_device_info.props.status is not None
            and bool(self.coordinator.roborock_device_info.props.status.in_cleaning)
        )

    def _handle_coordinator_update(self):
        # Bump last updated every third time the coordinator runs, so that async_image
        # will be called and we will evaluate on the new coordinator data if we should
        # update the cache.
        if (
            dt_util.utcnow() - self.image_last_updated
        ).total_seconds() > IMAGE_CACHE_INTERVAL and self.is_map_valid():
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        """Update the image if it is not cached."""
        if self.is_map_valid():
            map_data: bytes = await self.cloud_api.get_map_v1()
            self.cached_map = self._create_image(map_data)
            self.coordinator.config_entry.async_create_task(
                self.hass,
                self._roborock_storage.async_save_map(self._attr_name, self.cached_map),
            )
        return self.cached_map

    def _create_image(self, map_bytes: bytes) -> bytes:
        """Create an image using the map parser."""
        parsed_map = self.parser.parse(map_bytes)
        if parsed_map.image is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="map_failure",
            )
        img_byte_arr = io.BytesIO()
        parsed_map.image.data.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()


async def create_coordinator_maps(
    coord: RoborockDataUpdateCoordinator, hass: HomeAssistant
) -> list[RoborockMap]:
    """Get the starting map information for all maps for this device. The following steps must be done synchronously.

    Only one map can be loaded at a time per device.
    """
    entities = []
    roborock_storage = await get_roborock_storage(hass, coord.config_entry.entry_id)
    cur_map = coord.current_map
    # This won't be None at this point as the coordinator will have run first.
    assert cur_map is not None
    # Sort the maps so that we start with the current map and we can skip the
    # load_multi_map call.
    maps_info = sorted(
        coord.maps.items(), key=lambda data: data[0] == cur_map, reverse=True
    )
    maps = await asyncio.gather(
        *(roborock_storage.async_load_map(map_name) for map_name in coord.maps.values())
    )
    storage_updates = []
    for (map_flag, map_name), storage_map in zip(maps_info, maps):
        unique_id = f"{slugify(coord.roborock_device_info.device.duid)}_map_{map_name}"
        # Load the map - so we can access it with get_map_v1
        api_data: bytes | None = storage_map
        create_map = False
        if api_data is None:
            # Only get the map data on startup if a) we haven't added the entity before
            # b) The entity does not have the needed restore data.
            if map_flag != cur_map:
                # Only change the map and sleep if we have multiple maps.
                await coord.api.send_command(RoborockCommand.LOAD_MULTI_MAP, [map_flag])
                # We cannot get the map until the roborock servers fully process the
                # map change.
                await asyncio.sleep(MAP_SLEEP)
            # Get the map data
            api_data = await coord.cloud_api.get_map_v1()
            create_map = True
        roborock_map = RoborockMap(
            unique_id,
            coord,
            map_flag,
            api_data,
            map_name,
            roborock_storage,
            create_map,
        )
        entities.append(roborock_map)
        if create_map and roborock_map.cached_map != b"":
            storage_updates.append(
                roborock_storage.async_save_map(map_name, roborock_map.cached_map)
            )
    await asyncio.gather(*storage_updates)
    if len(coord.maps) != 1:
        # Set the map back to the map the user previously had selected so that it
        # does not change the end user's app.
        # Only needs to happen when we changed maps above.
        await coord.cloud_api.send_command(RoborockCommand.LOAD_MULTI_MAP, [cur_map])
    return entities
