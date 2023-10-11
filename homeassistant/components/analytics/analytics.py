"""Analytics helper class for the analytics integration."""
from __future__ import annotations

import asyncio
from asyncio import timeout
from dataclasses import asdict as dataclass_asdict, dataclass
from datetime import datetime
from typing import Any
import uuid

import aiohttp

from homeassistant.components import hassio
from homeassistant.components.api import ATTR_INSTALLATION_TYPE
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.energy import (
    DOMAIN as ENERGY_DOMAIN,
    is_configured as energy_is_configured,
)
from homeassistant.components.recorder import (
    DOMAIN as RECORDER_DOMAIN,
    get_instance as get_recorder_instance,
)
import homeassistant.config as conf_util
from homeassistant.config_entries import SOURCE_IGNORE
from homeassistant.const import ATTR_DOMAIN, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.system_info import async_get_system_info
from homeassistant.loader import (
    Integration,
    IntegrationNotFound,
    async_get_integrations,
)
from homeassistant.setup import async_get_loaded_integrations

from .const import (
    ANALYTICS_ENDPOINT_URL,
    ANALYTICS_ENDPOINT_URL_DEV,
    ATTR_ADDON_COUNT,
    ATTR_ADDONS,
    ATTR_ARCH,
    ATTR_AUTO_UPDATE,
    ATTR_AUTOMATION_COUNT,
    ATTR_BASE,
    ATTR_BOARD,
    ATTR_CERTIFICATE,
    ATTR_CONFIGURED,
    ATTR_CUSTOM_INTEGRATIONS,
    ATTR_DIAGNOSTICS,
    ATTR_ENERGY,
    ATTR_ENGINE,
    ATTR_HEALTHY,
    ATTR_INTEGRATION_COUNT,
    ATTR_INTEGRATIONS,
    ATTR_OPERATING_SYSTEM,
    ATTR_PROTECTED,
    ATTR_RECORDER,
    ATTR_SLUG,
    ATTR_STATE_COUNT,
    ATTR_STATISTICS,
    ATTR_SUPERVISOR,
    ATTR_SUPPORTED,
    ATTR_USAGE,
    ATTR_USER_COUNT,
    ATTR_UUID,
    ATTR_VERSION,
    LOGGER,
    PREFERENCE_SCHEMA,
    STORAGE_KEY,
    STORAGE_VERSION,
)


@dataclass
class AnalyticsData:
    """Analytics data."""

    onboarded: bool
    preferences: dict[str, bool]
    uuid: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalyticsData:
        """Initialize analytics data from a dict."""
        return cls(
            data["onboarded"],
            data["preferences"],
            data["uuid"],
        )


