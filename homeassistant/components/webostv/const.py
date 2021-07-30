"""Constants used for LG webOS Smart TV."""
import asyncio

from aiopylgtv import PyLGTVCmdException
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

DOMAIN = "webostv"
PLATFORMS = ["media_player"]
DATA_CONFIG_ENTRY = "config_entry"
DATA_HASS_CONFIG = "hass_config"
DEFAULT_NAME = "LG webOS Smart TV"

ATTR_BUTTON = "button"
ATTR_CONFIG_ENTRY_ID = "entry_id"
ATTR_PAYLOAD = "payload"
ATTR_SOUND_OUTPUT = "sound_output"

CONF_ON_ACTION = "turn_on_action"
CONF_SOURCES = "sources"

SERVICE_BUTTON = "button"
SERVICE_COMMAND = "command"
SERVICE_SELECT_SOUND_OUTPUT = "select_sound_output"

LIVE_TV_APP_ID = "com.webos.app.livetv"

TRIGGER_TYPE_TURN_ON = "turn_on"

WEBOSTV_EXCEPTIONS = (
    OSError,
    ConnectionClosed,
    ConnectionClosedOK,
    ConnectionRefusedError,
    PyLGTVCmdException,
    asyncio.TimeoutError,
    asyncio.CancelledError,
)
