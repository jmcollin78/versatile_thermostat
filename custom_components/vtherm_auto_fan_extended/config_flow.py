"""Config flow for vtherm_auto_fan_extended."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_FAN_MODE,
    CONF_AUTO_FAN_MODES,
    CONF_TARGET_VTHERM,
    DEFAULT_OPTIONS,
    DOMAIN,
)


def build_options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the shared options schema from the given defaults."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_AUTO_FAN_MODE,
                default=defaults.get(CONF_AUTO_FAN_MODE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(CONF_AUTO_FAN_MODES),
                    translation_key="auto_fan_mode",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def build_user_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the per-thermostat schema (entity selector + options)."""
    schema: dict[Any, Any] = {
        vol.Required(CONF_TARGET_VTHERM): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN)
        )
    }
    schema.update(build_options_schema(defaults).schema)
    return vol.Schema(schema)


class AutoFanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Manage Auto Fan plugin config entries."""

    VERSION = 1

    def is_matching(self, other_flow: "AutoFanConfigFlow") -> bool:
        """Return True if the other flow targets the same entry."""
        return other_flow.unique_id == self.unique_id

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Create the global defaults entry first, then per-thermostat ones."""
        del user_input
        if not self._async_current_entries():
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Auto Fan defaults",
                data=dict(DEFAULT_OPTIONS),
            )

        return await self.async_step_thermostat()

    async def async_step_global(self, user_input: dict[str, Any] | None = None):
        """Handle the global defaults entry explicitly."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Auto Fan defaults", data=user_input)

        return self.async_show_form(
            step_id="global",
            data_schema=build_options_schema(dict(DEFAULT_OPTIONS)),
        )

    async def async_step_thermostat(self, user_input: dict[str, Any] | None = None):
        """Handle the per-thermostat entry."""
        if user_input is not None:
            entity_id = user_input.get(CONF_TARGET_VTHERM)
            registry = er.async_get(self.hass)
            reg_entry = registry.async_get(entity_id)
            if reg_entry is None or reg_entry.unique_id is None:
                return self.async_show_form(
                    step_id="thermostat",
                    data_schema=build_user_schema(dict(DEFAULT_OPTIONS)),
                    errors={CONF_TARGET_VTHERM: "invalid_entity"},
                )

            target_unique_id = reg_entry.unique_id
            await self.async_set_unique_id(f"{DOMAIN}-{target_unique_id}")
            self._abort_if_unique_id_configured()

            data = dict(user_input)
            data[CONF_TARGET_VTHERM] = target_unique_id
            state = self.hass.states.get(entity_id)
            title = state.name if state is not None else entity_id
            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="thermostat",
            data_schema=build_user_schema(dict(DEFAULT_OPTIONS)),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Allow reconfiguring an existing entry."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            new_data = {**entry.data, **user_input}
            return self.async_update_reload_and_abort(
                entry,
                data=new_data,
                options={},
            )

        defaults = dict(DEFAULT_OPTIONS)
        defaults.update(entry.options or entry.data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=build_options_schema(defaults),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return AutoFanOptionsFlow(config_entry)


class AutoFanOptionsFlow(OptionsFlow):
    """Edit Auto Fan plugin options."""

    def __init__(self, config_entry) -> None:
        """Store the config entry being edited."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = dict(DEFAULT_OPTIONS)
        defaults.update(self._config_entry.options or self._config_entry.data)
        return self.async_show_form(
            step_id="init",
            data_schema=build_options_schema(defaults),
        )
