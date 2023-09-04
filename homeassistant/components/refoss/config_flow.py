"""ConfigFlow for Refoss."""

from __future__ import annotations

from typing import Any

from refoss_ha.util import get_mac_address

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_MAC
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class RefossConfigFlow(ConfigFlow, domain=DOMAIN):
    """RefossConfigFlow for Refoss."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """async_step_user for Refoss."""
        mac = get_mac_address()

        entry = await self.async_set_unique_id(mac)

        data = {
            CONF_MAC: mac,
        }

        if entry is not None:
            self._abort_if_unique_id_configured(updates=data, reload_on_update=True)

        return self.async_create_entry(title="Refoss", data=data)
