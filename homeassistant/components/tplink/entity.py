"""Common code for tplink."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Concatenate, ParamSpec, TypeVar

from kasa import AuthenticationError, Device, KasaException, TimeoutError

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TPLinkDataUpdateCoordinator

_T = TypeVar("_T", bound="CoordinatedTPLinkEntity")
_P = ParamSpec("_P")


def async_refresh_after(
    func: Callable[Concatenate[_T, _P], Awaitable[None]],
) -> Callable[Concatenate[_T, _P], Coroutine[Any, Any, None]]:
    """Define a wrapper to raise HA errors and refresh after."""

    async def _async_wrap(self: _T, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)
        except AuthenticationError as ex:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_authentication",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except TimeoutError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_timeout",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        except KasaException as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_error",
                translation_placeholders={
                    "func": func.__name__,
                    "exc": str(ex),
                },
            ) from ex
        await self.coordinator.async_request_refresh()

    return _async_wrap


class CoordinatedTPLinkEntity(CoordinatorEntity[TPLinkDataUpdateCoordinator]):
    """Common base class for all coordinated tplink entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        parent: Device | None = None,
        add_to_parent: bool = False,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.device: Device = device
        unique_id = (
            f"{device.device_id}-parent"
            if parent and add_to_parent
            else device.device_id
        )
        device_id = parent.device_id if parent and add_to_parent else device.device_id
        if parent:
            name = parent.alias if add_to_parent else f"{parent.alias} - {device.alias}"
        else:
            name = device.alias
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            # Do we need to figure out migration for existing devices.
            # connections={(dr.CONNECTION_NETWORK_MAC, device.mac)},
            identifiers={(DOMAIN, str(device_id))},
            manufacturer="TP-Link",
            model=device.model,
            name=name,
            sw_version=device.hw_info["sw_ver"],
            hw_version=device.hw_info["hw_ver"],
        )
        if parent is not None and not add_to_parent:
            self._attr_device_info["via_device"] = (DOMAIN, str(parent.device_id))
