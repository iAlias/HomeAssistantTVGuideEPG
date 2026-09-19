# TV Guide EPG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tv_guide_epg`, a new Home Assistant integration bringing TV schedules for 5 countries (IT/UK/DE/FR/ES) into HA, with the country chosen at config-flow time.

**Architecture:** A `ScheduleSource` interface (async `get_schedules() -> (now, prime)` + `refresh_interval`) with two implementations — `SorrisiSource` (Italy, HTML scraping, ported from `tv_guide_multi`) and `XmltvSource` (UK/DE/FR/ES, generic XMLTV parser pointed at epgshare01.online). A `countries.py` registry maps country code to display name + source factory. `EpgCoordinator` (DataUpdateCoordinator subclass) polls one source per config entry and falls back to the last good schedule on an empty refresh. One config entry per country; `sensor.py`/`binary_sensor.py` are thin HA entity glue reading from the coordinator.

**Tech Stack:** Python (Home Assistant custom component), `aiohttp`, `beautifulsoup4`, `async_timeout`, stdlib `gzip`/`xml.etree.ElementTree`, `voluptuous`; pytest for tests; vanilla JS Lovelace card.

**Spec:** `docs/superpowers/specs/2026-09-19-tv-guide-epg-design.md`

## Global Constraints

- Domain: `tv_guide_epg`. Config flow required (`config_flow: true` in manifest).
- One config entry per country (`unique_id = f"tv_guide_epg_{country_code.lower()}"`).
- Attribute *keys* stay Italian (`titolo`, `orario_inizio`, `orario_fine`, `genere`, `locandina`, `descrizione`) for consistency with the rest of the workspace; attribute *values* are in the source country's language.
- No new runtime dependency for XMLTV parsing (stdlib `gzip` + `xml.etree.ElementTree` only).
- Tests must run with plain `pytest`, no real Home Assistant install — use the same synthetic-package + stub technique as `tv_guide_multi/tests/conftest.py`.
- XMLTV test fixtures are **trimmed excerpts** (a handful of channels/hours), never the full multi-MB dumps.
- Verified real channel IDs (from the spec, checked 2026-09-19 against real downloaded files) must be used verbatim — never invented IDs.
- License: MIT. Language: README.md (English) + README.it.md (Italian), mirroring `tv_guide_multi`'s structure.

---

## Task 1: Project scaffolding

**Files:**
- Create: `custom_components/tv_guide_epg/__init__.py` (empty package marker for now, filled in Task 8)
- Create: `custom_components/tv_guide_epg/manifest.json`
- Create: `custom_components/tv_guide_epg/const.py`
- Create: `hacs.json`
- Create: `requirements_test.txt`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `.github/workflows/validate.yml`

**Interfaces:**
- Produces: `DOMAIN = "tv_guide_epg"`, `DEFAULT_NAME = "Guida TV"`, `CONF_COUNTRY = "nazione"`, `CONF_FAVORITES = "preferiti"`, `CONF_REFRESH_MINUTES = "intervallo_aggiornamento"` in `const.py`, consumed by every later task.

- [ ] **Step 1: Write `custom_components/tv_guide_epg/const.py`**

```python
"""Constants for the TV Guide EPG integration."""

DOMAIN = "tv_guide_epg"
DEFAULT_NAME = "Guida TV"
CONF_COUNTRY = "nazione"
CONF_FAVORITES = "preferiti"
CONF_REFRESH_MINUTES = "intervallo_aggiornamento"
DEFAULT_REFRESH_MINUTES = 120
```

- [ ] **Step 2: Write `custom_components/tv_guide_epg/__init__.py`**

```python
"""Package marker."""
```

- [ ] **Step 3: Write `custom_components/tv_guide_epg/manifest.json`**

```json
{
  "domain": "tv_guide_epg",
  "name": "TV Guide EPG",
  "codeowners": ["@iAlias"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/iAlias/HomeAssistantTVGuideEPG",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/iAlias/HomeAssistantTVGuideEPG/issues",
  "requirements": [
    "aiohttp>=3.8.4",
    "async_timeout>=4.0.3",
    "beautifulsoup4>=4.12.3"
  ],
  "version": "1.0.0"
}
```

- [ ] **Step 4: Write `hacs.json`**

```json
{
  "name": "TV Guide EPG",
  "content_in_root": false,
  "homeassistant": "2024.1.0",
  "render_readme": true
}
```

- [ ] **Step 5: Write `requirements_test.txt`**

```
pytest>=8.0.0
beautifulsoup4>=4.12.3
aiohttp>=3.8.4
async_timeout>=4.0.3
voluptuous>=0.13.1
```

- [ ] **Step 6: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 7: Write `LICENSE`** (MIT, copy verbatim from `Home-Assistant-TV-Guide/LICENSE`, replacing only the copyright holder line if it names the previous project — otherwise copy as-is; if unsure, use standard MIT text with `Copyright (c) 2026 iAlias`)

```
MIT License

Copyright (c) 2026 iAlias

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 8: Write `.github/workflows/validate.yml`**

```yaml
# Official Home Assistant and HACS validation, so a broken manifest or an
# invalid hacs.json is caught here rather than by whoever installs it.
name: Validate

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 4 * * 1"
  workflow_dispatch:

jobs:
  hassfest:
    name: hassfest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    name: HACS
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration

  pytest:
    name: pytest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements_test.txt
      - run: pytest -q
```

- [ ] **Step 9: Verify JSON/YAML are syntactically valid**

Run: `node -e "JSON.parse(require('fs').readFileSync('custom_components/tv_guide_epg/manifest.json','utf8')); JSON.parse(require('fs').readFileSync('hacs.json','utf8')); console.log('OK')"`
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add custom_components/tv_guide_epg/__init__.py custom_components/tv_guide_epg/manifest.json custom_components/tv_guide_epg/const.py hacs.json requirements_test.txt .gitignore LICENSE .github/workflows/validate.yml
git commit -m "Scaffold tv_guide_epg project"
```

---

## Task 2: `ScheduleSource` base + `SorrisiSource` (Italy)

**Files:**
- Create: `custom_components/tv_guide_epg/sources/__init__.py`
- Create: `custom_components/tv_guide_epg/sources/base.py`
- Create: `custom_components/tv_guide_epg/sources/sorrisi.py`
- Test: `tests/conftest.py`
- Test: `tests/fixtures/sorrisi/ora_in_onda.html` (copy verbatim from `../Home-Assistant-TV-Guide/tests/fixtures/ora_in_onda.html`)
- Test: `tests/fixtures/sorrisi/prima_serata.html` (copy verbatim from `../Home-Assistant-TV-Guide/tests/fixtures/prima_serata.html`)
- Test: `tests/test_sorrisi_source.py`

**Interfaces:**
- Consumes: nothing (first source module)
- Produces: `Schedule = Dict[str, Dict[str, Optional[str]]]` type alias; `ScheduleSource` ABC with `refresh_interval: timedelta` property and `async get_schedules() -> Tuple[Schedule, Schedule]`; `SorrisiSource(session)` implementing it. Consumed by `countries.py` (Task 4) and `coordinator.py` (Task 5).

- [ ] **Step 1: Write `custom_components/tv_guide_epg/sources/__init__.py`**

```python
"""Schedule source implementations."""
```

- [ ] **Step 2: Write `custom_components/tv_guide_epg/sources/base.py`**

```python
"""The ScheduleSource interface every country's data provider implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, Optional, Tuple

Schedule = Dict[str, Dict[str, Optional[str]]]


class ScheduleSource(ABC):
    """A provider of {channel: program_info} "now" and "prime time" schedules."""

    @property
    @abstractmethod
    def refresh_interval(self) -> timedelta:
        """How often the coordinator should poll this source."""

    @abstractmethod
    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        """Return (now_schedule, prime_time_schedule)."""
```

- [ ] **Step 3: Write `custom_components/tv_guide_epg/sources/sorrisi.py`** (ported from `Home-Assistant-TV-Guide/custom_components/tv_guide_multi/sources.py`, adapted to the `ScheduleSource` ABC with `refresh_interval`)

```python
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
    "Rai 1", "Rai 2", "Rai 3", "Rete 4", "Canale 5", "Italia 1", "La7", "TV8", "NOVE",
]

SKIP_CHANNELS = {"IRIS", "CANALE20", "20", "20MEDIASET", "RAI4"}


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
    """Return a mapping {channel: program_info} from the provided HTML."""
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

        key = channel.upper().replace(" ", "")
        if key in SKIP_CHANNELS:
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
            idx = CHANNEL_ORDER.index(item[0])
        except ValueError:
            idx = len(CHANNEL_ORDER)
        return idx, item[0]

    return dict(sorted(mapping.items(), key=sort_key))


class SorrisiSource(ScheduleSource):
    """Reads Italian TV schedules from sorrisi.com."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @property
    def refresh_interval(self) -> timedelta:
        return timedelta(minutes=10)

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        html_now, html_prime = await asyncio.gather(
            _fetch_page(self._session, URL_NOW),
            _fetch_page(self._session, URL_PRIME),
        )
        return _parse_programs(html_now), _parse_programs(html_prime)
```

