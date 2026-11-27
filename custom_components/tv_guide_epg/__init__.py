"""TV Guide EPG integration setup."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import homeassistant.helpers.config_validation as cv
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.setup import async_when_setup

from .const import CONF_COUNTRY, CONF_PRIME_TIME_HOUR, CONF_REFRESH_MINUTES, DEFAULT_PRIME_TIME_HOUR, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES, make_italy_sources, source_name

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = ["sensor", "binary_sensor"]
CARD_URL_PATH = f"/{DOMAIN}"
CARD_FILENAME = "tv-guide-epg-card.js"
CARD_JS_URL = f"{CARD_URL_PATH}/{CARD_FILENAME}"
CARD_DIR = Path(__file__).parent / "frontend"
_CARD_REGISTERED = f"{DOMAIN}_card_registered"
LOVELACE_DOMAIN = "lovelace"


def _card_version() -> str:
    try:
        manifest = json.loads((Path(__file__).parent / "manifest.json").read_text("utf-8"))
        return str(manifest.get("version", "0"))
    except (OSError, ValueError):
        return "0"


async def _async_register_card(hass: HomeAssistant) -> None:
    if hass.data.get(_CARD_REGISTERED):
        return
    hass.data[_CARD_REGISTERED] = True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(CARD_DIR), cache_headers=False)]
    )
    async_when_setup(hass, LOVELACE_DOMAIN, _async_add_lovelace_resource)


async def _async_add_lovelace_resource(hass: HomeAssistant, component: str) -> None:
    resources = getattr(hass.data.get(LOVELACE_DOMAIN), "resources", None)
    if resources is None:
        _LOGGER.warning("Lovelace resources unavailable; add %s manually as a JavaScript module", CARD_JS_URL)
        return
    if getattr(resources, "store", None) is None:
        _LOGGER.warning("Lovelace is in YAML mode: add %s to your resources as a module", CARD_JS_URL)
        return
    await resources.async_get_info()
    wanted = f"{CARD_JS_URL}?v={_card_version()}"
    for item in resources.async_items():
        if not str(item.get("url", "")).startswith(CARD_JS_URL):
            continue
        if item["url"] != wanted:
            await resources.async_update_item(item["id"], {"url": wanted})
        return
    await resources.async_create_item({"res_type": "module", "url": wanted})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await _async_register_card(hass)

    async def _async_refresh_service(call: ServiceCall) -> None:
        country = call.data.get(CONF_COUNTRY)
        entries = hass.data.get(DOMAIN, {})
        for entry_id, coordinators in entries.items():
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry and (not country or entry.data.get(CONF_COUNTRY) == country):
                for coordinator in coordinators.values():
                    await coordinator.async_refresh()

    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(DOMAIN, "refresh", _async_refresh_service)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_register_card(hass)
    session = async_get_clientsession(hass)
    country_code = entry.data[CONF_COUNTRY]
    if country_code == "IT":
        sources = make_italy_sources(
            session,
            entry.options.get(CONF_REFRESH_MINUTES),
            entry.options.get(CONF_PRIME_TIME_HOUR, DEFAULT_PRIME_TIME_HOUR),
        )
    else:
        sources = {"epgshare": COUNTRIES[country_code].make_source(
            session, entry.options.get(CONF_REFRESH_MINUTES),
            entry.options.get(CONF_PRIME_TIME_HOUR, DEFAULT_PRIME_TIME_HOUR),
        )}
    coordinators = {}
    for source_id, source in sources.items():
        coordinator = EpgCoordinator(
            hass, entry, source, source_id,
            source_name(source_id) if country_code == "IT" else COUNTRIES[country_code].name,
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[source_id] = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
