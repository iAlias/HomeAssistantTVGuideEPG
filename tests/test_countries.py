"""Tests for the country registry.

Constructing a source with ``session=None`` is safe here: both source classes
only store the session, they never touch it until ``get_schedules`` runs.
"""

from custom_components.tv_guide_epg.countries import COUNTRIES
from custom_components.tv_guide_epg.sources.sorrisi import SorrisiSource
from custom_components.tv_guide_epg.sources.xmltv import XmltvSource

XMLTV_COUNTRIES = ("UK", "DE", "FR", "ES")


def test_all_five_launch_countries_present():
    assert set(COUNTRIES) == {"IT", "UK", "DE", "FR", "ES"}


def test_every_country_has_a_display_name():
    for code, config in COUNTRIES.items():
        assert config.name, f"{code} has no display name"


def test_italy_uses_sorrisi_source_with_fixed_interval():
    config = COUNTRIES["IT"]
    assert config.configurable_interval is False
    assert isinstance(config.make_source(None, None), SorrisiSource)


def test_italy_ignores_a_requested_interval():
    source = COUNTRIES["IT"].make_source(None, 30)
    assert source.refresh_interval.total_seconds() == 10 * 60


def test_xmltv_countries_use_xmltv_source_with_configurable_interval():
    for code in XMLTV_COUNTRIES:
        config = COUNTRIES[code]
        assert config.configurable_interval is True
        source = config.make_source(None, 30)
        assert isinstance(source, XmltvSource)
        assert source.refresh_interval.total_seconds() == 30 * 60


def test_xmltv_countries_default_to_two_hours():
    for code in XMLTV_COUNTRIES:
        source = COUNTRIES[code].make_source(None, None)
        assert source.refresh_interval.total_seconds() == 120 * 60


def test_xmltv_countries_point_at_their_own_epgshare_tag():
    expected_tags = {"UK": "UK1", "DE": "DE1", "FR": "FR1", "ES": "ES1"}
    for code, tag in expected_tags.items():
        source = COUNTRIES[code].make_source(None, None)
        assert source._url.endswith(f"epg_ripper_{tag}.xml.gz")


def test_xmltv_countries_declare_channels_with_display_names():
    for code in XMLTV_COUNTRIES:
        source = COUNTRIES[code].make_source(None, None)
        assert source._channel_order, f"{code} has no channels configured"
        # Every configured channel id must have a human-readable name.
        assert set(source._channel_order) == set(source._channel_names)


def test_uk_uses_the_channel_five_variant_that_has_data():
    # Channel.5.uk exists in the feed but carries no programmes; the HD variant
    # is the one with real data (verified 2026-09-19).
    source = COUNTRIES["UK"].make_source(None, None)
    assert "Channel.5.HD.uk" in source._channel_order
    assert "Channel.5.uk" not in source._channel_order


def test_every_country_declares_its_channels():
    for code, config in COUNTRIES.items():
        channels = config.make_source(None, None).channels
        assert channels, f"{code} declares no channels"
        assert len(channels) == len(set(channels)), f"{code} has duplicate channel names"


def test_channel_counts_match_the_documented_entity_totals():
    """Two sensors per channel: 18 for Italy, 10 for the UK, 12 for the others."""
    expected = {"IT": 9, "UK": 5, "DE": 6, "FR": 6, "ES": 6}
    actual = {code: len(cfg.make_source(None, None).channels) for code, cfg in COUNTRIES.items()}
    assert actual == expected
