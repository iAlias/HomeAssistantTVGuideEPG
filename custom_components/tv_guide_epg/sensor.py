"""TV Guide EPG sensors.

Each config entry (one country) exposes:
- ``<name> - Ora in onda`` for the current programmes;
- ``<name> - Prima serata`` for the prime time programmes.
"""

from __future__ import annotations

from typing import Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COUNTRY, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors from a config entry."""
    coordinator: EpgCoordinator = hass.data[DOMAIN][entry.entry_id]
    base_name = entry.data.get("name", entry.title)
    country_code = entry.data[CONF_COUNTRY]
    async_add_entities([
        EpgNowSensor(base_name, country_code, coordinator),
        EpgPrimeSensor(base_name, country_code, coordinator),
    ])


class _EpgBase(CoordinatorEntity[EpgCoordinator], SensorEntity):
    """Common functionality for both sensors."""

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(coordinator)
        self._base_name = base_name
        self._country_code = country_code

    @staticmethod
    def _first_title(cache: Dict[str, Dict[str, Optional[str]]]) -> str:
        first = next(iter(cache.values()), None)
        return first["titolo"] if first else "Nessun dato"

    def _common_attributes(self) -> Dict[str, object]:
        return {
            "nazione": self._country_code,
            "fonte": COUNTRIES[self._country_code].name,
        }


class EpgNowSensor(_EpgBase):
    """Current programmes sensor."""

    _attr_icon = "mdi:television-play"

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(base_name, country_code, coordinator)
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = f"tvguide_epg_{country_code.lower()}_now"

    @property
    def native_value(self) -> str:
        cache_now, _ = self.coordinator.data
        return self._first_title(cache_now)

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        cache_now, _ = self.coordinator.data
        return {"programmi_correnti": cache_now, **self._common_attributes()}


class EpgPrimeSensor(_EpgBase):
    """Prime time programmes sensor."""

    _attr_icon = "mdi:movie-open"

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(base_name, country_code, coordinator)
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = f"tvguide_epg_{country_code.lower()}_prime"

    @property
    def native_value(self) -> str:
        _, cache_prime = self.coordinator.data
        return self._first_title(cache_prime)

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        _, cache_prime = self.coordinator.data
        return {"prima_serata": cache_prime, **self._common_attributes()}
