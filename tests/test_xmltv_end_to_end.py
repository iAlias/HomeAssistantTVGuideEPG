"""End-to-end tests for XmltvSource.get_schedules().

The other XMLTV tests cover the pure functions; these exercise the full async
path — HTTP fetch, gzip handling, parsing, and the now/prime computation —
against a fake session, so a regression in the plumbing between them is caught
too.
"""

import asyncio
import gzip
from pathlib import Path

from custom_components.tv_guide_epg.sources.xmltv import XmltvSource

FIXTURE = (Path(__file__).parent / "fixtures" / "xmltv" / "uk_excerpt.xml").read_bytes()
CHANNELS = {"BBC.One.Lon.HD.uk": "BBC One", "ITV1.HD.uk": "ITV1"}


class _FakeResponse:
    def __init__(self, status: int, payload: bytes) -> None:
        self.status = status
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


class _FakeSession:
    """Minimal stand-in for aiohttp.ClientSession.get()."""

    def __init__(self, status: int = 200, payload: bytes = b"", raises: bool = False) -> None:
        self._status = status
        self._payload = payload
        self._raises = raises
        self.requested_url = None

    async def get(self, url: str):
        self.requested_url = url
        if self._raises:
            raise OSError("connection refused")
        return _FakeResponse(self._status, self._payload)


def _build(session) -> XmltvSource:
    return XmltvSource(
        session,
        url="https://example.com/epg_ripper_UK1.xml.gz",
        channel_order=list(CHANNELS),
        channel_names=dict(CHANNELS),
    )


def test_get_schedules_handles_gzipped_payload():
    session = _FakeSession(payload=gzip.compress(FIXTURE))
    now, prime = asyncio.run(_build(session).get_schedules())

    assert session.requested_url.endswith("epg_ripper_UK1.xml.gz")
    # Prime time is derived from the feed regardless of the current clock.
    assert prime["BBC One"]["titolo"] == "Casualty"
    assert prime["ITV1"]["titolo"] == "Emmerdale"
    # "now" depends on the real clock, so only its shape is asserted here.
    assert isinstance(now, dict)


def test_get_schedules_accepts_plain_uncompressed_xml():
    session = _FakeSession(payload=FIXTURE)
    _, prime = asyncio.run(_build(session).get_schedules())
    assert prime["BBC One"]["titolo"] == "Casualty"


def test_get_schedules_returns_empty_on_http_error():
    session = _FakeSession(status=503, payload=b"nope")
    assert asyncio.run(_build(session).get_schedules()) == ({}, {})


def test_get_schedules_returns_empty_when_the_request_raises():
    session = _FakeSession(raises=True)
    assert asyncio.run(_build(session).get_schedules()) == ({}, {})


def test_get_schedules_returns_empty_on_malformed_xml():
    session = _FakeSession(payload=gzip.compress(b"<tv><programme"))
    assert asyncio.run(_build(session).get_schedules()) == ({}, {})


def test_get_schedules_returns_empty_on_empty_body():
    session = _FakeSession(payload=b"")
    assert asyncio.run(_build(session).get_schedules()) == ({}, {})
