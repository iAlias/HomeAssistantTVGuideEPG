<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**International TV schedules inside Home Assistant — pick your country when you add the integration.**

[![Validate](https://github.com/iAlias/HomeAssistantTvGuideMulti/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTvGuideMulti/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-1.0.0-orange)](custom_components/tv_guide_epg/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

A sibling project to [TV Guide Multi-Source](https://github.com/iAlias/HomeAssistantTVGuide)
(Italy only), covering several countries. You pick a country when you add the integration, and can
add it again for a second one. Each instance exposes "on now" and "prime time" sensors, optional
favorite-program binary sensors, and a Lovelace card that renders them as a real guide.

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
| Italy | sorrisi.com | Rai 1, Rai 2, Rai 3, Rete 4, Canale 5, Italia 1, La7, TV8, NOVE |
| United Kingdom | epgshare01.online (XMLTV) | BBC One, BBC Two, ITV1, Channel 4, Channel 5 |
| Germany | epgshare01.online (XMLTV) | Das Erste, ZDF, RTL, SAT.1, ProSieben, VOX |
| France | epgshare01.online (XMLTV) | TF1, France 2, France 3, France 5, M6, Arte |
| Spain | epgshare01.online (XMLTV) | La 1, La 2, Antena 3, Cuatro, Telecinco, laSexta |

Every channel above was verified against the live feed — ids present in a feed but carrying no
programme data were deliberately left out. More countries can be added later; see
[Things worth knowing](#things-worth-knowing).

## What it installs

Per country instance:

| Entity | State | Attributes |
|---|---|---|
| `<name> - Ora in onda` | the current programme on the first configured channel | `programmi_correnti`: a channel → programme-info mapping, plus `nazione` and `fonte` |
| `<name> - Prima serata` | the evening programme on the first configured channel | `prima_serata`: a channel → programme-info mapping, plus `nazione` and `fonte` |
| `In onda: <favorite>` (one per configured favorite) | on when that title is airing now, on any of the instance's channels | `canali`: matching channel → title |

Each programme carries `titolo`, `orario_inizio`, `orario_fine`, `genere`, `locandina` and
`descrizione` (fields the source doesn't publish come back empty). Attribute *keys* are Italian for
consistency with this author's other Home Assistant projects; attribute *values* are in the source
country's own language.

## Installation

### 1. The integration, via HACS

1. HACS → Integrations → top-right menu → **Custom repositories**
2. Add `https://github.com/iAlias/HomeAssistantTvGuideMulti`, category **Integration**
3. Install, then restart Home Assistant
4. **Settings → Devices & services → Add integration** → search **TV Guide EPG**
5. Pick a country and confirm the name (it becomes the prefix for both sensors)

Add the integration again to follow a second country. Each country can only be added once.

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

`now_entity` and `prime_entity` are required; `channels` picks and orders which channels to show
(omit it and the card displays every channel present in the sensor data, in the order the
integration provides). Point a second card at a second country's entities to show both.

## Favorite programs

From **Settings → Devices & services → TV Guide EPG → Configure** you can list favorite titles
(partial matches are fine, comma-separated, e.g. `Casualty, Report`). One `binary_sensor` per
title turns on whenever a programme containing it airs on any of that instance's channels —
handy for an automation that notifies you when a show you follow starts.

The same screen lets you choose how often the schedule is downloaded (30 minutes / 1 hour /
2 hours / 4 hours) for the XMLTV-based countries. Italy is not listed there: it polls small,
already-filtered pages every 10 minutes.

## How it works

- Fetching and parsing sit behind a `ScheduleSource` interface
  (`custom_components/tv_guide_epg/sources/base.py`); `countries.py` maps each country code to a
  concrete source, so adding a country touches nothing else.
- **Italy** uses `SorrisiSource`, ported from `tv_guide_multi`: it reads two already-filtered pages
  ("ora in tv" and "stasera in tv") every 10 minutes.
- **UK / Germany / France / Spain** use `XmltvSource`, which downloads one full day's schedule
  (XMLTV, gzip-compressed) from [epgshare01.online](https://epgshare01.online) — a free EPG
  aggregator for legal use — and works out locally which programme is on air (its time window
  covers the current moment) and which is closest to 21:00. Because these files are several
  megabytes, the poll interval is configurable and defaults to 2 hours.
- If a refresh comes back empty, for either kind of source, the coordinator keeps serving the last
  successfully parsed schedule instead of collapsing straight to `Nessun dato`.

## Things worth knowing

- **Two kinds of source, one interface.** Adding a country means either reusing `XmltvSource` with
  a new epgshare01.online tag and channel list, or writing a small bespoke `ScheduleSource` like
  `SorrisiSource` when no usable feed exists — no changes to the coordinator, entities, card or
  config flow either way.
- **epgshare01.online is a free third-party aggregator**, not affiliated with any broadcaster. If a
  country stops updating, check their status first.
- **Prime time is simplified.** "The programme closest to 21:00" is the same rule for every
  XMLTV country in v1, even though real prime time varies by country (later in Spain, earlier in
  Germany). Easy to make configurable later.
- **Channel ids are not guesses.** Every default channel was checked against the real feed; for
  example `Channel.5.uk` exists but is empty, so the UK list uses `Channel.5.HD.uk` instead.

## Development

```bash
pip install -r requirements_test.txt
pytest -q
```

Tests cover HTML parsing (Italy, against full real pages), XMLTV parsing and the now/prime-time
computation (against a trimmed excerpt, with an injected clock so results don't depend on when the
suite runs), the favorite-matching logic, the country registry, and the stale-data fallback — no
Home Assistant installation required.

## Requirements

- Home Assistant **2025.1.0** or newer
- Outbound internet access to `sorrisi.com` (Italy) and/or `epgshare01.online` (other countries)
- [HACS](https://hacs.xyz/) (optional, for one-click updates) or manual installation

## License

[MIT](LICENSE). Schedule data belongs to the respective broadcasters and aggregators; this
integration displays it for personal use within your own Home Assistant instance.
