"""The dhcp integration."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Iterable
import contextlib
from dataclasses import dataclass
from datetime import timedelta
from fnmatch import translate
from functools import lru_cache
import itertools
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Final, cast

from aiodiscover import DiscoverHosts
from aiodiscover.discovery import (
    HOSTNAME as DISCOVERY_HOSTNAME,
    IP_ADDRESS as DISCOVERY_IP_ADDRESS,
    MAC_ADDRESS as DISCOVERY_MAC_ADDRESS,
)
from cached_ipaddress import cached_ip_addresses
from scapy.config import conf
from scapy.error import Scapy_Exception

from homeassistant import config_entries
from homeassistant.components.device_tracker import (
    ATTR_HOST_NAME,
    ATTR_IP,
    ATTR_MAC,
    ATTR_SOURCE_TYPE,
    CONNECTED_DEVICE_REGISTERED,
    DOMAIN as DEVICE_TRACKER_DOMAIN,
    SourceType,
)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
    STATE_HOME,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.data_entry_flow import BaseServiceInfo
from homeassistant.helpers import config_validation as cv, discovery_flow
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceRegistry,
    async_get,
    format_mac,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_added_domain,
    async_track_time_interval,
)
from homeassistant.helpers.typing import ConfigType, EventType
from homeassistant.loader import DHCPMatcher, async_get_dhcp

from .const import DOMAIN

if TYPE_CHECKING:
    from scapy.packet import Packet

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

FILTER = "udp and (port 67 or 68)"
REQUESTED_ADDR = "requested_addr"
MESSAGE_TYPE = "message-type"
HOSTNAME: Final = "hostname"
MAC_ADDRESS: Final = "macaddress"
IP_ADDRESS: Final = "ip"
REGISTERED_DEVICES: Final = "registered_devices"
DHCP_REQUEST = 3
SCAN_INTERVAL = timedelta(minutes=60)


_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DhcpServiceInfo(BaseServiceInfo):
    """Prepared info from dhcp entries."""

    ip: str
    hostname: str
    macaddress: str


@dataclass(slots=True)
class DhcpMatchers:
    """Prepared info from dhcp entries."""

    registered_devices_domains: set[str]
    no_oui_matchers: dict[str, list[DHCPMatcher]]
    oui_matchers: dict[str, list[DHCPMatcher]]


def async_index_integration_matchers(
    integration_matchers: list[DHCPMatcher],
) -> DhcpMatchers:
    """Index the integration matchers.

    We have three types of matchers:

    1. Registered devices
    2. Devices with no OUI - index by first char of lower() hostname
    3. Devices with OUI - index by OUI
    """
    registered_devices_domains: set[str] = set()
    no_oui_matchers: dict[str, list[DHCPMatcher]] = {}
    oui_matchers: dict[str, list[DHCPMatcher]] = {}
    for matcher in integration_matchers:
        domain = matcher["domain"]
        if REGISTERED_DEVICES in matcher:
            registered_devices_domains.add(domain)
            continue

        if mac_address := matcher.get(MAC_ADDRESS):
            oui_matchers.setdefault(mac_address[:6], []).append(matcher)
            continue

        if hostname := matcher.get(HOSTNAME):
            first_char = hostname[0].lower()
            no_oui_matchers.setdefault(first_char, []).append(matcher)

    return DhcpMatchers(
        registered_devices_domains=registered_devices_domains,
        no_oui_matchers=no_oui_matchers,
        oui_matchers=oui_matchers,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the dhcp component."""
    watchers: list[WatcherBase] = []
    address_data: dict[str, dict[str, str]] = {}
    integration_matchers = async_index_integration_matchers(await async_get_dhcp(hass))
    # For the passive classes we need to start listening
    # for state changes and connect the dispatchers before
    # everything else starts up or we will miss events
    for passive_cls in (DeviceTrackerRegisteredWatcher, DeviceTrackerWatcher):
        passive_watcher = passive_cls(hass, address_data, integration_matchers)
        await passive_watcher.async_start()
        watchers.append(passive_watcher)

    async def _initialize(event: Event) -> None:
        for active_cls in (DHCPWatcher, NetworkWatcher):
            active_watcher = active_cls(hass, address_data, integration_matchers)
            await active_watcher.async_start()
            watchers.append(active_watcher)

        async def _async_stop(event: Event) -> None:
            for watcher in watchers:
                await watcher.async_stop()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _initialize)
    return True


