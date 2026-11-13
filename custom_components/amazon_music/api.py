"""Client minimal pour l'API GraphQL web d'Amazon Music (lecture seule)."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import (
    API_KEY,
    GQL_URL,
    QUERY_PLAYLIST_TRACKS,
    QUERY_SEARCH,
    QUERY_TRACK,
    QUERY_USER_PLAYLISTS,
    TERRITORY,
    WEB_URL,
)

_LOGGER = logging.getLogger(__name__)


class AmazonMusicError(Exception):
    """Erreur générique du client."""


class AmazonMusicAuthError(AmazonMusicError):
    """Session expirée ou cookies / jetons CSRF invalides."""


class AmazonMusicApi:
    """Client qui rejoue les requêtes du site web avec la session de l'utilisateur.

    Le serveur exige les trois en-têtes CSRF ensemble (csrf-token, csrf-rnd,
    csrf-ts), copiés depuis une requête du site. Un seul en-tête suffit
    à faire échouer l'authentification (401).
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        session_token: str,
        session_id: str,
        csrf_token: str,
        csrf_rnd: str,
        csrf_ts: str,
        device_id: str,
    ) -> None:
        self._session = session
        self._session_token = session_token
        self._session_id = session_id
        self._csrf_token = csrf_token
        self._csrf_rnd = csrf_rnd
        self._csrf_ts = csrf_ts
        self._device_id = device_id

    def _headers(self) -> dict[str, str]:
        return {
            "accept": "application/graphql-response+json, application/json",
            "accept-language": "fr-FR",
            "content-language": "fr-FR",
            "content-type": "application/json",
            "csrf-token": self._csrf_token,
            "csrf-rnd": self._csrf_rnd,
            "csrf-ts": self._csrf_ts,
            "music-territory": TERRITORY,
            "x-amzn-client-subscription-tier": "UNLIMITED_HD",
            "x-amzn-device-id": self._device_id,
            "x-amzn-device-type": "A16ZV8BU3SN1N3",
            "x-amzn-feature-flags": "api-cache,use-ups",
            "x-amzn-session-id": self._session_id,
            "x-api-key": API_KEY,
            "cookie": f"session-token={self._session_token}; session-id={self._session_id}",
            "referer": WEB_URL,
        }

    async def _gql(
        self, operation: str, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        body = {"operationName": operation, "variables": variables, "query": query}
        try:
            async with self._session.post(
                GQL_URL, headers=self._headers(), data=json.dumps(body)
            ) as resp:
                if resp.status in (401, 403):
                    raise AmazonMusicAuthError(
                        "Cookies ou jetons CSRF refusés (session expirée ?)"
                    )
                if resp.status != 200:
                    raise AmazonMusicError(f"HTTP {resp.status} sur {operation}")
                payload = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise AmazonMusicError(f"Requête {operation} échouée : {err}") from err

        if "errors" in payload:
            messages = " ; ".join(e.get("message", "?") for e in payload["errors"])
            raise AmazonMusicError(f"Erreur GraphQL : {messages}")
        return payload.get("data", {})

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