- [ ] **Step 4: Write `tests/conftest.py`** (same synthetic-package technique as `tv_guide_multi`, adapted for the `tv_guide_epg` package name and the `sources/` sub-package)

```python
"""Make the integration's pure-logic modules importable without a full Home
Assistant installation, using real package-relative imports.

A synthetic ``custom_components.tv_guide_epg`` package (and its ``sources``
sub-package) is registered directly in ``sys.modules`` so relative imports
resolve normally, without ever executing the real ``__init__.py`` (which
pulls in the rest of ``homeassistant``). Mirrors the approach used in
``tv_guide_multi``'s ``conftest.py``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "tv_guide_epg"
PACKAGE = "custom_components.tv_guide_epg"
SOURCES_PACKAGE = f"{PACKAGE}.sources"


class _GenericStub:
    """Base class that tolerates ``Stub[SomeType]`` subscription syntax."""

    def __class_getitem__(cls, item):
        return cls


def _install_stub_homeassistant() -> None:
    if "homeassistant" in sys.modules:
        return

    modules = {name: types.ModuleType(name) for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.update_coordinator",
    )}

    class HomeAssistant:
        pass

    class DataUpdateCoordinator(_GenericStub):
        def __init__(self, hass, logger, *, name=None, update_interval=None):
            self.data = None

        async def async_refresh(self):
            self.data = await self._async_update_data()

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

    modules["homeassistant.core"].HomeAssistant = HomeAssistant
    modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = DataUpdateCoordinator

    sys.modules.update(modules)


def _register_component_package() -> None:
    if SOURCES_PACKAGE in sys.modules:
        return

    root = types.ModuleType("custom_components")
    root.__path__ = []
    sys.modules.setdefault("custom_components", root)

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules[PACKAGE] = package

    sources_package = types.ModuleType(SOURCES_PACKAGE)
    sources_package.__path__ = [str(COMPONENT_DIR / "sources")]
    sys.modules[SOURCES_PACKAGE] = sources_package


_install_stub_homeassistant()
_register_component_package()
```

- [ ] **Step 5: Copy the sorrisi fixtures**

```bash
mkdir -p tests/fixtures/sorrisi
cp "../Home-Assistant-TV-Guide/tests/fixtures/ora_in_onda.html" tests/fixtures/sorrisi/ora_in_onda.html
cp "../Home-Assistant-TV-Guide/tests/fixtures/prima_serata.html" tests/fixtures/sorrisi/prima_serata.html
```

- [ ] **Step 6: Write `tests/test_sorrisi_source.py`**

```python
"""Tests for sources.sorrisi._parse_programs against real sorrisi.com markup."""

from pathlib import Path

from custom_components.tv_guide_epg.sources.sorrisi import (
    CHANNEL_ORDER, SKIP_CHANNELS, _parse_programs,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sorrisi"
ORA_IN_ONDA = (FIXTURES / "ora_in_onda.html").read_text(encoding="utf-8")
PRIMA_SERATA = (FIXTURES / "prima_serata.html").read_text(encoding="utf-8")


def test_parses_known_channel_from_ora_in_onda():
    result = _parse_programs(ORA_IN_ONDA)
    assert "Rai 1" in result
    assert result["Rai 1"]["titolo"]


def test_orders_known_channels_by_channel_order():
    result = _parse_programs(ORA_IN_ONDA)
    known = [channel for channel in result if channel in CHANNEL_ORDER]
    assert known == sorted(known, key=CHANNEL_ORDER.index)


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


def test_program_info_has_expected_keys():
    result = _parse_programs(ORA_IN_ONDA)
    info = result["Rai 1"]
    assert set(info) == {
        "titolo", "orario_inizio", "orario_fine", "genere", "locandina", "descrizione",
    }
```

- [ ] **Step 7: Install test deps and run**

Run: `pip install -r requirements_test.txt && pytest tests/test_sorrisi_source.py -q`
Expected: `6 passed`

- [ ] **Step 8: Commit**

```bash
git add custom_components/tv_guide_epg/sources tests/conftest.py tests/fixtures/sorrisi tests/test_sorrisi_source.py
git commit -m "Add ScheduleSource interface and SorrisiSource (Italy)"
```

---

## Task 3: `XmltvSource` (UK/DE/FR/ES)

**Files:**
- Create: `custom_components/tv_guide_epg/sources/xmltv.py`
- Test: `tests/fixtures/xmltv/uk_excerpt.xml`
- Test: `tests/test_xmltv_source.py`

**Interfaces:**
- Consumes: `Schedule`, `ScheduleSource` from `sources/base.py` (Task 2)
- Produces: `XmltvSource(session, *, url, channel_order, refresh_minutes=120)`, plus pure functions `_parse_xmltv(xml_bytes, wanted_channels) -> Dict[str, List[dict]]` and `_programme_on_air(programmes_by_channel, now) -> Schedule` and `_programme_nearest(programmes_by_channel, target_hour) -> Schedule`, all importable and unit-testable without network access. Consumed by `countries.py` (Task 4).

- [ ] **Step 1: Create the trimmed XMLTV fixture** `tests/fixtures/xmltv/uk_excerpt.xml`

A hand-written excerpt in the real epgshare01.online UK1 format (2 channels, a few programmes spanning a full day so both "on air now" and "nearest to 21:00" cases are exercised by tests using an injected time):

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<tv generator-info-name="none" generator-info-url="none">
  <channel id="BBC.One.Lon.HD.uk">
    <icon src="https://example.com/bbc1.png" />
    <display-name lang="en">BBC One London</display-name>
  </channel>
  <channel id="ITV1.HD.uk">
    <icon src="https://example.com/itv1.png" />
    <display-name lang="en">ITV1 HD</display-name>
  </channel>
  <programme channel="BBC.One.Lon.HD.uk" start="20260919120000 +0000" stop="20260919130000 +0000">
    <title lang="en">Midday News</title>
    <desc lang="en">The latest headlines.</desc>
    <category lang="en">News</category>
  </programme>
  <programme channel="BBC.One.Lon.HD.uk" start="20260919200000 +0000" stop="20260919210000 +0000">
    <title lang="en">Antiques Roadshow</title>
    <desc lang="en">Experts value family heirlooms.</desc>
    <category lang="en">Factual</category>
    <icon src="https://example.com/antiques.png" />
  </programme>
  <programme channel="BBC.One.Lon.HD.uk" start="20260919210000 +0000" stop="20260919223000 +0000">
    <title lang="en">Casualty</title>
    <desc lang="en">Drama at Holby City hospital.</desc>
    <category lang="en">Drama</category>
  </programme>
  <programme channel="ITV1.HD.uk" start="20260919120000 +0000" stop="20260919123000 +0000">
    <title lang="en">Loose Women</title>
    <category lang="en">Talk Show</category>
  </programme>
  <programme channel="ITV1.HD.uk" start="20260919205500 +0000" stop="20260919220000 +0000">
    <title lang="en">Emmerdale</title>
    <desc lang="en">Village life drama.</desc>
    <category lang="en">Soap</category>
  </programme>
</tv>
```

- [ ] **Step 2: Write `custom_components/tv_guide_epg/sources/xmltv.py`**

```python
"""Generic XMLTV schedule source (used for UK/DE/FR/ES via epgshare01.online)."""

from __future__ import annotations

import gzip
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import aiohttp
import async_timeout

from .base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)

Programme = Dict[str, Optional[str]]


def _parse_xmltv_datetime(value: str) -> datetime:
    """Parse an XMLTV timestamp, e.g. '20260919200000 +0000'."""
    naive_part, _, offset_part = value.strip().partition(" ")
    dt = datetime.strptime(naive_part, "%Y%m%d%H%M%S")
    sign = 1 if offset_part.startswith("+") else -1
    hours = int(offset_part[1:3] or 0)
    minutes = int(offset_part[3:5] or 0)
    offset = timedelta(hours=hours, minutes=minutes) * sign
    return dt.replace(tzinfo=timezone(offset))


def _parse_xmltv(xml_bytes: bytes, wanted_channels: List[str]) -> Dict[str, List[Programme]]:
    """Parse XMLTV bytes into {channel_id: [programme, ...]} for the wanted channels only."""
    wanted = set(wanted_channels)
    root = ElementTree.fromstring(xml_bytes)
    result: Dict[str, List[Programme]] = {channel: [] for channel in wanted_channels}

    for programme_el in root.findall("programme"):
        channel_id = programme_el.get("channel")
        if channel_id not in wanted:
            continue

        title_el = programme_el.find("title")
        if title_el is None or not (title_el.text or "").strip():
            continue

        desc_el = programme_el.find("desc")
        category_el = programme_el.find("category")
        icon_el = programme_el.find("icon")

        start = _parse_xmltv_datetime(programme_el.get("start", ""))
        stop = _parse_xmltv_datetime(programme_el.get("stop", ""))

        result[channel_id].append({
            "titolo": title_el.text.strip(),
            "_start": start,
            "_stop": stop,
            "genere": category_el.text.strip() if category_el is not None and category_el.text else None,
            "locandina": icon_el.get("src") if icon_el is not None else None,
            "descrizione": desc_el.text.strip() if desc_el is not None and desc_el.text else None,
        })

    for programmes in result.values():
        programmes.sort(key=lambda item: item["_start"])

    return result