class WatcherBase(ABC):
    """Base class for dhcp and device tracker watching."""

    def __init__(
        self,
        hass: HomeAssistant,
        address_data: dict[str, dict[str, str]],
        integration_matchers: DhcpMatchers,
    ) -> None:
        """Initialize class."""
        super().__init__()

        self.hass = hass
        self._integration_matchers = integration_matchers
        self._address_data = address_data

    @abstractmethod
    async def async_stop(self) -> None:
        """Stop the watcher."""

    @abstractmethod
    async def async_start(self) -> None:
        """Start the watcher."""

    def process_client(self, ip_address: str, hostname: str, mac_address: str) -> None:
        """Process a client."""
        self.hass.loop.call_soon_threadsafe(
            self.async_process_client, ip_address, hostname, mac_address
        )

    @callback
    def async_process_client(
        self, ip_address: str, hostname: str, mac_address: str
    ) -> None:
        """Process a client."""
        if (made_ip_address := cached_ip_addresses(ip_address)) is None:
            # Ignore invalid addresses
            _LOGGER.debug("Ignoring invalid IP Address: %s", ip_address)
            return

        if (
            made_ip_address.is_link_local
            or made_ip_address.is_loopback
            or made_ip_address.is_unspecified
        ):
            # Ignore self assigned addresses, loopback, invalid
            return

        data = self._address_data.get(ip_address)
        if (
            data
            and data[MAC_ADDRESS] == mac_address
            and data[HOSTNAME].startswith(hostname)
        ):
            # If the address data is the same no need
            # to process it
            return

        data = {MAC_ADDRESS: mac_address, HOSTNAME: hostname}
        self._address_data[ip_address] = data

        lowercase_hostname = hostname.lower()
        uppercase_mac = mac_address.upper()

        _LOGGER.debug(
            "Processing updated address data for %s: mac=%s hostname=%s",
            ip_address,
            uppercase_mac,
            lowercase_hostname,
        )

        matched_domains: set[str] = set()
        matchers = self._integration_matchers
        registered_devices_domains = matchers.registered_devices_domains

        dev_reg: DeviceRegistry = async_get(self.hass)
        if device := dev_reg.async_get_device(
            connections={(CONNECTION_NETWORK_MAC, uppercase_mac)}
        ):
            for entry_id in device.config_entries:
                if (
                    entry := self.hass.config_entries.async_get_entry(entry_id)
                ) and entry.domain in registered_devices_domains:
                    matched_domains.add(entry.domain)

        oui = uppercase_mac[:6]
        lowercase_hostname_first_char = (
            lowercase_hostname[0] if len(lowercase_hostname) else ""
        )
        for matcher in itertools.chain(
            matchers.no_oui_matchers.get(lowercase_hostname_first_char, ()),
            matchers.oui_matchers.get(oui, ()),
        ):
            domain = matcher["domain"]
            if (
                matcher_hostname := matcher.get(HOSTNAME)
            ) is not None and not _memorized_fnmatch(
                lowercase_hostname, matcher_hostname
            ):
                continue

            _LOGGER.debug("Matched %s against %s", data, matcher)
            matched_domains.add(domain)

        for domain in matched_domains:
            discovery_flow.async_create_flow(
                self.hass,
                domain,
                {"source": config_entries.SOURCE_DHCP},
                DhcpServiceInfo(
                    ip=ip_address,
                    hostname=lowercase_hostname,
                    macaddress=mac_address,
                ),
            )


