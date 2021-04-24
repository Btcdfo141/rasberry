"""The tests for the Media group platform."""
from os import path

from homeassistant.components.group import DOMAIN
from homeassistant.components.media_player import (
    ATTR_MEDIA_SHUFFLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_DOMAIN,
    SERVICE_SHUFFLE_SET,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_SET,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_STOP,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.setup import async_setup_component


async def test_default_state(hass):
    """Test media group default state."""
    hass.states.async_set("media_player.player_1", "on")
    await async_setup_component(
        hass,
        MEDIA_DOMAIN,
        {
            MEDIA_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["media_player.player_1", "media_player.player_2"],
                "name": "Media group",
            }
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    state = hass.states.get("media_player.media_group")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0
    assert state.attributes.get(ATTR_ENTITY_ID) == [
        "media_player.player_1",
        "media_player.player_2",
    ]


async def test_state_reporting(hass):
    """Test the state reporting."""
    await async_setup_component(
        hass,
        MEDIA_DOMAIN,
        {
            MEDIA_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["media_player.player_1", "media_player.player_2"],
            }
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    assert hass.states.get("media_player.media_group").state == STATE_UNKNOWN

    hass.states.async_set("media_player.player_1", STATE_ON)
    hass.states.async_set("media_player.player_2", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get("media_player.media_group").state == STATE_ON

    hass.states.async_set("media_player.player_1", STATE_ON)
    hass.states.async_set("media_player.player_2", STATE_OFF)
    await hass.async_block_till_done()
    assert hass.states.get("media_player.media_group").state == STATE_ON

    hass.states.async_set("media_player.player_1", STATE_OFF)
    hass.states.async_set("media_player.player_2", STATE_OFF)
    await hass.async_block_till_done()
    assert hass.states.get("media_player.media_group").state == STATE_OFF

    hass.states.async_set("media_player.player_1", STATE_UNAVAILABLE)
    hass.states.async_set("media_player.player_2", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get("media_player.media_group").state == STATE_UNAVAILABLE


async def test_supported_features(hass):
    """Test supported features reporting."""
    pause_play_stop = SUPPORT_PAUSE | SUPPORT_PLAY | SUPPORT_STOP
    play_media = SUPPORT_PLAY_MEDIA
    volume = SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP

    await async_setup_component(
        hass,
        MEDIA_DOMAIN,
        {
            MEDIA_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["media_player.player_1", "media_player.player_2"],
            }
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    hass.states.async_set(
        "media_player.player_1", STATE_ON, {ATTR_SUPPORTED_FEATURES: 0}
    )
    await hass.async_block_till_done()
    state = hass.states.get("media_player.media_group")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0

    hass.states.async_set(
        "media_player.player_1",
        STATE_ON,
        {ATTR_SUPPORTED_FEATURES: pause_play_stop},
    )
    await hass.async_block_till_done()
    state = hass.states.get("media_player.media_group")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == pause_play_stop

    hass.states.async_set(
        "media_player.player_2",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: play_media | volume},
    )
    await hass.async_block_till_done()
    state = hass.states.get("media_player.media_group")
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        == pause_play_stop | play_media | volume
    )

    hass.states.async_set(
        "media_player.player_2", STATE_OFF, {ATTR_SUPPORTED_FEATURES: play_media}
    )
    await hass.async_block_till_done()
    state = hass.states.get("media_player.media_group")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == pause_play_stop | play_media


async def test_service_calls(hass):
    """Test service calls."""
    await async_setup_component(
        hass,
        MEDIA_DOMAIN,
        {
            MEDIA_DOMAIN: [
                {"platform": "demo"},
                {
                    "platform": DOMAIN,
                    "entities": [
                        "media_player.bedroom",
                        "media_player.kitchen",
                        "media_player.living_room",
                    ],
                },
            ]
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    assert hass.states.get("media_player.media_group").state == STATE_PLAYING
    await hass.services.async_call(
        MEDIA_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "media_player.media_group"},
        blocking=True,
    )

    await hass.async_block_till_done()
    assert hass.states.get("media_player.bedroom").state == STATE_OFF
    assert hass.states.get("media_player.kitchen").state == STATE_OFF
    assert hass.states.get("media_player.living_room").state == STATE_OFF

    await hass.services.async_call(
        MEDIA_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "media_player.media_group"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("media_player.bedroom").state == STATE_PLAYING
    assert hass.states.get("media_player.kitchen").state == STATE_PLAYING
    assert hass.states.get("media_player.living_room").state == STATE_PLAYING

    await hass.services.async_call(
        MEDIA_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: "media_player.media_group",
            ATTR_MEDIA_VOLUME_LEVEL: 0.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get("media_player.bedroom").attributes[ATTR_MEDIA_VOLUME_LEVEL]
        == 0.5
    )
    assert (
        hass.states.get("media_player.kitchen").attributes[ATTR_MEDIA_VOLUME_LEVEL]
        == 0.5
    )
    assert (
        hass.states.get("media_player.living_room").attributes[ATTR_MEDIA_VOLUME_LEVEL]
        == 0.5
    )

    await hass.services.async_call(
        MEDIA_DOMAIN,
        SERVICE_SHUFFLE_SET,
        {ATTR_ENTITY_ID: "media_player.media_group", ATTR_MEDIA_SHUFFLE: True},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get("media_player.bedroom").attributes[ATTR_MEDIA_SHUFFLE] is True
    )
    assert (
        hass.states.get("media_player.kitchen").attributes[ATTR_MEDIA_SHUFFLE] is True
    )
    assert (
        hass.states.get("media_player.living_room").attributes[ATTR_MEDIA_SHUFFLE]
        is True
    )


async def test_nested_group(hass):
    """Test nested media group."""
    hass.states.async_set("media_player.player_1", "on")
    await async_setup_component(
        hass,
        MEDIA_DOMAIN,
        {
            MEDIA_DOMAIN: [
                {
                    "platform": DOMAIN,
                    "entities": ["media_player.group_1"],
                    "name": "Nested Group",
                },
                {
                    "platform": DOMAIN,
                    "entities": ["media_player.player_1", "media_player.player_2"],
                    "name": "Group 1",
                },
            ]
        },
    )
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    state = hass.states.get("media_player.group_1")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ENTITY_ID) == [
        "media_player.player_1",
        "media_player.player_2",
    ]

    state = hass.states.get("media_player.nested_group")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ENTITY_ID) == ["media_player.group_1"]


def _get_fixtures_base_path():
    return path.dirname(path.dirname(path.dirname(__file__)))
