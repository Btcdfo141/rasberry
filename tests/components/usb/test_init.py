"""Tests for the USB Discovery integration."""
import os
import sys
from unittest.mock import MagicMock, patch, sentinel

import pytest

from homeassistant.components import usb
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.setup import async_setup_component

from . import slae_sh_device


@pytest.fixture(name="operating_system")
def mock_operating_system():
    """Mock running Home Assistant Operating system."""
    with patch(
        "homeassistant.components.usb.system_info.async_get_system_info",
        return_value={
            "hassio": True,
            "docker": True,
        },
    ):
        yield


@pytest.fixture(name="docker")
def mock_docker():
    """Mock running Home Assistant in docker container."""
    with patch(
        "homeassistant.components.usb.system_info.async_get_system_info",
        return_value={
            "hassio": False,
            "docker": True,
        },
    ):
        yield


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Only works on linux",
)
async def test_discovered_by_observer_before_started(hass, operating_system):
    """Test a device is discovered by the observer before started."""

    async def _mock_monitor_observer_callback(callback):
        await hass.async_add_executor_job(
            callback, MagicMock(action="add", device_path="/dev/new")
        )

    def _create_mock_monitor_observer(monitor, callback, name):
        hass.async_create_task(_mock_monitor_observer_callback(callback))
        return MagicMock()

    new_usb = [{"domain": "test1", "vid": "3039", "pid": "3039"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch(
        "pyudev.MonitorObserver", new=_create_mock_monitor_observer
    ):
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()

    with patch("homeassistant.components.usb.comports", return_value=[]), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 1
    assert mock_config_flow.mock_calls[0][1][0] == "test1"


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Only works on linux",
)
async def test_removal_by_observer_before_started(hass, operating_system):
    """Test a device is removed by the observer before started."""

    async def _mock_monitor_observer_callback(callback):
        await hass.async_add_executor_job(
            callback, MagicMock(action="remove", device_path="/dev/new")
        )

    def _create_mock_monitor_observer(monitor, callback, name):
        hass.async_create_task(_mock_monitor_observer_callback(callback))
        return MagicMock()

    new_usb = [{"domain": "test1", "vid": "3039", "pid": "3039"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch(
        "pyudev.MonitorObserver", new=_create_mock_monitor_observer
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()

    with patch("homeassistant.components.usb.comports", return_value=[]):
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 0


async def test_discovered_by_websocket_scan(hass, hass_ws_client):
    """Test a device is discovered from websocket scan."""
    new_usb = [{"domain": "test1", "vid": "3039", "pid": "3039"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch("pyudev.Context", side_effect=ImportError), patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        ws_client = await hass_ws_client(hass)
        await ws_client.send_json({"id": 1, "type": "usb/scan"})
        response = await ws_client.receive_json()
        assert response["success"]
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 1
    assert mock_config_flow.mock_calls[0][1][0] == "test1"


async def test_discovered_by_websocket_scan_match_vid_only(hass, hass_ws_client):
    """Test a device is discovered from websocket scan only matching vid."""
    new_usb = [{"domain": "test1", "vid": "3039"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch("pyudev.Context", side_effect=ImportError), patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        ws_client = await hass_ws_client(hass)
        await ws_client.send_json({"id": 1, "type": "usb/scan"})
        response = await ws_client.receive_json()
        assert response["success"]
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 1
    assert mock_config_flow.mock_calls[0][1][0] == "test1"


async def test_discovered_by_websocket_scan_match_vid_wrong_pid(hass, hass_ws_client):
    """Test a device is discovered from websocket scan only matching vid but wrong pid."""
    new_usb = [{"domain": "test1", "vid": "3039", "pid": "9999"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch("pyudev.Context", side_effect=ImportError), patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        ws_client = await hass_ws_client(hass)
        await ws_client.send_json({"id": 1, "type": "usb/scan"})
        response = await ws_client.receive_json()
        assert response["success"]
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 0


async def test_discovered_by_websocket_no_vid_pid(hass, hass_ws_client):
    """Test a device is discovered from websocket scan with no vid or pid."""
    new_usb = [{"domain": "test1", "vid": "3039", "pid": "9999"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=None,
            pid=None,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch("pyudev.Context", side_effect=ImportError), patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        ws_client = await hass_ws_client(hass)
        await ws_client.send_json({"id": 1, "type": "usb/scan"})
        response = await ws_client.receive_json()
        assert response["success"]
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 0


@pytest.mark.parametrize("exception_type", [ImportError, OSError])
async def test_non_matching_discovered_by_scanner_after_started(
    hass, exception_type, hass_ws_client
):
    """Test a websocket scan that does not match."""
    new_usb = [{"domain": "test1", "vid": "4444", "pid": "4444"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch("pyudev.Context", side_effect=exception_type), patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        ws_client = await hass_ws_client(hass)
        await ws_client.send_json({"id": 1, "type": "usb/scan"})
        response = await ws_client.receive_json()
        assert response["success"]
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 0


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Only works on linux",
)
async def test_not_discovered_by_observer_before_started_on_docker(hass, docker):
    """Test a device is not discovered since observer is not running on bare docker."""

    async def _mock_monitor_observer_callback(callback):
        await hass.async_add_executor_job(
            callback, MagicMock(action="add", device_path="/dev/new")
        )

    def _create_mock_monitor_observer(monitor, callback, name):
        hass.async_create_task(_mock_monitor_observer_callback(callback))
        return MagicMock()

    new_usb = [{"domain": "test1", "vid": "3039", "pid": "3039"}]

    mock_comports = [
        MagicMock(
            device=slae_sh_device.device,
            vid=12345,
            pid=12345,
            serial_number=slae_sh_device.serial_number,
            manufacturer=slae_sh_device.manufacturer,
            description=slae_sh_device.description,
        )
    ]

    with patch(
        "homeassistant.components.usb.async_get_usb", return_value=new_usb
    ), patch(
        "homeassistant.components.usb.comports", return_value=mock_comports
    ), patch(
        "pyudev.MonitorObserver", new=_create_mock_monitor_observer
    ):
        assert await async_setup_component(hass, "usb", {"usb": {}})
        await hass.async_block_till_done()

    with patch("homeassistant.components.usb.comports", return_value=[]), patch.object(
        hass.config_entries.flow, "async_init"
    ) as mock_config_flow:
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()

    assert len(mock_config_flow.mock_calls) == 0


def test_get_serial_by_id_no_dir():
    """Test serial by id conversion if there's no /dev/serial/by-id."""
    p1 = patch("os.path.isdir", MagicMock(return_value=False))
    p2 = patch("os.scandir")
    with p1 as is_dir_mock, p2 as scan_mock:
        res = usb.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 0


def test_get_serial_by_id():
    """Test serial by id conversion."""
    p1 = patch("os.path.isdir", MagicMock(return_value=True))
    p2 = patch("os.scandir")

    def _realpath(path):
        if path is sentinel.matched_link:
            return sentinel.path
        return sentinel.serial_link_path

    p3 = patch("os.path.realpath", side_effect=_realpath)
    with p1 as is_dir_mock, p2 as scan_mock, p3:
        res = usb.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 1

        entry1 = MagicMock(spec_set=os.DirEntry)
        entry1.is_symlink.return_value = True
        entry1.path = sentinel.some_path

        entry2 = MagicMock(spec_set=os.DirEntry)
        entry2.is_symlink.return_value = False
        entry2.path = sentinel.other_path

        entry3 = MagicMock(spec_set=os.DirEntry)
        entry3.is_symlink.return_value = True
        entry3.path = sentinel.matched_link

        scan_mock.return_value = [entry1, entry2, entry3]
        res = usb.get_serial_by_id(sentinel.path)
        assert res is sentinel.matched_link
        assert is_dir_mock.call_count == 2
        assert scan_mock.call_count == 2


def test_human_readable_device_name():
    """Test human readable device name includes the passed data."""
    name = usb.human_readable_device_name(
        "/dev/null",
        "612020FD",
        "Silicon Labs",
        "HubZ Smart Home Controller - HubZ Z-Wave Com Port",
        "10C4",
        "8A2A",
    )
    assert "/dev/null" in name
    assert "612020FD" in name
    assert "Silicon Labs" in name
    assert "HubZ Smart Home Controller - HubZ Z-Wave Com Port"[:26] in name
    assert "10C4" in name
    assert "8A2A" in name

    name = usb.human_readable_device_name(
        "/dev/null",
        "612020FD",
        "Silicon Labs",
        None,
        "10C4",
        "8A2A",
    )
    assert "/dev/null" in name
    assert "612020FD" in name
    assert "Silicon Labs" in name
    assert "10C4" in name
    assert "8A2A" in name
