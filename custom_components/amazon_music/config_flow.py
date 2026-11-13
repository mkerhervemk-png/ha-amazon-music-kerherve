"""Configuration par saisie des cookies de la session Amazon Music."""

from __future__ import annotations

from collections.abc import Mapping
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

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COOKIES): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class AmazonMusicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Assistant de configuration (création, reconnexion, reconfiguration)."""

    VERSION = 2

    async def _check(self, raw: str) -> tuple[str, str | None, str | None]:
        """Renvoie (cookies nettoyés, identifiant du compte, erreur)."""
        cookies = clean_cookies(raw)
        session = async_create_clientsession(
            self.hass, cookie_jar=aiohttp.DummyCookieJar()
        )
        api = AmazonMusicApi(session, cookies)
        try:
            # Vérifie le compte, puis une lecture qui exige vraiment la session.
            await api.async_refresh_config()
            await api.async_list_playlists(1)
        except AmazonMusicAuthError:
            return cookies, None, "invalid_auth"
        except AmazonMusicError:
            return cookies, None, "cannot_connect"
        return cookies, api.customer_id, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            cookies, customer, error = await self._check(user_input[CONF_COOKIES])
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(customer)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Amazon Music", data={CONF_COOKIES: cookies}
                )
        return self.async_show_form(
            step_id="user", data_schema=STEP_SCHEMA, errors=errors
        )

    async def _update(
        self,
        step_id: str,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, Any] | None,
    ) -> config_entries.ConfigFlowResult:
        """Remplace les cookies d'une entrée existante."""
        errors: dict[str, str] = {}
        if user_input is not None:
            cookies, customer, error = await self._check(user_input[CONF_COOKIES])
            if error:
                errors["base"] = error
            elif entry.unique_id and customer != entry.unique_id:
                errors["base"] = "wrong_account"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={CONF_COOKIES: cookies}
                )
        return self.async_show_form(
            step_id=step_id, data_schema=STEP_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return await self._update(
            "reauth_confirm", self._get_reauth_entry(), user_input
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return await self._update(
            "reconfigure", self._get_reconfigure_entry(), user_input
        )
