"""Tests for the pure XMLTV parsing/scheduling logic in sources.xmltv.

All time-dependent assertions inject an explicit ``now`` rather than reading the
system clock, so the suite gives the same answer regardless of when it runs.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from xml.etree import ElementTree

from custom_components.tv_guide_epg.sources.xmltv import (
    XmltvSource,
    _parse_xmltv,
    _parse_xmltv_datetime,
    _programme_nearest,
    _programme_on_air,
    _resolve_timezone,
)

FIXTURES = Path(__file__).parent / "fixtures" / "xmltv"
FIXTURE = (FIXTURES / "uk_excerpt.xml").read_bytes()
MADRID_FIXTURE = (FIXTURES / "es_excerpt.xml").read_bytes()

CHANNEL_ORDER = ["BBC.One.Lon.HD.uk", "ITV1.HD.uk"]
CHANNEL_NAMES = {"BBC.One.Lon.HD.uk": "BBC One", "ITV1.HD.uk": "ITV1", "Channel.5.uk": "Channel 5"}

ES_ORDER = ["La.1.es"]
ES_NAMES = {"La.1.es": "La 1"}


# --- timestamp parsing -------------------------------------------------------

def test_parse_xmltv_datetime_reads_utc_offset():
    assert _parse_xmltv_datetime("20260919200000 +0000") == datetime(
        2026, 9, 19, 20, 0, tzinfo=timezone.utc
    )


def test_parse_xmltv_datetime_handles_negative_offset():
    assert _parse_xmltv_datetime("20260919200000 -0500").utcoffset() == timedelta(hours=-5)


def test_parse_xmltv_datetime_handles_positive_offset():
    assert _parse_xmltv_datetime("20260919200000 +0200").utcoffset() == timedelta(hours=2)


def test_parse_xmltv_datetime_defaults_to_utc_without_offset():
    assert _parse_xmltv_datetime("20260919200000").tzinfo == timezone.utc


# --- parsing -----------------------------------------------------------------

def test_parse_xmltv_extracts_only_wanted_channels():
    result = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    assert set(result) == set(CHANNEL_ORDER)
    assert len(result["BBC.One.Lon.HD.uk"]) == 3
    assert len(result["ITV1.HD.uk"]) == 2


def test_parse_xmltv_ignores_channels_not_requested():
    assert set(_parse_xmltv(FIXTURE, ["BBC.One.Lon.HD.uk"])) == {"BBC.One.Lon.HD.uk"}


def test_parse_xmltv_returns_empty_list_for_channel_without_programmes():
    assert _parse_xmltv(FIXTURE, ["Channel.5.uk"]) == {"Channel.5.uk": []}


def test_parse_xmltv_sorts_programmes_by_start_time():
    programmes = _parse_xmltv(FIXTURE, ["BBC.One.Lon.HD.uk"])["BBC.One.Lon.HD.uk"]
    starts = [item["_start"] for item in programmes]
    assert starts == sorted(starts)


def test_parse_xmltv_drops_zero_length_programmes():
    """Real feeds contain start == stop entries; they can never be on air."""
    programmes = _parse_xmltv(MADRID_FIXTURE, ES_ORDER)["La.1.es"]
    titles = [item["titolo"] for item in programmes]
    assert "Entrata a durata zero" not in titles
    assert "Telediario" in titles


def test_parse_xmltv_raises_on_malformed_xml():
    with pytest.raises(ElementTree.ParseError):
        _parse_xmltv(b"<tv><programme", CHANNEL_ORDER)


# --- on air ------------------------------------------------------------------

def test_programme_on_air_picks_the_programme_covering_now():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 21, 30, tzinfo=timezone.utc)
    result = _programme_on_air(programmes, now, CHANNEL_ORDER, CHANNEL_NAMES)
    assert result["BBC One"]["titolo"] == "Casualty"
    assert result["ITV1"]["titolo"] == "Emmerdale"


def test_programme_on_air_empty_when_nothing_covers_now():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 5, 0, tzinfo=timezone.utc)
    assert _programme_on_air(programmes, now, CHANNEL_ORDER, CHANNEL_NAMES) == {}


def test_programme_on_air_formats_times_and_keeps_optional_fields():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 20, 30, tzinfo=timezone.utc)
    info = _programme_on_air(programmes, now, CHANNEL_ORDER, CHANNEL_NAMES)["BBC One"]
    assert info == {
        "titolo": "Antiques Roadshow",
        "orario_inizio": "20:00",
        "orario_fine": "21:00",
        "genere": "Factual",
        "locandina": "https://example.com/antiques.png",
        "descrizione": "Experts value family heirlooms.",
    }


def test_missing_optional_fields_become_none():
    programmes = _parse_xmltv(FIXTURE, ["ITV1.HD.uk"])
    now = datetime(2026, 9, 19, 12, 15, tzinfo=timezone.utc)
    info = _programme_on_air(programmes, now, ["ITV1.HD.uk"], CHANNEL_NAMES)["ITV1"]
    assert info["titolo"] == "Loose Women"
    assert info["descrizione"] is None
    assert info["locandina"] is None


def test_on_air_times_are_rendered_in_the_country_timezone():
    """The UK feed publishes +0000 even in summer, when London is +0100."""
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 20, 30, tzinfo=timezone.utc)
    info = _programme_on_air(
        programmes, now, CHANNEL_ORDER, CHANNEL_NAMES, ZoneInfo("Europe/London")
    )["BBC One"]
    # 20:00 UTC is 21:00 British Summer Time.
    assert info["orario_inizio"] == "21:00"
    assert info["orario_fine"] == "22:00"


# --- prime time --------------------------------------------------------------

def test_programme_nearest_picks_closest_start_to_target_hour():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    result = _programme_nearest(programmes, now, 21, CHANNEL_ORDER, CHANNEL_NAMES)
    # Casualty starts exactly at 21:00 in the feed's own offset.
    assert result["BBC One"]["titolo"] == "Casualty"
    # Emmerdale starts 20:55, five minutes from the target.
    assert result["ITV1"]["titolo"] == "Emmerdale"


def test_programme_nearest_uses_the_country_timezone_not_utc():
    """A +0200 feed must not have its prime time computed in UTC.

    The Spanish excerpt has a programme at 21:00 Madrid time and another at
    23:00 Madrid time. Computing the 21:00 target in UTC would wrongly pick the
    23:00 one (21:00 UTC == 23:00 in Madrid).
    """
    programmes = _parse_xmltv(MADRID_FIXTURE, ES_ORDER)
    now = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    result = _programme_nearest(
        programmes, now, 21, ES_ORDER, ES_NAMES, ZoneInfo("Europe/Madrid")
    )
    assert result["La 1"]["titolo"] == "Prima serata spagnola"
    assert result["La 1"]["orario_inizio"] == "21:00"


def test_programme_nearest_skips_channels_without_programmes():
    programmes = _parse_xmltv(FIXTURE, ["Channel.5.uk"])
    now = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    assert _programme_nearest(programmes, now, 21, ["Channel.5.uk"], CHANNEL_NAMES) == {}


# --- timezone resolution -----------------------------------------------------

def test_resolve_timezone_returns_the_named_zone():
    assert _resolve_timezone("Europe/Madrid") == ZoneInfo("Europe/Madrid")


def test_resolve_timezone_returns_none_for_unknown_zone():
    assert _resolve_timezone("Not/AZone") is None


def test_resolve_timezone_returns_none_when_unset():
    assert _resolve_timezone(None) is None


# --- source configuration ----------------------------------------------------

def test_refresh_interval_reflects_configured_minutes():
    source = XmltvSource(
        session=None, url="https://example.com/epg.xml.gz", channel_order=[], refresh_minutes=30
    )
    assert source.refresh_interval == timedelta(minutes=30)


def test_refresh_interval_defaults_to_two_hours():
    source = XmltvSource(session=None, url="https://example.com/epg.xml.gz", channel_order=[])
    assert source.refresh_interval == timedelta(minutes=120)
