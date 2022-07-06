"""Constants for the Canary integration."""

from typing import Final

DOMAIN: Final = "canary"

MANUFACTURER: Final = "Canary Connect, Inc"

# Configuration
CONF_FFMPEG_ARGUMENTS: Final = "ffmpeg_arguments"
CONF_ENTRY_TIMEOUT_HOURS: Final = "entry_timeout_hours"

# Data
DATA_COORDINATOR: Final = "coordinator"
DATA_UNDO_UPDATE_LISTENER: Final = "undo_update_listener"

# Defaults
DEFAULT_FFMPEG_ARGUMENTS: Final = "-pred 1"
DEFAULT_TIMEOUT: Final = 10
DEFAULT_ENTRY_TIMEOUT_HOURS: Final = 14
