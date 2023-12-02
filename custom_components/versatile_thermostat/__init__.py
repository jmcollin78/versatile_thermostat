"""The Versatile Thermostat integration."""
from __future__ import annotations

from typing import Dict

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry, ConfigType
from homeassistant.core import HomeAssistant

from .base_thermostat import BaseThermostat

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_AUTO_REGULATION_LIGHT,
    CONF_AUTO_REGULATION_MEDIUM,
    CONF_AUTO_REGULATION_STRONG,
    CONF_AUTO_REGULATION_SLOW,
    CONF_AUTO_REGULATION_EXPERT,
    CONF_SHORT_EMA_PARAMS,
)

from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)

SELF_REGULATION_PARAM_SCHEMA = {
    vol.Required("kp"): vol.Coerce(float),
    vol.Required("ki"): vol.Coerce(float),
    vol.Required("k_ext"): vol.Coerce(float),
    vol.Required("offset_max"): vol.Coerce(float),
    vol.Required("stabilization_threshold"): vol.Coerce(float),
    vol.Required("accumulated_error_threshold"): vol.Coerce(float),
}

EMA_PARAM_SCHEMA = {
    vol.Required("max_alpha"): vol.Coerce(float),
    vol.Required("halflife_sec"): vol.Coerce(float),
    vol.Required("precision"): cv.positive_int,
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                CONF_AUTO_REGULATION_EXPERT: vol.Schema(SELF_REGULATION_PARAM_SCHEMA),
                CONF_SHORT_EMA_PARAMS: vol.Schema(EMA_PARAM_SCHEMA),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(
    hass: HomeAssistant, config: ConfigType
):  # pylint: disable=unused-argument
    """Initialisation de l'intégration"""
    _LOGGER.info(
        "Initializing %s integration with config: %s",
        DOMAIN,
        config.get(DOMAIN),
    )

    hass.data.setdefault(DOMAIN, {})

    # L'argument config contient votre fichier configuration.yaml
    vtherm_config = config.get(DOMAIN)

    if vtherm_config is not None:
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
        api.set_global_config(vtherm_config)
    else:
        _LOGGER.info("No global config from configuration.yaml available")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Versatile Thermostat from a config entry."""

    _LOGGER.debug(
        "Calling async_setup_entry entry: entry_id='%s', value='%s'",
        entry.entry_id,
        entry.data,
    )

    api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    api.add_entry(entry)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if api:
            api.remove_entry(entry)

    return unload_ok


# Example migration function
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new = {**config_entry.data}
        # TO DO: modify Config Entry data if there will be something to migrate

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True
