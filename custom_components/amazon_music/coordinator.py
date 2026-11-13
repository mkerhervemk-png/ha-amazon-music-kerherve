"""Relecture périodique des données Amazon Music pour les entités."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AmazonMusicApi, AmazonMusicAuthError, AmazonMusicError
from .const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

# Titres possibles de la playlist des titres aimés selon la langue du compte.
LIKES_TITLES = {"mes likes", "my likes", "meine likes", "mis me gusta"}


def find_likes_playlist(playlists: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Repère la playlist des titres aimés (titre connu, sinon identifiant sans tiret)."""
    for playlist in playlists:
        if (playlist.get("title") or "").strip().lower() in LIKES_TITLES:
            return playlist
    for playlist in playlists:
        pid = playlist.get("id") or ""
        if len(pid) == 32 and "-" not in pid:
            return playlist
    return None


class AmazonMusicCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Lit playlists, playlists suivies et dernier titre aimé."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: AmazonMusicApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            playlists = await self.api.async_list_playlists()
            data: dict[str, Any] = {
                "playlists": playlists,
                "followed": [],
                "likes": None,
                "last_liked": None,
            }
            # Les deux lectures suivantes sont secondaires : une erreur ne doit
            # pas rendre toutes les entités indisponibles.
            try:
                data["followed"] = await self.api.async_list_followed_playlists()
            except AmazonMusicAuthError:
                raise
            except AmazonMusicError as err:
                _LOGGER.warning("Playlists suivies illisibles : %s", err)
            likes = find_likes_playlist(playlists)
            if likes:
                data["likes"] = likes
                try:
                    first = await self.api.async_get_playlist_tracks(likes["id"], 1)
                    if first["tracks"]:
                        data["last_liked"] = first["tracks"][0]
                except AmazonMusicAuthError:
                    raise
                except AmazonMusicError as err:
                    _LOGGER.warning("Dernier titre aimé illisible : %s", err)
            return data
        except AmazonMusicAuthError as err:
            raise ConfigEntryAuthFailed(
                "Session Amazon Music expirée : recollez les cookies"
            ) from err
        except AmazonMusicError as err:
            raise UpdateFailed(str(err)) from err
