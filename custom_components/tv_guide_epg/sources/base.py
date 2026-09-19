"""The ScheduleSource interface every country's data provider implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

Schedule = Dict[str, Dict[str, Optional[str]]]


class ScheduleSource(ABC):
    """A provider of {channel: program_info} "now" and "prime time" schedules."""

    @property
    @abstractmethod
    def channels(self) -> List[str]:
        """The channels this source covers, in display order.

        Declared up front rather than derived from fetched data, so the
        entities exist even when the first refresh comes back empty.
        """

    @property
    @abstractmethod
    def refresh_interval(self) -> timedelta:
        """How often the coordinator should poll this source."""

    @abstractmethod
    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        """Return (now_schedule, prime_time_schedule)."""
