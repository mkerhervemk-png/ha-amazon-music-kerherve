"""Client minimal pour l'API GraphQL web d'Amazon Music (lecture seule)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_KEY,
    CONFIG_URL,
    CSRF_MAX_AGE,
    GQL_URL,
    QUERY_PLAYLIST_TRACKS,
    QUERY_SEARCH,
    QUERY_TRACK,
    QUERY_USER_PLAYLISTS,
    TERRITORY,
    WEB_URL,
)

_LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class AmazonMusicError(Exception):
    """Erreur générique du client."""


class AmazonMusicAuthError(AmazonMusicError):
    """Session expirée ou cookies invalides."""


def clean_cookies(raw: str) -> str:
    """Nettoie la ligne de cookies collée (préfixe « cookie: », retours à la ligne)."""
    value = " ".join(raw.replace("\r", " ").replace("\n", " ").split())
    if value.lower().startswith("cookie:"):
        value = value[7:].strip()
    return value


class AmazonMusicApi:
    """Client qui rejoue les requêtes du site web avec les cookies de l'utilisateur.

    Les jetons CSRF, l'appareil et la session sont lus sur config.json puis
    renouvelés automatiquement : seuls les cookies sont à fournir.
    """

    def __init__(self, session: aiohttp.ClientSession, cookies: str) -> None:
        self._session = session
        self._cookies = clean_cookies(cookies)
        self._config: dict[str, Any] = {}
        self._config_time = 0.0

    @property
    def customer_id(self) -> str | None:
        return self._config.get("customerId")

    async def async_refresh_config(self) -> dict[str, Any]:
        """Lit config.json : vérifie que le compte est reconnu et récupère le CSRF."""
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "cookie": self._cookies,
            "origin": WEB_URL.rstrip("/"),
            "referer": WEB_URL,
            "user-agent": USER_AGENT,
        }
        try:
            async with self._session.post(
                CONFIG_URL, headers=headers, data="{}"
            ) as resp:
                if resp.status in (401, 403):
                    raise AmazonMusicAuthError("Cookies refusés par Amazon Music")
                if resp.status != 200:
                    raise AmazonMusicError(f"HTTP {resp.status} sur config.json")
                config = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise AmazonMusicError(f"Lecture de config.json échouée : {err}") from err
        except ValueError as err:
            raise AmazonMusicError("Réponse config.json illisible") from err

        csrf = config.get("csrf") if isinstance(config, dict) else None
        if not isinstance(config, dict) or not config.get("customerId"):
            raise AmazonMusicAuthError(
                "Compte non reconnu : cookies incomplets ou session expirée"
            )
        if not csrf or not all(csrf.get(k) for k in ("token", "rnd", "ts")):
            raise AmazonMusicError("config.json ne contient pas les jetons CSRF")
        self._config = config
        self._config_time = time.monotonic()
        return config

    async def _ensure_config(self) -> None:
        if not self._config or time.monotonic() - self._config_time > CSRF_MAX_AGE:
            await self.async_refresh_config()

    def _headers(self) -> dict[str, str]:
        cfg = self._config
        csrf = cfg["csrf"]
        return {
            "accept": "application/graphql-response+json, application/json",
            "accept-language": "fr-FR",
            "content-language": "fr-FR",
            "content-type": "application/json",
            "csrf-token": str(csrf["token"]),
            "csrf-rnd": str(csrf["rnd"]),
            "csrf-ts": str(csrf["ts"]),
            "music-territory": cfg.get("musicTerritory") or TERRITORY,
            "x-amzn-client-subscription-tier": cfg.get("tier") or "UNLIMITED_HD",
            "x-amzn-device-id": str(cfg.get("deviceId", "")),
            "x-amzn-device-type": cfg.get("deviceType") or "A16ZV8BU3SN1N3",
            "x-amzn-feature-flags": "api-cache,use-ups",
            "x-amzn-session-id": str(cfg.get("sessionId", "")),
            "x-api-key": API_KEY,
            "cookie": self._cookies,
            "origin": WEB_URL.rstrip("/"),
            "referer": WEB_URL,
            "user-agent": USER_AGENT,
        }

    async def _gql(
        self, operation: str, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        body = json.dumps(
            {"operationName": operation, "variables": variables, "query": query}
        )
        await self._ensure_config()
        payload: dict[str, Any] = {}
        for attempt in (1, 2):
            try:
                async with self._session.post(
                    GQL_URL, headers=self._headers(), data=body
                ) as resp:
                    status = resp.status
                    if status == 200:
                        payload = await resp.json(content_type=None)
            except aiohttp.ClientError as err:
                raise AmazonMusicError(f"Requête {operation} échouée : {err}") from err
            if status in (401, 403):
                if attempt == 1:
                    # Jetons CSRF périmés : on les redemande une fois.
                    await self.async_refresh_config()
                    continue
                raise AmazonMusicAuthError("Session Amazon Music refusée")
            if status != 200:
                raise AmazonMusicError(f"HTTP {status} sur {operation}")
            break

        if "errors" in payload:
            messages = " ; ".join(e.get("message", "?") for e in payload["errors"])
            raise AmazonMusicError(f"Erreur GraphQL : {messages}")
        return payload.get("data") or {}

    async def async_get_track(self, track_id: str) -> dict[str, Any]:
        """Métadonnées d'un titre (lecture seule)."""
        data = await self._gql("Track", QUERY_TRACK, {"id": track_id})
        track = data.get("track")
        if not track:
            raise AmazonMusicError(f"Titre introuvable : {track_id}")
        album = track.get("album") or {}
        images = album.get("images") or []
        artists = [
            e["node"]["name"]
            for e in (track.get("contributingArtists") or {}).get("edges", [])
            if e.get("node")
        ]
        return {
            "id": track.get("id"),
            "title": track.get("title"),
            "artists": artists,
            "album": album.get("title"),
            "image": images[0]["url"] if images else None,
        }

    async def async_list_playlists(self, limit: int = 50) -> list[dict[str, Any]]:
        """Playlists créées par le compte (lecture seule, première page)."""
        data = await self._gql(
            "UserPlaylists",
            QUERY_USER_PLAYLISTS,
            {"firstLimit": float(limit), "afterCursor": None},
        )
        user = data.get("user") or {}
        edges = (user.get("playlists") or {}).get("edges", [])
        return [
            {
                "id": e["node"]["id"],
                "title": (e["node"].get("title") or "").strip(),
                "track_count": e["node"].get("trackCount"),
            }
            for e in edges
            if e.get("node")
        ]

    async def async_get_playlist_tracks(
        self, playlist_id: str, limit: int = 50
    ) -> dict[str, Any]:
        """Titres d'une playlist (lecture seule, première page)."""
        data = await self._gql(
            "PlaylistTracks",
            QUERY_PLAYLIST_TRACKS,
            {"id": playlist_id, "limit": float(limit)},
        )
        playlist = data.get("playlist")
        if not playlist:
            raise AmazonMusicError(f"Playlist introuvable : {playlist_id}")
        tracks = [
            {"id": e["node"]["id"], "title": e["node"].get("title")}
            for e in (playlist.get("tracks") or {}).get("edges", [])
            if e.get("node")
        ]
        return {
            "id": playlist.get("id"),
            "title": (playlist.get("title") or "").strip(),
            "track_count": playlist.get("trackCount"),
            "tracks": tracks,
        }

    async def async_search(self, query: str) -> list[dict[str, Any]]:
        """Suggestions de recherche (artistes, playlists, titres, albums)."""
        data = await self._gql("GetSearchSuggestions", QUERY_SEARCH, {"query": query})
        edges = (
            ((data.get("searchSuggestions") or {}).get("suggestedEntities") or {})
            .get("edges", [])
        )
        results = []
        for e in edges:
            node = e.get("node") or {}
            if not node:
                continue
            results.append(
                {
                    "type": node.get("__typename"),
                    "id": node.get("id"),
                    "name": node.get("name") or node.get("title"),
                }
            )
        return results
