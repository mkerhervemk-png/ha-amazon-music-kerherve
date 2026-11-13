"""Client minimal pour l'API GraphQL web d'Amazon Music (lecture et écriture)."""

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
    MUTATION_ADD_TRACK,
    MUTATION_CREATE_PLAYLIST,
    MUTATION_DELETE_PLAYLIST,
    MUTATION_REMOVE_TRACK,
    MUTATION_SET_LIKE,
    PAGE_SIZE,
    QUERY_FOLLOWED_PLAYLISTS,
    QUERY_PLAYLIST_TRACKS,
    QUERY_SEARCH,
    QUERY_SEARCH_CATALOG,
    QUERY_TRACK,
    QUERY_USER_PLAYLISTS,
    SEARCH_TYPES,
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

    @staticmethod
    def _artists(node: dict[str, Any]) -> list[str]:
        return [
            e["node"]["name"]
            for e in (node.get("contributingArtists") or {}).get("edges", [])
            if e.get("node")
        ]

    # ------------------------------------------------------------ lecture

    async def async_get_track(self, track_id: str) -> dict[str, Any]:
        """Métadonnées d'un titre."""
        data = await self._gql("Track", QUERY_TRACK, {"id": track_id})
        track = data.get("track")
        if not track:
            raise AmazonMusicError(f"Titre introuvable : {track_id}")
        album = track.get("album") or {}
        images = album.get("images") or []
        return {
            "id": track.get("id"),
            "title": track.get("title"),
            "artists": self._artists(track),
            "album": album.get("title"),
            "image": images[0]["url"] if images else None,
            "duration": track.get("duration"),
            "like_state": (track.get("likesContext") or {}).get("state"),
        }

    async def _paged_playlists(
        self, operation: str, query: str, field: str, limit: int
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor: str | None = None
        while len(results) < limit:
            data = await self._gql(
                operation,
                query,
                {"limit": float(min(PAGE_SIZE, limit - len(results))), "cursor": cursor},
            )
            block = (data.get("user") or {}).get(field) or {}
            new = 0
            for e in block.get("edges", []):
                node = e.get("node") or {}
                if not node.get("id") or node["id"] in seen:
                    continue
                seen.add(node["id"])
                new += 1
                results.append(
                    {
                        "id": node["id"],
                        "title": (node.get("title") or "").strip(),
                        "track_count": node.get("trackCount"),
                    }
                )
            page = block.get("pageInfo") or {}
            cursor = page.get("token")
            if not page.get("hasNextPage") or not cursor or not new:
                break
        return results[:limit]

    async def async_list_playlists(self, limit: int = 500) -> list[dict[str, Any]]:
        """Playlists créées par le compte (toutes les pages, jusqu'à limit)."""
        return await self._paged_playlists(
            "UserPlaylists", QUERY_USER_PLAYLISTS, "playlists", limit
        )

    async def async_list_followed_playlists(
        self, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Playlists suivies par le compte (toutes les pages, jusqu'à limit)."""
        return await self._paged_playlists(
            "FollowedPlaylists", QUERY_FOLLOWED_PLAYLISTS, "followedPlaylists", limit
        )

    async def _playlist_pages(self, playlist_id: str, limit: int):
        """Parcourt les titres d'une playlist ; renvoie (playlist, arêtes)."""
        edges: list[dict[str, Any]] = []
        playlist: dict[str, Any] = {}
        cursor: str | None = None
        while len(edges) < limit:
            data = await self._gql(
                "PlaylistTracks",
                QUERY_PLAYLIST_TRACKS,
                {
                    "id": playlist_id,
                    "limit": float(min(PAGE_SIZE, limit - len(edges))),
                    "cursor": cursor,
                },
            )
            playlist = data.get("playlist") or {}
            if not playlist:
                raise AmazonMusicError(f"Playlist introuvable : {playlist_id}")
            block = playlist.get("tracks") or {}
            page_edges = [e for e in block.get("edges", []) if e.get("node")]
            edges.extend(page_edges)
            page = block.get("pageInfo") or {}
            cursor = page.get("token")
            if not page.get("hasNextPage") or not cursor or not page_edges:
                break
        return playlist, edges[:limit]

    async def async_get_playlist_tracks(
        self, playlist_id: str, limit: int = 100
    ) -> dict[str, Any]:
        """Titres d'une playlist (pages suivies automatiquement jusqu'à limit)."""
        playlist, edges = await self._playlist_pages(playlist_id, limit)
        return {
            "id": playlist.get("id"),
            "title": (playlist.get("title") or "").strip(),
            "track_count": playlist.get("trackCount"),
            "tracks": [
                {
                    "id": e["node"]["id"],
                    "title": e["node"].get("title"),
                    "artists": self._artists(e["node"]),
                    "album": (e["node"].get("album") or {}).get("title"),
                    "image": next(
                        (
                            i.get("url")
                            for i in (e["node"].get("album") or {}).get("images") or []
                        ),
                        None,
                    ),
                }
                for e in edges
            ],
        }

    async def async_search(self, query: str) -> list[dict[str, Any]]:
        """Suggestions de recherche rapides."""
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

    async def async_search_catalog(
        self, query: str, types: list[str] | None = None, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        """Recherche complète dans le catalogue, regroupée par type."""
        types = types or SEARCH_TYPES
        specs = [{"label": t, "types": [t], "limit": limit} for t in types]
        data = await self._gql(
            "SpecSearch",
            QUERY_SEARCH_CATALOG,
            {"searchText": query, "specifications": specs},
        )
        out: dict[str, list[dict[str, Any]]] = {t: [] for t in types}
        for block in (data.get("specificationSearch") or {}).get("result") or []:
            label = block.get("label")
            for e in block.get("edges") or []:
                node = e.get("node") or {}
                if not node.get("id"):
                    continue
                item = {
                    "type": node.get("__typename"),
                    "id": node.get("id"),
                    "name": node.get("name") or node.get("title"),
                }
                if node.get("__typename") == "Track":
                    item["artists"] = self._artists(node)
                out.setdefault(label, []).append(item)
        return out

    # ----------------------------------------------------------- écriture

    async def async_create_playlist(
        self,
        title: str,
        description: str | None = None,
        track_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        data = await self._gql(
            "CreatePlaylist",
            MUTATION_CREATE_PLAYLIST,
            {"title": title, "description": description, "trackAsins": track_ids},
        )
        playlist = data.get("createPlaylist")
        if not playlist or not playlist.get("id"):
            raise AmazonMusicError("Création de playlist refusée")
        return {"id": playlist["id"], "title": playlist.get("title")}

    async def async_delete_playlist(self, playlist_id: str) -> dict[str, Any]:
        data = await self._gql(
            "deletePlaylist", MUTATION_DELETE_PLAYLIST, {"id": playlist_id}
        )
        result = data.get("deletePlaylist") or {}
        return {"id": result.get("id"), "deleted": bool(result.get("isDeleted"))}

    async def async_add_track(
        self, playlist_id: str, track_id: str, reject_duplicates: bool = True
    ) -> dict[str, Any]:
        data = await self._gql(
            "addTrackToPlaylist",
            MUTATION_ADD_TRACK,
            {
                "id": playlist_id,
                "trackId": track_id,
                "rejectDuplicateTracks": reject_duplicates,
            },
        )
        result = data.get("appendTracks")
        if not result:
            raise AmazonMusicError("Ajout du titre refusé")
        return {"id": result.get("id"), "track_count": result.get("trackCount")}

    async def async_remove_track(
        self, playlist_id: str, track_id: str
    ) -> dict[str, Any]:
        """Retire la première occurrence d'un titre dans une playlist.

        Le curseur d'une entrée a la forme « position:identifiant » ; le serveur
        attend l'identifiant seul.
        """
        _, edges = await self._playlist_pages(playlist_id, 5000)
        entry = next(
            (e.get("cursor") for e in edges if e["node"].get("id") == track_id), None
        )
        if entry is None:
            raise AmazonMusicError(f"Titre {track_id} absent de la playlist")
        data = await self._gql(
            "removeTrackFromPlaylist",
            MUTATION_REMOVE_TRACK,
            {"id": playlist_id, "cursor": str(entry).split(":")[-1]},
        )
        result = data.get("removeTracks")
        if not result:
            raise AmazonMusicError("Retrait du titre refusé")
        return {"id": result.get("id"), "track_count": result.get("trackCount")}

    async def async_set_track_like(self, track_id: str, state: str) -> dict[str, Any]:
        """state : LIKE, NEUTRAL (aucun avis) ou DISLIKE."""
        if state == "NONE":
            state = "NEUTRAL"
        data = await self._gql(
            "likeTrack", MUTATION_SET_LIKE, {"likeState": state, "trackId": track_id}
        )
        track = (data.get("setTrackLikeState") or {}).get("track") or {}
        return {
            "id": track.get("id") or track_id,
            "like_state": (track.get("likesContext") or {}).get("state"),
        }
