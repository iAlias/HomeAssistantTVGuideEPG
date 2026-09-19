"""Registry mapping a country code to its display name and data source.

Adding a country means adding one entry here — either reusing ``XmltvSource``
with an epgshare01.online tag and channel list, or pointing at a bespoke
``ScheduleSource`` when the country has no usable XMLTV feed (as with Italy).

Every channel id below was verified against the real feed on 2026-09-19: ids
that exist in the channel list but carry no programmes (``Channel.5.uk`` was
one) are deliberately excluded in favour of the variant that has data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import aiohttp

from .sources.base import ScheduleSource
from .sources.sorrisi import SorrisiSource
from .sources.xmltv import XmltvSource

EPGSHARE01_URL = "https://epgshare01.online/epgshare01/epg_ripper_{tag}.xml.gz"

SourceFactory = Callable[[aiohttp.ClientSession, Optional[int]], ScheduleSource]


@dataclass(frozen=True)
class CountryConfig:
    """How one country is fetched and presented."""

    name: str
    configurable_interval: bool
    make_source: SourceFactory


def _xmltv_factory(tag: str, channels: Dict[str, str]) -> SourceFactory:
    """Build a factory for an epgshare01.online country.

    ``channels`` maps the feed's channel id to the display name shown to the
    user, and its order is the order channels appear in the sensors.
    """
    channel_order: List[str] = list(channels)

    def make_source(session: aiohttp.ClientSession, minutes: Optional[int]) -> ScheduleSource:
        return XmltvSource(
            session,
            url=EPGSHARE01_URL.format(tag=tag),
            channel_order=channel_order,
            channel_names=dict(channels),
            refresh_minutes=minutes or 120,
        )

    return make_source


COUNTRIES: Dict[str, CountryConfig] = {
    "IT": CountryConfig(
        name="Italia",
        configurable_interval=False,
        make_source=lambda session, _minutes: SorrisiSource(session),
    ),
    "UK": CountryConfig(
        name="Regno Unito",
        configurable_interval=True,
        make_source=_xmltv_factory("UK1", {
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
        make_source=_xmltv_factory("DE1", {
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
        make_source=_xmltv_factory("FR1", {
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
        make_source=_xmltv_factory("ES1", {
            "La.1.es": "La 1",
            "La.2.es": "La 2",
            "Antena.3.es": "Antena 3",
            "Cuatro.es": "Cuatro",
            "Telecinco.es": "Telecinco",
            "laSexta.es": "laSexta",
        }),
    ),
}
