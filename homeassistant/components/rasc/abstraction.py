"""The rasc abstraction."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import datetime
from datetime import timedelta
import json
import time
from typing import TYPE_CHECKING, Any, TypeVar, cast

from homeassistant.components import notify
from homeassistant.const import (
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_EVENT,
    CONF_SERVICE,
    CONF_SERVICE_DATA,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    HassJobType,
    HomeAssistant,
    Service,
    ServiceCall,
    ServiceResponse,
    callback,
)
from homeassistant.helpers.dynamic_polling import get_best_distribution, get_polls
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import device_entities
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from .const import (
    CHANGE_TIMEOUT,
    DEFAULT_FAILURE_TIMEOUT,
    LOGGER,
    RASC_ACK,
    RASC_COMPLETE,
    RASC_START,
)
from .helpers import fire

_R = TypeVar("_R")


class RASCAbstraction:
    """RASC Component."""

    def __init__(self, logger, domain, hass: HomeAssistant) -> None:
        """Initialize an rasc entity."""
        self.logger = logger
        self.domain = domain
        self.hass = hass
        self._store = RASCStore(self.hass)
        self._states: dict[str, RASCState] = {}

    def _get_entity_ids(self, service_call: ServiceCall):
        entities: list[str] = []
        if ATTR_DEVICE_ID in service_call.data:
            entities += [
                entity
                for _device_id in service_call.data[ATTR_DEVICE_ID]
                for entity in device_entities(self.hass, _device_id)
            ]
        if ATTR_ENTITY_ID in service_call.data:
            if isinstance(service_call.data[ATTR_ENTITY_ID], str):
                entities += [service_call.data[ATTR_ENTITY_ID]]
            else:
                entities += service_call.data[ATTR_ENTITY_ID]
        return entities

    def _track_service(self, context: Context, service_call: ServiceCall):
        component = self.hass.data.get(service_call.domain)
        if not component or not hasattr(component, "async_get_platforms"):
            return
        entity_ids = self._get_entity_ids(service_call)
        platforms = component.async_get_platforms(entity_ids)
        for platform, entities in platforms:
            for entity in entities:
                self._states[entity.entity_id].start_tracking(platform)

    def _init_states(self, context: Context, service_call: ServiceCall):
        component = self.hass.data.get(service_call.domain)
        if not component or not hasattr(component, "async_get_platforms"):
            return
        entity_ids = self._get_entity_ids(service_call)
        platforms = component.async_get_platforms(entity_ids)
        for _, entities in platforms:
            for entity in entities:
                self._states[entity.entity_id] = self._get_rasc_state(
                    context, entity, service_call
                )

    def _get_rasc_state(
        self, context: Context, entity: Entity, service_call: ServiceCall
    ) -> RASCState:
        """Get RASC state on the given Event e."""
        params = {
            CONF_SERVICE: service_call.service,
            CONF_SERVICE_DATA: service_call.data,
        }
        start_state = (
            entity.async_get_action_target_state({CONF_EVENT: RASC_START, **params})
        ) or {}
        complete_state = (
            entity.async_get_action_target_state({CONF_EVENT: RASC_COMPLETE, **params})
        ) or {}
        return RASCState(
            self.hass,
            context,
            entity,
            service_call,
            start_state,
            complete_state,
            self._store,
        )

    async def _prepare_ack(
        self, context: Context, handler: Service, service_call: ServiceCall
    ) -> ServiceResponse:
        entity_ids = self._get_entity_ids(service_call)

        response: ServiceResponse = None
        job = handler.job
        target = job.target
        if job.job_type == HassJobType.Coroutinefunction:
            if TYPE_CHECKING:
                target = cast(Callable[..., Coroutine[Any, Any, _R]], target)
            response = await target(service_call)
        elif job.job_type == HassJobType.Callback:
            if TYPE_CHECKING:
                target = cast(Callable[..., _R], target)
            response = target(service_call)
        else:
            if TYPE_CHECKING:
                target = cast(Callable[..., _R], target)
            response = await self.hass.async_add_executor_job(target, service_call)

        # TODO: track entities independently (service._handle_entity_call) # pylint: disable=fixme
        # start tracking after receiving ack
        for entity_id in entity_ids:
            fire(
                self.hass,
                RASC_ACK,
                entity_id,
                service_call.service,
                LOGGER,
                service_call.data,
            )
        self._track_service(context, service_call)
        return response

    async def _prepare_start(
        self, context: Context, service_call: ServiceCall
    ) -> ServiceResponse:
        entity_ids = self._get_entity_ids(service_call)

        def check_started() -> bool:
            for entity_id in entity_ids:
                if (
                    not self._states[entity_id].started
                    and not self._states[entity_id].failed
                ):
                    return False
            return True

        async with context.cv:
            await context.cv.wait_for(check_started)
            context.cv.notify_all()
            if any(not self._states[entity_id].started for entity_id in entity_ids):
                raise ServiceFailureError("Service failed before started")
            return entity_ids

    async def _prepare_compl(
        self, context: Context, service_call: ServiceCall
    ) -> ServiceResponse:
        entity_ids = self._get_entity_ids(service_call)

        def check_completed() -> bool:
            for entity_id in entity_ids:
                if (
                    not self._states[entity_id].completed
                    and not self._states[entity_id].failed
                ):
                    return False
            return True

        async with context.cv:
            await context.cv.wait_for(check_completed)
            context.cv.notify_all()
            if any(not self._states[entity_id].completed for entity_id in entity_ids):
                raise ServiceFailureError("Service failed before completed")
            return entity_ids

    async def _failure_handler(
        self, context: Context, service_call: ServiceCall
    ) -> None:
        entity_ids = self._get_entity_ids(service_call)

        async with context.cv:
            await context.cv.wait_for(
                lambda: all(
                    self._states[entity_id].failed or self._states[entity_id].completed
                    for entity_id in entity_ids
                )
            )
            context.cv.notify_all()

            successful_actions = []
            failed_actions = []
            for entity_id in entity_ids:
                if self._states[entity_id].failed:
                    failed_actions.append(entity_id)
                else:
                    successful_actions.append(entity_id)
                del self._states[entity_id]
            message = {
                "action": service_call.service,
                "successful": successful_actions,
                "failed": failed_actions,
            }
            if failed_actions:
                # prevent infinite recursion
                if service_call.domain != notify.DOMAIN:
                    notification = {
                        "message": json.dumps(message, indent=2),
                        "title": "Action Failed",
                    }
                    await self.hass.services.async_call(
                        notify.DOMAIN,
                        notify.SERVICE_PERSISTENT_NOTIFICATION,
                        notification,
                    )

    async def async_load(self) -> None:
        """Load persistent store."""
        await self._store.async_load()

    @callback
    async def async_on_push_event(self, entity: Entity) -> None:
        """Handle update event from push-based entity."""
        rasc_state = self._states.get(entity.entity_id)
        if not rasc_state:
            return
        if rasc_state.completed or rasc_state.failed:
            return
        await rasc_state.update()

    def execute_service(
        self, handler: Service, service_call: ServiceCall
    ) -> tuple[
        asyncio.Task[ServiceResponse],
        asyncio.Task[ServiceResponse],
        asyncio.Task[ServiceResponse],
    ]:
        """Execute a service."""

        # for response wait-notify
        context = Context()

        # init states for entities
        self._init_states(context, service_call)

        # create async task for A, S, C
        ack_task = self.hass.async_create_task(
            self._prepare_ack(context, handler, service_call)
        )
        start_task = self.hass.async_create_task(
            self._prepare_start(context, service_call)
        )
        compl_task = self.hass.async_create_task(
            self._prepare_compl(context, service_call)
        )

        # failure detection task
        self.hass.async_create_task(self._failure_handler(context, service_call))

        return (ack_task, start_task, compl_task)


class StateDetector:
    """RASC State Detector."""

    def __init__(self, history: list[float] | None) -> None:
        """Init State Detector."""
        super().__init__()
        # no history is found, polling statically
        if history is None or len(history) == 0:
            self._static = True
            # TODO: upper bound shouldn't be None # pylint: disable=fixme
            self._attr_upper_bound = None
            return
        self._static = False
        self._cur_poll = 0
        # only one data in history, poll exactly on that moment
        if len(history) == 1:
            self._polls = [history[0]]
            # TODO: upper bound shouldn't be None # pylint: disable=fixme
            self._attr_upper_bound = None
            return
        # TODO: put this in bg # pylint: disable=fixme
        dist = get_best_distribution(history)
        self._attr_upper_bound = dist.ppf(0.99)
        self._polls = get_polls(dist, self._attr_upper_bound)

    @property
    def upper_bound(self) -> float | None:
        """Return upper bound."""
        return self._attr_upper_bound

    def next_interval(self) -> timedelta:
        """Get next interval."""
        if self._static:
            return timedelta(seconds=1)
        if self._cur_poll < len(self._polls):
            cur = self._cur_poll
            self._cur_poll += 1
            return timedelta(seconds=self._polls[cur])
        return timedelta(seconds=1)


class RASCHistory:
    """RASC History."""

    def __init__(
        self,
        st_history: list[float] | None = None,
        ct_history: list[float] | None = None,
    ) -> None:
        """Init History."""
        self.st_history = st_history or []
        self.ct_history = ct_history or []

    def append_s(self, start_time: float) -> None:
        """Append start time to history."""
        self.st_history.append(start_time)

    def append_c(self, complete_time: float) -> None:
        """Append complete time to history."""
        self.ct_history.append(complete_time)


class RASCState:
    """RASC State."""

    def __init__(
        self,
        hass: HomeAssistant,
        context: Context,
        entity: Entity,
        service_call: ServiceCall,
        start_state: dict[str, Any],
        complete_state: dict[str, Any],
        store: RASCStore,
    ) -> None:
        """Init rasc state."""
        self.hass = hass
        self._start_state = start_state
        self._complete_state = complete_state
        self._transition = service_call.data.get("transition", 0)
        self._service_call = service_call
        self._entity = entity
        self._attr_failed = False
        self._attr_started = False
        self._attr_completed = False
        self._context = context
        self._store = store
        self._next_response = RASC_ACK
        # tracking
        self._tracking_task: asyncio.Task[Any] | None = None
        self._s_detector: StateDetector | None = None
        self._c_detector: StateDetector | None = None
        self._exec_time: float | None = None
        # polling component
        self._platform: EntityPlatform | DataUpdateCoordinator | None = None
        # failure detection
        self._last_changed: datetime.datetime | None = None
        self._checking_failure = False
        self._check_listener: CALLBACK_TYPE | None = None
        self._current_state = entity.__dict__

    @property
    def time_elapsed(self) -> float:
        """Return the elapsed time since started."""
        if not self._exec_time:
            return 0
        return time.time() - self._exec_time

    @property
    def failed(self) -> bool:
        """Return if the action has failed."""
        return self._attr_failed

    @property
    def started(self) -> bool:
        """Return if the action has started."""
        return self._attr_started

    @property
    def completed(self) -> bool:
        """Return if the action has completed."""
        return self._attr_completed

    async def _track(self) -> None:
        if not self._platform:
            return
        # let platform state polling the state
        next_interval = self._get_polling_interval()
        await self._platform.track_entity_state(self._entity, next_interval)
        await self.update()

        if self.completed or self.failed:
            return

        await self._track()

    async def _check_failure(self, _: datetime.datetime) -> None:
        self._checking_failure = True
        self._last_changed = dt_util.utcnow()

        if self._check_listener:
            self._check_listener()
        self._check_listener = async_track_point_in_time(
            self.hass,
            self._check_no_progress,
            dt_util.utcnow() + timedelta(seconds=CHANGE_TIMEOUT),
        )

    async def _check_no_progress(self, now: datetime.datetime):
        if self.completed:
            return
        if not self._last_changed:
            return
        if (now - self._last_changed).total_seconds() > CHANGE_TIMEOUT:
            await self.set_failed()

    def _match_target_state(self, target_state: dict[str, Any]) -> bool:
        matched = True
        if not target_state:
            raise ValueError("no entry in rules.")

        for attr, match in target_state.items():
            entity_attr = getattr(self._entity, attr)
            if entity_attr is None:
                LOGGER.warning(
                    "Entity %s does not have attribute %s", self._entity.entity_id, attr
                )
                continue
            if not match(entity_attr):
                matched = False
                break
        return matched

    def _update_current_state(self) -> None:
        for attr in self._complete_state:
            curr_value = getattr(self._entity, attr)
            prev_value = self._current_state.get(attr)
            if curr_value is None:
                LOGGER.warning(
                    "Entity %s does not have attribute %s", self._entity.entity_id, attr
                )
                continue
            if curr_value != prev_value:
                self._last_changed = dt_util.utcnow()
                self._current_state[attr] = curr_value
                if self._checking_failure:
                    if self._check_listener:
                        self._check_listener()
                    self._check_listener = async_track_point_in_time(
                        self.hass,
                        self._check_no_progress,
                        self._last_changed + timedelta(seconds=CHANGE_TIMEOUT),
                    )

    def _update_store(self, tts: bool = False, ttc: bool = False):
        key = ",".join(
            (self._entity.entity_id, self._service_call.service, str(self._transition))
        )
        histories = self._store.histories
        if key not in histories:
            histories[key] = RASCHistory()

        if tts:
            histories[key].append_s(self.time_elapsed)
        if ttc:
            histories[key].append_c(self.time_elapsed)

        self.hass.loop.create_task(self._store.async_save())

    def _get_polling_interval(self) -> timedelta:
        """Get polling interval."""
        if self._next_response == RASC_START:
            if not self._s_detector:
                return timedelta(seconds=1)
            return self._s_detector.next_interval()
        if self._next_response == RASC_COMPLETE:
            if not self._c_detector:
                return timedelta(seconds=1)
            return self._c_detector.next_interval()
        return timedelta(seconds=1)

    @callback
    async def update(self) -> None:
        """Handle callback function after polling."""
        entity_id = self._entity.entity_id
        action = self._service_call.service
        # check complete state
        complete_state_matched = self._match_target_state(self._complete_state)
        # prevent hazardous changes
        transition = self._transition
        if complete_state_matched and (
            transition is None or self.time_elapsed > transition / 2
        ):
            # fire start response if haven't
            if not self.started:
                await self.set_started()
                self._update_store(tts=True)
                fire(
                    self.hass,
                    RASC_START,
                    entity_id,
                    action,
                    LOGGER,
                    self._service_call.data,
                )

            await self.set_completed()
            self._update_store(ttc=True)
            fire(
                self.hass,
                RASC_COMPLETE,
                entity_id,
                action,
                LOGGER,
                self._service_call.data,
            )
            # cancel failure checker
            if self._check_listener:
                self._check_listener()

            return

        start_state_matched = self._match_target_state(self._start_state)
        if start_state_matched and not self.started:
            fire(
                self.hass,
                RASC_START,
                entity_id,
                action,
                LOGGER,
                self._service_call.data,
            )
            await self.set_started()
            self._update_store(tts=True)

        # update _last_changed
        self._update_current_state()

    def start_tracking(self, platform: EntityPlatform | DataUpdateCoordinator) -> None:
        """Start tracking the state."""
        self._next_response = RASC_START
        self._exec_time = time.time()
        coordinator: DataUpdateCoordinator | None = getattr(
            self._entity, "coordinator", None
        )
        # push-based devices dont need adaptive polling
        if not self._entity.should_poll and not coordinator:
            return

        if coordinator:
            self._platform = coordinator
        else:
            self._platform = platform
        # retrieve history by key
        key = ",".join(
            (self._entity.entity_id, self._service_call.service, str(self._transition))
        )
        history = self._store.histories.get(key, RASCHistory())
        self._s_detector = StateDetector(history.st_history)
        self._c_detector = StateDetector(history.ct_history)
        # fire failure if exceed upper_bound
        if self._s_detector.upper_bound and self._c_detector.upper_bound:
            upper_bound = self._s_detector.upper_bound + self._c_detector.upper_bound
        else:
            upper_bound = DEFAULT_FAILURE_TIMEOUT
        async_track_point_in_time(
            self.hass,
            self._check_failure,
            dt_util.utcnow() + timedelta(seconds=upper_bound),
        )

        self._tracking_task = self.hass.async_create_task(self._track())

    async def set_failed(self):
        """Set failed."""
        if self._tracking_task:
            self._tracking_task.cancel()
            self._tracking_task = None
        self._attr_failed = True
        async with self._context.cv:
            self._context.cv.notify_all()

    async def set_started(self):
        """Set started."""
        self._exec_time = time.time()
        self._attr_started = True
        self._next_response = RASC_COMPLETE
        async with self._context.cv:
            self._context.cv.notify_all()

    async def set_completed(self):
        """Set completed."""
        if not self._attr_started:
            self._attr_started = True
        self._attr_completed = True
        self._next_response = None
        async with self._context.cv:
            self._context.cv.notify_all()


class RASCStore:
    """RASC perminent store."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize a new config object."""
        self.hass = hass

        self.histories: dict[str, RASCHistory] = {}
        self._store = self._ConfigStore(hass)
        self._init_lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load stored data."""
        async with self._init_lock:
            if (data := await self._store.async_load()) is None:
                data = cast(dict[str, dict[str, dict[str, list[float]]]], {})

            self.histories = {
                key: RASCHistory(**hist)
                for key, hist in data.get("history", {}).items()
            }

    async def async_save(self) -> None:
        """Store data."""
        await self._store.async_save(
            {
                "history": {
                    key: {
                        "st_history": hist.st_history,
                        "ct_history": hist.ct_history,
                    }
                    for key, hist in self.histories.items()
                }
            }
        )

    class _ConfigStore(Store[dict[str, dict[str, dict[str, list[float]]]]]):
        def __init__(self, hass: HomeAssistant) -> None:
            """Initialize storage class."""
            super().__init__(
                hass,
                1,
                "rasc",
                private=True,
                atomic_writes=True,
            )


class Context:
    """RASC Context."""

    def __init__(self) -> None:
        """Initialize context."""
        self.cv = asyncio.Condition()


class ServiceFailureError(Exception):
    """RASC failure error."""

    def __init__(self, message):
        """Initialize error."""
        super().__init__(message)
