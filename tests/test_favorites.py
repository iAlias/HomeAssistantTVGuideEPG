"""Tests for the pure favorite-matching logic behind binary_sensor.py."""

from custom_components.tv_guide_epg.favorites import matching_channels, parse_favorites


def test_parse_favorites_splits_and_trims():
    assert parse_favorites(" Report, Chi l'ha visto?,, Propaganda Live ") == [
        "Report",
        "Chi l'ha visto?",
        "Propaganda Live",
    ]


def test_parse_favorites_empty_string_returns_empty_list():
    assert parse_favorites("") == []
    assert parse_favorites("   ") == []


def test_matching_channels_case_insensitive_substring():
    schedule = {
        "Rai 3": {"titolo": "Report"},
        "Rai 1": {"titolo": "Telegiornale"},
    }
    assert matching_channels(schedule, "report") == {"Rai 3": "Report"}


def test_matching_channels_matches_partial_title():
    schedule = {"BBC One": {"titolo": "Casualty - Series 41"}}
    assert matching_channels(schedule, "Casualty") == {"BBC One": "Casualty - Series 41"}


def test_matching_channels_no_match_returns_empty_dict():
    schedule = {"Rai 1": {"titolo": "Telegiornale"}}
    assert matching_channels(schedule, "Report") == {}


def test_matching_channels_multiple_channels_can_match():
    schedule = {
        "Rai 3": {"titolo": "Report"},
        "La7": {"titolo": "Report - Repliche"},
    }
    assert matching_channels(schedule, "Report") == {
        "Rai 3": "Report",
        "La7": "Report - Repliche",
    }


def test_matching_channels_tolerates_missing_title():
    schedule = {"Rai 1": {}}
    assert matching_channels(schedule, "Report") == {}
