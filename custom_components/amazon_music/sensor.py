"""Capteurs Amazon Music."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AmazonMusicEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            PlaylistsSensor(coordinator, "playlists", "Playlists", "mdi:playlist-music"),
            PlaylistsSensor(
                coordinator, "followed", "Playlists suivies", "mdi:playlist-star"
            ),
            LikesSensor(coordinator),
            LastLikedSensor(coordinator),
        ]
    )


class PlaylistsSensor(AmazonMusicEntity, SensorEntity):
    """Nombre de playlists, avec la liste en attribut."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "playlists"

    def __init__(self, coordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get(self._key) or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"playlists": self.coordinator.data.get(self._key) or []}


class LikesSensor(AmazonMusicEntity, SensorEntity):
    """Nombre de titres aimés."""

    _attr_name = "Titres aimés"
    _attr_icon = "mdi:heart"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "titres"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "likes")

    @property
    def native_value(self) -> int | None:
        likes = self.coordinator.data.get("likes")
        return likes.get("track_count") if likes else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        likes = self.coordinator.data.get("likes") or {}
        return {"playlist_id": likes.get("id"), "playlist_title": likes.get("title")}


class LastLikedSensor(AmazonMusicEntity, SensorEntity):
    """Dernier titre aimé, avec sa pochette."""

    _attr_name = "Dernier titre aimé"
    _attr_icon = "mdi:music-note-plus"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "last_liked")

    @property
    def _track(self) -> dict[str, Any]:
        return self.coordinator.data.get("last_liked") or {}

    @property
    def native_value(self) -> str | None:
        title = self._track.get("title")
        return title[:255] if title else None

    @property
    def entity_picture(self) -> str | None:
        return self._track.get("image")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        track = self._track
        return {
            "track_id": track.get("id"),
            "artists": ", ".join(track.get("artists") or []),
            "album": track.get("album"),
            "image": track.get("image"),
        }
