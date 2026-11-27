<img src="custom_components/tv_guide_epg/brand/icon.png" width="96" alt="TV Guide EPG" align="right">

# TV Guide EPG

**TV schedules inside Home Assistant, with an EPG provider selectable per Lovelace card.**

[![Validate](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantTVGuideEPG/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-2.3.1-orange)](custom_components/tv_guide_epg/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

The integration creates Home Assistant sensors for programmes currently on air and prime time.
Its Lovelace card includes search, filters, programme progress, upcoming programmes and posters
when the provider supplies artwork.

For Italy, four providers are selectable independently in each card: Sorrisi, IPTV-EPG.org,
ZapprTV and EPG Italia. Each provider has its own coordinator and sensor set. This means that
two cards can display different EPG providers at the same time.

> **Testing status:** version 2.3.1 is under testing on the
> [feature branch](https://github.com/iAlias/HomeAssistantTVGuideEPG/tree/feature/card-source-selector)
> and has not been merged into `main` or published as a HACS release. Provider feeds and channel
> coverage must be checked in a real Home Assistant installation. See [Provider notes](#provider-notes).

---

## Contents

- [Supported countries and providers](#supported-countries-and-providers)
- [What it installs](#what-it-installs)
- [Installation](#installation)
- [Lovelace card](#lovelace-card)
- [Favorite programs](#favorite-programs)
- [How it works](#how-it-works)
- [Provider notes](#provider-notes)
- [Development and tests](#development-and-tests)
- [Requirements](#requirements)
- [License](#license)

---

## Supported countries and providers

| Country | Provider | Implementation |
|---|---|---|
| Italy | Sorrisi | Existing Sorrisi HTML source |
| Italy | IPTV-EPG.org | XMLTV feed, channel matching by display name |
| Italy | ZapprTV | Aggregated JSON feed and published channel identifiers |
| Italy | EPG Italia | XMLTV feed, channel matching by display name |
| United Kingdom | epgshare01.online | XMLTV |
| Germany | epgshare01.online | XMLTV |
| France | epgshare01.online | XMLTV |
| Spain | epgshare01.online | XMLTV |

The Italian XMLTV adapters recognize a set of national channels, including Rai, Mediaset, LA7,
TV8, NOVE, Real Time, DMAX and Cielo. Actual availability depends on the channel names and
programme records present in each provider's feed. ZapprTV currently has a narrower explicit
channel mapping; it does not provide every channel in the XMLTV adapters' list.

The integration does not guarantee that every provider carries every channel or that every
programme includes a description or poster.

## What it installs

For each channel and provider, the integration creates two sensors:

| Sensor | State | Useful attributes |
|---|---|---|
| `<channel> - Ora in onda` | Current programme title | `orario_inizio`, `orario_fine`, `genere`, `locandina`, `descrizione`, `prossimi` |
| `<channel> - Prima serata` | Programme closest to prime time | Same programme attributes |

Each sensor also exposes `canale`, `nazione`, `fonte`, `source_id`, `tipo` and `posizione`.
The `source_id` attribute lets the Lovelace card select only the sensors belonging to the
configured provider.

Favorite-program binary sensors are also available. They monitor the primary source for the
configured country (Sorrisi for Italy).

## Installation

### Home Assistant Marketplace (Home Assistant 2026.11 and newer)

1. Open **Settings → Marketplace**.
2. Select **Add from link** in the upper-right corner.
3. In **GitHub link**, enter `https://github.com/iAlias/HomeAssistantTVGuideEPG`.
4. Select **Add**. If the Marketplace cannot detect the content type, choose **Integration** and add it again.
5. Open **TV Guide EPG** from the repository list and select **Install**.
6. Follow the integration setup flow. If Home Assistant asks for a restart, restart before completing setup.

Adding a custom repository requires connecting a GitHub account to the Marketplace. The repository must be public and contain the `hacs.json` file in its root.

### Older installations using HACS (Home Assistant 2026.10 and older)

1. Open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/iAlias/HomeAssistantTVGuideEPG` with category **Integration**.
3. Install the integration and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Search for **TV Guide EPG**, choose a country and complete setup.


### Manual installation

Copy the `custom_components/tv_guide_epg` directory into
`<config>/custom_components/tv_guide_epg`, then restart Home Assistant.

The integration serves its Lovelace card as a frontend module after setup. You should not need
to copy the JavaScript file into `config/www` or add a separate resource manually. If you had
previously added a manual card resource, remove the obsolete resource and reload the browser.

## Lovelace card

Add **Guida TV EPG** from the Lovelace card picker. The visual editor includes a **Fonte EPG**
dropdown. The chosen provider is stored in that card's own configuration, so changing one card
does not change the provider selected in another card.

The basic YAML configuration is:

```yaml
type: custom:tv-guide-epg-card
```

Optional settings:

```yaml
type: custom:tv-guide-epg-card
title: Guida TV
nazione: IT
source_id: zappr
channels:
  - Rai 1
  - Rai 2
  - Canale 5
```

Available Italian `source_id` values:

| Provider | Value |
|---|---|
| Sorrisi | `sorrisi` |
| IPTV-EPG.org | `iptv_epg` |
| ZapprTV | `zappr` |
| EPG Italia | `epgitalia` |

Normally, select the provider from the visual editor instead of entering `source_id` manually.
The card offers providers for which it can find source sensors in Home Assistant.

The card provides:
- search by channel or programme;
- **All**, **On now**, **Upcoming** and **Prime time** filters;
- programme progress bar;
- horizontal strip of upcoming programmes;
- poster images when available, with a fallback when an image cannot load;
- manual refresh.

## Favorite programs

Open **Settings → Devices & services → TV Guide EPG → Configure** to enter favorite titles.
Partial matches are accepted; separate multiple titles with commas. A binary sensor turns on
when a matching title is airing on one of the primary source's channels.

The options flow also controls refresh intervals for sources that support a configurable
interval. Some providers use their own fixed refresh interval.

## How it works

- Each provider implements the `ScheduleSource` interface.
- Each active provider gets a separate `EpgCoordinator`, so refresh failures and cached schedules
  are isolated from other providers.
- The sensor platform creates separate entities per provider and channel. Provider-specific
  entity IDs include the source identifier; existing primary-source entity IDs are retained where
  possible for compatibility.
- The Lovelace card filters sensors by `source_id`. Its selection is local to the card.
- The `tv_guide_epg.refresh` service refreshes the configured providers for the selected country
  (or all configured countries if no country is supplied).

## Provider notes

- **Sorrisi:** the project retains the existing HTML extraction code. The site's published terms
  restrict automated extraction and reuse of its content. Check the current terms and obtain
  written permission from the provider before redistributing or using this source beyond permitted
  personal use. Keeping the adapter in this repository does not mean that its use is authorized.
- **IPTV-EPG.org and EPG Italia:** these adapters read external XMLTV feeds and match channel
  display names against a maintained alias list. Feed format, reachability, channel naming and
  coverage can change. An unmatched channel will not have programme data.
- **ZapprTV:** the adapter depends on the JSON feed and channel identifiers published by the
  ZapprTV project. Its upstream data can change independently of this integration. The repository
  code's license does not automatically grant rights to upstream schedules, logos or images.
- **Data and images:** programme data, descriptions, artwork and logos remain subject to the
  respective provider's terms and rights. The integration does not claim ownership of them.
- **Fallback:** when a provider refresh fails or returns no usable data, its coordinator attempts
  to keep its last valid schedule. A different provider is not silently substituted.

## Development and tests

Install the test dependencies and run:

```bash
pip install -r requirements_test.txt
pytest -q
```

These tests do not replace a full Home Assistant test. Before treating a provider as production
ready, verify its live endpoint, response schema, channel coverage, programme times and images
from the target Home Assistant installation.

## Requirements

- Home Assistant version compatible with the integration manifest (2025.1.0 or newer).
- Outbound HTTPS access to the selected EPG provider.
- HACS for managed installation, or manual installation.

## License

The integration source code is released under the [MIT License](LICENSE). This license applies
to this repository's code; it does not grant rights to third-party EPG data, descriptions, logos,
posters or other provider content.
