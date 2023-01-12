"""The ISY/IoX integration data models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pyisy import ISY
from pyisy.constants import PROTO_INSTEON
from pyisy.networking import NetworkCommand
from pyisy.nodes import Group, Node
from pyisy.programs import Program
from pyisy.variables import Variable

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.helpers.entity_registry as er

from .const import (
    _LOGGER,
    CONF_NETWORK,
    NODE_AUX_PROP_PLATFORMS,
    NODE_PLATFORMS,
    PROGRAM_PLATFORMS,
    ROOT_NODE_PLATFORMS,
    VARIABLE_PLATFORMS,
)


@dataclass
class IsyData:
    """Data for the ISY/IoX integration."""

    hass: HomeAssistant
    config_entry: config_entries.ConfigEntry
    root: ISY
    nodes: dict[Platform, list[Node | Group]]
    root_nodes: dict[Platform, list[Node]]
    variables: dict[Platform, list[tuple[str, Program, Program]]]
    programs: dict[Platform, list[Variable]]
    net_resources: list[NetworkCommand]
    devices: dict[str, DeviceInfo]
    aux_props: dict[Platform, list[tuple[Node, str]]]

    def __init__(
        self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry
    ) -> None:
        """Initialize an empty ISY data class."""
        self.hass = hass
        self.config_entry = config_entry
        self.nodes = {p: [] for p in NODE_PLATFORMS}
        self.root_nodes = {p: [] for p in ROOT_NODE_PLATFORMS}
        self.aux_props = {p: [] for p in NODE_AUX_PROP_PLATFORMS}
        self.programs = {p: [] for p in PROGRAM_PLATFORMS}
        self.variables = {p: [] for p in VARIABLE_PLATFORMS}
        self.net_resources = []
        self.devices = {}

    @property
    def uuid(self) -> str:
        """Return the ISY UUID identification."""
        return cast(str, self.root.uuid)

    def uid_base(self, node: Node | Group | Variable | Program | NetworkCommand) -> str:
        """Return the unique id base string for a given node."""
        if isinstance(node, NetworkCommand):
            return f"{self.uuid}_{CONF_NETWORK}_{node.address}"
        return f"{self.uuid}_{node.address}"

    @property
    def unique_ids(self) -> set[tuple[Platform, str]]:
        """Return all the unique ids for a config entry id."""
        current_unique_ids: set[tuple[Platform, str]] = {
            (Platform.BUTTON, f"{self.uuid}_query")
        }

        # Structure and prefixes here must match what's added in __init__ and helpers
        for platform in NODE_PLATFORMS:
            for node in self.nodes[platform]:
                current_unique_ids.add((platform, self.uid_base(node)))

        for platform in NODE_AUX_PROP_PLATFORMS:
            for node, control in self.aux_props[platform]:
                current_unique_ids.add((platform, f"{self.uid_base(node)}_{control}"))

        for platform in PROGRAM_PLATFORMS:
            for _, node, _ in self.programs[platform]:
                current_unique_ids.add((platform, self.uid_base(node)))

        for platform in VARIABLE_PLATFORMS:
            for node in self.variables[platform]:
                current_unique_ids.add((platform, self.uid_base(node)))
                if platform == Platform.NUMBER:
                    current_unique_ids.add((platform, f"{self.uid_base(node)}_init"))

        for platform in ROOT_NODE_PLATFORMS:
            for node in self.root_nodes[platform]:
                current_unique_ids.add((platform, f"{self.uid_base(node)}_query"))
                if platform == Platform.BUTTON and node.protocol == PROTO_INSTEON:
                    current_unique_ids.add((platform, f"{self.uid_base(node)}_beep"))

        for node in self.net_resources:
            current_unique_ids.add((Platform.BUTTON, self.uid_base(node)))

        return current_unique_ids

    @callback
    def async_cleanup_registry_entries(self) -> None:
        """Remove extra entities that are no longer part of the integration."""
        entity_registry = er.async_get(self.hass)

        existing_entries = er.async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        entities = {
            (entity.domain, entity.unique_id): entity.entity_id
            for entity in existing_entries
        }

        extra_entities = set(entities.keys()).difference(self.unique_ids)
        if not extra_entities:
            return

        for entity in extra_entities:
            if entity_registry.async_is_registered(entities[entity]):
                entity_registry.async_remove(entities[entity])

        _LOGGER.debug(
            ("Cleaning up ISY entities: removed %s extra entities for %s"),
            len(extra_entities),
            self.config_entry.title,
        )
