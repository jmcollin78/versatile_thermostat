# pylint: disable=line-too-long
# pylint: disable=invalid-name
""" Implements the VersatileThermostat climate component """
import logging


import voluptuous as vol

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.helpers import entity_platform

from homeassistant.const import CONF_NAME, STATE_ON, STATE_OFF, STATE_HOME, STATE_NOT_HOME

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_PRESETS_WITH_AC,
    SERVICE_SET_PRESENCE,
    SERVICE_SET_PRESET_TEMPERATURE,
    SERVICE_SET_SECURITY,
    SERVICE_SET_WINDOW_BYPASS,
    SERVICE_SET_AUTO_REGULATION_MODE,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_SWITCH,
    CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_VALVE
)

from .thermostat_switch import ThermostatOverSwitch
from .thermostat_climate import ThermostatOverClimate
from .thermostat_valve import ThermostatOverValve

_LOGGER = logging.getLogger(__name__)

# _LOGGER.setLevel(logging.DEBUG)


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

    # Instantiate the right base class
    if vt_type == CONF_THERMOSTAT_SWITCH:
        entity = ThermostatOverSwitch(hass, unique_id, name, entry.data)
    elif vt_type == CONF_THERMOSTAT_CLIMATE:
        entity = ThermostatOverClimate(hass, unique_id, name, entry.data)
    elif vt_type == CONF_THERMOSTAT_VALVE:
        entity = ThermostatOverValve(hass, unique_id, name, entry.data)

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
        SERVICE_SET_SECURITY,
        {
            vol.Optional("delay_min"): cv.positive_int,
            vol.Optional("min_on_percent"): vol.Coerce(float),
            vol.Optional("default_on_percent"): vol.Coerce(float),
        },
        "service_set_security",
    )

    platform.async_register_entity_service(
        SERVICE_SET_WINDOW_BYPASS,
        {
            vol.Required("window_bypass"): vol.In([True, False]
            ),
        },
        "service_set_window_bypass_state",
    )

    platform.async_register_entity_service(
        SERVICE_SET_AUTO_REGULATION_MODE,
        {
            vol.Required("auto_regulation_mode"): vol.In(["None", "Light", "Medium", "Strong"]),
        },
        "service_set_auto_regulation_mode",
    )
