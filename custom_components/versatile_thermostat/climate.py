""" Implements the VersatileThermostat climate component """

import logging


import voluptuous as vol

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.helpers import entity_platform

from homeassistant.const import (
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
    STATE_HOME,
    STATE_NOT_HOME,
)

from .const import *  # pylint: disable=wildcard-import,unused-wildcard-import

from .thermostat_switch import ThermostatOverSwitch
from .thermostat_climate import ThermostatOverClimate
from .thermostat_valve import ThermostatOverValve
from .thermostat_climate_valve import ThermostatOverClimateValve
from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat thermostat with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)
    have_valve_regulation = (
        entry.data.get(CONF_AUTO_REGULATION_MODE) == CONF_AUTO_REGULATION_VALVE
    )

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        # Initialize the central power manager
        vtherm_api = VersatileThermostatAPI.get_vtherm_api(hass)
        vtherm_api.central_power_manager.post_init(entry.data)
        return

    # Instantiate the right base class
    entity = None
    if vt_type == CONF_THERMOSTAT_SWITCH:
        entity = ThermostatOverSwitch(hass, unique_id, name, entry.data)
    elif vt_type == CONF_THERMOSTAT_CLIMATE:
        if have_valve_regulation is True:
            entity = ThermostatOverClimateValve(hass, unique_id, name, entry.data)
        else:
            entity = ThermostatOverClimate(hass, unique_id, name, entry.data)
    elif vt_type == CONF_THERMOSTAT_VALVE:
        entity = ThermostatOverValve(hass, unique_id, name, entry.data)
    else:
        _LOGGER.error(
            "Cannot create Versatile Thermostat name=%s of type %s which is unknown",
            name,
            vt_type,
        )
        return

    async_add_entities([entity], True)

    # Add services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_PRESENCE,
        {
            vol.Required("presence"): vol.In(
                [STATE_ON, STATE_OFF, STATE_HOME, STATE_NOT_HOME]
            ),
        },
        "service_set_presence",
    )

    platform.async_register_entity_service(
        SERVICE_SET_PRESET_TEMPERATURE,
        {
            vol.Required("preset"): vol.In(CONF_PRESETS_WITH_AC),
            vol.Optional("temperature"): vol.Coerce(float),
            vol.Optional("temperature_away"): vol.Coerce(float),
        },
        "service_set_preset_temperature",
    )

    platform.async_register_entity_service(
        SERVICE_SET_SAFETY,
        {
            vol.Optional("delay_min"): cv.positive_int,
            vol.Optional("min_on_percent"): vol.Coerce(float),
            vol.Optional("default_on_percent"): vol.Coerce(float),
        },
        "SERVICE_SET_SAFETY",
    )

    platform.async_register_entity_service(
        SERVICE_SET_WINDOW_BYPASS,
        {
            vol.Required("window_bypass"): vol.In([True, False]),
        },
        "service_set_window_bypass_state",
    )

    platform.async_register_entity_service(
        SERVICE_SET_AUTO_REGULATION_MODE,
        {
            vol.Required("auto_regulation_mode"): vol.In(
                ["None", "Light", "Medium", "Strong", "Slow", "Expert"]
            ),
        },
        "service_set_auto_regulation_mode",
    )

    platform.async_register_entity_service(
        SERVICE_SET_AUTO_FAN_MODE,
        {
            vol.Required("auto_fan_mode"): vol.In(
                ["None", "Low", "Medium", "High", "Turbo"]
            ),
        },
        "service_set_auto_fan_mode",
    )
