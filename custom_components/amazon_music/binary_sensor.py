"""Capteur de connexion Amazon Music."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AmazonMusicEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ConnectionSensor(coordinator)])


class ConnectionSensor(AmazonMusicEntity, BinarySensorEntity):
    """Allumé tant que la dernière lecture d'Amazon Music a réussi."""

    _attr_name = "Connexion"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "connection")

    @property
    def available(self) -> bool:
        # Reste lisible quand la session tombe : c'est justement l'information utile.
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