class Analytics:
    """Analytics helper class for the analytics integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Analytics class."""
        self.hass: HomeAssistant = hass
        self.session = async_get_clientsession(hass)
        self._data = AnalyticsData(False, {}, None)
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)

    @property
    def preferences(self) -> dict:
        """Return the current active preferences."""
        preferences = self._data.preferences
        return {
            ATTR_BASE: preferences.get(ATTR_BASE, False),
            ATTR_DIAGNOSTICS: preferences.get(ATTR_DIAGNOSTICS, False),
            ATTR_USAGE: preferences.get(ATTR_USAGE, False),
            ATTR_STATISTICS: preferences.get(ATTR_STATISTICS, False),
        }

    @property
    def onboarded(self) -> bool:
        """Return bool if the user has made a choice."""
        return self._data.onboarded

    @property
    def uuid(self) -> str | None:
        """Return the uuid for the analytics integration."""
        return self._data.uuid

    @property
    def endpoint(self) -> str:
        """Return the endpoint that will receive the payload."""
        if HA_VERSION.endswith("0.dev0"):
            # dev installations will contact the dev analytics environment
            return ANALYTICS_ENDPOINT_URL_DEV
        return ANALYTICS_ENDPOINT_URL

    @property
    def supervisor(self) -> bool:
        """Return bool if a supervisor is present."""
        return hassio.is_hassio(self.hass)

    async def load(self) -> None:
        """Load preferences."""
        stored = await self._store.async_load()
        if stored:
            self._data = AnalyticsData.from_dict(stored)

        if (
            self.supervisor
            and (supervisor_info := hassio.get_supervisor_info(self.hass)) is not None
            and not self.onboarded
        ):
            # User have not configured analytics, get this setting from the supervisor
            if supervisor_info[ATTR_DIAGNOSTICS] and not self.preferences.get(
                ATTR_DIAGNOSTICS, False
            ):
                self._data.preferences[ATTR_DIAGNOSTICS] = True
            elif not supervisor_info[ATTR_DIAGNOSTICS] and self.preferences.get(
                ATTR_DIAGNOSTICS, False
            ):
                self._data.preferences[ATTR_DIAGNOSTICS] = False

    async def save_preferences(self, preferences: dict) -> None:
        """Save preferences."""
        preferences = PREFERENCE_SCHEMA(preferences)
        self._data.preferences.update(preferences)
        self._data.onboarded = True

        await self._store.async_save(dataclass_asdict(self._data))

        if self.supervisor:
            await hassio.async_update_diagnostics(
                self.hass, self.preferences.get(ATTR_DIAGNOSTICS, False)
            )

    def should_send_analytics(self) -> bool:
        if not self.onboarded or not self.preferences.get(ATTR_BASE, False):
            LOGGER.debug("Nothing to submit")
            return False
        return True

    async def gather_analytics_info(self):
        supervisor_info = None
        operating_system_info: dict[str, Any] = {}

        if self.supervisor:
            supervisor_info = hassio.get_supervisor_info(self.hass)
            operating_system_info = hassio.get_os_info(self.hass) or {}

        system_info = await async_get_system_info(self.hass)
        return system_info, supervisor_info, operating_system_info

    async def send_payload(self, payload):
        try:
            async with timeout(30):
                response = await self.session.post(self.endpoint, json=payload)
                if response.status == 200:
                    LOGGER.info(
                        (
                            "Submitted analytics to Home Assistant servers. "
                            "Information submitted includes %s"
                        ),
                        payload,
                    )
                else:
                    LOGGER.warning(
                        "Sending analytics failed with statuscode %s from %s",
                        response.status,
                        self.endpoint,
                    )
        except asyncio.TimeoutError:
            LOGGER.error("Timeout sending analytics to %s", ANALYTICS_ENDPOINT_URL)
        except aiohttp.ClientError as err:
            LOGGER.error(
                "Error sending analytics to %s: %r", ANALYTICS_ENDPOINT_URL, err
            )

    def prepare_payload(self, system_info, supervisor_info, operating_system_info):
        payload: dict = {
            ATTR_UUID: self.uuid,
            ATTR_VERSION: HA_VERSION,
            ATTR_INSTALLATION_TYPE: system_info[ATTR_INSTALLATION_TYPE],
        }

        if supervisor_info is not None:
            payload.update(self._get_supervisor_payload(supervisor_info))

        if operating_system_info.get(ATTR_BOARD) is not None:
            payload[ATTR_OPERATING_SYSTEM] = {
                ATTR_BOARD: operating_system_info[ATTR_BOARD],
                ATTR_VERSION: operating_system_info[ATTR_VERSION],
            }

        return payload

    def _get_supervisor_payload(self, supervisor_info):
        return {
            ATTR_SUPERVISOR: {
                ATTR_HEALTHY: supervisor_info[ATTR_HEALTHY],
                ATTR_SUPPORTED: supervisor_info[ATTR_SUPPORTED],
                ATTR_ARCH: supervisor_info[ATTR_ARCH],
            }
        }

    async def send_analytics(self, _: datetime | None = None) -> None:
        """Send analytics."""

        if not self.should_send_analytics():
            return

        if self._data.uuid is None:
            self._data.uuid = uuid.uuid4().hex
            await self._store.async_save(dataclass_asdict(self._data))

        (
            system_info,
            supervisor_info,
            operating_system_info,
        ) = await self.gather_analytics_info()

        integrations = []
        custom_integrations = []
        addons = []

        payload = self.prepare_payload(
            system_info, supervisor_info, operating_system_info
        )

        if self.preferences.get(ATTR_USAGE, False) or self.preferences.get(
            ATTR_STATISTICS, False
        ):
            ent_reg = er.async_get(self.hass)
            yaml_configuration = await self.get_yaml_configuration()
            if yaml_configuration is None:
                return

            configuration_set = set(yaml_configuration)
            er_platforms = {
                entity.platform
                for entity in ent_reg.entities.values()
                if not entity.disabled
            }

            domains = async_get_loaded_integrations(self.hass)
            configured_integrations = await async_get_integrations(self.hass, domains)
            enabled_domains = set(configured_integrations)

            for integration in configured_integrations.values():
                if isinstance(integration, IntegrationNotFound):
                    continue

                if isinstance(integration, BaseException):
                    raise integration

                if not self._async_should_report_integration(
                    integration=integration,
                    yaml_domains=configuration_set,
                    entity_registry_platforms=er_platforms,
                ):
                    continue

                if not integration.is_built_in:
                    custom_integrations.append(
                        {
                            ATTR_DOMAIN: integration.domain,
                            ATTR_VERSION: integration.version,
                        }
                    )
                    continue

                integrations.append(integration.domain)

            if supervisor_info is not None:
                installed_addons = await asyncio.gather(
                    *(
                        hassio.async_get_addon_info(self.hass, addon[ATTR_SLUG])
                        for addon in supervisor_info[ATTR_ADDONS]
                    )
                )
                for addon in installed_addons:
                    addons.append(
                        {
                            ATTR_SLUG: addon[ATTR_SLUG],
                            ATTR_PROTECTED: addon[ATTR_PROTECTED],
                            ATTR_VERSION: addon[ATTR_VERSION],
                            ATTR_AUTO_UPDATE: addon[ATTR_AUTO_UPDATE],
                        }
                    )
        if self.preferences.get(ATTR_USAGE, False):
            payload = await self.get_usage_payload(
                supervisor_info,
                integrations,
                custom_integrations,
                addons,
                enabled_domains,
                payload,
            )

        if self.preferences.get(ATTR_STATISTICS, False):
            payload = await self.get_statistics_payload(
                supervisor_info, integrations, addons, payload
            )

        await self.send_payload(payload)

    async def get_yaml_configuration(self):
        try:
            return await conf_util.async_hass_config_yaml(self.hass)
        except HomeAssistantError as err:
            LOGGER.error(err)
            return None

    async def get_usage_payload(
        self,
        supervisor_info,
        integrations,
        custom_integrations,
        addons,
        enabled_domains,
        payload,
    ):
        payload[ATTR_CERTIFICATE] = self.hass.http.ssl_certificate is not None
        payload[ATTR_INTEGRATIONS] = integrations
        payload[ATTR_CUSTOM_INTEGRATIONS] = custom_integrations

        if supervisor_info is not None:
            payload[ATTR_ADDONS] = addons

        if ENERGY_DOMAIN in enabled_domains:
            payload[ATTR_ENERGY] = {
                ATTR_CONFIGURED: await energy_is_configured(self.hass)
            }

        if RECORDER_DOMAIN in enabled_domains:
            instance = get_recorder_instance(self.hass)
            engine = instance.database_engine
            if engine and engine.version is not None:
                payload[ATTR_RECORDER] = {
                    ATTR_ENGINE: engine.dialect.value,
                    ATTR_VERSION: engine.version,
                }

        return payload

    async def get_statistics_payload(
        self, supervisor_info, integrations, addons, payload
    ):
        payload[ATTR_STATE_COUNT] = len(self.hass.states.async_all())
        payload[ATTR_AUTOMATION_COUNT] = len(
            self.hass.states.async_all(AUTOMATION_DOMAIN)
        )
        payload[ATTR_INTEGRATION_COUNT] = len(integrations)

        if supervisor_info is not None:
            payload[ATTR_ADDON_COUNT] = len(addons)

        payload[ATTR_USER_COUNT] = len(
            [
                user
                for user in await self.hass.auth.async_get_users()
                if not user.system_generated
            ]
        )

        return payload

    @callback
    def _async_should_report_integration(
        self,
        integration: Integration,
        yaml_domains: set[str],
        entity_registry_platforms: set[str],
    ) -> bool:
        """Return a bool to indicate if this integration should be reported."""
        if integration.disabled:
            return False

        # Check if the integration is defined in YAML or in the entity registry
        if (
            integration.domain in yaml_domains
            or integration.domain in entity_registry_platforms
        ):
            return True

        # Check if the integration provide a config flow
        if not integration.config_flow:
            return False

        entries = self.hass.config_entries.async_entries(integration.domain)

        # Filter out ignored and disabled entries
        return any(
            entry
            for entry in entries
            if entry.source != SOURCE_IGNORE and entry.disabled_by is None
        )