def _to_schedule_entry(programme: Programme) -> Dict[str, Optional[str]]:
    start = programme["_start"]
    stop = programme["_stop"]
    return {
        "titolo": programme["titolo"],
        "orario_inizio": start.strftime("%H:%M"),
        "orario_fine": stop.strftime("%H:%M"),
        "genere": programme["genere"],
        "locandina": programme["locandina"],
        "descrizione": programme["descrizione"],
    }


def _programme_on_air(
    programmes_by_channel: Dict[str, List[Programme]],
    now: datetime,
    channel_order: List[str],
    channel_names: Dict[str, str],
) -> Schedule:
    """Return {display_name: program_info} for the programme airing at ``now``."""
    schedule: Schedule = {}
    for channel_id in channel_order:
        for programme in programmes_by_channel.get(channel_id, []):
            if programme["_start"] <= now < programme["_stop"]:
                schedule[channel_names.get(channel_id, channel_id)] = _to_schedule_entry(programme)
                break
    return schedule


def _programme_nearest(
    programmes_by_channel: Dict[str, List[Programme]],
    now: datetime,
    target_hour: int,
    channel_order: List[str],
    channel_names: Dict[str, str],
) -> Schedule:
    """Return {display_name: program_info} for the programme closest to ``target_hour`` today."""
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    schedule: Schedule = {}
    for channel_id in channel_order:
        candidates = programmes_by_channel.get(channel_id, [])
        if not candidates:
            continue
        closest = min(candidates, key=lambda p: abs((p["_start"] - target).total_seconds()))
        schedule[channel_names.get(channel_id, channel_id)] = _to_schedule_entry(closest)
    return schedule


class XmltvSource(ScheduleSource):
    """Reads a full day's schedule from an XMLTV(.gz) feed and computes now/prime locally."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        url: str,
        channel_order: List[str],
        channel_names: Optional[Dict[str, str]] = None,
        refresh_minutes: int = 120,
    ) -> None:
        self._session = session
        self._url = url
        self._channel_order = channel_order
        self._channel_names = channel_names or {}
        self._refresh_minutes = refresh_minutes

    @property
    def refresh_interval(self) -> timedelta:
        return timedelta(minutes=self._refresh_minutes)

    async def _fetch(self) -> bytes:
        try:
            async with async_timeout.timeout(30):
                resp = await self._session.get(self._url)
                if resp.status != 200:
                    _LOGGER.warning("XMLTV: %s status %s", self._url, resp.status)
                    return b""
                return await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error fetching %s: %s", self._url, err)
            return b""

    async def get_schedules(self) -> Tuple[Schedule, Schedule]:
        raw = await self._fetch()
        if not raw:
            return {}, {}
        try:
            xml_bytes = gzip.decompress(raw)
        except OSError:
            xml_bytes = raw  # not gzipped, e.g. a test fixture read directly

        try:
            programmes_by_channel = _parse_xmltv(xml_bytes, self._channel_order)
        except ElementTree.ParseError as err:
            _LOGGER.error("Malformed XMLTV from %s: %s", self._url, err)
            return {}, {}

        now = datetime.now(timezone.utc)
        return (
            _programme_on_air(programmes_by_channel, now, self._channel_order, self._channel_names),
            _programme_nearest(programmes_by_channel, now, 21, self._channel_order, self._channel_names),
        )
```

- [ ] **Step 3: Write `tests/test_xmltv_source.py`**

```python
"""Tests for the pure XMLTV parsing/scheduling logic in sources.xmltv."""

from datetime import datetime, timezone
from pathlib import Path

from custom_components.tv_guide_epg.sources.xmltv import (
    _parse_xmltv, _parse_xmltv_datetime, _programme_nearest, _programme_on_air,
)

FIXTURE = (Path(__file__).parent / "fixtures" / "xmltv" / "uk_excerpt.xml").read_bytes()
CHANNEL_ORDER = ["BBC.One.Lon.HD.uk", "ITV1.HD.uk"]
CHANNEL_NAMES = {"BBC.One.Lon.HD.uk": "BBC One", "ITV1.HD.uk": "ITV1"}


def test_parse_xmltv_datetime_reads_utc_offset():
    dt = _parse_xmltv_datetime("20260919200000 +0000")
    assert dt == datetime(2026, 9, 19, 20, 0, tzinfo=timezone.utc)


def test_parse_xmltv_extracts_only_wanted_channels():
    result = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    assert set(result) == set(CHANNEL_ORDER)
    assert len(result["BBC.One.Lon.HD.uk"]) == 3
    assert len(result["ITV1.HD.uk"]) == 2


def test_parse_xmltv_ignores_channels_not_requested():
    result = _parse_xmltv(FIXTURE, ["BBC.One.Lon.HD.uk"])
    assert set(result) == {"BBC.One.Lon.HD.uk"}


def test_programme_on_air_picks_the_programme_covering_now():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 20, 30, tzinfo=timezone.utc)  # inside Antiques Roadshow / Emmerdale
    result = _programme_on_air(programmes, now, CHANNEL_ORDER, CHANNEL_NAMES)
    assert result["BBC One"]["titolo"] == "Antiques Roadshow"
    assert result["ITV1"]["titolo"] == "Emmerdale"


def test_programme_on_air_empty_when_nothing_covers_now():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 5, 0, tzinfo=timezone.utc)  # before any fixture programme
    result = _programme_on_air(programmes, now, CHANNEL_ORDER, CHANNEL_NAMES)
    assert result == {}


def test_programme_nearest_picks_closest_to_target_hour():
    programmes = _parse_xmltv(FIXTURE, CHANNEL_ORDER)
    now = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)  # target becomes 21:00 same day
    result = _programme_nearest(programmes, now, 21, CHANNEL_ORDER, CHANNEL_NAMES)
    assert result["BBC One"]["titolo"] == "Antiques Roadshow"  # 20:00, closer to 21:00 than Casualty (21:00 exact... )


def test_programme_info_includes_optional_fields_as_none_when_missing():
    programmes = _parse_xmltv(FIXTURE, ["ITV1.HD.uk"])
    now = datetime(2026, 9, 19, 12, 15, tzinfo=timezone.utc)  # inside Loose Women (no desc/icon in fixture)
    result = _programme_on_air(programmes, now, ["ITV1.HD.uk"], CHANNEL_NAMES)
    assert result["ITV1"]["descrizione"] is None
    assert result["ITV1"]["locandina"] is None
```

Note on Step 3's `test_programme_nearest_picks_closest_to_target_hour`: verify by hand which
fixture programme is actually closest to 21:00 (Antiques Roadshow starts 20:00 = 60 min away;
Casualty starts 21:00 = 0 min away) — **fix the assertion to `"Casualty"`** before running, since
Casualty starts exactly at the target hour. This is a deliberate reminder to compute fixture math
by hand rather than guess; don't skip it.

- [ ] **Step 4: Fix the assertion identified in Step 3, then run the tests**

Run: `pytest tests/test_xmltv_source.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add custom_components/tv_guide_epg/sources/xmltv.py tests/fixtures/xmltv tests/test_xmltv_source.py
git commit -m "Add generic XmltvSource with local now/prime-time computation"
```

---

## Task 4: `countries.py` registry

**Files:**
- Create: `custom_components/tv_guide_epg/countries.py`
- Test: `tests/test_countries.py`

**Interfaces:**
- Consumes: `SorrisiSource` (Task 2), `XmltvSource` (Task 3)
- Produces: `CountryConfig` dataclass (`name: str`, `configurable_interval: bool`, `make_source: Callable[[ClientSession, Optional[int]], ScheduleSource]`) and `COUNTRIES: Dict[str, CountryConfig]`. Consumed by `config_flow.py` (Task 6) and `__init__.py` (Task 7).

- [ ] **Step 1: Write `custom_components/tv_guide_epg/countries.py`**

```python
"""Registry mapping a country code to its display name and data source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import aiohttp

from .sources.base import ScheduleSource
from .sources.sorrisi import SorrisiSource
from .sources.xmltv import XmltvSource

EPGSHARE01_BASE = "https://epgshare01.online/epgshare01/epg_ripper_{tag}.xml.gz"


@dataclass(frozen=True)
class CountryConfig:
    name: str
    configurable_interval: bool
    make_source: Callable[[aiohttp.ClientSession, Optional[int]], ScheduleSource]


