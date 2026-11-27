"""XMLTV providers matched by channel display names instead of provider-specific IDs."""
from __future__ import annotations

import gzip
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from xml.etree import ElementTree

import aiohttp
import async_timeout

from .base import Schedule, ScheduleSource
from .xmltv import (
    _parse_xmltv,
    _programme_nearest,
    _programme_on_air,
    _programme_upcoming,
    _resolve_timezone,
)

_LOGGER = logging.getLogger(__name__)

CHANNELS = [
    "Rai 1", "Rai 2", "Rai 3", "Rai 4", "Rai 5", "Rai Movie",
    "Rete 4", "Canale 5", "Italia 1", "La7", "TV8", "Nove",
    "20", "Iris", "La5", "Real Time", "DMAX", "Cielo",
]

ALIASES = {
    "Rai 1": ("rai 1", "rai1", "rai 1 hd", "rai1.it", "rai1.it@sd"),
    "Rai 2": ("rai 2", "rai2", "rai 2 hd", "rai2.it", "rai2.it@sd"),
    "Rai 3": ("rai 3", "rai3", "rai 3 hd", "rai3.it", "rai3.it@sd"),
    "Rai 4": ("rai 4", "rai4", "rai 4 hd", "rai4.it"),
    "Rai 5": ("rai 5", "rai5", "rai 5 hd", "rai5.it"),
    "Rai Movie": ("rai movie", "raimovie", "rai movie hd"),
    "Rete 4": ("rete 4", "rete4", "rete 4 hd", "rete4.it"),
    "Canale 5": ("canale 5", "canale5", "canale 5 hd", "canale5.it"),
    "Italia 1": ("italia 1", "italia1", "italia 1 hd", "italia1.it"),
    "La7": ("la7", "la 7", "la7 hd", "la7.it"),
    "TV8": ("tv8", "tv 8", "tv8 hd"),
    "Nove": ("nove", "nove hd"),
    "20": ("20", "20 mediaset", "mediaset 20", "canale 20"),
    "Iris": ("iris", "iris hd"),
    "La5": ("la5", "la 5", "la5 hd"),
    "Real Time": ("real time", "realtime", "real time hd"),
    "DMAX": ("dmax", "dmax hd"),
    "Cielo": ("cielo", "cielo hd"),
}


def _norm(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


class NamedXmltvSource(ScheduleSource):
    """Download XMLTV and map provider channel IDs through display-name aliases."""

    def __init__(self, session: aiohttp.ClientSession, url: str, refresh_minutes: int = 240):
        self._session = session
        self._url = url
        self._refresh_minutes = refresh_minutes

    @property
    def channels(self) -> List[str]:
        return list(CHANNELS)

    @property
    def refresh_interval(self):
        from datetime import timedelta
        return timedelta(minutes=self._refresh_minutes)

    async def _fetch(self) -> bytes:
        async with async_timeout.timeout(60):
            async with self._session.get(self._url, timeout=55) as response:
                response.raise_for_status()
                return await response.read()

    async def get_schedules(self):
        raw = await self._fetch()
        if raw.startswith(b"\x1f\x8b"):
            raw = gzip.decompress(raw)
        root = ElementTree.fromstring(raw)

        aliases = {_norm(alias): channel for channel, names in ALIASES.items() for alias in names}
        id_to_name: Dict[str, str] = {}
        for channel in root.findall("channel"):
            channel_id = channel.get("id")
            if not channel_id:
                continue
            names = [el.text.strip() for el in channel.findall("display-name") if el.text]
            for name in names:
                match = aliases.get(_norm(name))
                if match:
                    id_to_name[channel_id] = match
                    break

        ordered_ids = []
        channel_names = {}
        for channel_name in CHANNELS:
            found = next((cid for cid, name in id_to_name.items() if name == channel_name), None)
            if found:
                ordered_ids.append(found)
                channel_names[found] = channel_name

        if not ordered_ids:
            raise ValueError(f"Nessun canale italiano riconosciuto nel feed XMLTV: {self._url}")

        programmes = _parse_xmltv(raw, ordered_ids)
        now = datetime.now(timezone.utc)
        current = _programme_on_air(programmes, now, ordered_ids, channel_names)
        upcoming = _programme_upcoming(programmes, now, ordered_ids, channel_names)
        for channel, info in current.items():
            info["prossimi"] = upcoming.get(channel, [])
        prime = _programme_nearest(
            programmes, now, 21, ordered_ids, channel_names, _resolve_timezone("Europe/Rome")
        )
        return current, prime
