"""TV Guide EPG integration setup."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_COUNTRY, CONF_REFRESH_MINUTES, DOMAIN
from .coordinator import EpgCoordinator
from .countries import COUNTRIES

PLATFORMS = ["sensor", "binary_sensor"]

# The card ships inside the integration folder, so it is served by Home
# Assistant itself and loaded on every dashboard. That way it shows up under
# "Add card" as soon as an instance is configured, with no copy into
# config/www and no manually added Lovelace resource.
CARD_URL_PATH = f"/{DOMAIN}"
CARD_FILENAME = "tv-guide-epg-card.js"
CARD_JS_URL = f"{CARD_URL_PATH}/{CARD_FILENAME}"
CARD_DIR = Path(__file__).parent / "frontend"
_CARD_REGISTERED = f"{DOMAIN}_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card once per Home Assistant run, and load it everywhere.

    Called from both ``async_setup`` and ``async_setup_entry``: Home Assistant
    only runs ``async_setup`` when the component is first set up, so a plain
    "reload" of the config entry — the reflex after updating the integration —
    would otherwise leave the card unregistered until the next full restart.
    """
    if hass.data.get(_CARD_REGISTERED):
        return
    hass.data[_CARD_REGISTERED] = True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(CARD_DIR), cache_headers=False)]
    )
    add_extra_js_url(hass, CARD_JS_URL)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the Lovelace card and register it as a frontend module."""
    await _async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TV Guide EPG from a config entry (one country per entry)."""
    await _async_register_card(hass)

    session = async_get_clientsession(hass)
    country_code = entry.data[CONF_COUNTRY]
    source = COUNTRIES[country_code].make_source(
        session, entry.options.get(CONF_REFRESH_MINUTES)
    )

    coordinator = EpgCoordinator(hass, entry, source)
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
