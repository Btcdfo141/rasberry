"""const."""
from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

COORDINATORS = "coordinators"

DATA_DISCOVERY_SERVICE = "refoss_discovery"
DATA_DISCOVERY_INTERVAL = "refoss_discovery_interval"

DISCOVERY_SCAN_INTERVAL = 30
DISCOVERY_TIMEOUT = 8
DISPATCH_DEVICE_DISCOVERED = "refoss_device_discovered"
DISPATCHERS = "dispatchers"

DOMAIN = "refoss"
COORDINATOR = "coordinator"
