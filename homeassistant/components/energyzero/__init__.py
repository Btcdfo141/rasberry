"""The EnergyZero integration."""
from __future__ import annotations

from datetime import date, datetime

from energyzero import Electricity, Gas, VatOption

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_END,
    ATTR_INCL_VAT,
    ATTR_START,
    DOMAIN,
    ENERGY_SERVICE_NAME,
    GAS_SERVICE_NAME,
    SERVICE_SCHEMA,
    PriceType,
)
from .coordinator import EnergyZeroDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


def __get_date(date_input: str | None) -> date | datetime:
    """Get date."""
    if not date_input:
        return dt_util.now().date()

    if value := dt_util.parse_datetime(date_input):
        return value

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_date",
        translation_placeholders={
            "date": date_input,
        },
    )


def __serialize_prices(prices: Electricity | Gas) -> ServiceResponse:
    """Serialize prices."""
    return {
        "prices": [
            {
                key: str(value) if isinstance(value, datetime) else value
                for key, value in timestamp_price.items()
            }
            for timestamp_price in prices.timestamp_prices
        ]
    }


async def __get_prices(
    coordinator: EnergyZeroDataUpdateCoordinator,
    call: ServiceCall,
    price_type: PriceType,
) -> ServiceResponse:
    start = __get_date(call.data.get(ATTR_START))
    end = __get_date(call.data.get(ATTR_END))

    vat = VatOption.INCLUDE if call.data.get(ATTR_INCL_VAT) else VatOption.EXCLUDE

    data: Electricity | Gas

    if price_type == PriceType.GAS:
        data = await coordinator.energyzero.gas_prices(
            start_date=start,
            end_date=end,
            vat=vat,
        )
    else:
        data = await coordinator.energyzero.energy_prices(
            start_date=start,
            end_date=end,
            vat=vat,
        )

    return __serialize_prices(data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EnergyZero from a config entry."""

    coordinator = EnergyZeroDataUpdateCoordinator(hass)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.energyzero.close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def get_gas_prices(call: ServiceCall) -> ServiceResponse:
        """Search gas prices."""
        return await __get_prices(coordinator, call, PriceType.GAS)

    async def get_energy_prices(call: ServiceCall) -> ServiceResponse:
        """Search energy prices."""
        return await __get_prices(coordinator, call, PriceType.ENERGY)

    hass.services.async_register(
        DOMAIN,
        GAS_SERVICE_NAME,
        get_gas_prices,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        ENERGY_SERVICE_NAME,
        get_energy_prices,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload EnergyZero config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
