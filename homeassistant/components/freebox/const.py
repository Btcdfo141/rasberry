"""Freebox component constants."""
from __future__ import annotations

import socket

from homeassistant.const import Platform

DOMAIN = "freebox"
SERVICE_FLIP = "flip"
SERVICE_REBOOT = "reboot"

APP_DESC = {
    "app_id": "hass",
    "app_name": "Home Assistant",
    "app_version": "0.106",
    "device_name": socket.gethostname(),
}
API_VERSION = "v6"

PLATFORMS = [
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CAMERA,
]

DEFAULT_DEVICE_NAME = "Unknown device"

# to store the cookie
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


CONNECTION_SENSORS_KEYS = {"rate_down", "rate_up"}

# Icons
DEVICE_ICONS = {
    "freebox_delta": "mdi:television-guide",
    "freebox_hd": "mdi:television-guide",
    "freebox_mini": "mdi:television-guide",
    "freebox_player": "mdi:television-guide",
    "ip_camera": "mdi:cctv",
    "ip_phone": "mdi:phone-voip",
    "laptop": "mdi:laptop",
    "multimedia_device": "mdi:play-network",
    "nas": "mdi:nas",
    "networking_device": "mdi:network",
    "printer": "mdi:printer",
    "router": "mdi:router-wireless",
    "smartphone": "mdi:cellphone",
    "tablet": "mdi:tablet",
    "television": "mdi:television",
    "vg_console": "mdi:gamepad-variant",
    "workstation": "mdi:desktop-tower-monitor",
}

ATTR_DETECTION = "detection"
ATTR_ACTIVATION = "activation"
ATTR_QUALITY = "quality"
ATTR_SENSITIVITY = "sensitivity"
ATTR_THRESHOLD = "threshold"
ATTR_FLIP = "flip"
ATTR_TIMESTAMP = "timestamp"
ATTR_VOLUME = "volume"
ATTR_SOUND_DETECTION = "sound_detection"
ATTR_SOUND_TRIGGER = "sound_trigger"
ATTR_RTSP = "rtsp"
ATTR_DISK = "disk"

CATEGORY_TO_MODEL = {
    "pir": "F-HAPIR01A",
    "camera": "F-HACAM01A",
    "dws": "F-HADWS01A",
    "kfb": "F-HAKFB01A",
    "alarm": "F-MSEC07A",
    "rts": "RTS",
    "iohome": "IOHome",
}

HOME_COMPATIBLE_PLATFORMS = [
    Platform.CAMERA,
]
