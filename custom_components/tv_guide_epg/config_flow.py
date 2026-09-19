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

REFRESH_CHOICES = {
    30: "30 minuti",
    60: "1 ora",
    120: "2 ore (consigliato)",
    240: "4 ore",
}


class TvGuideEpgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TV Guide EPG: one entry per country."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        if user_input is not None:
            country_code = user_input[CONF_COUNTRY]
            await self.async_set_unique_id(f"{DOMAIN}_{country_code.lower()}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{user_input['name']} ({COUNTRIES[country_code].name})",
                data=user_input,
            )

        schema = vol.Schema({
            vol.Required(CONF_COUNTRY): vol.In(
                {code: config.name for code, config in COUNTRIES.items()}
            ),
            vol.Optional("name", default=DEFAULT_NAME): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "TvGuideEpgOptionsFlow":
        return TvGuideEpgOptionsFlow(config_entry)


class TvGuideEpgOptionsFlow(OptionsFlow):
    """Favorite programs, plus the poll interval for XMLTV-backed countries."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        # Kept under a private name on purpose: since 2024.11 Home Assistant
        # injects `config_entry` itself and exposes it as a read-only property,
        # so assigning to it raises AttributeError on current versions. A
        # private reference works on every version in our supported range.
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        country = COUNTRIES[self._entry.data[CONF_COUNTRY]]
        schema_dict = {
            vol.Optional(
                CONF_FAVORITES,
                default=self._entry.options.get(CONF_FAVORITES, ""),
            ): str
        }

        if country.configurable_interval:
            current = self._entry.options.get(
                CONF_REFRESH_MINUTES, DEFAULT_REFRESH_MINUTES
            )
            schema_dict[vol.Optional(CONF_REFRESH_MINUTES, default=current)] = vol.In(
                REFRESH_CHOICES
            )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
