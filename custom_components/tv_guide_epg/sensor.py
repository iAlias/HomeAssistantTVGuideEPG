"""TV Guide EPG sensors: two per channel.

Each channel gets a "Ora in onda" and a "Prima serata" sensor — for Italy that
is 18 entities. Putting every channel in the attributes of a single entity, as
earlier versions did, made the data invisible unless you also installed the
card; one entity per channel is directly usable in dashboards and automations.
"""

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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create two sensors for every channel this country covers."""
    coordinator: EpgCoordinator = hass.data[DOMAIN][entry.entry_id]
    country_code = entry.data[CONF_COUNTRY]

    async_add_entities(
        EpgChannelSensor(coordinator, country_code, channel, slot, position)
        for position, channel in enumerate(coordinator.channels, start=1)
        for slot in (SLOT_NOW, SLOT_PRIME)
    )


class EpgChannelSensor(CoordinatorEntity[EpgCoordinator], SensorEntity):
    """What is on one channel, either right now or in prime time."""

    def __init__(
        self,
        coordinator: EpgCoordinator,
        country_code: str,
        channel: str,
        slot: str,
        position: int,
    ) -> None:
        super().__init__(coordinator)
        self._country_code = country_code
        self._channel = channel
        self._slot = slot
        self._position = position
        self._attr_name = f"{channel} - {SLOT_LABELS[slot]}"
        self._attr_icon = SLOT_ICONS[slot]
        self._attr_unique_id = (
            f"tvguide_epg_{country_code.lower()}_{slugify(channel)}_{slot}"
        )

    @property
    def _program(self) -> Optional[Dict[str, Optional[str]]]:
        now, prime = self.coordinator.data
        schedule = now if self._slot == SLOT_NOW else prime
        return schedule.get(self._channel)

    @property
    def native_value(self) -> str:
        program = self._program
        return program["titolo"] if program else NO_DATA

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        program = self._program or {}
        return {
            "canale": self._channel,
            "nazione": self._country_code,
            "fonte": COUNTRIES[self._country_code].name,
            "tipo": self._slot,
            "posizione": self._position,
            "orario_inizio": program.get("orario_inizio"),
            "orario_fine": program.get("orario_fine"),
            "genere": program.get("genere"),
            "locandina": program.get("locandina"),
            "descrizione": program.get("descrizione"),
        }