class NetworkWatcher(WatcherBase):
    """Class to query ptr records routers."""

    def __init__(
        self,
        hass: HomeAssistant,
        address_data: dict[str, dict[str, str]],
        integration_matchers: DhcpMatchers,
    ) -> None:
        """Initialize class."""
        super().__init__(hass, address_data, integration_matchers)
        self._unsub: Callable[[], None] | None = None
        self._discover_hosts: DiscoverHosts | None = None
        self._discover_task: asyncio.Task | None = None

    async def async_stop(self) -> None:
        """Stop scanning for new devices on the network."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._discover_task:
            self._discover_task.cancel()
            self._discover_task = None

    async def async_start(self) -> None:
        """Start scanning for new devices on the network."""
        self._discover_hosts = DiscoverHosts()
        self._unsub = async_track_time_interval(
            self.hass,
            self.async_start_discover,
            SCAN_INTERVAL,
            name="DHCP network watcher",
        )
        self.async_start_discover()

    @callback
    def async_start_discover(self, *_: Any) -> None:
        """Start a new discovery task if one is not running."""
        if self._discover_task and not self._discover_task.done():
            return
        self._discover_task = self.hass.async_create_task(self.async_discover())

    async def async_discover(self) -> None:
        """Process discovery."""
        assert self._discover_hosts is not None
        for host in await self._discover_hosts.async_discover():
            self.async_process_client(
                host[DISCOVERY_IP_ADDRESS],
                host[DISCOVERY_HOSTNAME],
                _format_mac(host[DISCOVERY_MAC_ADDRESS]),
            )


class DeviceTrackerWatcher(WatcherBase):
    """Class to watch dhcp data from routers."""

    def __init__(
        self,
        hass: HomeAssistant,
        address_data: dict[str, dict[str, str]],
        integration_matchers: DhcpMatchers,
    ) -> None:
        """Initialize class."""
        super().__init__(hass, address_data, integration_matchers)
        self._unsub: Callable[[], None] | None = None

    async def async_stop(self) -> None:
        """Stop watching for new device trackers."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_start(self) -> None:
        """Stop watching for new device trackers."""
        self._unsub = async_track_state_added_domain(
            self.hass, [DEVICE_TRACKER_DOMAIN], self._async_process_device_event
        )
        for state in self.hass.states.async_all(DEVICE_TRACKER_DOMAIN):
            self._async_process_device_state(state)

    @callback
    def _async_process_device_event(
        self, event: EventType[EventStateChangedData]
    ) -> None:
        """Process a device tracker state change event."""
        self._async_process_device_state(event.data["new_state"])

    @callback
    def _async_process_device_state(self, state: State | None) -> None:
        """Process a device tracker state."""
        if state is None or state.state != STATE_HOME:
            return

        attributes = state.attributes

        if attributes.get(ATTR_SOURCE_TYPE) != SourceType.ROUTER:
            return

        ip_address = attributes.get(ATTR_IP)
        hostname = attributes.get(ATTR_HOST_NAME, "")
        mac_address = attributes.get(ATTR_MAC)

        if ip_address is None or mac_address is None:
            return

        self.async_process_client(ip_address, hostname, _format_mac(mac_address))


