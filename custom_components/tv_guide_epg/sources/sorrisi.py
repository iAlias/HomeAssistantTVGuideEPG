"""Reads Italian TV schedules from sorrisi.com."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple

import aiohttp
import async_timeout
from bs4 import BeautifulSoup

from .base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)

URL_NOW = "https://www.sorrisi.com/guidatv/ora-in-tv/"
URL_PRIME = "https://www.sorrisi.com/guidatv/stasera-in-tv/"

CHANNEL_ORDER = [
    "Rai 1",
    "Rai 2",
    "Rai 3",
    "Rete 4",
    "Canale 5",
    "Italia 1",
    "La7",
    "TV8",
    "NOVE",
]

SKIP_CHANNELS = {"IRIS", "CANALE20", "20", "20MEDIASET", "RAI4"}


def _normalize(channel: str) -> str:
    """Key used to match a channel name regardless of spacing or case.

    sorrisi.com is not consistent about this: the same channels appear as
    "La 7", "Nove" and "TV 8" on the page while being commonly written La7,
    NOVE and TV8. Comparing raw names left those three unmatched, so they fell
    out of the LCN ordering and got sorted alphabetically at the end.
    """
    return channel.upper().replace(" ", "")


CHANNEL_ORDER_KEYS = [_normalize(name) for name in CHANNEL_ORDER]


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with async_timeout.timeout(15):
            resp = await session.get(url)
            if resp.status != 200:
                _LOGGER.warning("Sorrisi: %s status %s", url, resp.status)
                return ""
            return await resp.text()
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error fetching %s: %s", url, err)
        return ""


def _extract_start_time(article) -> Optional[str]:
    time_el = article.find("time", class_="gtv-program-time")
    return time_el.get_text(strip=True) if time_el else None


def _extract_end_time(article) -> Optional[str]:
    time_el = article.find("time", class_="gtv-program-time")
    end_ts = time_el.get("data-end-ts") if time_el else None
    if not end_ts:
        return None
    try:
        return datetime.fromtimestamp(int(end_ts)).strftime("%H:%M")
    except (TypeError, ValueError, OSError):
        return None


def _extract_genre(article) -> Optional[str]:
    label = article.find("div", class_="gtv-program-label")
    return label.get_text(strip=True) if label else None


def _extract_image(article) -> Optional[str]:
    img = article.select_one("figure.gtv-program-image img")
    src = img.get("src") if img else None
    if not src:
        return None
    return f"https:{src}" if src.startswith("//") else src


def _extract_abstract(article) -> Optional[str]:
    abstract = article.find("p", class_="gtv-program-abstract")
    return abstract.get_text(strip=True) if abstract else None


def _parse_programs(html: str) -> Schedule:
    """Return a mapping {channel: program_info} from the provided HTML.

    ``program_info`` always has a ``titolo`` key; the other fields are ``None``
    when sorrisi.com does not publish them for that program.
    """
    soup = BeautifulSoup(html, "html.parser")
    mapping: Schedule = {}

    for header in soup.select("div.gtv-channel-header"):
        logo = header.find("a", class_="gtv-logo")
        channel = logo.get("data-channel-name") if logo else header.get_text(strip=True)

        article = header.find_next("article", class_="gtv-program-on-air") or \
            header.find_next("article", class_="gtv-program")
        title_el = article.find("h3", class_="gtv-program-title") if article else None
        if not (channel and title_el):
            continue

        if _normalize(channel) in SKIP_CHANNELS:
            continue

        mapping[channel.strip()] = {
            "titolo": title_el.get_text(strip=True),
            "orario_inizio": _extract_start_time(article),
            "orario_fine": _extract_end_time(article),
            "genere": _extract_genre(article),
            "locandina": _extract_image(article),
            "descrizione": _extract_abstract(article),
        }

    def sort_key(item):
        try:
            idx = CHANNEL_ORDER_KEYS.index(_normalize(item[0]))
        except ValueError:
            idx = len(CHANNEL_ORDER_KEYS)
        return idx, item[0]

    return dict(sorted(mapping.items(), key=sort_key))


class SorrisiSource(ScheduleSource):
    """Reads Italian TV schedules from sorrisi.com."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @property
    def refresh_interval(self) -> timedelta:
        # sorrisi.com serves small, already-filtered "now"/"tonight" pages, so a
        # short interval is cheap here (unlike the multi-MB XMLTV feeds).
        return timedelta(minutes=10)

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        html_now, html_prime = await asyncio.gather(
            _fetch_page(self._session, URL_NOW),
            _fetch_page(self._session, URL_PRIME),
        )
        return _parse_programs(html_now), _parse_programs(html_prime)
