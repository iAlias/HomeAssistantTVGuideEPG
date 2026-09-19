"""Tests for sources.sorrisi._parse_programs against real sorrisi.com markup.

The fixtures are full pages saved from sorrisi.com. Parsing is the most fragile
part of this source: if sorrisi.com changes its markup, these tests catch it
before the sensors silently start returning "Nessun dato" in production.
"""

from datetime import timedelta
from pathlib import Path

from custom_components.tv_guide_epg.sources.sorrisi import (
    CHANNEL_ORDER,
    CHANNEL_ORDER_KEYS,
    SKIP_CHANNELS,
    SorrisiSource,
    _normalize,
    _parse_programs,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sorrisi"
ORA_IN_ONDA = (FIXTURES / "ora_in_onda.html").read_text(encoding="utf-8")
PRIMA_SERATA = (FIXTURES / "prima_serata.html").read_text(encoding="utf-8")


def test_parses_known_channel_from_ora_in_onda():
    result = _parse_programs(ORA_IN_ONDA)
    assert "Rai 1" in result
    assert result["Rai 1"]["titolo"]


def test_every_parsed_channel_is_recognised_by_the_lcn_order():
    """Guards the spacing/case mismatch that silently broke the ordering.

    sorrisi.com writes "La 7", "Nove" and "TV 8"; CHANNEL_ORDER lists La7, TV8
    and NOVE. Matching raw names left those three unrecognised, and the earlier
    version of this test missed it by only checking channels that already
    matched.
    """
    result = _parse_programs(ORA_IN_ONDA)
    unrecognised = [ch for ch in result if _normalize(ch) not in CHANNEL_ORDER_KEYS]
    assert unrecognised == []


def test_orders_channels_by_italian_lcn_numbering():
    result = _parse_programs(ORA_IN_ONDA)
    positions = [CHANNEL_ORDER_KEYS.index(_normalize(ch)) for ch in result]
    assert positions == sorted(positions)


def test_la7_tv8_and_nove_come_after_italia_1():
    """The three channels whose names differ from their common spelling."""
    order = [_normalize(ch) for ch in _parse_programs(ORA_IN_ONDA)]
    assert order.index("ITALIA1") < order.index("LA7") < order.index("TV8") < order.index("NOVE")


def test_excludes_skip_channels():
    result = _parse_programs(ORA_IN_ONDA)
    normalized = {channel.upper().replace(" ", "") for channel in result}
    assert normalized.isdisjoint(SKIP_CHANNELS)


def test_parses_prima_serata_fixture():
    result = _parse_programs(PRIMA_SERATA)
    assert "Rai 1" in result
    assert result["Rai 1"]["titolo"]


def test_empty_html_returns_empty_mapping():
    assert _parse_programs("") == {}


def test_malformed_html_does_not_raise():
    assert _parse_programs("<div><not really html") == {}


def test_program_info_has_expected_keys():
    result = _parse_programs(ORA_IN_ONDA)
    info = result["Rai 1"]
    assert set(info) == {
        "titolo", "orario_inizio", "orario_fine", "genere", "locandina", "descrizione",
    }


def test_poster_url_is_absolute_when_present():
    result = _parse_programs(ORA_IN_ONDA)
    for info in result.values():
        if info["locandina"] is not None:
            assert info["locandina"].startswith("http")


def test_refresh_interval_is_ten_minutes():
    assert SorrisiSource(session=None).refresh_interval == timedelta(minutes=10)
