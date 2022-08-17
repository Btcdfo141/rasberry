"""The bluetooth integration."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
import itertools
import logging
from typing import TYPE_CHECKING, Final

from bleak.backends.scanner import AdvertisementDataCallback

from homeassistant import config_entries
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    HomeAssistant,
    callback as hass_callback,
)
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.event import async_track_time_interval

from .const import SOURCE_LOCAL, UNAVAILABLE_TRACK_SECONDS
from .match import (
    ADDRESS,
    BluetoothCallbackMatcher,
    IntegrationMatcher,
    ble_device_matches,
)
from .models import BluetoothCallback, BluetoothChange, BluetoothServiceInfoBleak
from .usage import install_multiple_bleak_catcher, uninstall_multiple_bleak_catcher

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    from .scanner import HaScanner

FILTER_UUIDS: Final = "UUIDs"


_LOGGER = logging.getLogger(__name__)


def _dispatch_bleak_callback(
    callback: AdvertisementDataCallback,
    filters: dict[str, set[str]],
    device: BLEDevice,
    advertisement_data: AdvertisementData,
) -> None:
    """Dispatch the callback."""
    if not callback:
        # Callback destroyed right before being called, ignore
        return  # type: ignore[unreachable] # pragma: no cover

    if (uuids := filters.get(FILTER_UUIDS)) and not uuids.intersection(
        advertisement_data.service_uuids
    ):
        return

    try:
        callback(device, advertisement_data)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error in callback: %s", callback)


class BluetoothManager:
    """Manage Bluetooth."""

    def __init__(
        self,
        hass: HomeAssistant,
        integration_matcher: IntegrationMatcher,
    ) -> None:
        """Init bluetooth discovery."""
        self.hass = hass
        self._integration_matcher = integration_matcher
        self._cancel_unavailable_tracking: CALLBACK_TYPE | None = None
        self._cancel_stop: CALLBACK_TYPE | None = None
        self._unavailable_callbacks: dict[str, list[Callable[[str], None]]] = {}
        self._callbacks: list[
            tuple[BluetoothCallback, BluetoothCallbackMatcher | None]
        ] = []
        self._bleak_callbacks: list[
            tuple[AdvertisementDataCallback, dict[str, set[str]]]
        ] = []
        self.history: dict[str, tuple[BLEDevice, AdvertisementData, float, str]] = {}
        self._scanners: list[HaScanner] = []

    @hass_callback
    def async_setup(self) -> None:
        """Set up the bluetooth manager."""
        install_multiple_bleak_catcher()
        self.async_setup_unavailable_tracking()
        self._cancel_stop = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._async_hass_stopping
        )

    @property
    def discovered_devices(self) -> Iterable[BLEDevice]:
        """Return all of discovered devices from all the scanners."""
        return itertools.chain.from_iterable(
            scanner.discovered_devices for scanner in self._scanners
        )

    @hass_callback
    def async_setup_unavailable_tracking(self) -> None:
        """Set up the unavailable tracking."""

        @hass_callback
        def _async_check_unavailable(now: datetime) -> None:
            """Watch for unavailable devices."""
            history_set = set(self.history)
            active_addresses = {device.address for device in self.discovered_devices}
            disappeared = history_set.difference(active_addresses)
            for address in disappeared:
                del self.history[address]
                if not (callbacks := self._unavailable_callbacks.get(address)):
                    continue
                for callback in callbacks:
                    try:
                        callback(address)
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.exception("Error in unavailable callback")

        self._cancel_unavailable_tracking = async_track_time_interval(
            self.hass,
            _async_check_unavailable,
            timedelta(seconds=UNAVAILABLE_TRACK_SECONDS),
        )

    @hass_callback
    def scanner_adv_received(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
        monotonic_time: float,
        source: str,
    ) -> None:
        """Handle a new advertisement from any scanner.

        Callbacks from all the scanners arrive here.

        In the future we will only process callbacks if

        - The device is not in the history
        - The RSSI is above a certain threshold better than
          than the source from the history or the timestamp
          in the history is older than 180s
        """
        self.history[device.address] = (
            device,
            advertisement_data,
            monotonic_time,
            source,
        )

        for callback_filters in self._bleak_callbacks:
            _dispatch_bleak_callback(*callback_filters, device, advertisement_data)

        matched_domains = self._integration_matcher.match_domains(
            device, advertisement_data
        )
        _LOGGER.debug(
            "%s: %s %s match: %s",
            source,
            device.address,
            advertisement_data,
            matched_domains,
        )

        if not matched_domains and not self._callbacks:
            return

        service_info: BluetoothServiceInfoBleak | None = None
        for callback, matcher in self._callbacks:
            if matcher is None or ble_device_matches(
                matcher, device, advertisement_data
            ):
                if service_info is None:
                    service_info = BluetoothServiceInfoBleak.from_advertisement(
                        device, advertisement_data, source
                    )
                try:
                    callback(service_info, BluetoothChange.ADVERTISEMENT)
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Error in bluetooth callback")

        if not matched_domains:
            return
        if service_info is None:
            service_info = BluetoothServiceInfoBleak.from_advertisement(
                device, advertisement_data, source
            )
        for domain in matched_domains:
            discovery_flow.async_create_flow(
                self.hass,
                domain,
                {"source": config_entries.SOURCE_BLUETOOTH},
                service_info,
            )

    @hass_callback
    def async_track_unavailable(
        self, callback: Callable[[str], None], address: str
    ) -> Callable[[], None]:
        """Register a callback."""
        self._unavailable_callbacks.setdefault(address, []).append(callback)

        @hass_callback
        def _async_remove_callback() -> None:
            self._unavailable_callbacks[address].remove(callback)
            if not self._unavailable_callbacks[address]:
                del self._unavailable_callbacks[address]

        return _async_remove_callback

    @hass_callback
    def async_register_callback(
        self,
        callback: BluetoothCallback,
        matcher: BluetoothCallbackMatcher | None = None,
    ) -> Callable[[], None]:
        """Register a callback."""
        callback_entry = (callback, matcher)
        self._callbacks.append(callback_entry)

        @hass_callback
        def _async_remove_callback() -> None:
            self._callbacks.remove(callback_entry)

        # If we have history for the subscriber, we can trigger the callback
        # immediately with the last packet so the subscriber can see the
        # device.
        if (
            matcher
            and (address := matcher.get(ADDRESS))
            and (device_adv_data := self.history.get(address))
        ):
            ble_device, adv_data, _, _ = device_adv_data
            try:
                callback(
                    BluetoothServiceInfoBleak.from_advertisement(
                        ble_device, adv_data, SOURCE_LOCAL
                    ),
                    BluetoothChange.ADVERTISEMENT,
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error in bluetooth callback")

        return _async_remove_callback

    @hass_callback
    def async_ble_device_from_address(self, address: str) -> BLEDevice | None:
        """Return the BLEDevice if present."""
        if ble_adv := self.history.get(address):
            return ble_adv[0]
        return None

    @hass_callback
    def async_address_present(self, address: str) -> bool:
        """Return if the address is present."""
        return address in self.history

    @hass_callback
    def async_discovered_service_info(self) -> list[BluetoothServiceInfoBleak]:
        """Return if the address is present."""
        return [
            BluetoothServiceInfoBleak.from_advertisement(
                device_adv[0], device_adv[1], SOURCE_LOCAL
            )
            for device_adv in self.history.values()
        ]

    async def _async_hass_stopping(self, event: Event) -> None:
        """Stop the Bluetooth integration at shutdown."""
        _LOGGER.debug("Stopping bluetooth manager")
        if self._cancel_unavailable_tracking:
            self._cancel_unavailable_tracking()
            self._cancel_unavailable_tracking = None
        if self._cancel_stop:
            self._cancel_stop()
            self._cancel_stop = None
        uninstall_multiple_bleak_catcher()

    @hass_callback
    def async_rediscover_address(self, address: str) -> None:
        """Trigger discovery of devices which have already been seen."""
        self._integration_matcher.async_clear_address(address)

    def async_register_scanner(self, scanner: HaScanner) -> CALLBACK_TYPE:
        """Register a new scanner."""

        def _unregister_scanner() -> None:
            self._scanners.remove(scanner)

        self._scanners.append(scanner)
        return _unregister_scanner

    @hass_callback
    def async_register_bleak_callback(
        self, callback: AdvertisementDataCallback, filters: dict[str, set[str]]
    ) -> CALLBACK_TYPE:
        """Register a callback."""
        callback_entry = (callback, filters)
        self._bleak_callbacks.append(callback_entry)

        @hass_callback
        def _remove_callback() -> None:
            self._bleak_callbacks.remove(callback_entry)

        # Replay the history since otherwise we miss devices
        # that were already discovered before the callback was registered
        # or we are in passive mode
        for device, advertisement_data, _, _ in self.history.values():
            _dispatch_bleak_callback(callback, filters, device, advertisement_data)

        return _remove_callback
