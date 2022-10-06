"""Constants for the Whirlpool Appliances integration."""

from whirlpool.backendselector import Region

DOMAIN = "whirlpool"
CONF_ALLOWED_REGIONS = ["EU", "US"]

CONF_REGIONS_MAP = {
    "EU": Region.EU,
    "US": Region.US,
}
