"""Choix d'une playlist depuis un tableau de bord."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import AmazonMusicEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([PlaylistSelect(coordinator)])


class PlaylistSelect(AmazonMusicEntity, SelectEntity, RestoreEntity):
    """Liste des playlists (créées puis suivies) ; le choix est mémorisé."""

    _attr_name = "Playlist"
    _attr_icon = "mdi:playlist-play"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "playlist_select")
        self._current: str | None = None

    def _all(self) -> list[dict[str, Any]]:
        data = self.coordinator.data or {}
        seen: set[str] = set()
        result = []
        for playlist in [*(data.get("playlists") or []), *(data.get("followed") or [])]:
            title = playlist.get("title")
            if title and title not in seen:
                seen.add(title)
                result.append(playlist)
        return result

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in self.options:
            self._current = last.state

    @property
    def options(self) -> list[str]:
        return [p["title"] for p in self._all()]

    @property
    def current_option(self) -> str | None:
        options = self.options
        if self._current in options:
            return self._current
        return options[0] if options else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = self.current_option
        playlist = next((p for p in self._all() if p["title"] == current), {})
        return {
            "playlist_id": playlist.get("id"),
            "track_count": playlist.get("track_count"),
        }

    async def async_select_option(self, option: str) -> None:
        self._current = option
        self.async_write_ha_state()
