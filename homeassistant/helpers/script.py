"""Helpers to execute scripts."""
import asyncio
from contextlib import suppress
from datetime import datetime
from itertools import islice
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import voluptuous as vol

from homeassistant import exceptions
import homeassistant.components.device_automation as device_automation
import homeassistant.components.scene as scene
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_CONDITION,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_TIMEOUT,
    SERVICE_TURN_ON,
)
from homeassistant.core import CALLBACK_TYPE, Context, HomeAssistant, callback
from homeassistant.helpers import (
    condition,
    config_validation as cv,
    service,
    template as template,
)
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_template,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.async_ import run_callback_threadsafe
from homeassistant.util.dt import utcnow

# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

CONF_ALIAS = "alias"
CONF_SERVICE = "service"
CONF_SERVICE_DATA = "data"
CONF_SEQUENCE = "sequence"
CONF_EVENT = "event"
CONF_EVENT_DATA = "event_data"
CONF_EVENT_DATA_TEMPLATE = "event_data_template"
CONF_DELAY = "delay"
CONF_WAIT_TEMPLATE = "wait_template"
CONF_CONTINUE = "continue_on_timeout"
CONF_SCENE = "scene"


ACTION_DELAY = "delay"
ACTION_WAIT_TEMPLATE = "wait_template"
ACTION_CHECK_CONDITION = "condition"
ACTION_FIRE_EVENT = "event"
ACTION_CALL_SERVICE = "call_service"
ACTION_DEVICE_AUTOMATION = "device"
ACTION_ACTIVATE_SCENE = "scene"


SCRIPT_PARALLEL_ALLOW = "allow"
SCRIPT_PARALLEL_ERROR = "error"
SCRIPT_PARALLEL_RESTART = "restart"
SCRIPT_PARALLEL_SKIP = "skip"
SCRIPT_PARALLEL_CHOICES = [
    SCRIPT_PARALLEL_ALLOW,
    SCRIPT_PARALLEL_ERROR,
    SCRIPT_PARALLEL_RESTART,
    SCRIPT_PARALLEL_SKIP,
]


def _determine_action(action):
    """Determine action type."""
    if CONF_DELAY in action:
        return ACTION_DELAY

    if CONF_WAIT_TEMPLATE in action:
        return ACTION_WAIT_TEMPLATE

    if CONF_CONDITION in action:
        return ACTION_CHECK_CONDITION

    if CONF_EVENT in action:
        return ACTION_FIRE_EVENT

    if CONF_DEVICE_ID in action:
        return ACTION_DEVICE_AUTOMATION

    if CONF_SCENE in action:
        return ACTION_ACTIVATE_SCENE

    return ACTION_CALL_SERVICE


def call_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: Optional[Sequence] = None,
    context: Optional[Context] = None,
) -> None:
    """Call a script based on a config entry."""
    Script(hass, cv.SCRIPT_SCHEMA(config)).run(variables, context)


