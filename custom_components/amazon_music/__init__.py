"""Intégration Amazon Music pour Home Assistant (non officielle)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError
from .coordinator import AmazonMusicCoordinator
from .const import (
    CONF_COOKIES,
    DOMAIN,
    LIKE_STATES,
    SEARCH_TYPES,
    SERVICE_ADD_TRACK,
    SERVICE_CREATE_PLAYLIST,
    SERVICE_DELETE_PLAYLIST,
    SERVICE_GET_PLAYLIST_TRACKS,
    SERVICE_GET_TRACK,
    SERVICE_LIST_FOLLOWED_PLAYLISTS,
    SERVICE_LIST_PLAYLISTS,
    SERVICE_PLAY_ON_ALEXA,
    SERVICE_REMOVE_TRACK,
    SERVICE_SEARCH,
    SERVICE_SEARCH_CATALOG,
    SERVICE_SET_TRACK_LIKE,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SELECT, Platform.SENSOR]

# Services qui modifient le compte : les entités sont relues ensuite.
WRITES = {
    SERVICE_ADD_TRACK,
    SERVICE_CREATE_PLAYLIST,
    SERVICE_DELETE_PLAYLIST,
    SERVICE_REMOVE_TRACK,
    SERVICE_SET_TRACK_LIKE,
}

_LIMIT = vol.All(vol.Coerce(int), vol.Range(min=1, max=5000))

SCHEMAS: dict[str, vol.Schema] = {
    SERVICE_GET_TRACK: vol.Schema({vol.Required("track_id"): cv.string}),
    SERVICE_LIST_PLAYLISTS: vol.Schema({vol.Optional("limit", default=500): _LIMIT}),
    SERVICE_LIST_FOLLOWED_PLAYLISTS: vol.Schema(
        {vol.Optional("limit", default=500): _LIMIT}
    ),
    SERVICE_GET_PLAYLIST_TRACKS: vol.Schema(
        {
            vol.Required("playlist_id"): cv.string,
            vol.Optional("limit", default=100): _LIMIT,
        }
    ),
    SERVICE_SEARCH: vol.Schema({vol.Required("query"): cv.string}),
    SERVICE_SEARCH_CATALOG: vol.Schema(
        {
            vol.Required("query"): cv.string,
            vol.Optional("types", default=SEARCH_TYPES): vol.All(
                cv.ensure_list, [vol.In(SEARCH_TYPES)]
            ),
            vol.Optional("limit", default=10): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=50)
            ),
        }
    ),
    SERVICE_CREATE_PLAYLIST: vol.Schema(
        {
            vol.Required("title"): cv.string,
            vol.Optional("description"): cv.string,
            vol.Optional("track_ids"): vol.All(cv.ensure_list, [cv.string]),
        }
    ),
    SERVICE_DELETE_PLAYLIST: vol.Schema({vol.Required("playlist_id"): cv.string}),
    SERVICE_ADD_TRACK: vol.Schema(
        {
            vol.Required("playlist_id"): cv.string,
            vol.Required("track_id"): cv.string,
            vol.Optional("reject_duplicates", default=True): cv.boolean,
        }
    ),
    SERVICE_REMOVE_TRACK: vol.Schema(
        {vol.Required("playlist_id"): cv.string, vol.Required("track_id"): cv.string}
    ),
    SERVICE_SET_TRACK_LIKE: vol.Schema(
        {
            vol.Required("track_id"): cv.string,
            vol.Optional("state", default="LIKE"): vol.All(
                vol.Upper, vol.In(LIKE_STATES)
            ),
        }
    ),
    SERVICE_PLAY_ON_ALEXA: vol.Schema(
        {
            vol.Required("entity_id"): cv.entity_ids,
            vol.Exclusive("playlist_id", "what"): cv.string,
            vol.Exclusive("track_id", "what"): cv.string,
            vol.Exclusive("query", "what"): cv.string,
        }
    ),
}

# Services de lecture : ne renvoient qu'une réponse.
READ_ONLY = {
    SERVICE_GET_TRACK,
    SERVICE_LIST_PLAYLISTS,
    SERVICE_LIST_FOLLOWED_PLAYLISTS,
    SERVICE_GET_PLAYLIST_TRACKS,
    SERVICE_SEARCH,
    SERVICE_SEARCH_CATALOG,
}


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
    coordinator = AmazonMusicCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    async def play_on_alexa(data: dict[str, Any]) -> dict[str, Any]:
        """Demande à Alexa Media Player de jouer un contenu Amazon Music."""
        if "playlist_id" in data:
            playlist = await api.async_get_playlist_tracks(data["playlist_id"], 1)
            phrase = f"ma playlist {playlist['title']}"
        elif "track_id" in data:
            track = await api.async_get_track(data["track_id"])
            phrase = " ".join([track["title"] or "", *track["artists"][:1]]).strip()
        elif "query" in data:
            phrase = data["query"]
        else:
            raise HomeAssistantError("Indiquez playlist_id, track_id ou query")
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": data["entity_id"],
                "media_content_type": "AMAZON_MUSIC",
                "media_content_id": phrase,
            },
            blocking=True,
        )
        return {"requested": phrase, "entity_id": data["entity_id"]}

    handlers: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {
        SERVICE_GET_TRACK: lambda d: api.async_get_track(d["track_id"]),
        SERVICE_LIST_PLAYLISTS: lambda d: api.async_list_playlists(d["limit"]),
        SERVICE_LIST_FOLLOWED_PLAYLISTS: lambda d: api.async_list_followed_playlists(
            d["limit"]
        ),
        SERVICE_GET_PLAYLIST_TRACKS: lambda d: api.async_get_playlist_tracks(
            d["playlist_id"], d["limit"]
        ),
        SERVICE_SEARCH: lambda d: api.async_search(d["query"]),
        SERVICE_SEARCH_CATALOG: lambda d: api.async_search_catalog(
            d["query"], d["types"], d["limit"]
        ),
        SERVICE_CREATE_PLAYLIST: lambda d: api.async_create_playlist(
            d["title"], d.get("description"), d.get("track_ids")
        ),
        SERVICE_DELETE_PLAYLIST: lambda d: api.async_delete_playlist(d["playlist_id"]),
        SERVICE_ADD_TRACK: lambda d: api.async_add_track(
            d["playlist_id"], d["track_id"], d["reject_duplicates"]
        ),
        SERVICE_REMOVE_TRACK: lambda d: api.async_remove_track(
            d["playlist_id"], d["track_id"]
        ),
        SERVICE_SET_TRACK_LIKE: lambda d: api.async_set_track_like(
            d["track_id"], d["state"]
        ),
        SERVICE_PLAY_ON_ALEXA: play_on_alexa,
    }
    # Les listes sont renvoyées sous une clé, car une réponse doit être un objet.
    wrap = {
        SERVICE_LIST_PLAYLISTS: "playlists",
        SERVICE_LIST_FOLLOWED_PLAYLISTS: "playlists",
        SERVICE_SEARCH: "results",
        SERVICE_SEARCH_CATALOG: "results",
    }

    def make(name: str):
        async def handle(call: ServiceCall) -> dict[str, Any] | None:
            try:
                result = await handlers[name](dict(call.data))
            except AmazonMusicAuthError as err:
                # Propose à l'utilisateur de recoller ses cookies.
                entry.async_start_reauth(hass)
                raise HomeAssistantError(
                    "Session Amazon Music expirée : recollez les cookies "
                    "(Paramètres → Appareils et services)"
                ) from err
            except AmazonMusicError as err:
                raise HomeAssistantError(str(err)) from err
            if name in WRITES:
                await coordinator.async_request_refresh()
            if name in wrap:
                result = {wrap[name]: result}
            return result if call.return_response else None

        return handle

    for name, schema in SCHEMAS.items():
        hass.services.async_register(
            DOMAIN,
            name,
            make(name),
            schema=schema,
            supports_response=(
                SupportsResponse.ONLY if name in READ_ONLY else SupportsResponse.OPTIONAL
            ),
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        for name in SCHEMAS:
            hass.services.async_remove(DOMAIN, name)
    return True
