"""Configuration par saisie des cookies de session Amazon Music."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError
from .const import (
    CONF_CSRF,
    CONF_DEVICE_ID,
    CONF_SESSION_ID,
    CONF_SESSION_TOKEN,
    DOMAIN,
)

# Titre de test utilisé pour valider la session (lecture seule).
TEST_TRACK_ID = "B0GWPYXQHB"

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SESSION_TOKEN): str,
        vol.Required(CONF_SESSION_ID): str,
        vol.Optional(CONF_CSRF): str,
    }
)


class AmazonMusicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Assistant de configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate(self.hass, user_input)
            except AmazonMusicAuthError:
                errors["base"] = "invalid_auth"
            except AmazonMusicError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_SESSION_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Amazon Music",
                    data={
                        **user_input,
                        CONF_DEVICE_ID: str(secrets.randbelow(10**19)),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )


async def _validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Teste la session en lisant les métadonnées d'un titre."""
    api = AmazonMusicApi(
        async_get_clientsession(hass),
        session_token=data[CONF_SESSION_TOKEN],
        session_id=data[CONF_SESSION_ID],
        csrf=data.get(CONF_CSRF),
        device_id=str(secrets.randbelow(10**19)),
    )
    await api.async_get_track(TEST_TRACK_ID)
