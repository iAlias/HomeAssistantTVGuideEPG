"""Adapter for the public ZapprTV aggregated EPG JSON feed."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import aiohttp
import async_timeout

from .base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)
URL = "https://epg.zappr.stream/it/dtt/national.json"
ROME = ZoneInfo("Europe/Rome")

# Source and ID pairs published in ZapprTV/channels' national Italian lineup.
CHANNEL_MAP = {
    "Rai 1": ("raiplay", "rai-1"),
    "Rai 2": ("raiplay", "rai-2"),
    "Rai 3": ("raiplay", "rai-3"),
    "Rai 4": ("raiplay", "rai-4"),
    "Rai 5": ("raiplay", "rai-5"),
    "Rai Movie": ("raiplay", "rai-movie"),
    "Rete 4": ("blue", "348"),
    "Canale 5": ("blue", "79"),
    "Italia 1": ("blue", "215"),
    "La7": ("blue", "237"),
    "TV8": ("blue", "266"),
    "Nove": ("blue", "118"),
    "20": ("blue", "1379"),
    "Iris": ("blue", "214"),
    "Real Time": ("blue", "346"),
    "DMAX": ("blue", "137"),
    "Cielo": ("blue", "96"),
}
CHANNELS = list(CHANNEL_MAP)


class ZapprSource(ScheduleSource):
    """Read the Zappr generated JSON and calculate current/prime-time programmes."""

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    @property
    def channels(self) -> List[str]:
        return list(CHANNELS)

    @property
    def refresh_interval(self):
        return timedelta(hours=4)

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        async with async_timeout.timeout(45):
            async with self._session.get(URL, timeout=40) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)

        now = datetime.now(ROME)
        current: Schedule = {}
        prime: Schedule = {}
        for channel, (provider, channel_id) in CHANNEL_MAP.items():
            entries = payload.get(provider, {}).get(str(channel_id), [])
            parsed = []
            for entry in entries:
                try:
                    start = datetime.fromisoformat(entry["startTime"]["iso"]).astimezone(ROME)
                    end = datetime.fromisoformat(entry["endTime"]["iso"]).astimezone(ROME)
                except (KeyError, TypeError, ValueError):
                    continue
                if end <= start:
                    continue
                parsed.append((start, end, entry))
            parsed.sort(key=lambda item: item[0])
            on_air = next((item for item in parsed if item[0] <= now < item[1]), None)
            if on_air:
                start, end, entry = on_air
                current[channel] = self._format(entry, start, end)
                upcoming = [
                    self._format(item, begin, finish)
                    for begin, finish, item in parsed if begin > now
                ][:4]
                current[channel]["prossimi"] = upcoming

            target = now.replace(hour=21, minute=0, second=0, microsecond=0)
            if not parsed:
                continue
            chosen = min(parsed, key=lambda item: abs((item[0] - target).total_seconds()))
            prime[channel] = self._format(chosen[2], chosen[0], chosen[1])

        if not current and not prime:
            raise ValueError("ZapprTV non ha restituito programmi per i canali configurati")
        return current, prime

    @staticmethod
    def _format(entry, start, end):
        return {
            "titolo": entry.get("name") or "Programma",
            "orario_inizio": start.strftime("%H:%M"),
            "orario_fine": end.strftime("%H:%M"),
            "genere": entry.get("category"),
            "locandina": entry.get("image"),
            "descrizione": entry.get("description") or entry.get("subtitle"),
        }
