"""The OpenAI Conversation integration."""

from __future__ import annotations

import base64
import json

import openai
import voluptuous as vol

from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    issue_registry as ir,
    selector,
)
from homeassistant.helpers.typing import ConfigType

from .const import DEFAULT_IMAGE_DESCRIPTION_PROMPT, DOMAIN, LOGGER

SERVICE_GENERATE_IMAGE = "generate_image"
SERVICE_DESCRIBE_IMAGE = "describe_image"

PLATFORMS = (Platform.CONVERSATION,)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up OpenAI Conversation."""

    async def render_image(call: ServiceCall) -> ServiceResponse:
        """Render an image with dall-e."""
        client = hass.data[DOMAIN][call.data["config_entry"]]

        if call.data["size"] in ("256", "512", "1024"):
            ir.async_create_issue(
                hass,
                DOMAIN,
                "image_size_deprecated_format",
                breaks_in_ha_version="2024.7.0",
                is_fixable=False,
                is_persistent=True,
                learn_more_url="https://www.home-assistant.io/integrations/openai_conversation/",
                severity=ir.IssueSeverity.WARNING,
                translation_key="image_size_deprecated_format",
            )
            size = "1024x1024"
        else:
            size = call.data["size"]

        try:
            response = await client.images.generate(
                model="dall-e-3",
                prompt=call.data["prompt"],
                size=size,
                quality=call.data["quality"],
                style=call.data["style"],
                response_format="url",
                n=1,
            )
        except openai.OpenAIError as err:
            raise HomeAssistantError(f"Error generating image: {err}") from err

        return response.data[0].model_dump(exclude={"b64_json"})

    async def describe_image(call: ServiceCall) -> ServiceResponse:
        """Describe an image using gpt-4 vision."""

        prompt = DEFAULT_IMAGE_DESCRIPTION_PROMPT

        if "prompt" in call.data:
            prompt = call.data["prompt"]

        LOGGER.info(f"Using prompt: {prompt}")

        opts = {"timeout": 10}

        if call.data["detail"] == "low":
            opts["width"] = 512
            opts["height"] = 512

        img = await async_get_image(hass, call.data["camera"], **opts)
        b64_bytes = base64.b64encode(img.content).decode("utf-8")

        client = hass.data[DOMAIN][call.data["config_entry"]]
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_bytes}",
                                "detail": call.data["detail"],
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"Response": response.choices[0].message.content}

    hass.services.async_register(
        DOMAIN,
        SERVICE_DESCRIBE_IMAGE,
        describe_image,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {"integration": DOMAIN}
                ),
                vol.Required("camera"): selector.EntitySelector({"domain": "camera"}),
                vol.Optional("prompt"): cv.string,
                vol.Optional("detail", default="low"): vol.In(("low", "high")),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_IMAGE,
        render_image,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {
                        "integration": DOMAIN,
                    }
                ),
                vol.Required("prompt"): cv.string,
                vol.Optional("size", default="1024x1024"): vol.In(
                    ("1024x1024", "1024x1792", "1792x1024", "256", "512", "1024")
                ),
                vol.Optional("quality", default="standard"): vol.In(("standard", "hd")),
                vol.Optional("style", default="vivid"): vol.In(("vivid", "natural")),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenAI Conversation from a config entry."""
    client = openai.AsyncOpenAI(api_key=entry.data[CONF_API_KEY])
    try:
        await hass.async_add_executor_job(client.with_options(timeout=10.0).models.list)
    except openai.AuthenticationError as err:
        LOGGER.error("Invalid API key: %s", err)
        return False
    except openai.OpenAIError as err:
        raise ConfigEntryNotReady(err) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenAI."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    hass.data[DOMAIN].pop(entry.entry_id)
    return True