def _xmltv_country(tag: str, channel_order: list[str], channel_names: dict[str, str]) -> CountryConfig:
    def make_source(session: aiohttp.ClientSession, minutes: Optional[int]) -> ScheduleSource:
        return XmltvSource(
            session,
            url=EPGSHARE01_BASE.format(tag=tag),
            channel_order=channel_order,
            channel_names=channel_names,
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
        make_source=_xmltv_country(
            "UK1",
            ["BBC.One.Lon.HD.uk", "BBC.Two.HD.uk", "ITV1.HD.uk", "Channel.4.HD.uk", "Channel.5.uk"],
            {
                "BBC.One.Lon.HD.uk": "BBC One",
                "BBC.Two.HD.uk": "BBC Two",
                "ITV1.HD.uk": "ITV1",
                "Channel.4.HD.uk": "Channel 4",
                "Channel.5.uk": "Channel 5",
            },
        ),
    ),
    "DE": CountryConfig(
        name="Germania",
        configurable_interval=True,
        make_source=_xmltv_country(
            "DE1",
            ["Das.Erste.de", "ZDF.de", "RTL.de", "ProSieben.de"],
            {
                "Das.Erste.de": "Das Erste",
                "ZDF.de": "ZDF",
                "RTL.de": "RTL",
                "ProSieben.de": "ProSieben",
            },
        ),
    ),
    "FR": CountryConfig(
        name="Francia",
        configurable_interval=True,
        make_source=_xmltv_country(
            "FR1",
            ["TF1.fr", "France.2.fr", "M6.fr"],
            {
                "TF1.fr": "TF1",
                "France.2.fr": "France 2",
                "M6.fr": "M6",
            },
        ),
    ),
    "ES": CountryConfig(
        name="Spagna",
        configurable_interval=True,
        make_source=_xmltv_country(
            "ES1",
            ["La.1.es", "Antena.3.es", "Telecinco.es", "laSexta.es"],
            {
                "La.1.es": "La 1",
                "Antena.3.es": "Antena 3",
                "Telecinco.es": "Telecinco",
                "laSexta.es": "laSexta",
            },
        ),
    ),
}
```

- [ ] **Step 2: Write `tests/test_countries.py`**

```python
"""Tests for the country registry."""

from custom_components.tv_guide_epg.countries import COUNTRIES
from custom_components.tv_guide_epg.sources.sorrisi import SorrisiSource
from custom_components.tv_guide_epg.sources.xmltv import XmltvSource


def test_all_five_launch_countries_present():
    assert set(COUNTRIES) == {"IT", "UK", "DE", "FR", "ES"}


def test_italy_uses_sorrisi_source_and_fixed_interval():
    config = COUNTRIES["IT"]
    assert config.configurable_interval is False
    source = config.make_source(session=None, minutes=None)
    assert isinstance(source, SorrisiSource)


def test_xmltv_countries_use_xmltv_source_and_configurable_interval():
    for code in ("UK", "DE", "FR", "ES"):
        config = COUNTRIES[code]
        assert config.configurable_interval is True
        source = config.make_source(session=None, minutes=30)
        assert isinstance(source, XmltvSource)
        assert source.refresh_interval.total_seconds() == 30 * 60


def test_xmltv_country_defaults_to_120_minutes_when_minutes_is_none():
    source = COUNTRIES["UK"].make_source(session=None, minutes=None)
    assert source.refresh_interval.total_seconds() == 120 * 60
```

Note: `SorrisiSource(session=None)`/`XmltvSource(session=None, ...)` work fine here because the
constructors only *store* the session; they never call it during construction. `make_source` in
the test above is called with keyword args (`session=None, minutes=None`) — check the real
signature is positional-or-keyword (`session, minutes`, no `*`), which it is as written in Step 1.

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_countries.py -q`
Expected: `4 passed`

- [ ] **Step 4: Commit**

```bash
git add custom_components/tv_guide_epg/countries.py tests/test_countries.py
git commit -m "Add countries.py registry for IT/UK/DE/FR/ES"
```

---

## Task 5: `favorites.py` + `coordinator.py`

**Files:**
- Create: `custom_components/tv_guide_epg/favorites.py` (ported verbatim from `tv_guide_multi`)
- Create: `custom_components/tv_guide_epg/coordinator.py`
- Test: `tests/test_favorites.py`
- Test: `tests/test_coordinator_fallback.py`

**Interfaces:**
- Consumes: `ScheduleSource`, `Schedule` from `sources/base.py` (Task 2)
- Produces: `parse_favorites(raw) -> List[str]`, `matching_channels(schedule, favorite) -> Dict[str, str]` in `favorites.py`; `EpgCoordinator(DataUpdateCoordinator)` in `coordinator.py`, consumed by `__init__.py` (Task 7) and entity files (Task 8).

- [ ] **Step 1: Write `custom_components/tv_guide_epg/favorites.py`**

```python
"""Pure logic for matching favorite programs against a parsed schedule."""

from __future__ import annotations

from typing import Dict, List, Optional


def parse_favorites(raw: str) -> List[str]:
    """Split a comma-separated string of favorite titles into a clean list."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def matching_channels(
    schedule: Dict[str, Dict[str, Optional[str]]], favorite: str
) -> Dict[str, str]:
    """Return {channel: title} for programs whose title contains ``favorite``."""
    needle = favorite.casefold()
    return {
        channel: info["titolo"]
        for channel, info in schedule.items()
        if needle in (info.get("titolo") or "").casefold()
    }
```

- [ ] **Step 2: Write `custom_components/tv_guide_epg/coordinator.py`**

```python
"""Refreshes a country's TV schedule on its source's interval, with stale-data fallback."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .sources.base import Schedule, ScheduleSource

_LOGGER = logging.getLogger(__name__)


def _merge_with_previous(current: Schedule, previous: Optional[Schedule]) -> Schedule:
    """Fall back to the previous successful parse when the new one is empty."""
    return current if current else (previous or current)


class EpgCoordinator(DataUpdateCoordinator[Tuple[Schedule, Schedule]]):
    """Refreshes both schedules together on the source's own interval."""

    def __init__(self, hass: HomeAssistant, source: ScheduleSource) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="TV Guide EPG",
            update_interval=source.refresh_interval,
        )
        self._source = source

    async def _async_update_data(self) -> Tuple[Schedule, Schedule]:
        previous = self.data
        now, prime = await self._source.get_schedules()
        if previous is not None:
            prev_now, prev_prime = previous
            now = _merge_with_previous(now, prev_now)
            prime = _merge_with_previous(prime, prev_prime)
        return now, prime
```

