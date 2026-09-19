"""Generic XMLTV schedule source, used for the countries covered by epgshare01.online.

Unlike sorrisi.com, an XMLTV feed publishes a whole day's schedule rather than
pre-filtered "now"/"tonight" pages, so this module computes both locally from
the programme time windows. That keeps the definition of "on air" under our own
control (and unit-testable with an injected clock) instead of trusting whatever
a site decided to highlight.
"""

from __future__ import annotations

import gzip
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import aiohttp
import async_timeout

from .base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)

Programme = Dict[str, object]

PRIME_TIME_HOUR = 21


def _parse_xmltv_datetime(value: str) -> datetime:
    """Parse an XMLTV timestamp such as ``20260919200000 +0000``."""
    naive_part, _, offset_part = value.strip().partition(" ")
    parsed = datetime.strptime(naive_part, "%Y%m%d%H%M%S")
    if not offset_part:
        return parsed.replace(tzinfo=timezone.utc)
    sign = -1 if offset_part.startswith("-") else 1
    hours = int(offset_part[1:3] or 0)
    minutes = int(offset_part[3:5] or 0)
    offset = timedelta(hours=hours, minutes=minutes) * sign
    return parsed.replace(tzinfo=timezone(offset))


def _text_or_none(element) -> Optional[str]:
    if element is None or not element.text:
        return None
    stripped = element.text.strip()
    return stripped or None


def _parse_xmltv(xml_bytes: bytes, wanted_channels: List[str]) -> Dict[str, List[Programme]]:
    """Parse XMLTV bytes into {channel_id: [programme, ...]} for the wanted channels only.

    Filtering by channel while parsing matters: the real feeds carry tens of
    thousands of programmes across thousands of channels, and only a handful are
    ever displayed.
    """
    wanted = set(wanted_channels)
    root = ElementTree.fromstring(xml_bytes)
    result: Dict[str, List[Programme]] = {channel: [] for channel in wanted_channels}

    for programme_el in root.findall("programme"):
        channel_id = programme_el.get("channel")
        if channel_id not in wanted:
            continue

        title = _text_or_none(programme_el.find("title"))
        if not title:
            continue

        start_raw = programme_el.get("start")
        stop_raw = programme_el.get("stop")
        if not start_raw or not stop_raw:
            continue
        try:
            start = _parse_xmltv_datetime(start_raw)
            stop = _parse_xmltv_datetime(stop_raw)
        except ValueError:
            continue

        icon_el = programme_el.find("icon")

        result[channel_id].append({
            "titolo": title,
            "_start": start,
            "_stop": stop,
            "genere": _text_or_none(programme_el.find("category")),
            "locandina": icon_el.get("src") if icon_el is not None else None,
            "descrizione": _text_or_none(programme_el.find("desc")),
        })

    for programmes in result.values():
        programmes.sort(key=lambda item: item["_start"])

    return result


def _to_schedule_entry(programme: Programme) -> Dict[str, Optional[str]]:
    start: datetime = programme["_start"]
    stop: datetime = programme["_stop"]
    return {
        "titolo": programme["titolo"],
        "orario_inizio": start.strftime("%H:%M"),
        "orario_fine": stop.strftime("%H:%M"),
        "genere": programme["genere"],
        "locandina": programme["locandina"],
        "descrizione": programme["descrizione"],
    }


def _programme_on_air(
    programmes_by_channel: Dict[str, List[Programme]],
    now: datetime,
    channel_order: List[str],
    channel_names: Dict[str, str],
) -> Schedule:
    """Return {display_name: program_info} for the programme airing at ``now``."""
    schedule: Schedule = {}
    for channel_id in channel_order:
        for programme in programmes_by_channel.get(channel_id, []):
            if programme["_start"] <= now < programme["_stop"]:
                schedule[channel_names.get(channel_id, channel_id)] = _to_schedule_entry(programme)
                break
    return schedule


def _programme_nearest(
    programmes_by_channel: Dict[str, List[Programme]],
    now: datetime,
    target_hour: int,
    channel_order: List[str],
    channel_names: Dict[str, str],
) -> Schedule:
    """Return {display_name: program_info} for the programme closest to ``target_hour``."""
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    schedule: Schedule = {}
    for channel_id in channel_order:
        candidates = programmes_by_channel.get(channel_id, [])
        if not candidates:
            continue
        closest = min(candidates, key=lambda p: abs((p["_start"] - target).total_seconds()))
        schedule[channel_names.get(channel_id, channel_id)] = _to_schedule_entry(closest)
    return schedule


class XmltvSource(ScheduleSource):
    """Downloads a full day's XMLTV feed and derives now/prime-time locally."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        url: str,
        channel_order: List[str],
        channel_names: Optional[Dict[str, str]] = None,
        refresh_minutes: int = 120,
    ) -> None:
        self._session = session
        self._url = url
        self._channel_order = channel_order
        self._channel_names = channel_names or {}
        self._refresh_minutes = refresh_minutes

    @property
    def refresh_interval(self) -> timedelta:
        return timedelta(minutes=self._refresh_minutes)

    async def _fetch(self) -> bytes:
        try:
            async with async_timeout.timeout(30):
                resp = await self._session.get(self._url)
                if resp.status != 200:
                    _LOGGER.warning("XMLTV: %s status %s", self._url, resp.status)
                    return b""
                return await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error fetching %s: %s", self._url, err)
            return b""

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        raw = await self._fetch()
        if not raw:
            return {}, {}

        try:
            xml_bytes = gzip.decompress(raw)
        except (OSError, EOFError):
            xml_bytes = raw

        try:
            programmes_by_channel = _parse_xmltv(xml_bytes, self._channel_order)
        except ElementTree.ParseError as err:
            _LOGGER.error("Malformed XMLTV from %s: %s", self._url, err)
            return {}, {}

        now = datetime.now(timezone.utc)
        return (
            _programme_on_air(programmes_by_channel, now, self._channel_order, self._channel_names),
            _programme_nearest(
                programmes_by_channel, now, PRIME_TIME_HOUR, self._channel_order, self._channel_names
            ),
        )
