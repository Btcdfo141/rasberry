"""Support for interfacing with the HASS MPRIS agent."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, cast

from hassmpris.proto import mpris_pb2
import hassmpris_client
import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_PLAYBACK_RATE,
    DOMAIN,
    ENTRY_CLIENT,
    ENTRY_UNLOADERS,
    LOGGER as _LOGGER,
)

PLATFORM = "media_player"

DISCOVERY_SCHEMA = vol.Schema(
    {
        vol.Required("player_id"): cv.string,
    }
)

SUPPORTED_MINIMAL = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
)
SUPPORTED_TURN_OFF = MediaPlayerEntityFeature.TURN_OFF
SUPPORTED_TURN_ON = MediaPlayerEntityFeature.TURN_ON

# Enable to remove clones (second / third, nth instances)
# of any player when the player exits.  Not enabled by
# default because events in the logbook disappear when
# the player goes away.
# Clones are always removed upon start or reload of the
# integration, since there is no value in keeping them
# around.
REMOVE_CLONES_WHILE_RUNNING = False


def _feat2bitfield(bitfield: int, obj: object) -> str:
    fields = []
    for feat in dir(obj):
        val = getattr(obj, feat)
        if not isinstance(val, int):
            continue
        if bitfield & val:
            fields.append(feat)
    return ",".join(fields)


class HASSMPRISEntity(MediaPlayerEntity):
    """This class represents an MPRIS media player entity."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = SUPPORTED_MINIMAL
    _attr_playback_rate: float = 1.0

    def __init__(
        self,
        client: hassmpris_client.AsyncMPRISClient,
        integration_id: str,
        player_id: str,
        initial_state: str | None = None,
    ) -> None:
        """
        Initialize the entity.

        Parameters:
          client: the client to the remote agent
          integration_id: unique identifier of the integration
          player_id: the name / unique identifier of the player
        """
        super().__init__()
        if client is None:
            raise ValueError("Instantiation of this class requires a client")
        self.client: hassmpris_client.AsyncMPRISClient | None = client
        self._client_host = self.client.host
        self.player_id = player_id
        self._integration_id = integration_id
        self._attr_available = True
        self._metadata: dict[str, Any] = {}
        if initial_state is not None:
            self._attr_state = initial_state

    async def set_unavailable(self):
        """Mark player as unavailable."""
        _LOGGER.debug("Marking %s as unavailable", self.name)
        self.client = None
        self._attr_available = False
        await self.update_state(STATE_UNKNOWN)

    async def async_removed_from_registry(self) -> None:
        """Clean up when removed from the registry."""
        self.client = None

    async def set_available(
        self,
        client: hassmpris_client.AsyncMPRISClient,
    ):
        """
        Mark a player as available again.

        Parameters:
          client: the new client to use to talk to the agent
        """
        _LOGGER.debug("Marking %s as available", self.name)
        self.client = client
        self._client_host = self.client.host
        self._attr_available = True
        if self.hass:
            await self.async_update_ha_state(True)

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this entity."""
        return self._integration_id + "-" + self.player_id

    @property
    def name(self):
        """Return the name of the entity."""
        return self.player_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information associated with the entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._integration_id)},
            name="MPRIS agent at %s" % self._client_host,
            manufacturer="Freedesktop",
        )

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    @property
    def state(self):
        """Return the current playback state of the entity."""
        return self._attr_state

    @staticmethod
    def config_schema():
        """Return the discovery schema."""
        return DISCOVERY_SCHEMA

    async def async_media_play(self):
        """Begin playback."""
        if self.client:
            await self.client.play(self.player_id)

    async def async_media_pause(self):
        """Pause playback."""
        if self.client:
            await self.client.pause(self.player_id)

    async def async_media_stop(self):
        """Stop playback."""
        if self.client:
            await self.client.stop(self.player_id)

    async def async_media_next_track(self):
        """Skip to next track."""
        if self.client:
            await self.client.next(self.player_id)

    async def async_media_previous_track(self):
        """Skip to previous track."""
        if self.client:
            await self.client.previous(self.player_id)

    async def async_media_seek(self, position: float):
        """Send seek command."""
        if self.client:
            trackid = self._metadata.get("mpris:trackid")
            if trackid:
                await self.client.set_position(
                    self.player_id,
                    trackid,
                    position,
                )

    async def update_state(
        self,
        new_state: str,
    ):
        """Update player state based on reports from the server."""
        if new_state == self._attr_state:
            return

        _LOGGER.debug(
            "Updating state from %s to %s",
            self._attr_state,
            new_state,
        )
        self._attr_state = new_state
        if self.hass:
            await self.async_update_ha_state(True)

    async def update_metadata(self, new_metadata: dict[str, Any]):
        """Update player metadata based on incoming metadata (a dict)."""
        self._metadata = new_metadata
        if "mpris:length" in self._metadata:
            length: int | None = round(
                float(self._metadata["mpris:length"]) / 1000 / 1000
            )
            if length is not None and length <= 0:
                length = None
        else:
            length = None

        self._attr_media_duration = length
        self._attr_media_position = 0 if length is not None else None
        self._attr_media_position_updated_at = dt_util.utcnow()

        _LOGGER.debug("Setting media duration to %s", self._attr_media_duration)
        _LOGGER.debug("Setting media position to %s", self._attr_media_position)

        if self.hass:
            await self.async_update_ha_state(True)

    async def update_position(self, new_position: float):
        """Update position."""
        self._attr_media_position_updated_at = dt_util.utcnow()
        self._attr_media_position = (
            round(new_position) if new_position is not None else None
        )
        _LOGGER.debug("Setting media position to %s", self._attr_media_position)
        if self.hass:
            await self.async_update_ha_state(True)

    async def update_mpris_properties(
        self,
        props: mpris_pb2.MPRISPlayerProperties,
    ):
        """Update player properties based on incoming MPRISPlayerProperties."""
        _LOGGER.debug("%s: new properties: %s", self.name, props)

        feats = self._attr_supported_features
        if props.HasField("CanControl"):
            if not props.CanControl:
                feats = 0
            else:
                feats = SUPPORTED_MINIMAL

        update_state = False

        for name, bitwisefield in {
            "CanPlay": MediaPlayerEntityFeature.PLAY,
            "CanPause": MediaPlayerEntityFeature.PAUSE,
            "CanSeek": MediaPlayerEntityFeature.SEEK,
            "CanGoNext": MediaPlayerEntityFeature.NEXT_TRACK,
            "CanGoPrevious": MediaPlayerEntityFeature.PREVIOUS_TRACK,
        }.items():
            if props.HasField(name):
                val = getattr(props, name)
                if val:
                    feats = feats | bitwisefield
                else:
                    feats = feats & ~bitwisefield

        if feats != self._attr_supported_features:
            _LOGGER.debug(
                "%s: new feature bitfield: (%s) %s",
                self.name,
                feats,
                _feat2bitfield(feats, MediaPlayerEntityFeature),
            )
            self._attr_supported_features = feats
            update_state = True

        if props.HasField("Rate") and props.Rate != self._attr_playback_rate:
            _LOGGER.debug("%s: new rate: %s", self.name, props.Rate)
            self._attr_playback_rate = props.Rate
            update_state = True

        if update_state and self.hass:
            await self.async_update_ha_state(True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.state == STATE_OFF:
            return {}
        return {ATTR_PLAYBACK_RATE: self._attr_playback_rate}


class EntityManager:
    """
    The entity manager manages MPRIS media player entities.

    This class is responsible for maintaining the known player entities
    in sync with the state as reported by the server, as well as keeping
    tabs of newly-appeared players and players that have gone.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        mpris_client: hassmpris_client.AsyncMPRISClient,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """
        Initialize the entity manager.

        Parameters:
          hass: the HomeAssistant singleton
          config_entry: the configuration entry associated with
                        this component (or integration?)
          async_add_entities: callback to add entities async
        """
        self.hass = hass
        self.config_entry = config_entry
        self.async_add_entities = async_add_entities
        self._client = mpris_client
        self._players: dict[str, HASSMPRISEntity] = {}
        self._shutdown: asyncio.Future[bool] = asyncio.Future()
        self._started = False

    @property
    def players(self) -> dict[str, HASSMPRISEntity]:
        """Return the players known to this entity manager."""
        return self._players

    @property
    def client(self) -> hassmpris_client.AsyncMPRISClient:
        """Return the MPRIS client associated with this entity manager."""
        return self._client

    async def start(self):
        """Start the entity manager as a separate task."""
        self.hass.loop.create_task(self.run())

    async def run(self):
        """Run the entity manager."""
        if self._started:
            _LOGGER.debug("%X: Thread already started", id(self))
            return
        self._started = True
        _LOGGER.debug("%X: Streaming updates started", id(self))
        while not self._shutdown.done():
            try:
                try:
                    await self._monitor_updates()
                except Exception as exc:
                    if self._shutdown.done():
                        _LOGGER.debug(
                            "%X: Ignoring %s since we are shut down", id(self), exc
                        )
                        await self._shutdown
                        continue
                    raise
            except hassmpris_client.Unauthenticated:
                _LOGGER.error(
                    "We have been deauthorized -- no further updates "
                    "will occur until reauthentication"
                )
                self.config_entry.async_start_reauth(self.hass)
                await self.stop()
            except hassmpris_client.ClientException as exc:
                _LOGGER.error(
                    "%X: We lost connectivity (%s) -- reconnecting", id(self), exc
                )
                await asyncio.sleep(5)
            except Exception as exc:
                await self.stop(exception=exc)
                raise
        await self._shutdown
        _LOGGER.debug("%X: Streaming updates ended", id(self))

    async def stop(
        self,
        *unused_args: Any,
        exception: Exception | None = None,
    ) -> None:
        """Stop the loop."""
        try:
            if exception:
                self._shutdown.set_exception(exception)
            else:
                self._shutdown.set_result(True)
        except asyncio.InvalidStateError:
            pass

    async def _mark_all_entities_unavailable(self):
        for entity in self.players.values():
            await entity.set_unavailable()

    async def _mark_all_entities_available(self):
        for entity in self.players.values():
            await entity.set_available(self.client)

    async def _finish_initial_players_sync(self):
        """
        Sync know player and registry entry state.

        Called when the agent has sent us the full list of players it knows
        about, and we are ready to materialize players for entities in the
        registry but currently unknown to the agent.

        This is necessary so that Home Assistant can later request the agent
        turn on (spawn) a known player that is currently off.
        """
        # It is probably best to investigate using entity lifecycle hooks:
        # https://developers.home-assistant.io/docs/core/entity/#lifecycle-hooks

        def get_player_id(
            entity: er.RegistryEntry | HASSMPRISEntity,
        ) -> str:
            return entity.unique_id.split("-", 1)[1]

        reg = er.async_get(self.hass)

        player_entries = {
            get_player_id(e): e
            for e in reg.entities.values()
            if e.config_entry_id == self.config_entry.entry_id
        }

        player_ids = {
            get_player_id(entity)
            for entity in list(player_entries.values()) + list(self.players.values())
        }

        for player_id in player_ids:
            self._sync_player_presence(
                player_id,
                self.players.get(player_id),
                player_entries.get(player_id),
            )

    def _sync_player_presence(
        self,
        player_id: str,
        player: HASSMPRISEntity | None,
        entry: er.RegistryEntry | None,
    ):
        """Sync entity and config entry for the player.

        `player` will be None if the directory of known players does not
        contain it.  Else it will be defined.
        """

        def is_first_instance() -> bool:
            return not bool(re.match(".* [(]\\d+[)]", player_id))

        def is_off(player: HASSMPRISEntity) -> bool:
            offstates = [STATE_OFF, STATE_UNKNOWN]
            return player.state in offstates

        if is_first_instance():
            # This is (by ID) the first instance of a player.
            if player is None:
                # We do not have a player in our directory that represents
                # this entity in the registry.  So we "bring it back", in OFF
                # state.
                _LOGGER.debug("%X: Resuscitating known player %s", id(self), player_id)
                entity = HASSMPRISEntity(
                    self.client,
                    self.config_entry.entry_id,
                    player_id,
                    initial_state=STATE_OFF,
                )
                self.players[player_id] = entity
                self.async_add_entities([entity])
        else:
            # This is a second instance of a player.
            # E.g. `VLC media player`` is not a second instance,
            # but `VLC media player 2`` is in fact a second instance.
            # Many media players can launch multiple instances, but we
            # don't necessarily want to keep all those instances around
            # if they are off or unknown.

            # The copycat player is in the directory, but its state is off
            # or unknown.  This means the agent knew about it at some
            # point, but it is now gone.  So we remove it from the list of
            # players we know about.
            remove_from_directory = player and is_off(player)

            # The agent does not know about this player, or the player
            # is off / unknown.  That means we can remove its entity record
            # from the registry (to keep the record clean of entities
            # which may very well never reappear).
            remove_from_registry = not player or remove_from_directory

            if remove_from_directory:
                _LOGGER.debug(
                    "%X: Removing copy %s from directory", id(self), player_id
                )
                del self.players[player_id]
            if remove_from_registry:
                entity_id = (
                    entry.entity_id if entry else player.entity_id if player else None
                )
                if entity_id is not None:
                    # Entry and player cannot both be None, but the typing
                    # machinery does not know that.
                    _LOGGER.debug(
                        "%X: Removing copy %s from registry (entity ID %s)",
                        id(self),
                        player_id,
                        entity_id,
                    )
                    reg = er.async_get(self.hass)
                    reg.async_remove(entity_id)

    async def _monitor_updates(self):
        """Obtain a real-time eed of player updates."""
        try:
            started_syncing = False
            finished_syncing = False
            async for update in self.client.stream_updates():
                if not started_syncing:
                    # First update.  Mark entities available.
                    await self._mark_all_entities_available()
                    started_syncing = True
                if update.HasField("player"):
                    # There's a player update incoming.
                    await self._handle_update(update.player)
                elif not finished_syncing:
                    # Ah, this is the signal that all players known to the agent
                    # have had their information sent to Home Assistant.
                    await self._finish_initial_players_sync()
                    finished_syncing = True
        finally:
            # Whether due to error or request, we no longer get updates.
            # All entities are now unavailable from the standpoint of the
            # HASS MPRIS client, so we mark them as such.
            await self._mark_all_entities_unavailable()

    async def _handle_update(
        self,
        discovery_data: mpris_pb2.MPRISUpdateReply,
    ):
        """Handle a single player update."""
        _LOGGER.debug("%X: Handling update: %s", id(self), discovery_data)
        state = STATE_IDLE
        fire_status_update_observed = False
        table = {
            mpris_pb2.PlayerStatus.GONE: STATE_OFF,
            mpris_pb2.PlayerStatus.APPEARED: STATE_IDLE,
            mpris_pb2.PlayerStatus.PLAYING: STATE_PLAYING,
            mpris_pb2.PlayerStatus.PAUSED: STATE_PAUSED,
            mpris_pb2.PlayerStatus.STOPPED: STATE_IDLE,
        }
        if discovery_data.status != mpris_pb2.PlayerStatus.UNKNOWN:
            state = table[discovery_data.status]
            fire_status_update_observed = True

        fire_metadata_update_observed = False
        if discovery_data.json_metadata:
            fire_metadata_update_observed = True
            metadata = json.loads(discovery_data.json_metadata)

        fire_properties_update_observed = False
        if discovery_data.HasField("properties"):
            fire_properties_update_observed = True
            mpris_properties = discovery_data.properties
        fire_seeked_observed = False
        if discovery_data.HasField("seeked"):
            fire_seeked_observed = True
            position = discovery_data.seeked.position

        player_id = discovery_data.player_id

        if player_id in self.players:
            player: HASSMPRISEntity = self.players[player_id]
        else:
            player = HASSMPRISEntity(
                self.client,
                self.config_entry.entry_id,
                player_id,
            )
            self.async_add_entities([player])
            self.players[player_id] = player

        if fire_status_update_observed:
            await player.update_state(state)
        if fire_metadata_update_observed:
            await player.update_metadata(metadata)
        if fire_properties_update_observed:
            await player.update_mpris_properties(mpris_properties)
        if fire_seeked_observed:
            await player.update_position(position)

        # Final hook to remove duplicates which are gone.
        if fire_status_update_observed and REMOVE_CLONES_WHILE_RUNNING:
            self._sync_player_presence(player_id, player, None)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up all the media players for the MPRIS integration."""
    component_data = hass.data[DOMAIN][config_entry.entry_id]
    mpris_client = cast(
        hassmpris_client.AsyncMPRISClient,
        component_data[ENTRY_CLIENT],
    )
    manager = EntityManager(
        hass,
        config_entry,
        mpris_client,
        async_add_entities,
    )

    await manager.start()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, manager.stop)

    async def async_stop_manager():
        _LOGGER.debug("Stopping entity manager")
        await manager.stop()
        _LOGGER.debug("Entity manager stopped")

    component_data[ENTRY_UNLOADERS].append(async_stop_manager)

    return True
