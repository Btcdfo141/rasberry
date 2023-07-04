"""Support for ESPHome cameras."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

from aioesphomeapi import CameraInfo, CameraState
from aiohttp import web
import async_timeout

from homeassistant.components import camera
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import (
    EsphomeEntity,
    platform_async_setup_entry,
)

ESPHOME_CAMERA_TIMEOUT_SECONDS = 5  # This is hardcoded in ESPHome
MAXIMUM_WIFI_LATENCY_SECONDS = 5
CAMERA_TIMEOUT = ESPHOME_CAMERA_TIMEOUT_SECONDS + MAXIMUM_WIFI_LATENCY_SECONDS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up esphome cameras based on a config entry."""
    await platform_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        info_type=CameraInfo,
        entity_type=EsphomeCamera,
        state_type=CameraState,
    )


class EsphomeCamera(Camera, EsphomeEntity[CameraInfo, CameraState]):
    """A camera implementation for ESPHome."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize."""
        Camera.__init__(self)
        EsphomeEntity.__init__(self, *args, **kwargs)
        self._image_event = asyncio.Event()

    @callback
    def _on_state_update(self) -> None:
        """Notify listeners of new image when update arrives."""
        super()._on_state_update()
        image_event = self._image_event
        image_event.set()
        image_event.clear()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return single camera image bytes."""
        return await self._async_request_image(self._client.request_single_image)

    async def _async_request_image(
        self, request_method: Callable[[], Coroutine[Any, Any, None]]
    ) -> bytes | None:
        """Wait for an image to be available and return it."""
        if not self.available:
            return None
        await request_method()
        async with async_timeout.timeout(CAMERA_TIMEOUT):
            await self._image_event.wait()
        if not self.available:
            # Availability can change while waiting for 'image_event'
            return None  # type: ignore[unreachable]
        return self._state.data

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse:
        """Serve an HTTP MJPEG stream from the camera."""
        return await camera.async_get_still_stream(
            request,
            partial(self._async_request_image, self._client.request_image_stream),
            camera.DEFAULT_CONTENT_TYPE,
            0.0,
        )
