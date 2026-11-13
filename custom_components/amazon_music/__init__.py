"""Intégration Amazon Music pour Home Assistant (lecture seule)."""

from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError
from .const import (
    CONF_COOKIES,
    DOMAIN,
    SERVICE_GET_PLAYLIST_TRACKS,
    SERVICE_GET_TRACK,
    SERVICE_LIST_PLAYLISTS,
    SERVICE_SEARCH,
)

SERVICE_GET_TRACK_SCHEMA = vol.Schema({vol.Required("track_id"): str})
SERVICE_LIST_PLAYLISTS_SCHEMA = vol.Schema({vol.Optional("limit", default=50): int})
SERVICE_GET_PLAYLIST_TRACKS_SCHEMA = vol.Schema(
    {
        vol.Required("playlist_id"): str,
        vol.Optional("limit", default=50): int,
    }
)
SERVICE_SEARCH_SCHEMA = vol.Schema({vol.Required("query"): str})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Crée le client à partir des cookies saisis dans la configuration."""
    session = async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())
    api = AmazonMusicApi(session, entry.data[CONF_COOKIES])
    try:
        await api.async_refresh_config()
    except AmazonMusicAuthError as err:
        raise ConfigEntryAuthFailed(
            "Session Amazon Music expirée : recollez les cookies"
        ) from err
    except AmazonMusicError as err:
        raise ConfigEntryNotReady(str(err)) from err
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

    async def handle_get_playlist_tracks(call: ServiceCall) -> dict:
        try:
            return await api.async_get_playlist_tracks(
                call.data["playlist_id"], call.data["limit"]
            )
        except AmazonMusicAuthError as err:
            raise RuntimeError(
                "Session Amazon Music expirée : reconfigurez l'intégration"
            ) from err
        except AmazonMusicError as err:
            raise RuntimeError(str(err)) from err

    async def handle_search(call: ServiceCall) -> dict:
        try:
            return {"results": await api.async_search(call.data["query"])}
        except AmazonMusicAuthError as err:
            raise RuntimeError(
                "Session Amazon Music expirée : reconfigurez l'intégration"
            ) from err
        except AmazonMusicError as err:
            raise RuntimeError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLAYLIST_TRACKS,
        handle_get_playlist_tracks,
        schema=SERVICE_GET_PLAYLIST_TRACKS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        handle_search,
        schema=SERVICE_SEARCH_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
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
        hass.services.async_remove(DOMAIN, SERVICE_GET_PLAYLIST_TRACKS)
        hass.services.async_remove(DOMAIN, SERVICE_SEARCH)
    return True
