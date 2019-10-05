"""The Samsung TV integration."""


async def async_setup(hass, config):
    """Set up the Samsung TV integration."""
    return True


async def async_setup_entry(hass, entry):
    """Set up the Samsung TV platform."""
    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    hass.async_add_job(
        hass.config_entries.async_forward_entry_unload(entry, "media_player")
    )

    return True
