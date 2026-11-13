"""Intégration Amazon Music pour Home Assistant (lecture seule, version initiale)."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError
from .const import (
    CONF_CSRF,
    CONF_DEVICE_ID,
    CONF_SESSION_ID,
    CONF_SESSION_TOKEN,
    DOMAIN,
    SERVICE_GET_TRACK,
    SERVICE_LIST_PLAYLISTS,
)

SERVICE_GET_TRACK_SCHEMA = vol.Schema({vol.Required("track_id"): str})
SERVICE_LIST_PLAYLISTS_SCHEMA = vol.Schema({vol.Optional("limit", default=50): int})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Crée le client à partir des cookies saisis dans la configuration."""
    api = AmazonMusicApi(
        async_get_clientsession(hass),
        session_token=entry.data[CONF_SESSION_TOKEN],
        session_id=entry.data[CONF_SESSION_ID],
        csrf=entry.data.get(CONF_CSRF),
        device_id=entry.data[CONF_DEVICE_ID],
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    async def handle_get_track(call: ServiceCall) -> dict:
        try:
            return await api.async_get_track(call.data["track_id"])
        except AmazonMusicAuthError as err:
            raise RuntimeError(
                "Session Amazon Music expirée : reconfigurez l'intégration"
            ) from err
        except AmazonMusicError as err:
            raise RuntimeError(str(err)) from err

    async def handle_list_playlists(call: ServiceCall) -> dict:
        try:
            playlists = await api.async_list_playlists(call.data["limit"])
        except AmazonMusicAuthError as err:
            raise RuntimeError(
                "Session Amazon Music expirée : reconfigurez l'intégration"
            ) from err
        except AmazonMusicError as err:
            raise RuntimeError(str(err)) from err
        return {"playlists": playlists}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TRACK,
        handle_get_track,
        schema=SERVICE_GET_TRACK_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_PLAYLISTS,
        handle_list_playlists,
        schema=SERVICE_LIST_PLAYLISTS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_GET_TRACK)
        hass.services.async_remove(DOMAIN, SERVICE_LIST_PLAYLISTS)
    return True
