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
from homeassistant.helpers.service import async_register_admin_service

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
    CONF_SAFETY_DELAY_MIN,
    CONF_SAFETY_MIN_ON_PERCENT,
    CONF_SAFETY_DEFAULT_ON_PERCENT,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_THERMOSTAT_TYPE,
    CONF_USE_WINDOW_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_POWER_FEATURE,
    CONF_USE_CENTRAL_BOILER_FEATURE,
    CONF_POWER_SENSOR,
    CONF_PRESENCE_SENSOR,
    CONF_UNDERLYING_LIST,
    CONF_HEATER,
    CONF_HEATER_2,
    CONF_HEATER_3,
    CONF_HEATER_4,
    CONF_CLIMATE,
    CONF_CLIMATE_2,
    CONF_CLIMATE_3,
    CONF_CLIMATE_4,
    CONF_VALVE,
    CONF_VALVE_2,
    CONF_VALVE_3,
    CONF_VALVE_4,
    CONF_THERMOSTAT_SWITCH,
    CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_VALVE,
    CONF_MAX_ON_PERCENT,
    CONF_AUTO_TPI_MODE,
    CONF_AUTO_TPI_ENABLE_UPDATE_CONFIG,
    CONF_AUTO_TPI_ENABLE_NOTIFICATION,
    CONF_AUTO_TPI_CALCULATION_METHOD,
    CONF_AUTO_TPI_EMA_ALPHA,
    CONF_AUTO_TPI_AVG_INITIAL_WEIGHT,
    CONF_AUTO_TPI_MAX_COEF_INT,
    CONF_AUTO_TPI_EMA_DECAY_RATE,
    CONF_AUTO_TPI_KEEP_EXT_LEARNING,
    CONF_AUTO_TPI_CONTINUOUS_LEARNING,
    CONF_AUTO_TPI_HEATER_HEATING_TIME,
    CONF_AUTO_TPI_HEATER_COOLING_TIME,
    CONF_AUTO_TPI_HEATING_POWER,
    CONF_AUTO_TPI_COOLING_POWER,
    AUTO_TPI_METHOD_AVG,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_STEP_TEMPERATURE,
    CONF_TEMP_UNIT,
    TEMP_UNIT_C,
    TEMP_UNIT_F,
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
                vol.Optional(CONF_MAX_ON_PERCENT): vol.Coerce(float),
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
        await api.notify_central_mode_change()

    if hass.state == CoreState.running:
        await _async_startup_internal()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_startup_internal)

    async_register_admin_service(
        hass,
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

    if hass.state == CoreState.running:
        await api.init_vtherm_links(entry.entry_id)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""

    _LOGGER.debug(
        "Calling update_listener entry: entry_id='%s', value='%s'",
        entry.entry_id,
        entry.data,
    )

    if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG:
        await reload_all_vtherm(hass)
    else:
        await hass.config_entries.async_reload(entry.entry_id)
        # Reload the central boiler list of entities
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
        if api is not None:
            await api.central_boiler_manager.reload_central_boiler_entities_list()
            await api.init_vtherm_links(entry.entry_id)


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
    _LOGGER.debug(
        "Migrating from version %s/%s", config_entry.version, config_entry.minor_version
    )

    if (
        config_entry.version != CONFIG_VERSION
        or config_entry.minor_version != CONFIG_MINOR_VERSION
    ):
        _LOGGER.debug(
            "Migration to %s/%s is needed", CONFIG_VERSION, CONFIG_MINOR_VERSION
        )
        new = {**config_entry.data}

        thermostat_type = config_entry.data.get(CONF_THERMOSTAT_TYPE)

        if thermostat_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
            new[CONF_USE_WINDOW_FEATURE] = True
            new[CONF_USE_MOTION_FEATURE] = True
            new[CONF_USE_POWER_FEATURE] = new.get(CONF_POWER_SENSOR, None) is not None
            new[CONF_USE_PRESENCE_FEATURE] = (
                new.get(CONF_PRESENCE_SENSOR, None) is not None
            )

            new[CONF_USE_CENTRAL_BOILER_FEATURE] = new.get(
                "add_central_boiler_control", False
            ) or new.get(CONF_USE_CENTRAL_BOILER_FEATURE, False)

        if config_entry.data.get(CONF_UNDERLYING_LIST, None) is None:
            underlying_list = []
            if thermostat_type == CONF_THERMOSTAT_SWITCH:
                underlying_list = [
                    config_entry.data.get(CONF_HEATER, None),
                    config_entry.data.get(CONF_HEATER_2, None),
                    config_entry.data.get(CONF_HEATER_3, None),
                    config_entry.data.get(CONF_HEATER_4, None),
                ]
            elif thermostat_type == CONF_THERMOSTAT_CLIMATE:
                underlying_list = [
                    config_entry.data.get(CONF_CLIMATE, None),
                    config_entry.data.get(CONF_CLIMATE_2, None),
                    config_entry.data.get(CONF_CLIMATE_3, None),
                    config_entry.data.get(CONF_CLIMATE_4, None),
                ]
            elif thermostat_type == CONF_THERMOSTAT_VALVE:
                underlying_list = [
                    config_entry.data.get(CONF_VALVE, None),
                    config_entry.data.get(CONF_VALVE_2, None),
                    config_entry.data.get(CONF_VALVE_3, None),
                    config_entry.data.get(CONF_VALVE_4, None),
                ]

            new[CONF_UNDERLYING_LIST] = [
                entity for entity in underlying_list if entity is not None
            ]

            for key in [
                CONF_HEATER,
                CONF_HEATER_2,
                CONF_HEATER_3,
                CONF_HEATER_4,
                CONF_CLIMATE,
                CONF_CLIMATE_2,
                CONF_CLIMATE_3,
                CONF_CLIMATE_4,
                CONF_VALVE,
                CONF_VALVE_2,
                CONF_VALVE_3,
                CONF_VALVE_4,
            ]:
                new.pop(key, None)

            # Migration 2.0 to 2.1 -> rename security parameters into safety

        if config_entry.version == CONFIG_VERSION and config_entry.minor_version == 0:
            for key in [
                "security_delay_min",
                "security_min_on_percent",
                "security_default_on_percent",
            ]:
                new_key = key.replace("security_", "safety_")
                old_value = config_entry.data.get(key, None)
                if old_value is not None:
                    new[new_key] = old_value
                new.pop(key, None)

        # Migration 2.1 to 2.2 -> add default temperature values based on system unit
        if new.get(CONF_TEMP_MIN) is None:
            unit = hass.config.units.temperature_unit
            if unit == TEMP_UNIT_F:
                new[CONF_TEMP_MIN] = 45
                new[CONF_TEMP_MAX] = 95
                new[CONF_STEP_TEMPERATURE] = 1.0
                new[CONF_TEMP_UNIT] = TEMP_UNIT_F
            else:
                new[CONF_TEMP_MIN] = 7
                new[CONF_TEMP_MAX] = 35
                new[CONF_STEP_TEMPERATURE] = 0.1
                new[CONF_TEMP_UNIT] = TEMP_UNIT_C

        # Update the config entry with migrated data
        hass.config_entries.async_update_entry(
            config_entry,
            data=new,
            version=CONFIG_VERSION,
            minor_version=CONFIG_MINOR_VERSION
        )

        _LOGGER.info("Migration to version %s.%s successful", CONFIG_VERSION, CONFIG_MINOR_VERSION)

    return True