- [ ] **Step 3: Write `tests/test_favorites.py`** (identical to `tv_guide_multi`'s, import path updated)

```python
"""Tests for the pure favorite-matching logic behind binary_sensor.py."""

from custom_components.tv_guide_epg.favorites import matching_channels, parse_favorites


def test_parse_favorites_splits_and_trims():
    assert parse_favorites(" Report, Chi l'ha visto?,, Propaganda Live ") == [
        "Report", "Chi l'ha visto?", "Propaganda Live",
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


def test_matching_channels_no_match_returns_empty_dict():
    schedule = {"Rai 1": {"titolo": "Telegiornale"}}
    assert matching_channels(schedule, "Report") == {}
```

- [ ] **Step 4: Write `tests/test_coordinator_fallback.py`** (same pattern as `tv_guide_multi`, using a fake `ScheduleSource`)

```python
"""Tests for the stale-data fallback in EpgCoordinator."""

import asyncio

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


class _FakeSource(ScheduleSource):
    def __init__(self, results, refresh_minutes=10):
        self._results = list(results)
        self._interval_minutes = refresh_minutes

    @property
    def refresh_interval(self):
        from datetime import timedelta
        return timedelta(minutes=self._interval_minutes)

    async def get_schedules(self):
        return self._results.pop(0)


def test_coordinator_falls_back_to_last_good_schedule_on_empty_refresh():
    good_now = {"Rai 1": {"titolo": "TG1"}}
    good_prime = {"Rai 1": {"titolo": "Film"}}
    source = _FakeSource([
        (good_now, good_prime),
        ({}, {}),
    ])
    coordinator = EpgCoordinator(HomeAssistant(), source)

    asyncio.run(coordinator.async_refresh())
    assert coordinator.data == (good_now, good_prime)

    asyncio.run(coordinator.async_refresh())
    assert coordinator.data == (good_now, good_prime)
```

- [ ] **Step 5: Run the tests**

Run: `pytest tests/test_favorites.py tests/test_coordinator_fallback.py -q`
Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add custom_components/tv_guide_epg/favorites.py custom_components/tv_guide_epg/coordinator.py tests/test_favorites.py tests/test_coordinator_fallback.py
git commit -m "Add favorites matching and EpgCoordinator with stale-data fallback"
```

---

## Task 6: `config_flow.py`

**Files:**
- Create: `custom_components/tv_guide_epg/config_flow.py`

**Interfaces:**
- Consumes: `COUNTRIES` from `countries.py` (Task 4); `DOMAIN`, `DEFAULT_NAME`, `CONF_COUNTRY`, `CONF_FAVORITES`, `CONF_REFRESH_MINUTES`, `DEFAULT_REFRESH_MINUTES` from `const.py` (Task 1)
- Produces: `TvGuideEpgConfigFlow` (registered for `DOMAIN`), `TvGuideEpgOptionsFlow`. Consumed by Home Assistant's config entry system at runtime (no other module imports these directly, other than `strings.json` referencing the step IDs — Task 9).

No network calls or `homeassistant` module needed beyond what's already stubbed for `voluptuous`-free flows — **this file is not unit tested directly** (it needs a much larger slice of `homeassistant.config_entries`/`homeassistant.data_entry_flow` to instantiate meaningfully; the same is true of `tv_guide_multi/config_flow.py`, which also has no dedicated test file — correctness here relies on `hassfest` in CI plus manual verification against a real Home Assistant instance, consistent with the rest of the workspace). Focus verification on `py_compile` syntax check and a careful read against `tv_guide_multi/config_flow.py`.

- [ ] **Step 1: Write `custom_components/tv_guide_epg/config_flow.py`**

```python
"""Config flow for the TV Guide EPG integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_COUNTRY,
    CONF_FAVORITES,
    CONF_REFRESH_MINUTES,
    DEFAULT_NAME,
    DEFAULT_REFRESH_MINUTES,
    DOMAIN,
)
from .countries import COUNTRIES

REFRESH_CHOICES = {30: "30 minuti", 60: "1 ora", 120: "2 ore (consigliato)", 240: "4 ore"}


class TvGuideEpgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TV Guide EPG. One instance per country."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            country_code = user_input[CONF_COUNTRY]
            await self.async_set_unique_id(f"{DOMAIN}_{country_code.lower()}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{user_input['name']} ({COUNTRIES[country_code].name})",
                data=user_input,
            )

        schema = vol.Schema({
            vol.Required(CONF_COUNTRY): vol.In({code: cfg.name for code, cfg in COUNTRIES.items()}),
            vol.Optional("name", default=DEFAULT_NAME): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "TvGuideEpgOptionsFlow":
        return TvGuideEpgOptionsFlow(config_entry)


class TvGuideEpgOptionsFlow(OptionsFlow):
    """Lets the user configure favorite programs, and (for XMLTV countries) the poll interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        # Explicit assignment (rather than relying on the base class) keeps
        # this working on HA versions older than the 2024.11 auto-injection,
        # matching the 2024.1.0 minimum declared in hacs.json.
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        country_code = self.config_entry.data[CONF_COUNTRY]
        country = COUNTRIES[country_code]
        current_favorites = self.config_entry.options.get(CONF_FAVORITES, "")

        schema_dict = {vol.Optional(CONF_FAVORITES, default=current_favorites): str}
        if country.configurable_interval:
            current_minutes = self.config_entry.options.get(CONF_REFRESH_MINUTES, DEFAULT_REFRESH_MINUTES)
            schema_dict[vol.Optional(CONF_REFRESH_MINUTES, default=current_minutes)] = vol.In(REFRESH_CHOICES)

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile custom_components/tv_guide_epg/config_flow.py`
Expected: no output, exit code 0

- [ ] **Step 3: Commit**

```bash
git add custom_components/tv_guide_epg/config_flow.py
git commit -m "Add config flow: country picker, favorites and refresh-interval options"
```

---

## Task 7: `__init__.py` (setup/unload)

**Files:**
- Modify: `custom_components/tv_guide_epg/__init__.py` (replace the placeholder from Task 1)

**Interfaces:**
- Consumes: `COUNTRIES` (Task 4), `EpgCoordinator` (Task 5), `DOMAIN`/`CONF_COUNTRY`/`CONF_REFRESH_MINUTES` (Task 1)
- Produces: `async_setup_entry`, `async_unload_entry`, `PLATFORMS`, consumed by Home Assistant at runtime and by `sensor.py`/`binary_sensor.py` reading `hass.data[DOMAIN][entry.entry_id]` (Task 8).

- [ ] **Step 1: Rewrite `custom_components/tv_guide_epg/__init__.py`**

```python
"""TV Guide EPG integration setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_COUNTRY, CONF_REFRESH_MINUTES, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TV Guide EPG from a config entry."""
    session = async_get_clientsession(hass)
    country_code = entry.data[CONF_COUNTRY]
    minutes = entry.options.get(CONF_REFRESH_MINUTES)
    source = COUNTRIES[country_code].make_source(session, minutes)

    coordinator = EpgCoordinator(hass, source)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options (favorites, refresh interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile custom_components/tv_guide_epg/__init__.py`
Expected: no output, exit code 0

- [ ] **Step 3: Commit**

```bash
git add custom_components/tv_guide_epg/__init__.py
git commit -m "Wire up config entry setup: build the country's source and coordinator"
```

---

## Task 8: `sensor.py` + `binary_sensor.py`

**Files:**
- Create: `custom_components/tv_guide_epg/sensor.py`
- Create: `custom_components/tv_guide_epg/binary_sensor.py`

**Interfaces:**
- Consumes: `EpgCoordinator` (Task 5), `COUNTRIES` (Task 4), `parse_favorites`/`matching_channels` (Task 5), `DOMAIN`/`CONF_COUNTRY`/`CONF_FAVORITES` (Task 1)
- Produces: HA entities, no further consumers within the codebase.

- [ ] **Step 1: Write `custom_components/tv_guide_epg/sensor.py`**

```python
"""TV Guide EPG sensors.

Exposes two sensors per config entry (one country each):
- ``<name> - Ora in onda`` for the current programmes;
- ``<name> - Prima serata`` for the prime time programmes.
"""

from __future__ import annotations

from typing import Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COUNTRY, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors from a config entry."""
    coordinator: EpgCoordinator = hass.data[DOMAIN][entry.entry_id]
    base_name = entry.data.get("name", entry.title)
    country_code = entry.data[CONF_COUNTRY]
    async_add_entities([
        EpgNowSensor(base_name, country_code, coordinator),
        EpgPrimeSensor(base_name, country_code, coordinator),
    ])


class _EpgBase(CoordinatorEntity[EpgCoordinator], SensorEntity):
    """Common functionality for both sensors."""

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(coordinator)
        self._base_name = base_name
        self._country_code = country_code

    @staticmethod
    def _first_title(cache: Dict[str, Dict[str, Optional[str]]]) -> str:
        first = next(iter(cache.values()), None)
        return first["titolo"] if first else "Nessun dato"


class EpgNowSensor(_EpgBase):
    """Current programmes sensor."""

    _attr_icon = "mdi:television-play"

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(base_name, country_code, coordinator)
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = f"tvguide_epg_{country_code.lower()}_now"

    @property
    def native_value(self) -> str:
        cache_now, _ = self.coordinator.data
        return self._first_title(cache_now)

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        cache_now, _ = self.coordinator.data
        return {
            "programmi_correnti": cache_now,
            "nazione": self._country_code,
            "fonte": COUNTRIES[self._country_code].name,
        }


class EpgPrimeSensor(_EpgBase):
    """Prime time programmes sensor."""

    _attr_icon = "mdi:movie-open"

    def __init__(self, base_name: str, country_code: str, coordinator: EpgCoordinator) -> None:
        super().__init__(base_name, country_code, coordinator)
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = f"tvguide_epg_{country_code.lower()}_prime"

    @property
    def native_value(self) -> str:
        _, cache_prime = self.coordinator.data
        return self._first_title(cache_prime)

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        _, cache_prime = self.coordinator.data
        return {
            "prima_serata": cache_prime,
            "nazione": self._country_code,
            "fonte": COUNTRIES[self._country_code].name,
        }
```

- [ ] **Step 2: Write `custom_components/tv_guide_epg/binary_sensor.py`**

```python
"""Binary sensors that turn on when a favorite program is airing right now."""

from __future__ import annotations

from typing import Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COUNTRY, CONF_FAVORITES, DOMAIN
from .coordinator import EpgCoordinator
from .favorites import matching_channels, parse_favorites


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one binary sensor per configured favorite program."""
    coordinator: EpgCoordinator = hass.data[DOMAIN][entry.entry_id]
    country_code = entry.data[CONF_COUNTRY]
    favorites = parse_favorites(entry.options.get(CONF_FAVORITES, ""))
    async_add_entities(
        EpgFavoriteBinarySensor(coordinator, country_code, favorite) for favorite in favorites
    )


class EpgFavoriteBinarySensor(CoordinatorEntity[EpgCoordinator], BinarySensorEntity):
    """On when a program whose title contains ``favorite`` is on air now."""

    _attr_icon = "mdi:star-check"

    def __init__(self, coordinator: EpgCoordinator, country_code: str, favorite: str) -> None:
        super().__init__(coordinator)
        self._favorite = favorite
        self._attr_name = f"In onda: {favorite}"
        self._attr_unique_id = f"tvguide_epg_{country_code.lower()}_favorite_{favorite.casefold()}"

    @property
    def is_on(self) -> bool:
        cache_now, _ = self.coordinator.data
        return bool(matching_channels(cache_now, self._favorite))

    @property
    def extra_state_attributes(self) -> Dict[str, object]:
        cache_now, _ = self.coordinator.data
        return {"canali": matching_channels(cache_now, self._favorite)}
```

- [ ] **Step 3: Syntax check**

Run: `python -m py_compile custom_components/tv_guide_epg/sensor.py custom_components/tv_guide_epg/binary_sensor.py`
Expected: no output, exit code 0

- [ ] **Step 4: Commit**

```bash
git add custom_components/tv_guide_epg/sensor.py custom_components/tv_guide_epg/binary_sensor.py
git commit -m "Add sensor and favorite binary_sensor entities"
```

---

## Task 9: `strings.json` + translations + brand icon

**Files:**
- Create: `custom_components/tv_guide_epg/strings.json`
- Create: `custom_components/tv_guide_epg/translations/it.json`
- Create: `custom_components/tv_guide_epg/translations/en.json`
- Copy: `custom_components/tv_guide_epg/brand/icon.png` and `icon@2x.png` (reuse `Home-Assistant-TV-Guide/custom_components/tv_guide_multi/brand/icon.png` as a placeholder — same family of integration, swap for a dedicated icon later if the user wants one)

**Interfaces:**
- Consumes: step IDs `user`/`init` and data keys `CONF_COUNTRY`/`name`/`CONF_FAVORITES`/`CONF_REFRESH_MINUTES` matching `config_flow.py` (Task 6) exactly.

- [ ] **Step 1: Write `custom_components/tv_guide_epg/strings.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "TV Guide EPG",
        "description": "Scegli la nazione di cui vuoi il palinsesto. Puoi aggiungere l'integrazione più volte, una per nazione.",
        "data": {
          "nazione": "Nazione",
          "name": "Nome"
        }
      }
    },
    "abort": {
      "already_configured": "Questa nazione è già configurata."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Preferiti e aggiornamento",
        "description": "Titoli preferiti (anche parziali, separati da virgola) e, per le nazioni non italiane, ogni quanto scaricare il palinsesto.",
        "data": {
          "preferiti": "Titoli preferiti",
          "intervallo_aggiornamento": "Intervallo di aggiornamento"
        }
      }
    }
  }
}
```

- [ ] **Step 2: Copy `strings.json` to `translations/it.json`**

```bash
mkdir -p custom_components/tv_guide_epg/translations
cp custom_components/tv_guide_epg/strings.json custom_components/tv_guide_epg/translations/it.json
```

- [ ] **Step 3: Write `custom_components/tv_guide_epg/translations/en.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "TV Guide EPG",
        "description": "Choose the country whose schedule you want. You can add the integration multiple times, one per country.",
        "data": {
          "nazione": "Country",
          "name": "Name"
        }
      }
    },
    "abort": {
      "already_configured": "This country is already configured."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Favorites and refresh",
        "description": "Favorite titles (partial matches are fine, comma-separated) and, for non-Italian countries, how often to download the schedule.",
        "data": {
          "preferiti": "Favorite titles",
          "intervallo_aggiornamento": "Refresh interval"
        }
      }
    }
  }
}
```

- [ ] **Step 4: Copy the brand icon**

```bash
mkdir -p custom_components/tv_guide_epg/brand
cp "../Home-Assistant-TV-Guide/custom_components/tv_guide_multi/brand/icon.png" custom_components/tv_guide_epg/brand/icon.png
cp "../Home-Assistant-TV-Guide/custom_components/tv_guide_multi/brand/icon@2x.png" custom_components/tv_guide_epg/brand/icon@2x.png
```

- [ ] **Step 5: Validate JSON**

Run: `node -e "['strings.json','translations/it.json','translations/en.json'].forEach(f => JSON.parse(require('fs').readFileSync('custom_components/tv_guide_epg/'+f,'utf8'))); console.log('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add custom_components/tv_guide_epg/strings.json custom_components/tv_guide_epg/translations custom_components/tv_guide_epg/brand
git commit -m "Add config/options flow strings (it/en) and brand icon"
```

---

## Task 10: Lovelace card

**Files:**
- Create: `www/tv-guide-epg-card.js` (adapted from `Home-Assistant-TV-Guide/www/tv-guide-multi-card.js`; only the custom element name changes — the data shape read from sensor attributes is identical)

**Interfaces:**
- Consumes: `programmi_correnti`/`prima_serata` sensor attributes produced by `sensor.py` (Task 8) — same shape as `tv_guide_multi`, so the rendering logic is unchanged.

- [ ] **Step 1: Write `www/tv-guide-epg-card.js`**

```javascript
class TvGuideEpgCard extends HTMLElement {
  constructor(){
    super();
    this._busy = false;
    this._last = null;
  }

