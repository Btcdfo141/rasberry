"""The Nmap Tracker integration."""

DOMAIN = "nmap_tracker"

PLATFORMS = ["device_tracker"]

NMAP_TRACKED_DEVICES = "nmap_tracked_devices"

# Interval in minutes to exclude devices from a scan while they are home
CONF_HOME_INTERVAL = "home_interval"
CONF_OPTIONS = "scan_options"
DEFAULT_OPTIONS = "-sP --host-timeout 3s"

TRACKER_SCAN_INTERVAL = 120
