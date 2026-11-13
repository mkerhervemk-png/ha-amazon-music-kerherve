"""Base commune des entités Amazon Music."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AmazonMusicCoordinator


class AmazonMusicEntity(CoordinatorEntity[AmazonMusicCoordinator]):
    """Entité rattachée à l'appareil « Amazon Music »."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AmazonMusicCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Amazon Music",
            manufacturer="Amazon",
            model="Compte Amazon Music (non officiel)",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://music.amazon.fr/",
        )
