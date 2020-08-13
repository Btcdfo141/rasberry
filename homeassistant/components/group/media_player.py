"""This platform allows several media players to be grouped into one media player."""
import logging
from typing import Dict, List, Optional, Set

import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN,
    PLATFORM_SCHEMA,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_MEDIA_STOP,
    SERVICE_PLAY_MEDIA,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    MediaPlayerEntity,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITIES,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import State, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event

# mypy: allow-incomplete-defs, allow-untyped-calls, allow-untyped-defs
# mypy: no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

KEY_CLEAR_PLAYLIST = "clear_playlist"
KEY_ON_OFF = "on_off"
KEY_PAUSE_PLAY_STOP = "play"
KEY_PLAY_MEDIA = "play_media"
KEY_SHUFFLE = "shuffle"
KEY_SEEK = "seek"
KEY_TRACKS = "tracks"
KEY_VOLUME = "volume"

DEFAULT_NAME = "Media Group"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_ENTITIES): cv.entities_domain(DOMAIN),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Media Group platform."""
    async_add_entities([MediaGroup(config[CONF_NAME], config[CONF_ENTITIES])])


class MediaGroup(MediaPlayerEntity):
    """Representation of a Media Group."""

    def __init__(self, name: str, entities: List[str]) -> None:
        """Initialize a Media Group entity."""
        self._name = name
        self._state = None
        self._supported_features: int = 0

        self._entities = entities
        self._players: Dict[str, Set[str]] = {
            KEY_CLEAR_PLAYLIST: set(),
            KEY_ON_OFF: set(),
            KEY_PAUSE_PLAY_STOP: set(),
            KEY_PLAY_MEDIA: set(),
            KEY_SHUFFLE: set(),
            KEY_SEEK: set(),
            KEY_TRACKS: set(),
            KEY_VOLUME: set(),
        }

    @callback
    def _update_supported_features_event(self, event):
        self.update_supported_features(
            event.data.get("entity_id"), event.data.get("new_state")
        )

    @callback
    def update_supported_features(
        self, entity_id: str, new_state: Optional[State], update_state: bool = True,
    ) -> None:
        """Update dictionaries with supported features."""
        if not new_state:
            for values in self._players.values():
                values.discard(entity_id)
            if update_state:
                self.async_schedule_update_ha_state(True)
            return

        features = new_state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if features & SUPPORT_CLEAR_PLAYLIST:
            self._players[KEY_CLEAR_PLAYLIST].add(entity_id)
        else:
            self._players[KEY_CLEAR_PLAYLIST].discard(entity_id)
        if features & (SUPPORT_PAUSE | SUPPORT_PLAY | SUPPORT_STOP):
            self._players[KEY_PAUSE_PLAY_STOP].add(entity_id)
        else:
            self._players[KEY_PAUSE_PLAY_STOP].discard(entity_id)
        if features & (SUPPORT_TURN_ON | SUPPORT_TURN_OFF):
            self._players[KEY_ON_OFF].add(entity_id)
        else:
            self._players[KEY_ON_OFF].discard(entity_id)
        if features & SUPPORT_PLAY_MEDIA:
            self._players[KEY_PLAY_MEDIA].add(entity_id)
        else:
            self._players[KEY_PLAY_MEDIA].discard(entity_id)
        if features & SUPPORT_SHUFFLE_SET:
            self._players[KEY_SHUFFLE].add(entity_id)
        else:
            self._players[KEY_SHUFFLE].discard(entity_id)
        if features & SUPPORT_SEEK:
            self._players[KEY_SEEK].add(entity_id)
        else:
            self._players[KEY_SEEK].discard(entity_id)
        if features & (SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK):
            self._players[KEY_TRACKS].add(entity_id)
        else:
            self._players[KEY_TRACKS].discard(entity_id)
        if features & (SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP):
            self._players[KEY_VOLUME].add(entity_id)
        else:
            self._players[KEY_VOLUME].discard(entity_id)

        if update_state:
            self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Register listeners."""
        for entity_id in self._entities:
            new_state = self.hass.states.get(entity_id)
            self.update_supported_features(entity_id, new_state, update_state=False)
        async_track_state_change_event(
            self.hass, self._entities, self._update_supported_features_event
        )
        await self.async_update()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def state(self) -> str:
        """Return the state of the media group."""
        return self._state or STATE_OFF  # type: ignore[unreachable]

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def should_poll(self) -> bool:
        """No polling needed for a media group."""
        return False

    @property
    def device_state_attributes(self) -> dict:
        """Return the state attributes for the media group."""
        return {ATTR_ENTITY_ID: self._entities}

    def media_next_track(self):
        """Send next track command."""
        data = {ATTR_ENTITY_ID: self._players[KEY_TRACKS]}
        self.hass.services.call(
            DOMAIN,
            SERVICE_MEDIA_NEXT_TRACK,
            data,
            blocking=True,
            context=self._context,
        )

    def media_pause(self):
        """Send pause command."""
        data = {ATTR_ENTITY_ID: self._players[KEY_PAUSE_PLAY_STOP]}
        self.hass.services.call(
            DOMAIN, SERVICE_MEDIA_PAUSE, data, blocking=True, context=self._context,
        )

    def media_play(self):
        """Send play command."""
        data = {ATTR_ENTITY_ID: self._players[KEY_PAUSE_PLAY_STOP]}
        self.hass.services.call(
            DOMAIN, SERVICE_MEDIA_PLAY, data, blocking=True, context=self._context,
        )

    def media_previous_track(self):
        """Send previous track command."""
        data = {ATTR_ENTITY_ID: self._players[KEY_TRACKS]}
        self.hass.services.call(
            DOMAIN,
            SERVICE_MEDIA_PREVIOUS_TRACK,
            data,
            blocking=True,
            context=self._context,
        )

    def media_seek(self, position):
        """Send seek command."""
        data = {
            ATTR_MEDIA_SEEK_POSITION: position,
            ATTR_ENTITY_ID: self._players[KEY_SEEK],
        }
        self.hass.services.call(
            DOMAIN, SERVICE_MEDIA_SEEK, data, blocking=True, context=self._context,
        )

    def media_stop(self):
        """Send stop command."""
        data = {ATTR_ENTITY_ID: self._players[KEY_PAUSE_PLAY_STOP]}
        self.hass.services.call(
            DOMAIN, SERVICE_MEDIA_STOP, data, blocking=True, context=self._context,
        )

    def mute_volume(self, mute):
        """Mute the volume."""
        data = {
            ATTR_MEDIA_VOLUME_MUTED: mute,
            ATTR_ENTITY_ID: self._players[KEY_VOLUME],
        }
        self.hass.services.call(
            DOMAIN, SERVICE_VOLUME_MUTE, data, blocking=True, context=self._context,
        )

    def play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        data = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: self._players[KEY_PLAY_MEDIA],
        }
        self.hass.services.call(
            DOMAIN, SERVICE_PLAY_MEDIA, data, blocking=True, context=self._context,
        )

    def turn_on(self):
        """Forward the turn_on command to all media in the media group."""
        data = {ATTR_ENTITY_ID: self._players[KEY_ON_OFF]}
        self.hass.services.call(
            DOMAIN, SERVICE_TURN_ON, data, blocking=True, context=self._context,
        )

    def set_volume_level(self, volume):
        """Set volume level(s)."""
        data = {
            ATTR_MEDIA_VOLUME_LEVEL: volume,
            ATTR_ENTITY_ID: self._players[KEY_VOLUME],
        }
        self.hass.services.call(
            DOMAIN, SERVICE_VOLUME_SET, data, blocking=True, context=self._context,
        )

    def turn_off(self):
        """Forward the turn_off command to all media in the media group."""
        data = {ATTR_ENTITY_ID: self._players[KEY_ON_OFF]}
        self.hass.services.call(
            DOMAIN, SERVICE_TURN_OFF, data, blocking=True, context=self._context,
        )

    async def async_volume_up(self):
        """Turn volume up for media player(s)."""
        for entity in self._players[KEY_VOLUME]:
            volume_level = self.hass.states.get(entity).attributes["volume_level"]
            if volume_level < 1:
                await self.async_set_volume_level(min(1, volume_level + 0.1))

    async def async_volume_down(self):
        """Turn volume down for media player(s)."""
        for entity in self._players[KEY_VOLUME]:
            volume_level = self.hass.states.get(entity).attributes["volume_level"]
            if volume_level > 0:
                await self.async_set_volume_level(max(0, volume_level - 0.1))

    async def async_update(self):
        """Query all members and determine the media group state."""
        all_states = [self.hass.states.get(x) for x in self._entities]
        not_none_states: List[State] = list(filter(None, all_states))
        states = [state.state for state in not_none_states]
        off_values = STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN

        if states:
            if states.count(states[0]) == len(states):
                self._state = states[0]
            elif any(state for state in states if state not in off_values) > 0:
                self._state = STATE_ON
            else:
                self._state = STATE_OFF

        supported_features = 0
        supported_features |= (
            SUPPORT_CLEAR_PLAYLIST if self._players[KEY_CLEAR_PLAYLIST] else 0
        )
        supported_features |= (
            SUPPORT_PAUSE | SUPPORT_PLAY | SUPPORT_STOP
            if self._players[KEY_PAUSE_PLAY_STOP]
            else 0
        )
        supported_features |= (
            SUPPORT_TURN_ON | SUPPORT_TURN_OFF if self._players[KEY_ON_OFF] else 0
        )
        supported_features |= SUPPORT_PLAY_MEDIA if self._players[KEY_PLAY_MEDIA] else 0
        supported_features |= SUPPORT_SHUFFLE_SET if self._players[KEY_SHUFFLE] else 0
        supported_features |= SUPPORT_SEEK if self._players[KEY_SEEK] else 0
        supported_features |= (
            SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK
            if self._players[KEY_TRACKS]
            else 0
        )
        supported_features |= (
            SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP
            if self._players[KEY_VOLUME]
            else 0
        )

        self._supported_features = supported_features
