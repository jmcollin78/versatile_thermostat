"""The Versatile Thermostat integration."""

from __future__ import annotations

from typing import Dict

import asyncio
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import SERVICE_RELOAD, EVENT_HOMEASSISTANT_STARTED

from homeassistant.config_entries import ConfigEntry, ConfigType
from homeassistant.core import HomeAssistant, CoreState, callback

from .base_thermostat import BaseThermostat

from .const import (
    DOMAIN,
    PLATFORMS,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,
    CONF_AUTO_REGULATION_LIGHT,
    CONF_AUTO_REGULATION_MEDIUM,
    CONF_AUTO_REGULATION_STRONG,
    CONF_AUTO_REGULATION_SLOW,
    CONF_AUTO_REGULATION_EXPERT,
    CONF_SHORT_EMA_PARAMS,
    CONF_SAFETY_MODE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_THERMOSTAT_TYPE,
    CONF_USE_WINDOW_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_POWER_FEATURE,
    CONF_USE_CENTRAL_BOILER_FEATURE,
    CONF_POWER_SENSOR,
    CONF_PRESENCE_SENSOR,
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

SAFETY_MODE_PARAM_SCHEMA = {
    vol.Required("check_outdoor_sensor"): bool,
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                CONF_AUTO_REGULATION_EXPERT: vol.Schema(SELF_REGULATION_PARAM_SCHEMA),
                CONF_SHORT_EMA_PARAMS: vol.Schema(EMA_PARAM_SCHEMA),
                CONF_SAFETY_MODE: vol.Schema(SAFETY_MODE_PARAM_SCHEMA),
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

    async def _handle_reload(_):
        """The reload callback"""
        await reload_all_vtherm(hass)

    hass.data.setdefault(DOMAIN, {})

    api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    # L'argument config contient votre fichier configuration.yaml
    vtherm_config = config.get(DOMAIN)
    if vtherm_config is not None:
        api.set_global_config(vtherm_config)
    else:
        _LOGGER.info("No global config from configuration.yaml available")

    # Listen HA starts to initialize all links between
    @callback
    async def _async_startup_internal(*_):
        _LOGGER.info(
            "VersatileThermostat - HA is started, initialize all links between VTherm entities"
        )
        await api.init_vtherm_links()

    if hass.state == CoreState.running:
        await _async_startup_internal()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_startup_internal)

    hass.helpers.service.async_register_admin_service(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    return True


async def reload_all_vtherm(hass):
    """Handle reload service call."""
    _LOGGER.info("Service %s.reload called: reloading integration", DOMAIN)

    current_entries = hass.config_entries.async_entries(DOMAIN)

    reload_tasks = [
        hass.config_entries.async_reload(entry.entry_id) for entry in current_entries
    ]

    await asyncio.gather(*reload_tasks)
    api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    if api:
        await api.reload_central_boiler_entities_list()
        await api.init_vtherm_links()


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

    await api.reload_central_boiler_entities_list()
    await api.init_vtherm_links()

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG:
        await reload_all_vtherm(hass)
    else:
        await hass.config_entries.async_reload(entry.entry_id)
        # Reload the central boiler list of entities
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
        if api is not None:
            await api.reload_central_boiler_entities_list()
            await api.init_vtherm_links()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if api:
            api.remove_entry(entry)
            await api.reload_central_boiler_entities_list()

    return unload_ok


# Example migration function
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if (
        config_entry.version != CONFIG_VERSION
        or config_entry.minor_version != CONFIG_MINOR_VERSION
    ):
        new = {**config_entry.data}

        if (
            config_entry.data.get(CONF_THERMOSTAT_TYPE)
            == CONF_THERMOSTAT_CENTRAL_CONFIG
        ):
            new[CONF_USE_WINDOW_FEATURE] = True
            new[CONF_USE_MOTION_FEATURE] = True
            new[CONF_USE_POWER_FEATURE] = new.get(CONF_POWER_SENSOR, None) is not None
            new[CONF_USE_PRESENCE_FEATURE] = (
                new.get(CONF_PRESENCE_SENSOR, None) is not None
            )

            new[CONF_USE_CENTRAL_BOILER_FEATURE] = new.get(
                "add_central_boiler_control", False
            )
        hass.config_entries.async_update_entry(
            config_entry,
            data=new,
            version=CONFIG_VERSION,
            minor_version=CONFIG_MINOR_VERSION,
        )

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True
