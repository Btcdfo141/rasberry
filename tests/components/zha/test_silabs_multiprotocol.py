"""Test ZHA Silicon Labs Multiprotocol support."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest
import zigpy.backups
import zigpy.state

from homeassistant.components import zha
from homeassistant.components.zha import api, silabs_multiprotocol
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from zigpy.application import ControllerApplication


@pytest.fixture(autouse=True)
def required_platform_only():
    """Only set up the required and required base platforms to speed up tests."""
    with patch("homeassistant.components.zha.PLATFORMS", ()):
        yield


async def test_async_get_channel_active(hass: HomeAssistant, setup_zha) -> None:
    """Test reading channel with an active ZHA installation."""
    await setup_zha()

    assert await silabs_multiprotocol.async_get_channel(hass) == 15


async def test_async_get_channel_missing(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test reading channel with an inactive ZHA installation, no valid channel."""
    await setup_zha()

    gateway = api._get_gateway(hass)
    await zha.async_unload_entry(hass, gateway.config_entry)

    # Network settings were never loaded for whatever reason
    zigpy_app_controller.state.network_info = zigpy.state.NetworkInfo()
    zigpy_app_controller.state.node_info = zigpy.state.NodeInfo()

    with patch(
        "bellows.zigbee.application.ControllerApplication.__new__",
        return_value=zigpy_app_controller,
    ):
        assert await silabs_multiprotocol.async_get_channel(hass) is None


async def test_async_get_channel_no_zha(hass: HomeAssistant) -> None:
    """Test reading channel with no ZHA config entries and no database."""
    assert await silabs_multiprotocol.async_get_channel(hass) is None


async def test_async_using_multipan_active(hass: HomeAssistant, setup_zha) -> None:
    """Test async_using_multipan with an active ZHA installation."""
    await setup_zha()

    assert await silabs_multiprotocol.async_using_multipan(hass) is False


async def test_async_using_multipan_no_zha(hass: HomeAssistant) -> None:
    """Test async_using_multipan with no ZHA config entries and no database."""
    assert await silabs_multiprotocol.async_using_multipan(hass) is False


async def test_change_channel(
    hass: HomeAssistant, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel."""
    await setup_zha()

    with patch.object(
        zigpy_app_controller, "move_network_to_channel", autospec=True
    ) as mock_move_network_to_channel:
        await silabs_multiprotocol.async_change_channel(hass, 20)

    assert mock_move_network_to_channel.mock_calls == [call(20)]


async def test_change_channel_no_zha(
    hass: HomeAssistant, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel with no ZHA config entries and no database."""
    with patch.object(
        zigpy_app_controller, "move_network_to_channel", autospec=True
    ) as mock_move_network_to_channel:
        await silabs_multiprotocol.async_change_channel(hass, 20)

    assert mock_move_network_to_channel.mock_calls == []
