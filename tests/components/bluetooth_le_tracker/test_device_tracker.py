"""Test Bluetooth LE device tracker."""

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components.bluetooth import BluetoothServiceInfo
from homeassistant.components.bluetooth_le_tracker import device_tracker
from homeassistant.components.device_tracker.const import (
    CONF_SCAN_INTERVAL,
    CONF_TRACK_NEW,
    DOMAIN,
)
from homeassistant.const import CONF_PLATFORM
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util, slugify

from tests.common import async_fire_time_changed


async def test_preserve_new_tracked_device_name(hass, mock_device_tracker_conf):
    """Test preserving tracked device name across new seens."""

    address = "DE:AD:BE:EF:13:37"
    name = "Mock device name"
    entity_id = f"{DOMAIN}.{slugify(name)}"

    with patch(
        "homeassistant.components.bluetooth.async_discovered_service_info"
    ) as mock_async_discovered_service_info, patch.object(
        device_tracker, "MIN_SEEN_NEW", 3
    ):

        device = BluetoothServiceInfo(
            name=name,
            address=address,
            rssi=-19,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
        )
        # Return with name when seen first time
        mock_async_discovered_service_info.return_value = [device]

        config = {
            CONF_PLATFORM: "bluetooth_le_tracker",
            CONF_SCAN_INTERVAL: timedelta(minutes=1),
            CONF_TRACK_NEW: True,
        }
        result = await async_setup_component(hass, DOMAIN, {DOMAIN: config})
        assert result

        # Seen once here; return without name when seen subsequent times
        BluetoothServiceInfo(
            name=None,
            address=address,
            rssi=-19,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
        )
        # Return with name when seen first time
        mock_async_discovered_service_info.return_value = [device]

        # Tick until device seen enough times for to be registered for tracking
        for _ in range(device_tracker.MIN_SEEN_NEW - 1):
            async_fire_time_changed(
                hass,
                dt_util.utcnow() + config[CONF_SCAN_INTERVAL] + timedelta(seconds=1),
            )
            await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.name == name
