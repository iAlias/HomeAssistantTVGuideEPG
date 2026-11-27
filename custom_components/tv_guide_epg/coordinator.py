"""Refreshes one EPG source on its own interval."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .sources.base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)


def _merge_with_previous(current: Schedule, previous: Optional[Schedule]) -> Schedule:
    return current if current else (previous or current)


class EpgCoordinator(DataUpdateCoordinator[Tuple[Schedule, Schedule]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, source: ScheduleSource,
                 source_id: str = "default", source_name: str = "EPG") -> None:
        super().__init__(
            hass, _LOGGER, name=f"TV Guide EPG - {source_name}",
            config_entry=entry, update_interval=source.refresh_interval,
        )
        self._source = source
        self.source_id = source_id
        self.source_name = source_name
        self.last_source_error: str | None = None

    @property
    def channels(self) -> list[str]:
        return self._source.channels

    async def _async_update_data(self) -> Tuple[Schedule, Schedule]:
        previous = self.data
        try:
            now, prime = await self._source.get_schedules()
        except Exception as err:  # noqa: BLE001
            self.last_source_error = str(err)
            _LOGGER.exception("TV Guide EPG source %s update failed", self.source_id)
            if previous is not None:
                return previous
            return {}, {}
        if not now and not prime:
            self.last_source_error = "La sorgente non ha restituito programmi"
        else:
            self.last_source_error = None
        if previous is not None:
            prev_now, prev_prime = previous
            now = _merge_with_previous(now, prev_now)
            prime = _merge_with_previous(prime, prev_prime)
        return now, prime
