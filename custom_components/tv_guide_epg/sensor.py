"""One now and one prime-time sensor per channel and EPG source."""
from __future__ import annotations

from typing import Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_COUNTRY, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES

SLOT_NOW = "ora_in_onda"
SLOT_PRIME = "prima_serata"
SLOT_LABELS = {SLOT_NOW: "Ora in onda", SLOT_PRIME: "Prima serata"}
SLOT_ICONS = {SLOT_NOW: "mdi:television-play", SLOT_PRIME: "mdi:movie-open"}
NO_DATA = "Nessun dato"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinators = hass.data[DOMAIN][entry.entry_id]
    country_code = entry.data[CONF_COUNTRY]
    entities = []
    for source_id, coordinator in coordinators.items():
        for position, channel in enumerate(coordinator.channels, start=1):
            for slot in (SLOT_NOW, SLOT_PRIME):
                entities.append(EpgChannelSensor(
                    coordinator, country_code, channel, slot, position, source_id
                ))
    async_add_entities(entities)


class EpgChannelSensor(CoordinatorEntity[EpgCoordinator], SensorEntity):
    def __init__(self, coordinator: EpgCoordinator, country_code: str, channel: str,
                 slot: str, position: int, source_id: str) -> None:
        super().__init__(coordinator)
        self._country_code = country_code
        self._channel = channel
        self._slot = slot
        self._position = position
        self._source_id = source_id
        self._attr_name = f"{channel} - {SLOT_LABELS[slot]} ({coordinator.source_name})"
        self._attr_icon = SLOT_ICONS[slot]
        # Keep existing Sorrisi entity IDs stable; namespace every additional provider.
        base = f"tvguide_epg_{country_code.lower()}_{slugify(channel)}_{slot}"
        self._attr_unique_id = base if source_id in {"sorrisi", "epgshare", "default"} else f"{base}_{source_id}"

    @property
    def _program(self) -> Optional[Dict[str, Optional[str]]]:
        now, prime = self.coordinator.data
        return (now if self._slot == SLOT_NOW else prime).get(self._channel)

    @property
    def native_value(self) -> str:
        program = self._program
        return program["titolo"] if program else NO_DATA

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        program = self._program or {}
        return {
            "canale": self._channel, "nazione": self._country_code,
            "fonte": self.coordinator.source_name, "source_id": self._source_id,
            "tipo": self._slot, "posizione": self._position,
            "orario_inizio": program.get("orario_inizio"),
            "orario_fine": program.get("orario_fine"),
            "genere": program.get("genere"), "locandina": program.get("locandina"),
            "descrizione": program.get("descrizione"), "prossimi": program.get("prossimi", []),
            "errore_sorgente": self.coordinator.last_source_error,
        }