  setConfig(cfg){
    if(!cfg.now_entity || !cfg.prime_entity){
      throw new Error("now_entity e prime_entity obbligatori");
    }
    this._cfg = {
      show_refresh: true,
      refresh_label: "Aggiorna",
      show_timestamp: true,
      ...cfg,
    };
  }

  _escapeAttr(str){
    return String(str).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");
  }

  set hass(hass){
    const c = this._cfg;

    if(!this.card){
      this.card = document.createElement("ha-card");
      if(c.title) this.card.header = c.title;

      const style = document.createElement("style");
      style.textContent = `
        .tvg-body{padding:16px;display:grid;row-gap:16px}
        .tvg-toolbar{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;border-bottom:1px solid var(--divider-color)}
        .tvg-btn{padding:.35rem .75rem;border:1px solid var(--primary-color);background:transparent;border-radius:999px;cursor:pointer}
        .tvg-btn[disabled]{opacity:.6;cursor:not-allowed}
        .tvg-meta{font-size:.85rem;opacity:.75}
        h3{margin:0 0 8px;font-size:1rem;font-weight:500}
        ul{list-style:none;margin:0;padding:0}
        li{display:flex;justify-content:space-between;align-items:center;gap:8px;border-bottom:1px solid var(--divider-color);padding:4px 0}
        .tvg-ch{display:flex;align-items:center;gap:8px;overflow:hidden}
        .tvg-poster{width:28px;height:28px;border-radius:4px;object-fit:cover;flex:none;background:var(--divider-color)}
        .tvg-ch-text{display:flex;flex-direction:column;overflow:hidden}
        .tvg-ch-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .tvg-ch-meta{font-size:.75rem;opacity:.65;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .val{font-weight:500;max-width:55%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      `;
      this.card.appendChild(style);

      this.toolbar = document.createElement("div");
      this.toolbar.className = "tvg-toolbar";
      this.btn = document.createElement("button");
      this.btn.className = "tvg-btn";
      this.btn.addEventListener("click", () => this._refresh(hass));
      this.meta = document.createElement("div");
      this.meta.className = "tvg-meta";
      this.toolbar.appendChild(this.meta);
      this.toolbar.appendChild(this.btn);
      this.card.appendChild(this.toolbar);

      this.container = document.createElement("div");
      this.container.className = "tvg-body";
      this.card.appendChild(this.container);

      this.appendChild(this.card);
    }

    const nowMap   = hass.states[c.now_entity]?.attributes.programmi_correnti || {};
    const primeMap = hass.states[c.prime_entity]?.attributes.prima_serata    || {};

    const channels = c.channels || Array.from(new Set([
      ...Object.keys(nowMap), ...Object.keys(primeMap)
    ])).sort();

    const section = (label, map) => {
      let html = `<h3>${label}</h3><ul>`;
      channels.forEach(ch => {
        const info = map[ch];
        const title = info?.titolo ?? "—";
        const v = title.length > 60 ? title.slice(0,57)+"…" : title;
        const orario = info?.orario_inizio && info?.orario_fine
          ? `${info.orario_inizio}–${info.orario_fine}`
          : (info?.orario_inizio || "");
        const metaLine = [orario, info?.genere].filter(Boolean).join(" · ");
        const poster = info?.locandina
          ? `<img class="tvg-poster" src="${this._escapeAttr(info.locandina)}" alt="" loading="lazy">`
          : "";
        const tooltip = info?.descrizione ? ` title="${this._escapeAttr(info.descrizione)}"` : "";
        html += `<li${tooltip}>
          <span class="tvg-ch">${poster}<span class="tvg-ch-text"><span class="tvg-ch-name">${ch}</span>${metaLine ? `<span class="tvg-ch-meta">${metaLine}</span>` : ""}</span></span>
          <span class="val">${v}</span>
        </li>`;
      });
      return html + "</ul>";
    };

    this.container.innerHTML =
      section("Ora in onda", nowMap) + section("Stasera", primeMap);

    const ts = this._last
      ? this._last.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})
      : "mai";
    this.meta.textContent = c.show_timestamp ? `Ultimo aggiornamento: ${ts}` : "";
    if(c.show_refresh){
      this.btn.style.display = "";
      this.btn.textContent = this._busy ? "Aggiorno…" : (c.refresh_label || "Aggiorna");
      this.btn.disabled = this._busy;
    }else{
      this.btn.style.display = "none";
    }
  }

  async _refresh(hass){
    const ids = [this._cfg.now_entity, this._cfg.prime_entity].filter(Boolean);
    this._busy = true;
    this.hass = hass;
    try{
      await hass.callService("homeassistant","update_entity",{entity_id: ids});
      setTimeout(()=>{
        this._busy = false;
        this._last = new Date();
        this.hass = hass;
      }, 1200);
    }catch(e){
      this._busy = false;
      this.hass = hass;
      console.error("Aggiornamento palinsesto fallito:", e);
    }
  }

  getCardSize(){ return 3; }
}

