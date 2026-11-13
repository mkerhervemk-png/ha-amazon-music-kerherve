"""Configuration par saisie des cookies de la session Amazon Music."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError, clean_cookies
from .const import CONF_COOKIES, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COOKIES): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class AmazonMusicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Assistant de configuration."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cookies = clean_cookies(user_input[CONF_COOKIES])
            session = async_create_clientsession(
                self.hass, cookie_jar=aiohttp.DummyCookieJar()
            )
            api = AmazonMusicApi(session, cookies)
            try:
                # Vérifie le compte, puis une lecture qui exige vraiment la session.
                await api.async_refresh_config()
                await api.async_list_playlists(1)
            except AmazonMusicAuthError:
                errors["base"] = "invalid_auth"
            except AmazonMusicError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(api.customer_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Amazon Music", data={CONF_COOKIES: cookies}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
