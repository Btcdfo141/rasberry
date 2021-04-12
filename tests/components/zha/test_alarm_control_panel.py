"""Test zha alarm control panel."""
from unittest.mock import AsyncMock, call, patch, sentinel

import pytest
import zigpy.profiles.zha as zha
import zigpy.zcl.clusters.security as security
import zigpy.zcl.foundation as zcl_f

from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_UNAVAILABLE,
)

from .common import async_enable_traffic, find_entity_id


@pytest.fixture
def zigpy_device(zigpy_device_mock):
    """Device tracker zigpy device."""
    endpoints = {
        1: {
            "in_clusters": [security.IasAce.cluster_id],
            "out_clusters": [],
            "device_type": zha.DeviceType.IAS_ANCILLARY_CONTROL,
        }
    }
    return zigpy_device_mock(
        endpoints, node_descriptor=b"\x02@\x8c\x02\x10RR\x00\x00\x00R\x00\x00"
    )


@patch(
    "zigpy.zcl.clusters.security.IasAce.client_command",
    new=AsyncMock(return_value=[sentinel.data, zcl_f.Status.SUCCESS]),
)
async def test_alarm_control_panel(hass, zha_device_joined_restored, zigpy_device):
    """Test zha alarm control panel platform."""

    zha_device = await zha_device_joined_restored(zigpy_device)
    cluster = zigpy_device.endpoints.get(1).ias_ace
    entity_id = await find_entity_id(ALARM_DOMAIN, zha_device, hass)
    assert entity_id is not None
    assert hass.states.get(entity_id).state == STATE_ALARM_DISARMED
    await async_enable_traffic(hass, [zha_device], enabled=False)
    # test that the panel was created and that it is unavailable
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, [zha_device])

    # test that the state has changed from unavailable to STATE_ALARM_DISARMED
    assert hass.states.get(entity_id).state == STATE_ALARM_DISARMED

    # arm_away from HA
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN, "alarm_arm_away", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_ARMED_AWAY
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Armed_Away,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )

    # disarm from HA
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "4321"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_DISARMED
    assert cluster.client_command.call_count == 2
    assert cluster.client_command.await_count == 2
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.Panel_Disarmed,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.No_Alarm,
    )

    # trip alarm from faulty code entry
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN, "alarm_arm_away", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_ARMED_AWAY
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "1111"},
        blocking=True,
    )
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "1111"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_TRIGGERED
    assert cluster.client_command.call_count == 4
    assert cluster.client_command.await_count == 4
    assert cluster.client_command.call_args == call(
        4,
        security.IasAce.PanelStatus.In_Alarm,
        0,
        security.IasAce.AudibleNotification.Default_Sound,
        security.IasAce.AlarmStatus.Emergency,
    )

    # reset the panel so it isn't in alarm state
    cluster.client_command.reset_mock()
    await hass.services.async_call(
        ALARM_DOMAIN,
        "alarm_disarm",
        {ATTR_ENTITY_ID: entity_id, "code": "4321"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_DISARMED
    cluster.client_command.reset_mock()
