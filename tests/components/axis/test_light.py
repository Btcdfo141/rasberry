"""Axis light platform tests."""

from copy import deepcopy
from unittest.mock import patch

from homeassistant.components.axis.const import DOMAIN as AXIS_DOMAIN
from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.setup import async_setup_component

from .test_device import (
    API_DISCOVERY_RESPONSE,
    LIGHT_CONTROL_RESPONSE,
    NAME,
    setup_axis_integration,
)

API_DISCOVERY_LIGHT_CONTROL = {
    "id": "light-control",
    "version": "1.1",
    "name": "Light Control",
}


LIGHT_STATUS_OFF = b'<?xml version="1.0" encoding="UTF-8"?>\n<tt:MetadataStream xmlns:tt="http://www.onvif.org/ver10/schema">\n<tt:Event><wsnt:NotificationMessage xmlns:tns1="http://www.onvif.org/ver10/topics" xmlns:tnsaxis="http://www.axis.com/2009/event/topics" xmlns:wsnt="http://docs.oasis-open.org/wsn/b-2" xmlns:wsa5="http://www.w3.org/2005/08/addressing"><wsnt:Topic Dialect="http://docs.oasis-open.org/wsn/t-1/TopicExpression/Simple">tns1:Device/tnsaxis:Light/Status</wsnt:Topic><wsnt:ProducerReference><wsa5:Address>uri://755cc9bb-cf3a-410b-bd1b-0ec97c6d6256/ProducerReference</wsa5:Address></wsnt:ProducerReference><wsnt:Message><tt:Message UtcTime="2020-09-05T04:25:51.692744Z" PropertyOperation="Initialized"><tt:Source><tt:SimpleItem Name="id" Value="0"/></tt:Source><tt:Key></tt:Key><tt:Data><tt:SimpleItem Name="state" Value="OFF"/></tt:Data></tt:Message></wsnt:Message></wsnt:NotificationMessage></tt:Event></tt:MetadataStream>\n'
LIGHT_STATUS_ON = b'<?xml version="1.0" encoding="UTF-8"?>\n<tt:MetadataStream xmlns:tt="http://www.onvif.org/ver10/schema">\n<tt:Event><wsnt:NotificationMessage xmlns:tns1="http://www.onvif.org/ver10/topics" xmlns:tnsaxis="http://www.axis.com/2009/event/topics" xmlns:wsnt="http://docs.oasis-open.org/wsn/b-2" xmlns:wsa5="http://www.w3.org/2005/08/addressing"><wsnt:Topic Dialect="http://docs.oasis-open.org/wsn/t-1/TopicExpression/Simple">tns1:Device/tnsaxis:Light/Status</wsnt:Topic><wsnt:ProducerReference><wsa5:Address>uri://755cc9bb-cf3a-410b-bd1b-0ec97c6d6256/ProducerReference</wsa5:Address></wsnt:ProducerReference><wsnt:Message><tt:Message UtcTime="2020-09-05T04:25:51.692744Z" PropertyOperation="Initialized"><tt:Source><tt:SimpleItem Name="id" Value="0"/></tt:Source><tt:Key></tt:Key><tt:Data><tt:SimpleItem Name="state" Value="ON"/></tt:Data></tt:Message></wsnt:Message></wsnt:NotificationMessage></tt:Event></tt:MetadataStream>\n'


async def test_platform_manually_configured(hass):
    """Test that nothing happens when platform is manually configured."""
    assert await async_setup_component(
        hass, LIGHT_DOMAIN, {LIGHT_DOMAIN: {"platform": AXIS_DOMAIN}}
    )

    assert AXIS_DOMAIN not in hass.data


async def test_no_lights(hass):
    """Test that no light events in Axis results in no light entities."""
    await setup_axis_integration(hass)

    assert not hass.states.async_entity_ids(LIGHT_DOMAIN)


async def test_no_light_entity_without_light_control_representation(
    hass, mock_axis_rtspclient
):
    """Verify no lights entities get created without light control representation."""
    api_discovery = deepcopy(API_DISCOVERY_RESPONSE)
    api_discovery["data"]["apiList"].append(API_DISCOVERY_LIGHT_CONTROL)

    light_control = deepcopy(LIGHT_CONTROL_RESPONSE)
    light_control["data"]["items"] = []

    with patch.dict(API_DISCOVERY_RESPONSE, api_discovery), patch.dict(
        LIGHT_CONTROL_RESPONSE, light_control
    ):
        await setup_axis_integration(hass)

    mock_axis_rtspclient(LIGHT_STATUS_ON)
    await hass.async_block_till_done()

    assert not hass.states.async_entity_ids(LIGHT_DOMAIN)


async def test_lights(hass, mock_axis_rtspclient):
    """Test that lights are loaded properly."""
    api_discovery = deepcopy(API_DISCOVERY_RESPONSE)
    api_discovery["data"]["apiList"].append(API_DISCOVERY_LIGHT_CONTROL)

    with patch.dict(API_DISCOVERY_RESPONSE, api_discovery):
        await setup_axis_integration(hass)

    # Add light
    with patch(
        "axis.light_control.LightControl.get_current_intensity",
        return_value={"data": {"intensity": 100}},
    ), patch(
        "axis.light_control.LightControl.get_valid_intensity",
        return_value={"data": {"ranges": [{"high": 150}]}},
    ):
        mock_axis_rtspclient(data=LIGHT_STATUS_ON)
        await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1

    entity_id = f"{LIGHT_DOMAIN}.{NAME}_ir_light_0"

    light_0 = hass.states.get(entity_id)
    assert light_0.state == STATE_ON
    assert light_0.name == f"{NAME} IR Light 0"

    # Turn on, set brightness, light already on
    with patch(
        "axis.light_control.LightControl.activate_light"
    ) as mock_activate, patch(
        "axis.light_control.LightControl.set_manual_intensity"
    ) as mock_set_intensity, patch(
        "axis.light_control.LightControl.get_current_intensity",
        return_value={"data": {"intensity": 100}},
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 50},
            blocking=True,
        )
        mock_activate.assert_not_awaited()
        mock_set_intensity.assert_called_once_with("led0", 29)

    # Turn off
    with patch(
        "axis.light_control.LightControl.deactivate_light"
    ) as mock_deactivate, patch(
        "axis.light_control.LightControl.get_current_intensity",
        return_value={"data": {"intensity": 100}},
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_deactivate.assert_called_once()

    # Event turn off light
    mock_axis_rtspclient(data=LIGHT_STATUS_OFF)
    await hass.async_block_till_done()

    light_0 = hass.states.get(entity_id)
    assert light_0.state == STATE_OFF

    # Turn on, set brightness
    with patch(
        "axis.light_control.LightControl.activate_light"
    ) as mock_activate, patch(
        "axis.light_control.LightControl.set_manual_intensity"
    ) as mock_set_intensity, patch(
        "axis.light_control.LightControl.get_current_intensity",
        return_value={"data": {"intensity": 100}},
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_activate.assert_called_once()
        mock_set_intensity.assert_not_called()

    # Turn off, light already off
    with patch(
        "axis.light_control.LightControl.deactivate_light"
    ) as mock_deactivate, patch(
        "axis.light_control.LightControl.get_current_intensity",
        return_value={"data": {"intensity": 100}},
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_deactivate.assert_not_called()
