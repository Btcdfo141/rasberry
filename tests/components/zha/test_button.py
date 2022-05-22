"""Test ZHA button."""
from unittest.mock import call, patch

from freezegun import freeze_time
import pytest
from zigpy.const import SIG_EP_PROFILE
from zigpy.exceptions import ZigbeeException
import zigpy.profiles.zha as zha
import zigpy.types as t
import zigpy.zcl.clusters.general as general
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster
import zigpy.zcl.clusters.security as security
import zigpy.zcl.foundation as zcl_f

from homeassistant.components.button import DOMAIN, ButtonDeviceClass
from homeassistant.components.button.const import SERVICE_PRESS
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_UNKNOWN,
)
from homeassistant.helpers import entity_registry as er

from .common import find_entity_id
from .conftest import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_TYPE

from tests.common import mock_coro


@pytest.fixture
async def contact_sensor(hass, zigpy_device_mock, zha_device_joined_restored):
    """Contact sensor fixture."""

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    security.IasZone.cluster_id,
                ],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.IAS_ZONE,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        },
    )

    zha_device = await zha_device_joined_restored(zigpy_device)
    return zha_device, zigpy_device.endpoints[1].identify


@pytest.fixture
async def tuya_water_valve(hass, zigpy_device_mock, zha_device_joined_restored):
    """Tuya Water Valve fixture."""

    class TuyaManufCluster(ManufacturerSpecificCluster):
        """Tuya manufacturer specific cluster."""

        cluster_id = 0xEF00
        ep_attribute = "tuya_manufacturer"

        attributes = {
            0xEF01: ("frost_lock_reset", t.Bool),
        }

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [general.Basic.cluster_id, TuyaManufCluster.cluster_id],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.ON_OFF_SWITCH,
            }
        },
        manufacturer="_TZE200_htnnfasr",
    )

    zha_device = await zha_device_joined_restored(zigpy_device)
    return zha_device, zigpy_device.endpoints[1].tuya_manufacturer


@freeze_time("2021-11-04 17:37:00", tz_offset=-1)
async def test_button(hass, contact_sensor):
    """Test zha button platform."""

    entity_registry = er.async_get(hass)
    zha_device, cluster = contact_sensor
    assert cluster is not None
    entity_id = await find_entity_id(DOMAIN, zha_device, hass)
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.UPDATE

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.entity_category == ENTITY_CATEGORY_DIAGNOSTIC

    with patch(
        "zigpy.zcl.Cluster.request",
        return_value=mock_coro([0x00, zcl_f.Status.SUCCESS]),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert len(cluster.request.mock_calls) == 1
        assert cluster.request.call_args[0][0] is False
        assert cluster.request.call_args[0][1] == 0
        assert cluster.request.call_args[0][3] == 5  # duration in seconds

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "2021-11-04T16:37:00+00:00"
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.UPDATE


async def test_frost_unlock(hass, tuya_water_valve):
    """Test custom frost unlock zha button."""

    entity_registry = er.async_get(hass)
    zha_device, cluster = tuya_water_valve
    assert cluster is not None
    entity_id = await find_entity_id(DOMAIN, zha_device, hass)
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.RESTART

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.entity_category == ENTITY_CATEGORY_CONFIG

    with patch(
        "zigpy.zcl.Cluster.request",
        return_value=mock_coro([0x00, zcl_f.Status.SUCCESS]),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert len(cluster.write_attributes.mock_calls) == 1
        assert cluster.write_attributes.call_args == call({"frost_lock_reset": 0})

    state = hass.states.get(entity_id)
    assert state
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.RESTART

    cluster.write_attributes.reset_mock()
    cluster.write_attributes.side_effect = ZigbeeException

    await hass.services.async_call(
        DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    assert len(cluster.write_attributes.mock_calls) == 1
    assert cluster.write_attributes.call_args == call({"frost_lock_reset": 0})
