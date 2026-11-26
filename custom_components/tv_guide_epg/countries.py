"""Registry mapping countries to their EPG data sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import aiohttp

from .sources.base import ScheduleSource
from .sources.sorrisi import SorrisiSource
from .sources.xmltv import XmltvSource

EPGSHARE01_URL = "https://epgshare01.online/epgshare01/epg_ripper_{tag}.xml.gz"
SourceFactory = Callable[[aiohttp.ClientSession, Optional[int], int], ScheduleSource]


@dataclass(frozen=True)
class CountryConfig:
    """How a country is fetched and presented."""

    name: str
    configurable_interval: bool
    make_source: SourceFactory


def _xmltv_factory(tag: str, timezone_name: str, channels: Dict[str, str]) -> SourceFactory:
    """Build a source factory for an epgshare01.online country."""
    channel_order: List[str] = list(channels)

    def make_source(
        session: aiohttp.ClientSession,
        minutes: Optional[int],
        prime_time_hour: int = 21,
    ) -> ScheduleSource:
        return XmltvSource(
            session,
            url=EPGSHARE01_URL.format(tag=tag),
            channel_order=channel_order,
            channel_names=dict(channels),
            timezone_name=timezone_name,
            refresh_minutes=minutes or 120,
            prime_time_hour=prime_time_hour,
        )

    return make_source


def _italy_factory(session: aiohttp.ClientSession, _minutes: Optional[int], _prime: int = 21):
    return SorrisiSource(session)


COUNTRIES: Dict[str, CountryConfig] = {
    "IT": CountryConfig(
        name="Italia",
        configurable_interval=False,
        make_source=_italy_factory,
    ),
    "UK": CountryConfig(
        name="Regno Unito",
        configurable_interval=True,
        make_source=_xmltv_factory("UK1", "Europe/London", {
            "BBC.One.Lon.HD.uk": "BBC One",
            "BBC.Two.HD.uk": "BBC Two",
            "ITV1.HD.uk": "ITV1",
            "Channel.4.HD.uk": "Channel 4",
            "Channel.5.HD.uk": "Channel 5",
        }),
    ),
    "DE": CountryConfig(
        name="Germania",
        configurable_interval=True,
        make_source=_xmltv_factory("DE1", "Europe/Berlin", {
            "Das.Erste.de": "Das Erste",
            "ZDF.de": "ZDF",
            "RTL.de": "RTL",
            "SAT.1.de": "SAT.1",
            "ProSieben.de": "ProSieben",
            "VOX.de": "VOX",
        }),
    ),
    "FR": CountryConfig(
        name="Francia",
        configurable_interval=True,
        make_source=_xmltv_factory("FR1", "Europe/Paris", {
            "TF1.fr": "TF1",
            "France.2.fr": "France 2",
            "France.3.fr": "France 3",
            "France.5.fr": "France 5",
            "M6.fr": "M6",
            "Arte.fr": "Arte",
        }),
    ),
    "ES": CountryConfig(
        name="Spagna",
        configurable_interval=True,
        make_source=_xmltv_factory("ES1", "Europe/Madrid", {
            "La.1.es": "La 1",
            "La.2.es": "La 2",
            "Antena.3.es": "Antena 3",
            "Cuatro.es": "Cuatro",
            "Telecinco.es": "Telecinco",
            "laSexta.es": "laSexta",
        }),
    ),
}
