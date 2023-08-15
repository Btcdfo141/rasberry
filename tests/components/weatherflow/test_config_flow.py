"""Test the IntelliFire config flow."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.components.weatherflow.const import DOMAIN
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.dt import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_address_in_use(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_has_devices_error_address_in_use: AsyncMock,
) -> None:
    """Test the address in use error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {"base": "address_in_use"}


async def test_cannot_connect(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_has_devices_error_listener
) -> None:
    """Test cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_abort_create(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_has_devices: AsyncMock
) -> None:
    """Test abort creation."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=mock_config_entry.data,
    )
    assert result["type"] == FlowResultType.ABORT


async def test_default_in_current_host(
    hass: HomeAssistant,
    mock_config_entry2: MockConfigEntry,
    mock_has_devices: AsyncMock,
):
    """Test the case where default host exists in the current host list."""
    mock_config_entry2.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.FORM


async def test_has_no_devices(
    hass: HomeAssistant, mock_has_no_devices: AsyncMock
) -> None:
    """Test a no device found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "4.3.2.1"},
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT


async def test_devices_with_mocks(
    hass: HomeAssistant, mock_start: AsyncMock, mock_stop: AsyncMock
) -> None:
    """Test getting user input."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY


# @pytest.mark.timeout(8)
async def test_devices_with_mocks_timeout(
    hass: HomeAssistant, mock_start_timeout: AsyncMock, mock_stop: AsyncMock
) -> None:
    """Test getting user input."""

    async def time_jump(hass: HomeAssistant):
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=10))
        await asyncio.sleep(1)

    # Start the time forarder task
    task = asyncio.create_task(time_jump(hass))

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM

    # Once finished cancel the bg task
    task.cancel()
