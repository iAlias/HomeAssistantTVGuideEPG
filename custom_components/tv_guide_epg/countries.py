"""Registry mapping countries to their EPG data sources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import aiohttp

from .sources.base import ScheduleSource
from .sources.sorrisi import SorrisiSource
from .sources.xmltv import XmltvSource
from .sources.named_xmltv import NamedXmltvSource
from .sources.zappr import ZapprSource

EPGSHARE01_URL = "https://epgshare01.online/epgshare01/epg_ripper_{tag}.xml.gz"
IPTV_EPG_URL = "https://iptv-epg.org/files/epg-it.xml"
EPGITALIA_URL = "https://www.epgitalia.tv/guidexz"
SourceFactory = Callable[[aiohttp.ClientSession, Optional[int], float], ScheduleSource]

ITALY_SOURCES = {
    "sorrisi": ("Sorrisi", lambda session, minutes, prime: SorrisiSource(session)),
    "iptv_epg": ("IPTV-EPG.org", lambda session, minutes, prime: NamedXmltvSource(session, IPTV_EPG_URL)),
    "zappr": ("ZapprTV", lambda session, minutes, prime: ZapprSource(session)),
    "epgitalia": ("EPG Italia", lambda session, minutes, prime: NamedXmltvSource(session, EPGITALIA_URL)),
}


@dataclass(frozen=True)
class CountryConfig:
    name: str
    configurable_interval: bool
    make_source: SourceFactory


def _xmltv_factory(tag: str, timezone_name: str, channels: Dict[str, str]) -> SourceFactory:
    channel_order: List[str] = list(channels)

    def make_source(session, minutes, prime_time_hour=21):
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


def make_italy_sources(session, minutes=None, prime=21):
    return {
        source_id: factory(session, minutes, prime)
        for source_id, (_name, factory) in ITALY_SOURCES.items()
    }


def source_name(source_id: str) -> str:
    return ITALY_SOURCES.get(source_id, (source_id, None))[0]


def _italy_factory(session, _minutes, _prime=21):
    return SorrisiSource(session)


COUNTRIES: Dict[str, CountryConfig] = {
    "IT": CountryConfig("Italia", False, _italy_factory),
    "UK": CountryConfig("Regno Unito", True, _xmltv_factory("UK1", "Europe/London", {
        "BBC.One.Lon.HD.uk": "BBC One", "BBC.Two.HD.uk": "BBC Two",
        "ITV1.HD.uk": "ITV1", "Channel.4.HD.uk": "Channel 4",
        "Channel.5.HD.uk": "Channel 5",
    })),
    "DE": CountryConfig("Germania", True, _xmltv_factory("DE1", "Europe/Berlin", {
        "Das.Erste.de": "Das Erste", "ZDF.de": "ZDF", "RTL.de": "RTL",
        "SAT.1.de": "SAT.1", "ProSieben.de": "ProSieben", "VOX.de": "VOX",
    })),
    "FR": CountryConfig("Francia", True, _xmltv_factory("FR1", "Europe/Paris", {
        "TF1.fr": "TF1", "France.2.fr": "France 2", "France.3.fr": "France 3",
        "France.5.fr": "France 5", "M6.fr": "M6", "Arte.fr": "Arte",
    })),
    "ES": CountryConfig("Spagna", True, _xmltv_factory("ES1", "Europe/Madrid", {
        "La.1.es": "La 1", "La.2.es": "La 2", "Antena.3.es": "Antena 3",
        "Cuatro.es": "Cuatro", "Telecinco.es": "Telecinco", "laSexta.es": "laSexta",
    })),
}
