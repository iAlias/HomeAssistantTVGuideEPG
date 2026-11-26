"""Config flow for the TV Guide EPG integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_COUNTRY,
    CONF_FAVORITES,
    CONF_PRIME_TIME_HOUR,
    CONF_REFRESH_MINUTES,
    DEFAULT_NAME,
    DEFAULT_PRIME_TIME_HOUR,
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
PRIME_TIME_CHOICES = {
    19: "19:00",
    20: "20:00",
    20.5: "20:30",
    21: "21:00",
    21.5: "21:30",
    22: "22:00",
}


class TvGuideEpgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle one config entry per country."""

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
        return TvGuideEpgOptionsFlow()


class TvGuideEpgOptionsFlow(OptionsFlow):
    """Configure favorites, refresh interval and prime-time hour."""

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        country = COUNTRIES[self.config_entry.data[CONF_COUNTRY]]
        schema_dict = {
            vol.Optional(
                CONF_FAVORITES,
                default=self.config_entry.options.get(CONF_FAVORITES, ""),
            ): str,
        }
        if country.configurable_interval:
            current = self.config_entry.options.get(
                CONF_REFRESH_MINUTES, DEFAULT_REFRESH_MINUTES
            )
            schema_dict[vol.Optional(CONF_REFRESH_MINUTES, default=current)] = vol.In(
                REFRESH_CHOICES
            )
            prime_current = self.config_entry.options.get(
                CONF_PRIME_TIME_HOUR, DEFAULT_PRIME_TIME_HOUR
            )
            schema_dict[vol.Optional(CONF_PRIME_TIME_HOUR, default=prime_current)] = vol.In(
                PRIME_TIME_CHOICES
            )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
