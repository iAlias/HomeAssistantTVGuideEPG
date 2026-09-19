"""Tests for the stale-data fallback in EpgCoordinator.

If a source changes shape or goes down, its parse comes back empty. Rather
than let the sensors immediately show "Nessun dato", the coordinator keeps
serving the last successfully parsed schedule.
"""

import asyncio
from datetime import timedelta

from custom_components.tv_guide_epg.coordinator import EpgCoordinator, _merge_with_previous
from custom_components.tv_guide_epg.sources.base import ScheduleSource
from homeassistant.core import HomeAssistant


def test_merge_with_previous_keeps_current_when_non_empty():
    current = {"Rai 1": {"titolo": "TG1"}}
    previous = {"Rai 1": {"titolo": "Vecchio programma"}}
    assert _merge_with_previous(current, previous) == current


def test_merge_with_previous_falls_back_when_current_empty():
    previous = {"Rai 1": {"titolo": "Vecchio programma"}}
    assert _merge_with_previous({}, previous) == previous


def test_merge_with_previous_returns_empty_when_nothing_to_fall_back_to():
    assert _merge_with_previous({}, None) == {}
    assert _merge_with_previous({}, {}) == {}


class _FakeEntry:
    """Stand-in for the config entry the coordinator is bound to."""

    entry_id = "test-entry"


class _FakeSource(ScheduleSource):
    """Returns a scripted sequence of (now, prime) results, one per call."""

    def __init__(self, results, refresh_minutes: int = 10, channels=("BBC One",)) -> None:
        self._results = list(results)
        self._refresh_minutes = refresh_minutes
        self._channels = list(channels)

    @property
    def channels(self):
        return list(self._channels)

    @property
    def refresh_interval(self) -> timedelta:
        return timedelta(minutes=self._refresh_minutes)

    async def get_schedules(self):
        return self._results.pop(0)


def test_coordinator_exposes_the_sources_channels():
    """Entities are built from this list, so it must not depend on fetched data."""
    source = _FakeSource([], channels=("BBC One", "ITV1"))
    coordinator = EpgCoordinator(HomeAssistant(), _FakeEntry(), source)
    assert coordinator.channels == ["BBC One", "ITV1"]


def test_coordinator_takes_its_interval_from_the_source():
    coordinator = EpgCoordinator(HomeAssistant(), _FakeEntry(), _FakeSource([], refresh_minutes=240))
    assert coordinator.update_interval == timedelta(minutes=240)


def test_coordinator_falls_back_to_last_good_schedule_on_empty_refresh():
    good_now = {"BBC One": {"titolo": "Casualty"}}
    good_prime = {"BBC One": {"titolo": "Film"}}
    source = _FakeSource([
        (good_now, good_prime),
        ({}, {}),  # simulates the source changing shape or going down
    ])
    coordinator = EpgCoordinator(HomeAssistant(), _FakeEntry(), source)

    asyncio.run(coordinator.async_refresh())
    assert coordinator.data == (good_now, good_prime)

    asyncio.run(coordinator.async_refresh())
    assert coordinator.data == (good_now, good_prime)


def test_coordinator_adopts_new_data_once_source_recovers():
    good_now = {"BBC One": {"titolo": "Casualty"}}
    good_prime = {"BBC One": {"titolo": "Film"}}
    new_now = {"BBC One": {"titolo": "Nuovo programma"}}
    source = _FakeSource([
        (good_now, good_prime),
        ({}, {}),
        (new_now, good_prime),
    ])
    coordinator = EpgCoordinator(HomeAssistant(), _FakeEntry(), source)

    for _ in range(3):
        asyncio.run(coordinator.async_refresh())

    assert coordinator.data == (new_now, good_prime)


def test_coordinator_keeps_each_schedule_independently():
    """A source can lose one schedule while keeping the other."""
    good_now = {"BBC One": {"titolo": "Casualty"}}
    good_prime = {"BBC One": {"titolo": "Film"}}
    new_now = {"BBC One": {"titolo": "Breakfast"}}
    source = _FakeSource([
        (good_now, good_prime),
        (new_now, {}),  # prime went missing, now is fine
    ])
    coordinator = EpgCoordinator(HomeAssistant(), _FakeEntry(), source)

    asyncio.run(coordinator.async_refresh())
    asyncio.run(coordinator.async_refresh())

    assert coordinator.data == (new_now, good_prime)