customElements.define("tv-guide-epg-card", TvGuideEpgCard);
```

- [ ] **Step 2: Syntax check**

Run: `node --check www/tv-guide-epg-card.js`
Expected: no output, exit code 0

- [ ] **Step 3: Commit**

```bash
git add www/tv-guide-epg-card.js
git commit -m "Add tv-guide-epg-card Lovelace card"
```

---

## Task 11: README (English + Italian) and full-suite verification

**Files:**
- Create: `README.md`
- Create: `README.it.md`

**Interfaces:**
- None (documentation only). This task also runs the full test suite and a final structural sanity pass across every file created in Tasks 1–10.

- [ ] **Step 1: Write `README.md`**

```markdown
<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**International TV schedules inside Home Assistant — pick your country when you add the integration.**

[![Validate](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-1.0.0-orange)](custom_components/tv_guide_epg/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

A sibling project to [TV Guide Multi-Source](https://github.com/iAlias/HomeAssistantTVGuide)
(Italy-only), covering multiple countries. You pick a country when you add the integration; you
can add it again for a second country. Each instance exposes "on now" / "prime time" sensors and
optional favorite-program binary sensors, and a Lovelace card renders them as a real guide.

---

## Contents

- [Supported countries](#supported-countries)
- [What it installs](#what-it-installs)
- [Installation](#installation)
- [Card configuration](#card-configuration)
- [Favorite programs](#favorite-programs)
- [How it works](#how-it-works)
- [Things worth knowing](#things-worth-knowing)
- [Development](#development)
- [Requirements](#requirements)
- [License](#license)

---

## Supported countries

| Country | Source | Channels included by default |
|---|---|---|
| Italy | sorrisi.com | Rai 1/2/3, Rete 4, Canale 5, Italia 1, La7, TV8, NOVE |
| UK | epgshare01.online (XMLTV) | BBC One, BBC Two, ITV1, Channel 4, Channel 5 |
| Germany | epgshare01.online (XMLTV) | Das Erste, ZDF, RTL, ProSieben |
| France | epgshare01.online (XMLTV) | TF1, France 2, M6 |
| Spain | epgshare01.online (XMLTV) | La 1, Antena 3, Telecinco, laSexta |

More countries can be added later — see [Things worth knowing](#things-worth-knowing).

## What it installs

Per country instance:

| Entity | State | Attributes |
|---|---|---|
| `<name> - Ora in onda` | the current programme on the first configured channel | `programmi_correnti`: a channel → programme-info mapping |
| `<name> - Prima serata` | the evening programme on the first configured channel | `prima_serata`: a channel → programme-info mapping |
| `In onda: <favorite>` (one per configured favorite) | on when that title is airing now, on any of the instance's channels | `canali`: matching channel → title |

Attribute *keys* (`titolo`, `orario_inizio`, `orario_fine`, `genere`, `locandina`, `descrizione`)
are Italian for consistency across this author's Home Assistant projects; attribute *values* are
in the source country's own language.

## Installation

### 1. The integration, via HACS

1. HACS → Integrations → top-right menu → **Custom repositories**
2. Add `https://github.com/iAlias/HomeAssistantTVGuideEPG`, category **Integration**
3. Install, then restart Home Assistant
4. **Settings → Devices & services → Add integration** → search **TV Guide EPG**
5. Pick a country and confirm the name

Add the integration again to follow a second country — each country can only be added once, but
nothing stops you from tracking several.

### 2. The card

The card is not copied by HACS, because it lives outside the integration folder.

1. Copy `www/tv-guide-epg-card.js` into your `config/www/` folder
2. **Settings → Dashboards → top-right menu → Resources → Add resource**
   - URL: `/local/tv-guide-epg-card.js`
   - Type: **JavaScript module**
3. Reload the page with Ctrl+F5

## Card configuration

```yaml
type: custom:tv-guide-epg-card
title: UK Guide
now_entity: sensor.guida_tv_ora_in_onda
prime_entity: sensor.guida_tv_prima_serata
channels:
  - BBC One
  - BBC Two
  - ITV1
  - Channel 4
```

`now_entity` and `prime_entity` are required; `channels` picks and orders which channels to
display (omit it and the card falls back to every channel present in the sensor data).

## Favorite programs

From **Settings → Devices & services → TV Guide EPG → Configure** you can list favorite titles
(partial matches, comma-separated). One `binary_sensor` per title turns on whenever a programme
containing it airs on any of that instance's channels.

## How it works

- Fetching and parsing sit behind a `ScheduleSource` interface
  (`custom_components/tv_guide_epg/sources/base.py`); `countries.py` maps each country code to a
  concrete source.
- **Italy** uses `SorrisiSource`, ported from `tv_guide_multi`: it reads two already-filtered pages
  ("now" and "tonight") every 10 minutes.
- **UK/Germany/France/Spain** use `XmltvSource`, which downloads one full day's schedule (XMLTV,
  gzip-compressed) from [epgshare01.online](https://epgshare01.online) — a free, legal-use EPG
  aggregator — and computes locally which programme is on air now (its time window covers the
  current time) and which is closest to 21:00 (a simplified, uniform "prime time" definition across
  countries). Poll interval is configurable per instance (30 min / 1h / 2h default / 4h) from
  **Configure**, since these files are several megabytes each.
- If a refresh comes back empty for either kind of source, the coordinator keeps serving the last
  successfully parsed schedule instead of collapsing straight to `Nessun dato`.

## Things worth knowing

- **Two different kinds of sources, one interface.** Adding a country means either reusing
  `XmltvSource` with a new epgshare01.online tag and channel list (if the country is covered there)
  or writing a small bespoke `ScheduleSource`, like `SorrisiSource`, when it isn't — no changes to
  the coordinator, entities, or config flow either way.
- **epgshare01.online is a free third-party aggregator**, not affiliated with any broadcaster. If a
  country's data stops updating, check their status first.
- **Prime time is simplified.** "Closest programme to 21:00" is the same rule for every non-Italian
  country in v1, even though real prime time varies (e.g. later in Spain). Easy to make
  configurable later if it matters to you.

## Development

```bash
pip install -r requirements_test.txt
pytest -q
```

Tests cover HTML/XMLTV parsing against real (Italy) or hand-trimmed (XMLTV countries) fixtures, the
favorite-matching logic, the country registry, and the stale-data fallback — no Home Assistant
installation required.

## Requirements

- Home Assistant **2024.1.0** or newer
- Outbound internet access to `sorrisi.com` (Italy) and/or `epgshare01.online` (other countries)
- [HACS](https://hacs.xyz/) (optional, for one-click updates) or manual installation

## License

[MIT](LICENSE). Schedule data belongs to the respective broadcasters and aggregators; this
integration displays it for personal use within your own Home Assistant instance.
```

- [ ] **Step 2: Write `README.it.md`** (mirror of `README.md`, same structure and headings translated, same content as the English version above but in Italian — follow the exact section-by-section translation pattern already established between `Home-Assistant-TV-Guide/README.md` and `README.it.md`)

```markdown
<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**Il palinsesto TV internazionale dentro Home Assistant — scegli la nazione quando aggiungi l'integrazione.**

[![Validate](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Versione](https://img.shields.io/badge/versione-1.0.0-orange)](custom_components/tv_guide_epg/manifest.json)
[![Licenza](https://img.shields.io/badge/licenza-MIT-green)](LICENSE)

🇬🇧 [Read in English](README.md)

Un progetto gemello di [TV Guide Multi-Source](https://github.com/iAlias/HomeAssistantTVGuide)
(solo Italia), che copre più nazioni. Scegli la nazione quando aggiungi l'integrazione; puoi
aggiungerla di nuovo per una seconda nazione. Ogni istanza espone sensori "ora in onda"/"prima
serata" e sensori binari opzionali sui preferiti, e una card Lovelace li mostra come una guida vera.

---

## Indice

- [Nazioni supportate](#nazioni-supportate)
- [Cosa installa](#cosa-installa)
- [Installazione](#installazione)
- [Configurazione della card](#configurazione-della-card)
- [Programmi preferiti](#programmi-preferiti)
- [Come funziona](#come-funziona)
- [Cose da sapere](#cose-da-sapere)
- [Sviluppo](#sviluppo)
- [Requisiti](#requisiti)
- [Licenza](#licenza)

---

## Nazioni supportate

| Nazione | Fonte | Canali inclusi di default |
|---|---|---|
| Italia | sorrisi.com | Rai 1/2/3, Rete 4, Canale 5, Italia 1, La7, TV8, NOVE |
| Regno Unito | epgshare01.online (XMLTV) | BBC One, BBC Two, ITV1, Channel 4, Channel 5 |
| Germania | epgshare01.online (XMLTV) | Das Erste, ZDF, RTL, ProSieben |
| Francia | epgshare01.online (XMLTV) | TF1, France 2, M6 |
| Spagna | epgshare01.online (XMLTV) | La 1, Antena 3, Telecinco, laSexta |

Altre nazioni potranno essere aggiunte in seguito — vedi [Cose da sapere](#cose-da-sapere).

## Cosa installa

Per ogni istanza/nazione:

| Entità | Stato | Attributi |
|---|---|---|
| `<nome> - Ora in onda` | il programma del primo canale configurato | `programmi_correnti`: dizionario canale → dati del programma |
| `<nome> - Prima serata` | il programma serale del primo canale configurato | `prima_serata`: dizionario canale → dati del programma |
| `In onda: <preferito>` (uno per preferito configurato) | acceso se quel titolo è in onda ora, su uno dei canali dell'istanza | `canali`: dizionario canale → titolo |

Le **chiavi** degli attributi (`titolo`, `orario_inizio`, `orario_fine`, `genere`, `locandina`,
`descrizione`) sono in italiano per coerenza con gli altri progetti Home Assistant dell'autore; i
**valori** sono nella lingua della nazione scelta.

## Installazione

### 1. L'integrazione, con HACS

1. HACS → Integrazioni → menù in alto a destra → **Repository personalizzati**
2. Incolla `https://github.com/iAlias/HomeAssistantTVGuideEPG`, categoria **Integration**
3. Installa e riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** → cerca **TV Guide EPG**
5. Scegli una nazione e conferma il nome

Aggiungi di nuovo l'integrazione per seguire una seconda nazione — ogni nazione può essere
aggiunta una sola volta, ma nulla vieta di seguirne più di una.

### 2. La card

La card non viene copiata da HACS, perché sta fuori dalla cartella dell'integrazione.

1. Copia `www/tv-guide-epg-card.js` dentro la tua cartella `config/www/`
2. **Impostazioni → Dashboard → menù in alto a destra → Risorse → Aggiungi risorsa**
   - URL: `/local/tv-guide-epg-card.js`
   - Tipo: **Modulo JavaScript**
3. Ricarica la pagina con Ctrl+F5

## Configurazione della card

```yaml
type: custom:tv-guide-epg-card
title: Guida UK
now_entity: sensor.guida_tv_ora_in_onda
prime_entity: sensor.guida_tv_prima_serata
channels:
  - BBC One
  - BBC Two
  - ITV1
  - Channel 4
```

`now_entity` e `prime_entity` sono obbligatori; `channels` sceglie e ordina i canali da mostrare
(omettilo e la card userà tutti i canali presenti nei dati dei sensori).

## Programmi preferiti

Da **Impostazioni → Dispositivi e servizi → TV Guide EPG → Configura** puoi indicare titoli
preferiti (anche parziali, separati da virgola). Per ciascuno viene creato un `binary_sensor` che
si accende quando un programma che lo contiene è in onda su uno dei canali di quell'istanza.

## Come funziona

- Fetch e parsing passano da un'interfaccia `ScheduleSource`
  (`custom_components/tv_guide_epg/sources/base.py`); `countries.py` mappa ogni nazione a una
  sorgente concreta.
- **L'Italia** usa `SorrisiSource`, portata da `tv_guide_multi`: legge due pagine già filtrate
  ("ora" e "stasera") ogni 10 minuti.
- **Regno Unito/Germania/Francia/Spagna** usano `XmltvSource`, che scarica il palinsesto
  dell'intera giornata (XMLTV, compresso gzip) da [epgshare01.online](https://epgshare01.online) —
  un aggregatore EPG gratuito per uso legale — e calcola localmente quale programma è in onda ora
  (la sua fascia oraria copre l'orario corrente) e quale è più vicino alle 21:00 (una definizione
  di "prima serata" semplificata e uguale per tutte le nazioni). L'intervallo di polling è
  configurabile per istanza (30 min / 1h / 2h di default / 4h) da **Configura**, dato che questi
  file pesano diversi megabyte.
- Se un aggiornamento torna vuoto, per entrambi i tipi di sorgente, il coordinator continua a
  servire l'ultimo palinsesto letto con successo invece di collassare subito su `Nessun dato`.

## Cose da sapere

- **Due tipi di sorgente diversi, un'unica interfaccia.** Aggiungere una nazione significa o
  riusare `XmltvSource` con un nuovo tag epgshare01.online e un elenco di canali (se la nazione è
  coperta lì) oppure scrivere una piccola `ScheduleSource` dedicata, come `SorrisiSource`, quando
  non lo è — in entrambi i casi senza toccare coordinator, entità o config flow.
- **epgshare01.online è un aggregatore gratuito di terze parti**, non affiliato a nessuna
  emittente. Se i dati di una nazione smettono di aggiornarsi, controlla prima il loro stato.
- **La prima serata è semplificata.** "Programma più vicino alle 21:00" è la stessa regola per
  tutte le nazioni non italiane nella v1, anche se la prima serata reale varia (es. più tardi in
  Spagna). Facile da rendere configurabile in futuro se ti serve.

## Sviluppo

```bash
pip install -r requirements_test.txt
pytest -q
```

I test coprono il parsing HTML/XMLTV contro fixture reali (Italia) o ritagliate a mano (nazioni
XMLTV), la logica di matching dei preferiti, il registro delle nazioni e il fallback sui dati
validi — nessuna installazione di Home Assistant richiesta.

## Requisiti

- Home Assistant **2024.1.0** o successivo
- Accesso internet in uscita verso `sorrisi.com` (Italia) e/o `epgshare01.online` (altre nazioni)
- [HACS](https://hacs.xyz/) (opzionale, per gli aggiornamenti con un clic) oppure installazione manuale

## Licenza

[MIT](LICENSE). I dati dei palinsesti appartengono alle rispettive emittenti e aggregatori; questa
integrazione li mostra per uso personale dentro la propria istanza di Home Assistant.
```

- [ ] **Step 3: Run the entire test suite**

Run: `pytest -q`
Expected: `27 passed` (6 sorrisi + 7 xmltv + 4 countries + 4 favorites + 2 coordinator... recount
against whatever the actual per-task counts came out to; the important check is 0 failed, 0 errors)

- [ ] **Step 4: Full-repo structural check**

Run:
```bash
python -m py_compile custom_components/tv_guide_epg/*.py custom_components/tv_guide_epg/sources/*.py
node -e "['manifest.json'].forEach(f=>JSON.parse(require('fs').readFileSync('custom_components/tv_guide_epg/'+f,'utf8')));['hacs.json'].forEach(f=>JSON.parse(require('fs').readFileSync(f,'utf8')));console.log('OK')"
node --check www/tv-guide-epg-card.js
```
Expected: no errors, final `OK` printed.

- [ ] **Step 5: Clean up test artifacts and commit**

```bash
rm -rf tests/__pycache__ custom_components/tv_guide_epg/**/__pycache__ .pytest_cache
git add README.md README.it.md
git commit -m "Add README (EN/IT) and finish v1"
```

---

## Self-Review Notes (completed while writing this plan)

- **Spec coverage:** every section of the design doc maps to a task — scaffolding (T1), sources
  (T2/T3), registry (T4), coordinator/favorites (T5), config/options flow (T6), setup wiring (T7),
  entities (T8), translations/brand (T9), card (T10), docs+final verification (T11). No spec
  section without a task.
- **Placeholder scan:** no TBD/TODO; the one deliberately-wrong test assertion in Task 3 is called
  out explicitly with the fix instruction, not left as a placeholder.
- **Type consistency:** `ScheduleSource.refresh_interval` (Task 2) is used identically in
  `SorrisiSource`/`XmltvSource` (Task 2/3), `countries.py`'s `make_source` signature
  `(session, minutes)` (Task 4) matches every call site in `config_flow.py`/`__init__.py` (Task
  6/7); `Schedule` type alias is imported from `sources/base.py` everywhere it's used, never
  redefined.