async def async_validate_action_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config."""
    action_type = _determine_action(config)

    if action_type == ACTION_DEVICE_AUTOMATION:
        platform = await device_automation.async_get_device_automation_platform(
            hass, config[CONF_DOMAIN], "action"
        )
        config = platform.ACTION_SCHEMA(config)  # type: ignore
    if action_type == ACTION_CHECK_CONDITION and config[CONF_CONDITION] == "device":
        platform = await device_automation.async_get_device_automation_platform(
            hass, config[CONF_DOMAIN], "condition"
        )
        config = platform.CONDITION_SCHEMA(config)  # type: ignore

    return config


class _StopScript(Exception):
    """Throw if script needs to stop."""


class _SuspendScript(Exception):
    """Throw if script needs to suspend."""


class Script:
    """Representation of a script."""

    def __init__(
        self,
        hass: HomeAssistant,
        sequence: Sequence[Dict[str, Any]],
        name: Optional[str] = None,
        change_listener: Optional[Callable[..., Any]] = None,
        mode: Optional[str] = None,
    ) -> None:
        """Initialize the script."""
        self.hass = hass
        self.sequence = sequence
        template.attach(hass, self.sequence)
        self.name = name
        self._change_listener = change_listener
        self._runs: List[Script._ScriptRun] = []
        self.last_triggered: Optional[datetime] = None
        self.can_cancel = any(
            CONF_DELAY in action or CONF_WAIT_TEMPLATE in action
            for action in self.sequence
        )
        self._config_cache: Dict[Set[Tuple], Callable[..., bool]] = {}
        self._mode = (
            mode
            if mode
            else SCRIPT_PARALLEL_RESTART
            if self.can_cancel
            else SCRIPT_PARALLEL_ALLOW
        )
        self._referenced_entities: Optional[Set[str]] = None
        self._referenced_devices: Optional[Set[str]] = None

    @property
    def last_action(self):
        """Return last action."""
        try:
            return self._runs[0].last_action
        except IndexError:
            return None

    @property
    def is_running(self) -> bool:
        """Return true if script is on."""
        return len(self._runs) > 0

    @property
    def referenced_devices(self):
        """Return a set of referenced devices."""
        if self._referenced_devices is not None:
            return self._referenced_devices

        referenced = set()

        for step in self.sequence:
            action = _determine_action(step)

            if action == ACTION_CHECK_CONDITION:
                referenced |= condition.async_extract_devices(step)

            elif action == ACTION_DEVICE_AUTOMATION:
                referenced.add(step[CONF_DEVICE_ID])

        self._referenced_devices = referenced
        return referenced

    @property
    def referenced_entities(self):
        """Return a set of referenced entities."""
        if self._referenced_entities is not None:
            return self._referenced_entities

        referenced = set()

        for step in self.sequence:
            action = _determine_action(step)

            if action == ACTION_CALL_SERVICE:
                data = step.get(service.CONF_SERVICE_DATA)
                if not data:
                    continue

                entity_ids = data.get(ATTR_ENTITY_ID)

                if entity_ids is None:
                    continue

                if isinstance(entity_ids, str):
                    entity_ids = [entity_ids]

                for entity_id in entity_ids:
                    referenced.add(entity_id)

            elif action == ACTION_CHECK_CONDITION:
                referenced |= condition.async_extract_entities(step)

            elif action == ACTION_ACTIVATE_SCENE:
                referenced.add(step[CONF_SCENE])

        self._referenced_entities = referenced
        return referenced

    def run(self, variables=None, context=None, logger=None, message_base=None):
        """Run script."""
        asyncio.run_coroutine_threadsafe(
            self.async_run(variables, context, logger, message_base), self.hass.loop
        ).result()

    class _ScriptRun:
        def __init__(
            self,
            hass: HomeAssistant,
            parent: "Script",
            variables: Optional[Sequence] = None,
            context: Optional[Context] = None,
            logger: Optional[logging.Logger] = None,
            message_base: Optional[str] = None,
        ) -> None:
            self.hass = hass
            self._parent = parent
            self._variables = variables
            self._context = context
            self._logger = logger or _LOGGER
            self._message_base = message_base or "Error executing script"
            self._actions = {
                ACTION_DELAY: self._async_delay,
                ACTION_WAIT_TEMPLATE: self._async_wait_template,
                ACTION_CHECK_CONDITION: self._async_check_condition,
                ACTION_FIRE_EVENT: self._async_fire_event,
                ACTION_CALL_SERVICE: self._async_call_service,
                ACTION_DEVICE_AUTOMATION: self._async_device_automation,
                ACTION_ACTIVATE_SCENE: self._async_activate_scene,
            }
            self.task: Optional[asyncio.Task] = None
            self.last_action = None
            self._cur = -1
            self._async_listener: List[CALLBACK_TYPE] = []

        async def async_run(self) -> None:
            """Run script."""
            if self._cur == -1:
                self._log("Running script")
                self._cur = 0

            assert not self._async_listener

            for cur, action in islice(
                enumerate(self._parent.sequence), self._cur, None
            ):
                try:
                    await self._handle_action(action)
                except _SuspendScript:
                    # Store next step to take and notify change listeners
                    self.task = None
                    self._cur = cur + 1
                    # pylint: disable=protected-access
                    if self._parent._change_listener:
                        self.hass.async_add_job(self._parent._change_listener)
                    return
                except _StopScript:
                    break
                except Exception as err:
                    self._async_log_exception(cur, action, err)
                    self._async_stop()
                    # Pass exception on.
                    raise

            self._async_stop()
            # pylint: disable=protected-access
            if self._parent._change_listener:
                self.hass.async_add_job(self._parent._change_listener)

        @callback
        def _async_stop(self):
            self._async_remove_listener()
            self._parent._runs.remove(self)  # pylint: disable=protected-access

        @callback
        def async_stop(self):
            """Stop script run."""
            self._async_stop()
            with suppress(AttributeError):
                self.task.cancel()

        @callback
        def _async_log_exception(self, step, action, exception):
            action_type = _determine_action(action)

            error = None
            meth = self._logger.error

            if isinstance(exception, vol.Invalid):
                error_desc = "Invalid data"

            elif isinstance(exception, exceptions.TemplateError):
                error_desc = "Error rendering template"

            elif isinstance(exception, exceptions.Unauthorized):
                error_desc = "Unauthorized"

            elif isinstance(exception, exceptions.ServiceNotFound):
                error_desc = "Service not found"

            else:
                # Print the full stack trace, unknown error
                error_desc = "Unknown error"
                meth = self._logger.exception
                error = ""

            if error is None:
                error = str(exception)

            meth(
                "%s. %s for %s at pos %s: %s",
                self._message_base,
                error_desc,
                action_type,
                step + 1,
                error,
            )

        async def _handle_action(self, action):
            """Handle an action."""
            await self._actions[_determine_action(action)](action)

        async def _async_delay(self, action):
            """Handle delay."""
            # Call ourselves in the future to continue work
            unsub = None

            @callback
            def async_script_delay(now):
                """Handle delay."""
                with suppress(ValueError):
                    self._async_listener.remove(unsub)
                self.task = self.hass.async_create_task(self.async_run())

            delay = action[CONF_DELAY]

            try:
                if isinstance(delay, template.Template):
                    delay = vol.All(cv.time_period, cv.positive_timedelta)(
                        delay.async_render(self._variables)
                    )
                elif isinstance(delay, dict):
                    delay_data = {}
                    delay_data.update(template.render_complex(delay, self._variables))
                    delay = cv.time_period(delay_data)
            except (exceptions.TemplateError, vol.Invalid) as ex:
                _LOGGER.error(
                    "Error rendering '%s' delay template: %s", self._parent.name, ex
                )
                raise _StopScript

            self.last_action = action.get(CONF_ALIAS, f"delay {delay}")
            self._log("Executing step %s" % self.last_action)

            unsub = async_track_point_in_utc_time(
                self.hass, async_script_delay, utcnow() + delay
            )
            self._async_listener.append(unsub)
            raise _SuspendScript

        async def _async_wait_template(self, action):
            """Handle a wait template."""
            # Call ourselves in the future to continue work
            wait_template = action[CONF_WAIT_TEMPLATE]
            wait_template.hass = self.hass

            self.last_action = action.get(CONF_ALIAS, "wait template")
            self._log("Executing step %s" % self.last_action)

            # check if condition already okay
            if condition.async_template(self.hass, wait_template, self._variables):
                return

            @callback
            def async_script_wait(entity_id, from_s, to_s):
                """Handle script after template condition is true."""
                self._async_remove_listener()
                self.task = self.hass.async_create_task(self.async_run())

            self._async_listener.append(
                async_track_template(
                    self.hass, wait_template, async_script_wait, self._variables
                )
            )

            if CONF_TIMEOUT in action:
                self._async_set_timeout(action)

            raise _SuspendScript

        async def _async_call_service(self, action):
            """Call the service specified in the action."""
            self.last_action = action.get(CONF_ALIAS, "call service")
            self._log("Executing step %s" % self.last_action)
            await service.async_call_from_config(
                self.hass,
                action,
                blocking=True,
                variables=self._variables,
                validate_config=False,
                context=self._context,
            )

        async def _async_device_automation(self, action):
            """Perform the device automation specified in the action."""
            self.last_action = action.get(CONF_ALIAS, "device automation")
            self._log("Executing step %s" % self.last_action)
            platform = await device_automation.async_get_device_automation_platform(
                self.hass, action[CONF_DOMAIN], "action"
            )
            await platform.async_call_action_from_config(
                self.hass, action, self._variables, self._context
            )

        async def _async_activate_scene(self, action):
            """Activate the scene specified in the action."""
            self.last_action = action.get(CONF_ALIAS, "activate scene")
            self._log("Executing step %s" % self.last_action)
            await self.hass.services.async_call(
                scene.DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: action[CONF_SCENE]},
                blocking=True,
                context=self._context,
            )

        async def _async_fire_event(self, action):
            """Fire an event."""
            self.last_action = action.get(CONF_ALIAS, action[CONF_EVENT])
            self._log("Executing step %s" % self.last_action)
            event_data = dict(action.get(CONF_EVENT_DATA, {}))
            if CONF_EVENT_DATA_TEMPLATE in action:
                try:
                    event_data.update(
                        template.render_complex(
                            action[CONF_EVENT_DATA_TEMPLATE], self._variables
                        )
                    )
                except exceptions.TemplateError as ex:
                    _LOGGER.error("Error rendering event data template: %s", ex)

            self.hass.bus.async_fire(
                action[CONF_EVENT], event_data, context=self._context
            )

        async def _async_check_condition(self, action):
            """Test if condition is matching."""
            config_cache_key = frozenset((k, str(v)) for k, v in action.items())
            # pylint: disable=protected-access
            config = self._parent._config_cache.get(config_cache_key)
            if not config:
                config = await condition.async_from_config(self.hass, action, False)
                self._parent._config_cache[config_cache_key] = config

            self.last_action = action.get(CONF_ALIAS, action[CONF_CONDITION])
            check = config(self.hass, self._variables)
            self._log(f"Test condition {self.last_action}: {check}")

            if not check:
                raise _StopScript

        def _async_set_timeout(self, action):
            """Schedule a timeout to abort or continue script."""
            timeout = action[CONF_TIMEOUT]
            unsub = None

            @callback
            def async_script_timeout(now):
                """Call after timeout is retrieve."""
                with suppress(ValueError):
                    self._async_listener.remove(unsub)
                self._async_remove_listener()

                # Check if we want to continue to execute
                # the script after the timeout
                if action.get(CONF_CONTINUE, True):
                    self.task = self.hass.async_create_task(self.async_run())
                else:
                    self._log("Timeout reached, abort script.")
                    self._async_stop()

            unsub = async_track_point_in_utc_time(
                self.hass, async_script_timeout, utcnow() + timeout
            )
            self._async_listener.append(unsub)

        def _async_remove_listener(self):
            """Remove listeners, if any."""
            for unsub in self._async_listener:
                unsub()
            self._async_listener.clear()

        def _log(self, msg):
            """Logger helper."""
            if self._parent.name is not None:
                msg = f"Script {self._parent.name}: {msg}"

            _LOGGER.info(msg)

    async def async_run(
        self,
        variables: Optional[Sequence] = None,
        context: Optional[Context] = None,
        logger: Optional[logging.Logger] = None,
        message_base: Optional[str] = None,
    ) -> None:
        """Run script."""
        if self.is_running:
            if self._mode == SCRIPT_PARALLEL_SKIP:
                self._log("Skipping script")
                return
            if self._mode == SCRIPT_PARALLEL_ERROR:
                if logger:
                    logger.error("%s. Already running", message_base)
                raise exceptions.HomeAssistantError(
                    f"{self.name if self.name else 'Script'} already running"
                )
            if self._mode == SCRIPT_PARALLEL_RESTART:
                self._log("Restarting script")
                self.async_stop()

        self.last_triggered = utcnow()
        run = Script._ScriptRun(
            self.hass, self, variables, context, logger, message_base
        )
        self._runs.append(run)
        run.task = self.hass.async_create_task(run.async_run())
        await run.task

    def stop(self) -> None:
        """Stop running script."""
        run_callback_threadsafe(self.hass.loop, self.async_stop).result()

    @callback
    def async_stop(self) -> None:
        """Stop running script."""
        if not self.is_running:
            return
        for run in self._runs:
            run.async_stop()
        if self._change_listener:
            self.hass.async_add_job(self._change_listener)

    def _log(self, msg):
        """Logger helper."""
        if self.name is not None:
            msg = f"Script {self.name}: {msg}"

        _LOGGER.info(msg)
