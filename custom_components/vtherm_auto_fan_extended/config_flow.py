"""Config flow for vtherm_auto_fan_extended."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_EXCLUSION_PATTERNS,
    CONF_TARGET_VTHERM,
    DEFAULT_EXCLUSION_PATTERNS,
    DOMAIN,
)


def _patterns_selector(options: list[str]) -> selector.SelectSelector:
    """Build the multi-value selector for the exclusion patterns."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(options),
            multiple=True,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _user_schema() -> vol.Schema:
    """Build the initial config schema (target VTherm + exclusion patterns)."""
    return vol.Schema(
        {
            vol.Required(CONF_TARGET_VTHERM): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN)
            ),
            vol.Optional(
                CONF_EXCLUSION_PATTERNS,
                default=list(DEFAULT_EXCLUSION_PATTERNS),
            ): _patterns_selector(DEFAULT_EXCLUSION_PATTERNS),
        }
    )


def _reconfigure_schema(current: list[str]) -> vol.Schema:
    """Build the reconfigure schema (exclusion patterns only)."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_EXCLUSION_PATTERNS,
                default=list(current),
            ): _patterns_selector(current),
        }
    )


def _invalid_patterns(patterns: list[str]) -> bool:
    """Return True when at least one pattern is not a compilable regex."""
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error:
            return True
    return False


class AutoFanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Manage Auto Fan plugin config entries."""

    VERSION = 1

    def is_matching(self, other_flow: "AutoFanConfigFlow") -> bool:
        """Return True if the other flow targets the same entry."""
        return other_flow.unique_id == self.unique_id

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Pick the target over_climate VTherm to attach the auto fan to."""
        if user_input is not None:
            patterns = user_input.get(
                CONF_EXCLUSION_PATTERNS, list(DEFAULT_EXCLUSION_PATTERNS)
            )
            if _invalid_patterns(patterns):
                return self.async_show_form(
                    step_id="user",
                    data_schema=_user_schema(),
                    errors={CONF_EXCLUSION_PATTERNS: "invalid_regex"},
                )

            entity_id = user_input[CONF_TARGET_VTHERM]
            registry = er.async_get(self.hass)
            reg_entry = registry.async_get(entity_id)
            if reg_entry is None or reg_entry.unique_id is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_user_schema(),
                    errors={CONF_TARGET_VTHERM: "invalid_entity"},
                )

            target_unique_id = reg_entry.unique_id
            await self.async_set_unique_id(f"{DOMAIN}-{target_unique_id}")
            self._abort_if_unique_id_configured()

            state = self.hass.states.get(entity_id)
            title = state.name if state is not None else entity_id
            return self.async_create_entry(
                title=title,
                data={
                    CONF_TARGET_VTHERM: target_unique_id,
                    CONF_EXCLUSION_PATTERNS: patterns,
                },
            )

        return self.async_show_form(step_id="user", data_schema=_user_schema())

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Edit the exclusion patterns of an existing entry (target fixed)."""
        entry = self._get_reconfigure_entry()
        current = entry.data.get(
            CONF_EXCLUSION_PATTERNS, list(DEFAULT_EXCLUSION_PATTERNS)
        )

        if user_input is not None:
            patterns = user_input.get(CONF_EXCLUSION_PATTERNS, list(current))
            if _invalid_patterns(patterns):
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=_reconfigure_schema(patterns),
                    errors={CONF_EXCLUSION_PATTERNS: "invalid_regex"},
                )
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_EXCLUSION_PATTERNS: patterns},
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_reconfigure_schema(current),
        )

