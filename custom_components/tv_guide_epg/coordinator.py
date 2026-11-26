"""Refreshes a country's TV schedule on its source's own interval."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .sources.base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)


def _merge_with_previous(current: Schedule, previous: Optional[Schedule]) -> Schedule:
    """Fall back to the previous successful parse when the new one is empty.

    An empty parse almost always means the source changed shape or went down (a
    schedule with genuinely nothing on air is not a real scenario). Keeping the
    last known-good schedule instead of collapsing straight to "Nessun dato"
    buys time to notice and fix the parser before the sensors go blank.
    """
    return current if current else (previous or current)


class EpgCoordinator(DataUpdateCoordinator[Tuple[Schedule, Schedule]]):
    """Refreshes both schedules together, at the cadence the source asks for."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, source: ScheduleSource
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="TV Guide EPG",
            config_entry=entry,
            update_interval=source.refresh_interval,
        )
        self._source = source
        self.last_source_error: str | None = None

    @property
    def channels(self) -> list[str]:
        """Channels this entry covers, in display order."""
        return self._source.channels

    async def _async_update_data(self) -> Tuple[Schedule, Schedule]:
        previous = self.data
        try:
            now, prime = await self._source.get_schedules()
        except Exception as err:  # noqa: BLE001
            self.last_source_error = str(err)
            _LOGGER.exception("TV Guide EPG source update failed")
            if previous is not None:
                return previous
            return {}, {}

        if not now and not prime:
            self.last_source_error = "La sorgente non ha restituito programmi"
            _LOGGER.warning("TV Guide EPG source returned an empty schedule")
        else:
            self.last_source_error = None

        if previous is not None:
            prev_now, prev_prime = previous
            now = _merge_with_previous(now, prev_now)
            prime = _merge_with_previous(prime, prev_prime)
        return now, prime