class DeviceTrackerRegisteredWatcher(WatcherBase):
    """Class to watch data from device tracker registrations."""

    def __init__(
        self,
        hass: HomeAssistant,
        address_data: dict[str, dict[str, str]],
        integration_matchers: DhcpMatchers,
    ) -> None:
        """Initialize class."""
        super().__init__(hass, address_data, integration_matchers)
        self._unsub: Callable[[], None] | None = None

    async def async_stop(self) -> None:
        """Stop watching for device tracker registrations."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_start(self) -> None:
        """Stop watching for device tracker registrations."""
        self._unsub = async_dispatcher_connect(
            self.hass, CONNECTED_DEVICE_REGISTERED, self._async_process_device_data
        )

    @callback
    def _async_process_device_data(self, data: dict[str, str | None]) -> None:
        """Process a device tracker state."""
        ip_address = data[ATTR_IP]
        hostname = data[ATTR_HOST_NAME] or ""
        mac_address = data[ATTR_MAC]

        if ip_address is None or mac_address is None:
            return

        self.async_process_client(ip_address, hostname, _format_mac(mac_address))


class DHCPWatcher(WatcherBase):
    """Class to watch dhcp requests."""

    def __init__(
        self,
        hass: HomeAssistant,
        address_data: dict[str, dict[str, str]],
        integration_matchers: DhcpMatchers,
    ) -> None:
        """Initialize class."""
        super().__init__(hass, address_data, integration_matchers)
        self._loop = asyncio.get_running_loop()
        self._sock: Any | None = None
        self._async_handle_dhcp_packet: Callable[[Packet], None] | None = None

    async def async_stop(self) -> None:
        """Stop watching for DHCP packets."""
        self._async_stop()

    @callback
    def _async_stop(self) -> None:
        """Stop watching for DHCP packets."""
        if self._sock:
            self._loop.remove_reader(self._sock.fileno())
            self._sock.close()
            self._sock = None

    async def async_start(self) -> None:
        """Start watching for dhcp packets."""
        try:
            await self._async_start()
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Error setting up DHCP watcher: %s", ex)

    async def _async_start(self) -> None:
        """Start watching for dhcp packets."""
        # Local import because importing from scapy has side effects such as opening
        # sockets

        from scapy import arch  # pylint: disable=import-outside-toplevel # noqa: F401
        from scapy.layers.dhcp import DHCP  # pylint: disable=import-outside-toplevel
        from scapy.layers.inet import IP  # pylint: disable=import-outside-toplevel
        from scapy.layers.l2 import Ether  # pylint: disable=import-outside-toplevel
        #
        # Importing scapy.sendrecv will cause a scapy resync which will
        # import scapy.arch.read_routes which will import scapy.sendrecv
        #
        # We avoid this circular import by importing arch above to ensure
        # the module is loaded and avoid the problem
        #

        @callback
        def _async_handle_dhcp_packet(packet: Packet) -> None:
            """Process a dhcp packet."""
            if not (dhcp_packet := packet.getlayer(DHCP)):
                return

            if TYPE_CHECKING:
                dhcp_packet = cast(DHCP, dhcp_packet)

            options_dict = _dhcp_options_as_dict(dhcp_packet.options)
            if options_dict.get(MESSAGE_TYPE) != DHCP_REQUEST:
                # Not a DHCP request
                return

            ip_address = options_dict.get(REQUESTED_ADDR) or cast(str, packet[IP].src)
            assert isinstance(ip_address, str)
            hostname = ""
            if (hostname_bytes := options_dict.get(HOSTNAME)) and isinstance(
                hostname_bytes, bytes
            ):
                with contextlib.suppress(AttributeError, UnicodeDecodeError):
                    hostname = hostname_bytes.decode()
            mac_address = _format_mac(cast(str, packet[Ether].src))

            if ip_address is not None and mac_address is not None:
                self.async_process_client(ip_address, hostname, mac_address)

        # disable scapy promiscuous mode as we do not need it
        conf.sniff_promisc = 0

        try:
            self._verify_working_pcap(FILTER)
        except (Scapy_Exception, ImportError) as ex:
            _LOGGER.error(
                "Cannot watch for dhcp packets without a functional packet filter: %s",
                ex,
            )
            return

        try:
            sock = self._make_listen_socket(FILTER)
            fileno = sock.fileno()
        except (Scapy_Exception, OSError) as ex:
            if os.geteuid() == 0:
                _LOGGER.error("Cannot watch for dhcp packets: %s", ex)
            else:
                _LOGGER.debug(
                    "Cannot watch for dhcp packets without root or CAP_NET_RAW: %s", ex
                )
            return

        self._sock = sock
        self._async_handle_dhcp_packet = _async_handle_dhcp_packet
        self._loop.add_reader(fileno, self._async_on_data)

    def _async_on_data(self) -> None:
        """Handle data from the socket."""
        if not (sock := self._sock):
            return

        try:
            data = sock.recv()
        except (BlockingIOError, InterruptedError):
            return
        except BaseException as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Fatal error while processing dhcp packet: %s", ex)
            self._async_stop()

        if TYPE_CHECKING:
            assert self._async_handle_dhcp_packet is not None

        if data:
            self._async_handle_dhcp_packet(data)

    def _make_listen_socket(self, cap_filter: str) -> Any:
        """Get a nonblocking listen socket."""
        from scapy.data import ETH_P_ALL  # pylint: disable=import-outside-toplevel
        from scapy.interfaces import (  # pylint: disable=import-outside-toplevel
            resolve_iface,
        )

        iface = conf.iface
        sock = resolve_iface(iface).l2listen()(
            type=ETH_P_ALL, iface=iface, filter=cap_filter
        )
        if hasattr(sock, "set_nonblock"):
            # Not all classes have set_nonblock so we have to call fcntl directly
            # in the event its not implemented
            sock.set_nonblock()
        else:
            import fcntl  # pylint: disable=import-outside-toplevel

            fcntl.fcntl(sock.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

        return sock

    def _verify_working_pcap(self, cap_filter: str) -> None:
        """Verify we can create a packet filter.

        If we cannot create a filter we will be listening for
        all traffic which is too intensive.
        """
        # Local import because importing from scapy has side effects such as opening
        # sockets
        from scapy.arch.common import (  # pylint: disable=import-outside-toplevel
            compile_filter,
        )

        compile_filter(cap_filter)


def _dhcp_options_as_dict(
    dhcp_options: Iterable[tuple[str, int | bytes | None]],
) -> dict[str, str | int | bytes | None]:
    """Extract data from packet options as a dict."""
    return {option[0]: option[1] for option in dhcp_options if len(option) >= 2}


def _format_mac(mac_address: str) -> str:
    """Format a mac address for matching."""
    return format_mac(mac_address).replace(":", "")


@lru_cache(maxsize=4096, typed=True)
def _compile_fnmatch(pattern: str) -> re.Pattern:
    """Compile a fnmatch pattern."""
    return re.compile(translate(pattern))


@lru_cache(maxsize=1024, typed=True)
def _memorized_fnmatch(name: str, pattern: str) -> bool:
    """Memorized version of fnmatch that has a larger lru_cache.

    The default version of fnmatch only has a lru_cache of 256 entries.
    With many devices we quickly reach that limit and end up compiling
    the same pattern over and over again.

    DHCP has its own memorized fnmatch with its own lru_cache
    since the data is going to be relatively the same
    since the devices will not change frequently
    """
    return bool(_compile_fnmatch(pattern).match(name))
