""" Implements the VersatileThermostat climate component """

import logging


import voluptuous as vol

from homeassistant.core import HomeAssistant, SupportsResponse

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import selector
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
        vtherm_api.reset_central_config()
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
        SERVICE_SET_SAFETY,
        {
            vol.Optional("delay_min"): cv.positive_int,
            vol.Optional("min_on_percent"): vol.Coerce(float),
            vol.Optional("default_on_percent"): vol.Coerce(float),
        },
        "service_set_safety",
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

    platform.async_register_entity_service(
        SERVICE_SET_HVAC_MODE_SLEEP,
        {},
        "service_set_hvac_mode_sleep",
    )

    platform.async_register_entity_service(
        SERVICE_LOCK,
        {
            vol.Optional("code"): cv.string,
        },
        "service_lock",
    )

    platform.async_register_entity_service(
        SERVICE_UNLOCK,
        {
            vol.Optional("code"): cv.string,
        },
        "service_unlock",
    )

    platform.async_register_entity_service(
        SERVICE_SET_TPI_PARAMETERS,
        {
            vol.Optional(CONF_TPI_COEF_INT): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.01, mode=selector.NumberSelectorMode.BOX)),
            vol.Optional(CONF_TPI_COEF_EXT): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1.0, step=0.001, mode=selector.NumberSelectorMode.BOX)),
            vol.Optional(CONF_MINIMAL_ACTIVATION_DELAY): cv.positive_int,
            vol.Optional(CONF_MINIMAL_DEACTIVATION_DELAY): cv.positive_int,
            vol.Optional(CONF_TPI_THRESHOLD_LOW): selector.NumberSelector(selector.NumberSelectorConfig(min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX)),
            vol.Optional(CONF_TPI_THRESHOLD_HIGH): selector.NumberSelector(selector.NumberSelectorConfig(min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        },
        "service_set_tpi_parameters",
    )

    platform.async_register_entity_service(
        SERVICE_SET_AUTO_TPI_MODE,
        {
            vol.Required("auto_tpi_mode"): vol.In([True, False]),
            vol.Optional("reinitialise", default=True): vol.In([True, False]),
        },
        "service_set_auto_tpi_mode",
    )

    platform.async_register_entity_service(
        SERVICE_AUTO_TPI_CALIBRATE_CAPACITY,
        {
            vol.Optional("start_date"): selector.DateTimeSelector(),
            vol.Optional("end_date"): selector.DateTimeSelector(),
            vol.Optional("save_to_config", default=False): vol.In([True, False]),
            vol.Optional("min_power_threshold", default=95): selector.NumberSelector(
                selector.NumberSelectorConfig(min=80, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("capacity_safety_margin", default=20): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
        },
        "service_auto_tpi_calibrate_capacity",
        supports_response=SupportsResponse.OPTIONAL,
    )

