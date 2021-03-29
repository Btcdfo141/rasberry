"""Trace support for automation."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from homeassistant.components.trace import ActionTrace, async_store_trace
from homeassistant.core import Context

# mypy: allow-untyped-calls, allow-untyped-defs
# mypy: no-check-untyped-defs, no-warn-return-any


class AutomationTrace(ActionTrace):
    """Container for automation trace."""

    def __init__(
        self,
        item_id: str,
        config: dict[str, Any],
        context: Context,
    ):
        """Container for automation trace."""
        key = ("automation", item_id)
        super().__init__(key, config, context)

    def as_short_dict(self) -> dict[str, Any]:
        """Return a brief dictionary version of this AutomationTrace."""

        result = super().as_short_dict()

        trigger = None

        if self._trace and "trigger" in self._trace:
            trigger = (
                self._trace["trigger"][0]
                ._variables.get("trigger", {})
                .get("description")
            )

        result["trigger"] = trigger

        return result


@contextmanager
def trace_automation(hass, automation_id, config, context):
    """Trace action execution of automation with automation_id."""
    trace = AutomationTrace(automation_id, config, context)
    async_store_trace(hass, trace)

    try:
        yield trace
    except Exception as ex:  # pylint: disable=broad-except
        if automation_id:
            trace.set_error(ex)
        raise ex
    finally:
        if automation_id:
            trace.finished()
