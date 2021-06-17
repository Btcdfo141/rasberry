"""Constants used in the Mikrotik components."""

from typing import Final

DOMAIN: Final = "mikrotik"
DEFAULT_API_PORT: Final = 8728
DEFAULT_DETECTION_TIME: Final = 300
DEFAULT_SCAN_INTERVAL: Final = 10
DEFAULT_DISABLE_TRACKING_WIRED: Final = True
DEFAULT_TRACK_WIRED_MODE: Final = "DHCP lease"

ATTR_MANUFACTURER: Final = "Mikrotik"
ATTR_SERIAL_NUMBER: Final = "serial-number"
ATTR_FIRMWARE: Final = "current-firmware"
ATTR_MODEL: Final = "model"

CONF_DISABLE_TRACKING_WIRED: Final = "disable_tracking_wired"
CONF_TRACK_WIRED_MODE: Final = "track_wired_mode"
CONF_DETECTION_TIME: Final = "detection_time"
CONF_REPEATER_MODE: Final = "repeater_mode"

TRACK_WIRED_MODES: Final = ["DHCP lease", "ARP ping"]

NAME: Final = "name"
INFO: Final = "info"
IDENTITY: Final = "identity"
ARP: Final = "arp"

CAPSMAN: Final = "capsman"
DHCP: Final = "dhcp"
WIRELESS: Final = "wireless"
IS_WIRELESS: Final = "is_wireless"
IS_CAPSMAN: Final = "is_capsman"

MIKROTIK_SERVICES: Final = {
    ARP: "/ip/arp/getall",
    CAPSMAN: "/caps-man/registration-table/getall",
    DHCP: "/ip/dhcp-server/lease/getall",
    IDENTITY: "/system/identity/getall",
    INFO: "/system/routerboard/getall",
    WIRELESS: "/interface/wireless/registration-table/getall",
    IS_WIRELESS: "/interface/wireless/print",
    IS_CAPSMAN: "/caps-man/interface/print",
}

PLATFORMS: Final = ["device_tracker"]

CLIENTS: Final = "clients"

CLIENT_ATTRIBUTES: Final = [
    "ssid",
    "interface",
    "signal-strength",
    "signal-to-noise",
    "rx-rate",
    "tx-rate",
    "uptime",
]

CMD_PING: Final = "/ping"
