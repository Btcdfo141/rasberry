"""Support for rasc."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import threading
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.rascalscheduler import (
    ActionEntity,
    Queue,
    QueueEntity,
    RoutineEntity,
)

from .const import DOMAIN, LOGGER

CONFIG_ACTION_ID = "action_id"
CONFIG_ENTITY_ID = "entity_id"
CONFIG_ACTION_ENTITY = "action_entity"
CONFIG_PARALLEL = "parallel"
CONFIG_SEQUENCE = "sequence"


RASC_SCHEDULED = "scheduled"
RASC_START = "start"
RASC_COMPLETE = "complete"
RASC_RESPONSE = "rasc_response"


def setup_rascal_scheduler_entity(hass: HomeAssistant) -> None:
    """Set up RASC scheduler entity."""
    LOGGER.info("Setup rascal entity")
    hass.data[DOMAIN] = RascalSchedulerEntity(hass)
    hass.bus.async_listen(RASC_RESPONSE, hass.data[DOMAIN].event_listener)


def create_x_ready_queue(hass: HomeAssistant, entity_id: str) -> None:
    """Create queue for x entity."""
    LOGGER.info("Create ready queue: %s", entity_id)
    scheduler = hass.data[DOMAIN]
    scheduler.ready_queues[entity_id] = QueueEntity(None)
    scheduler.active_routines[entity_id] = None


# def delete_x_active_queue(hass: HomeAssistant, entity_id: str) -> None:
#     """Delete x entity queue."""
#     try:
#         rascal_scheduler = hass.data[DOMAIN]
#         active_routines = rascal_scheduler.get_active_routines()
#         del active_routines[entity_id]
#     except (KeyError, ValueError):
#         LOGGER.warning("Unable to delete unknown queue %s", entity_id)


def get_rascal_scheduler(hass: HomeAssistant) -> RascalSchedulerEntity:
    """Get rascal scheduler."""
    return hass.data[DOMAIN]


def dag_operator(
    hass: HomeAssistant,
    routine_id: str,
    action_script: Sequence[dict[str, Any]],
) -> RoutineEntity:
    """Convert the script to the dag."""
    next_parents: list[ActionEntity] = []
    entities: dict[str, ActionEntity] = {}
    config: dict[str, Any] = {}

    # configuration for each node
    config["step"] = -1
    config["routine_id"] = routine_id
    config["hass"] = hass

    for _, script in enumerate(action_script):
        if (
            "parallel" not in script
            and "sequence" not in script
            and "service" not in script
        ):
            # print("[dsf_outside]")
            # print("next_parents: ")
            # for entity in next_parents:
            #     print(entity.action_id)

            config["step"] = config["step"] + 1
            action_id = config["routine_id"] + str(config["step"])

            entities[action_id] = ActionEntity(
                hass=hass,
                action=script,
                action_id=action_id,
                action_state=None,
                routine_id=config["routine_id"],
            )

            for entity in next_parents:
                entities[action_id].parents.append(entity)

            for entity in next_parents:
                entity.children.append(entities[action_id])

            next_parents.clear()
            next_parents.append(entities[action_id])

        else:
            leaf_nodes = dfs(script, config, next_parents, entities)
            next_parents.clear()
            next_parents = leaf_nodes

    # print("\n")
    # for key, value in entities.items():
    #     print("------- aciton_id:", key, "------------")
    #     print(value.action)
    #     print("parent: ")
    #     for entity in value.parents:
    #         print(entity.action_id, ",")

    #     print("children: ")
    #     for entity in value.children:
    #         print(entity.action_id, ",")

    RoutineEntity.set_counter(routine_id, 0)
    return RoutineEntity(routine_id, entities)


def dfs(
    script: dict[str, Any],
    config: dict[str, Any],
    parents: list[ActionEntity],
    entities: dict[str, Any],
) -> list[ActionEntity]:
    """Convert the script to the dag using dsf."""

    next_parents = []
    # print("script:", script)
    if "parallel" in script:
        for item in list(script.values())[0]:
            # print("[parallel dsf]")
            # print("parents:")
            # for entity in parents:
            #     print(entity.action_id)
            # print("next_parents: ")
            # for entity in next_parents:
            #     print(entity.action_id)
            # print("\n")

            leaf_entities = dfs(item, config, parents, entities)

            for entity in leaf_entities:
                next_parents.append(entity)

    elif "sequence" in script:
        next_parents = parents
        for item in list(script.values())[0]:
            # print("[sequence dsf]")
            # print("root:")
            # for entity in parents:
            #     print(entity.action_id)
            # print("next_parents: ")
            # for entity in next_parents:
            #     print(entity.action_id)
            # print("\n")

            leaf_entities = dfs(item, config, next_parents, entities)
            next_parents = leaf_entities

    else:
        # print("[general]")
        config["step"] = config["step"] + 1
        action_id = config["routine_id"] + str(config["step"])

        # print("action_id:", action_id)
        # print("action: ", script)
        # print("parents: ")
        # for entity in parents:
        #     print(entity.action_id, ",")
        # print("\n")

        entities[action_id] = ActionEntity(
            hass=config["hass"],
            action=script,
            action_id=action_id,
            action_state=None,
            routine_id=config["routine_id"],
        )

        for entity in parents:
            entities[action_id].parents.append(entity)

        for entity in parents:
            entity.children.append(entities[action_id])

        next_parents.append(entities[action_id])

    return next_parents


class BaseActiveRoutines:
    """Base class for active routines."""

    _active_routines: dict[str, ActionEntity]

    @property
    def active_routines(self) -> dict[str, ActionEntity]:
        """Get active routines."""
        return self._active_routines

    def get_active_routine(self, entity_id: str) -> ActionEntity:
        """Get active routine of entity_id."""
        return self._active_routines[entity_id]

    def print_active_routines(self) -> None:
        """Print the content of active routines."""
        print("\n-------------- Active Routines --------------")  # noqa: T201
        for entity_id in self._active_routines:
            print("entity_id: ", entity_id)  # noqa: T201
            if self._active_routines[entity_id] is None:
                print("None")  # noqa: T201
            else:
                print(  # noqa: T201
                    self._active_routines[entity_id].action_id,
                    self._active_routines[entity_id].action_state,
                )


class BaseReadyQueues:
    """Base class for ready queue."""

    _ready_queues: dict[str, QueueEntity]

    @property
    def ready_queues(self) -> dict[str, QueueEntity]:
        """Get ready routines."""
        return self._ready_queues

    def empty(self, entity_id) -> bool:
        """Return if the queue is empty or not."""
        return len(self._ready_queues[entity_id]) == 0

    def print_ready_queues(self) -> None:
        """Print the content of ready routines."""
        print("\n-------------- Ready Routines --------------")  # noqa: T201
        for entity_id, actions in self._ready_queues.items():
            print("entity_id:", entity_id)  # noqa: T201
            itr = iter(actions)
            for _i in range(0, len(actions)):
                action = next(itr)
                print(action.action_id, action.action_state)  # noqa: T201


class RascalSchedulerEntity(BaseActiveRoutines, BaseReadyQueues):
    """Representation of a rascal scehduler entity."""

    def __init__(self, hass):
        """Initialize rascal scheduler entity."""
        self.hass = hass
        self._ready_queues: Queue() = {}
        self._active_routines: dict[str, ActionEntity | None] = {}
        self.event_listener = self.handle_event

    # Listener to handle fired events
    async def handle_event(self, event):
        """Handle event."""
        eventType = event.data.get("type")
        entityID = event.data.get("entity_id")
        action_entity = self.get_active_routine(entityID)

        if eventType == RASC_COMPLETE:
            self.update_action_state(action_entity, RASC_COMPLETE)
            # self.print_active_routines()
            await self.async_schedule_next(action_entity)

        elif eventType == RASC_START:
            self.update_action_state(action_entity, RASC_START)
            # self.print_active_routines()

    async def async_schedule_next(self, action_entity: ActionEntity) -> None:
        """Schedule subroutines."""
        entity_id = action_entity.action[CONFIG_ENTITY_ID]

        def condition_check() -> bool:
            if action_entity.children:
                # print("parents: ", action_entity.children[0].parents)  # noqa: T201
                if action_entity.children[0].parents:
                    for p in action_entity.children[0].parents:
                        # print(  # noqa: T201
                        #     "parent: ", p.action, " state: ", p.action_state
                        # )
                        if p.action_state != RASC_COMPLETE:
                            return False

            return True

        if condition_check():
            self._schedule_subroutines(action_entity)

        self._set_active_routine(entity_id, None)
        await self._async_run_next(entity_id)

    def _schedule_subroutines(self, action_entity: ActionEntity) -> None:
        """Schedule subroutines."""
        if not action_entity.children:
            return

        self._set_ready_subroutines(action_entity)
        # self.print_ready_queues()

    async def _async_run_next(self, entity_id: str) -> None:
        """Execute FIFO."""
        if not self._ready_queues[entity_id].empty():
            next_action_entity = self._ready_queues[entity_id].pop(0)
            self._set_active_routine(entity_id, next_action_entity)

    def start_routine(self, routine_entity: RoutineEntity) -> None:
        """Start routine entity."""
        for _action_id, action_entity in routine_entity.actions.items():
            if not action_entity.parents:
                self._set_ready_routines(action_entity)

    def _set_ready_routines(self, action_entity: ActionEntity) -> None:
        """Set ready routines."""
        entity_id = action_entity.action[CONFIG_ENTITY_ID]
        if self._active_routines[entity_id] is None:
            self._set_active_routine(entity_id, action_entity)
        # else:
        #     self._ready_queues[entity_id].append(action_entity)
        #     self.update_action_state(
        #         action_entity.routine_id, action_entity.action_id, READY_STATE
        #     )

    def _set_ready_subroutines(self, action_entity: ActionEntity) -> None:
        """Set ready subroutines."""
        ready_actions = action_entity.children

        for action in ready_actions:
            entity_id = action.action[CONFIG_ENTITY_ID]

            if self._active_routines[entity_id] is None:
                self._set_active_routine(entity_id, action)
            else:
                self._ready_queues[entity_id].append(action)

    def _set_active_routine(
        self, entity_id: str, action_entity: ActionEntity | None
    ) -> None:
        """Set active routine."""
        self._active_routines[entity_id] = action_entity

        if action_entity is not None:
            self._active_routines[entity_id] = action_entity
            thread = threading.Thread(target=self.run, args=[action_entity])
            thread.start()

    def update_action_state(self, action_entity: ActionEntity, new_state: str) -> None:
        """Update action state to new state."""
        action_entity.action_state = new_state

    def run(self, action_entity: ActionEntity) -> None:
        """Run action."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(action_entity.attach_triggered())
        loop.close()
