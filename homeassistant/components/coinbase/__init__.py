"""The Coinbase integration."""
import asyncio
from datetime import timedelta
import logging

from coinbase.wallet.client import Client
from coinbase.wallet.error import AuthenticationError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_API_TOKEN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

from .const import (
    API_ACCOUNT_ID,
    CONF_CURRENCIES,
    CONF_EXCHANGE_RATES,
    CONF_YAML_API_TOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            cv.deprecated(CONF_API_KEY),
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_YAML_API_TOKEN): cv.string,
                vol.Optional(CONF_CURRENCIES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_EXCHANGE_RATES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Coinbase component."""
    if DOMAIN not in config:
        return True
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Coinbase from a config entry."""
    client = await hass.async_add_executor_job(
        Client,
        entry.data[CONF_API_KEY],
        entry.data[CONF_API_TOKEN],
    )
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = await hass.async_add_executor_job(
        CoinbaseData, client
    )
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CoinbaseData:
    """Get the latest data and update the states."""

    def __init__(self, client):
        """Init the coinbase data object."""

        self.client = client
        self.accounts = self.client.get_accounts()
        self.exchange_rates = self.client.get_exchange_rates()
        self.user_id = self.client.get_current_user()[API_ACCOUNT_ID]

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from coinbase."""

        try:
            response = self.client.get_accounts()
            accounts = response["data"]

            # Most of Coinbase's API seems paginated now (25 items per page, but first page has 24).
            # This API gives a 'next_starting_after' property to send back as a 'starting_after' param.
            # Their API documentation is not up to date when writing these lines (2021-05-20)
            next_starting_after = response.pagination.next_starting_after

            while next_starting_after:
                response = self.client.get_accounts(starting_after=next_starting_after)
                accounts = accounts + response["data"]
                next_starting_after = response.pagination.next_starting_after

            self.accounts = accounts

            self.exchange_rates = self.client.get_exchange_rates()
        except AuthenticationError as coinbase_error:
            _LOGGER.error(
                "Authentication error connecting to coinbase: %s", coinbase_error
            )
