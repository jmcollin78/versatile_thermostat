# pylint: disable=line-too-long, too-many-lines, invalid-name

"""Config flow for Versatile Thermostat integration."""
from __future__ import annotations

from typing import Any
import logging
import copy
from collections.abc import Mapping
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError

from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    OptionsFlow,
)

from homeassistant.data_entry_flow import FlowHandler, FlowResult

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent

from homeassistant.helpers import selector
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.input_boolean import (
    DOMAIN as INPUT_BOOLEAN_DOMAIN,
)

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_number import (
    DOMAIN as INPUT_NUMBER_DOMAIN,
)

from homeassistant.components.person import DOMAIN as PERSON_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN


from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_HEATER,
    CONF_HEATER_2,
    CONF_HEATER_3,
    CONF_HEATER_4,
    CONF_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_WINDOW_DELAY,
    CONF_WINDOW_AUTO_MAX_DURATION,
    CONF_WINDOW_AUTO_CLOSE_THRESHOLD,
    CONF_WINDOW_AUTO_OPEN_THRESHOLD,
    CONF_MOTION_SENSOR,
    CONF_MOTION_DELAY,
    CONF_MOTION_OFF_DELAY,
    CONF_MOTION_PRESET,
    CONF_NO_MOTION_PRESET,
    CONF_DEVICE_POWER,
    CONF_CYCLE_MIN,
    CONF_PRESET_POWER,
    CONF_PRESETS,
    CONF_PRESETS_WITH_AC,
    CONF_PRESETS_AWAY,
    CONF_PRESETS_AWAY_WITH_AC,
    CONF_PRESETS_SELECTIONABLE,
    CONF_PROP_FUNCTION,
    CONF_TPI_COEF_EXT,
    CONF_TPI_COEF_INT,
    CONF_PRESENCE_SENSOR,
    PROPORTIONAL_FUNCTION_TPI,
    CONF_SECURITY_DELAY_MIN,
    CONF_SECURITY_MIN_ON_PERCENT,
    CONF_SECURITY_DEFAULT_ON_PERCENT,
    DEFAULT_SECURITY_MIN_ON_PERCENT,
    DEFAULT_SECURITY_DEFAULT_ON_PERCENT,
    CONF_MINIMAL_ACTIVATION_DELAY,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_SWITCH,
    CONF_CLIMATE,
    CONF_CLIMATE_2,
    CONF_CLIMATE_3,
    CONF_CLIMATE_4,
    CONF_USE_WINDOW_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_POWER_FEATURE,
    CONF_AC_MODE,
    CONF_THERMOSTAT_TYPES,
    CONF_THERMOSTAT_VALVE,
    CONF_VALVE,
    CONF_VALVE_2,
    CONF_VALVE_3,
    CONF_VALVE_4,
    CONF_AUTO_REGULATION_MODES,
    CONF_AUTO_REGULATION_MODE,
    CONF_AUTO_REGULATION_NONE,
    CONF_AUTO_REGULATION_DTEMP,
    CONF_AUTO_REGULATION_PERIOD_MIN,
    CONF_INVERSE_SWITCH,
    UnknownEntity,
    WindowOpenDetectionMethod,
    CONF_AUTO_FAN_MODES,
    CONF_AUTO_FAN_MODE,
    CONF_AUTO_FAN_HIGH,
)

_LOGGER = logging.getLogger(__name__)


# Not used but can be useful in other context
# def schema_defaults(schema, **defaults):
#    """Create a new schema with default values filled in."""
#    copy = schema.extend({})
#    for field, field_type in copy.schema.items():
#        if isinstance(field_type, vol.In):
#            value = None
#
#            if value in field_type.container:
#                # field.default = vol.default_factory(value)
#                field.description = {"suggested_value": value}
#                continue
#
#        if field.schema in defaults:
#            # field.default = vol.default_factory(defaults[field])
#            field.description = {"suggested_value": defaults[field]}
#    return copy
#


def add_suggested_values_to_schema(
    data_schema: vol.Schema, suggested_values: Mapping[str, Any]
) -> vol.Schema:
    """Make a copy of the schema, populated with suggested values.

    For each schema marker matching items in `suggested_values`,
    the `suggested_value` will be set. The existing `suggested_value` will
    be left untouched if there is no matching item.
    """
    schema = {}
    for key, val in data_schema.schema.items():
        new_key = key
        if key in suggested_values and isinstance(key, vol.Marker):
            # Copy the marker to not modify the flow schema
            new_key = copy.copy(key)
            new_key.description = {"suggested_value": suggested_values[key]}
        schema[new_key] = val
    _LOGGER.debug("add_suggested_values_to_schema: schema=%s", schema)
    return vol.Schema(schema)


class VersatileThermostatBaseConfigFlow(FlowHandler):
    """The base Config flow class. Used to put some code in commons."""

    VERSION = 1
    _infos: dict

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos = infos
        is_empty: bool = not bool(infos)
        # Fix features selection depending to infos
        self._infos[CONF_USE_WINDOW_FEATURE] = (
            is_empty
            or self._infos.get(CONF_WINDOW_SENSOR) is not None
            or self._infos.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD) is not None
        )
        self._infos[CONF_USE_MOTION_FEATURE] = (
            is_empty or self._infos.get(CONF_MOTION_SENSOR) is not None
        )
        self._infos[CONF_USE_POWER_FEATURE] = is_empty or (
            self._infos.get(CONF_POWER_SENSOR) is not None
            and self._infos.get(CONF_MAX_POWER_SENSOR) is not None
        )
        self._infos[CONF_USE_PRESENCE_FEATURE] = (
            is_empty or self._infos.get(CONF_PRESENCE_SENSOR) is not None
        )

        self.STEP_USER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(
                    CONF_THERMOSTAT_TYPE, default=CONF_THERMOSTAT_SWITCH
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CONF_THERMOSTAT_TYPES, translation_key="thermostat_type"
                    )
                ),
                vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Required(CONF_EXTERNAL_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Required(CONF_CYCLE_MIN, default=5): cv.positive_int,
                vol.Required(CONF_TEMP_MIN, default=7): vol.Coerce(float),
                vol.Required(CONF_TEMP_MAX, default=35): vol.Coerce(float),
                vol.Optional(CONF_DEVICE_POWER, default="1"): vol.Coerce(float),
                vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
                vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
                vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
                vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
            }
        )

        self.STEP_THERMOSTAT_SWITCH = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(CONF_HEATER): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_HEATER_2): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_HEATER_3): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_HEATER_4): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Required(
                    CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI
                ): vol.In(
                    [
                        PROPORTIONAL_FUNCTION_TPI,
                    ]
                ),
                vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
                vol.Optional(CONF_INVERSE_SWITCH, default=False): cv.boolean,
            }
        )

        self.STEP_THERMOSTAT_CLIMATE = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(CONF_CLIMATE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN),
                ),
                vol.Optional(CONF_CLIMATE_2): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN),
                ),
                vol.Optional(CONF_CLIMATE_3): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN),
                ),
                vol.Optional(CONF_CLIMATE_4): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN),
                ),
                vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
                vol.Optional(
                    CONF_AUTO_REGULATION_MODE, default=CONF_AUTO_REGULATION_NONE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CONF_AUTO_REGULATION_MODES,
                        translation_key="auto_regulation_mode",
                    )
                ),
                vol.Optional(CONF_AUTO_REGULATION_DTEMP, default=0.5): vol.Coerce(
                    float
                ),
                vol.Optional(
                    CONF_AUTO_REGULATION_PERIOD_MIN, default=5
                ): cv.positive_int,
                vol.Optional(
                    CONF_AUTO_FAN_MODE, default=CONF_AUTO_FAN_HIGH
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CONF_AUTO_FAN_MODES,
                        translation_key="auto_fan_mode",
                    )
                ),
            }
        )

        self.STEP_THERMOSTAT_VALVE = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(CONF_VALVE): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_VALVE_2): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_VALVE_3): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_VALVE_4): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Required(
                    CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI
                ): vol.In(
                    [
                        PROPORTIONAL_FUNCTION_TPI,
                    ]
                ),
                vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
            }
        )

        self.STEP_TPI_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(CONF_TPI_COEF_INT, default=0.6): vol.Coerce(float),
                vol.Required(CONF_TPI_COEF_EXT, default=0.01): vol.Coerce(float),
            }
        )

        self.STEP_PRESETS_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Optional(v, default=0.0): vol.Coerce(float)
                for (k, v) in CONF_PRESETS.items()
            }
        )

        self.STEP_PRESETS_WITH_AC_DATA_SCHEMA = (  # pylint: disable=invalid-name
            vol.Schema(  # pylint: disable=invalid-name
                {
                    vol.Optional(v, default=0.0): vol.Coerce(float)
                    for (k, v) in CONF_PRESETS_WITH_AC.items()
                }
            )
        )

        self.STEP_WINDOW_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Optional(CONF_WINDOW_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_WINDOW_DELAY, default=30): cv.positive_int,
                vol.Optional(CONF_WINDOW_AUTO_OPEN_THRESHOLD): vol.Coerce(float),
                vol.Optional(CONF_WINDOW_AUTO_CLOSE_THRESHOLD): vol.Coerce(float),
                vol.Optional(CONF_WINDOW_AUTO_MAX_DURATION): cv.positive_int,
            }
        )

        self.STEP_MOTION_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Optional(CONF_MOTION_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_MOTION_DELAY, default=30): cv.positive_int,
                vol.Optional(CONF_MOTION_OFF_DELAY, default=300): cv.positive_int,
                vol.Optional(CONF_MOTION_PRESET, default="comfort"): vol.In(
                    CONF_PRESETS_SELECTIONABLE
                ),
                vol.Optional(CONF_NO_MOTION_PRESET, default="eco"): vol.In(
                    CONF_PRESETS_SELECTIONABLE
                ),
            }
        )

        self.STEP_POWER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Optional(CONF_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_MAX_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]
                    ),
                ),
                vol.Optional(CONF_PRESET_POWER, default="13"): vol.Coerce(float),
            }
        )

        self.STEP_PRESENCE_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Optional(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[
                            PERSON_DOMAIN,
                            BINARY_SENSOR_DOMAIN,
                            INPUT_BOOLEAN_DOMAIN,
                        ]
                    ),
                ),
            }
        ).extend(
            {
                vol.Optional(v, default=17): vol.Coerce(float)
                for (k, v) in CONF_PRESETS_AWAY.items()
            }
        )

        self.STEP_PRESENCE_WITH_AC_DATA_SCHEMA = (  # pylint: disable=invalid-name
            vol.Schema(
                {
                    vol.Optional(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=[
                                PERSON_DOMAIN,
                                BINARY_SENSOR_DOMAIN,
                                INPUT_BOOLEAN_DOMAIN,
                            ]
                        ),
                    ),
                }
            ).extend(
                {
                    vol.Optional(v, default=17): vol.Coerce(float)
                    for (k, v) in CONF_PRESETS_AWAY_WITH_AC.items()
                }
            )
        )

        self.STEP_ADVANCED_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
            {
                vol.Required(
                    CONF_MINIMAL_ACTIVATION_DELAY, default=10
                ): cv.positive_int,
                vol.Required(CONF_SECURITY_DELAY_MIN, default=60): cv.positive_int,
                vol.Required(
                    CONF_SECURITY_MIN_ON_PERCENT,
                    default=DEFAULT_SECURITY_MIN_ON_PERCENT,
                ): vol.Coerce(float),
                vol.Required(
                    CONF_SECURITY_DEFAULT_ON_PERCENT,
                    default=DEFAULT_SECURITY_DEFAULT_ON_PERCENT,
                ): vol.Coerce(float),
            }
        )

    async def validate_input(self, data: dict) -> None:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_*_DATA_SCHEMA with values provided by the user.
        """

        # check the heater_entity_id
        for conf in [
            CONF_HEATER,
            CONF_TEMP_SENSOR,
            CONF_EXTERNAL_TEMP_SENSOR,
            CONF_WINDOW_SENSOR,
            CONF_MOTION_SENSOR,
            CONF_POWER_SENSOR,
            CONF_MAX_POWER_SENSOR,
            CONF_PRESENCE_SENSOR,
            CONF_CLIMATE,
        ]:
            d = data.get(conf, None)  # pylint: disable=invalid-name
            if d is not None and self.hass.states.get(d) is None:
                _LOGGER.error(
                    "Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration",  # pylint: disable=line-too-long
                    d,
                )
                raise UnknownEntity(conf)

        # Check that only one window feature is used
        ws = data.get(CONF_WINDOW_SENSOR)  # pylint: disable=invalid-name
        waot = data.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD)
        wact = data.get(CONF_WINDOW_AUTO_CLOSE_THRESHOLD)
        wamd = data.get(CONF_WINDOW_AUTO_MAX_DURATION)
        if ws is not None and (
            waot is not None or wact is not None or wamd is not None
        ):
            _LOGGER.error(
                "Only one window detection method should be used. Use window_sensor or auto window open detection but not both"
            )
            raise WindowOpenDetectionMethod(CONF_WINDOW_SENSOR)

    def merge_user_input(self, data_schema: vol.Schema, user_input: dict):
        """For each schema entry not in user_input, set or remove values in infos"""
        self._infos.update(user_input)
        for key, _ in data_schema.schema.items():
            if key not in user_input and isinstance(key, vol.Marker):
                _LOGGER.debug(
                    "add_empty_values_to_user_input: %s is not in user_input", key
                )
                if key in self._infos:
                    self._infos.pop(key)
            # else:  This don't work but I don't know why. _infos seems broken after this (Not serializable exactly)
            #     self._infos[key] = user_input[key]

        _LOGGER.debug("merge_user_input: infos is now %s", self._infos)

    async def generic_step(self, step_id, data_schema, user_input, next_step_function):
        """A generic method step"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_%s user_input=%s", step_id, user_input
        )

        defaults = self._infos.copy()
        errors = {}

        if user_input is not None:
            defaults.update(user_input or {})
            try:
                await self.validate_input(user_input)
            except UnknownEntity as err:
                errors[str(err)] = "unknown_entity"
            except WindowOpenDetectionMethod as err:
                errors[str(err)] = "window_open_detection_method"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.merge_user_input(data_schema, user_input)
                _LOGGER.debug("_info is now: %s", self._infos)
                return await next_step_function()

        # ds = schema_defaults(data_schema, **defaults)  # pylint: disable=invalid-name
        ds = add_suggested_values_to_schema(
            data_schema=data_schema, suggested_values=defaults
        )  # pylint: disable=invalid-name

        return self.async_show_form(step_id=step_id, data_schema=ds, errors=errors)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        return await self.generic_step(
            "user", self.STEP_USER_DATA_SCHEMA, user_input, self.async_step_type
        )

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_type user_input=%s", user_input)

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_SWITCH:
            return await self.generic_step(
                "type", self.STEP_THERMOSTAT_SWITCH, user_input, self.async_step_tpi
            )
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_VALVE:
            return await self.generic_step(
                "type", self.STEP_THERMOSTAT_VALVE, user_input, self.async_step_tpi
            )
        else:
            return await self.generic_step(
                "type",
                self.STEP_THERMOSTAT_CLIMATE,
                user_input,
                self.async_step_presets,
            )

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_tpi user_input=%s", user_input)

        return await self.generic_step(
            "tpi", self.STEP_TPI_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presets user_input=%s", user_input)

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_WINDOW_FEATURE]:
            next_step = self.async_step_window
        elif self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        if self._infos.get(CONF_AC_MODE) is True:
            schema = self.STEP_PRESETS_WITH_AC_DATA_SCHEMA
        else:
            schema = self.STEP_PRESETS_DATA_SCHEMA

        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_window user_input=%s", user_input)

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        return await self.generic_step(
            "window", self.STEP_WINDOW_DATA_SCHEMA, user_input, next_step
        )

    async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window and motion sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_motion user_input=%s", user_input)

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        return await self.generic_step(
            "motion", self.STEP_MOTION_DATA_SCHEMA, user_input, next_step
        )

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_power user_input=%s", user_input)

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        return await self.generic_step(
            "power",
            self.STEP_POWER_DATA_SCHEMA,
            user_input,
            next_step,
        )

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presence user_input=%s", user_input)

        if self._infos.get(CONF_AC_MODE) is True:
            schema = self.STEP_PRESENCE_WITH_AC_DATA_SCHEMA
        else:
            schema = self.STEP_PRESENCE_DATA_SCHEMA

        return await self.generic_step(
            "presence",
            schema,
            user_input,
            self.async_step_advanced,
        )

    async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the advanced parameter flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_advanced user_input=%s", user_input)

        return await self.generic_step(
            "advanced",
            self.STEP_ADVANCED_DATA_SCHEMA,
            user_input,
            self.async_finalize,  # pylint: disable=no-member
        )

    async def async_finalize(self):
        """Should be implemented by Leaf classes"""
        raise HomeAssistantError(
            "async_finalize not implemented on VersatileThermostat sub-class"
        )

    def find_all_climates(self) -> list(str):
        """Find all climate known by HA"""
        component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
        ret: list(str) = list()
        for entity in component.entities:
            ret.append(entity.entity_id)
        _LOGGER.debug("Found all climate entities: %s", ret)
        return ret


class VersatileThermostatConfigFlow(
    VersatileThermostatBaseConfigFlow, HAConfigFlow, domain=DOMAIN
):
    """Handle a config flow for Versatile Thermostat."""

    def __init__(self) -> None:
        # self._info = dict()
        super().__init__(dict())
        _LOGGER.debug("CTOR ConfigFlow")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get options flow for this handler"""
        return VersatileThermostatOptionsFlowHandler(config_entry)

    async def async_finalize(self):
        """Finalization of the ConfigEntry creation"""
        _LOGGER.debug("ConfigFlow.async_finalize")
        return self.async_create_entry(title=self._infos[CONF_NAME], data=self._infos)


class VersatileThermostatOptionsFlowHandler(
    VersatileThermostatBaseConfigFlow, OptionsFlow
):
    """Handle options flow for Versatile Thermostat integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry.data.copy())
        self.config_entry = config_entry
        _LOGGER.debug(
            "CTOR VersatileThermostatOptionsFlowHandler info: %s, entry_id: %s",
            self._infos,
            config_entry.entry_id,
        )

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_init user_input =%s",
            user_input,
        )

        return await self.async_step_user()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_user user_input=%s", user_input
        )

        return await self.generic_step(
            "user", self.STEP_USER_DATA_SCHEMA, user_input, self.async_step_type
        )

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_user user_input=%s", user_input
        )

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_SWITCH:
            return await self.generic_step(
                "type", self.STEP_THERMOSTAT_SWITCH, user_input, self.async_step_tpi
            )
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_VALVE:
            return await self.generic_step(
                "type", self.STEP_THERMOSTAT_VALVE, user_input, self.async_step_tpi
            )
        else:
            return await self.generic_step(
                "type",
                self.STEP_THERMOSTAT_CLIMATE,
                user_input,
                self.async_step_presets,
            )

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the tpi flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_tpi user_input=%s", user_input
        )

        return await self.generic_step(
            "tpi", self.STEP_TPI_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_presets user_input=%s", user_input
        )

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_WINDOW_FEATURE]:
            next_step = self.async_step_window
        elif self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        if self._infos.get(CONF_AC_MODE) is True:
            schema = self.STEP_PRESETS_WITH_AC_DATA_SCHEMA
        else:
            schema = self.STEP_PRESETS_DATA_SCHEMA

        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_window user_input=%s", user_input
        )

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence
        return await self.generic_step(
            "window", self.STEP_WINDOW_DATA_SCHEMA, user_input, next_step
        )

    async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window and motion sensor flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_motion user_input=%s", user_input
        )

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        return await self.generic_step(
            "motion", self.STEP_MOTION_DATA_SCHEMA, user_input, next_step
        )

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_power user_input=%s", user_input
        )

        next_step = self.async_step_advanced
        if self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        return await self.generic_step(
            "power",
            self.STEP_POWER_DATA_SCHEMA,
            user_input,
            next_step,
        )

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_presence user_input=%s", user_input
        )

        if self._infos.get(CONF_AC_MODE) is True:
            schema = self.STEP_PRESENCE_WITH_AC_DATA_SCHEMA
        else:
            schema = self.STEP_PRESENCE_DATA_SCHEMA

        return await self.generic_step(
            "presence",
            schema,
            user_input,
            self.async_step_advanced,
        )

    async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the advanced flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_advanced user_input=%s", user_input
        )

        return await self.generic_step(
            "advanced",
            self.STEP_ADVANCED_DATA_SCHEMA,
            user_input,
            self.async_end,
        )

    async def async_end(self):
        """Finalization of the ConfigEntry creation"""
        if not self._infos[CONF_USE_WINDOW_FEATURE]:
            self._infos[CONF_WINDOW_SENSOR] = None
            self._infos[CONF_WINDOW_AUTO_CLOSE_THRESHOLD] = None
            self._infos[CONF_WINDOW_AUTO_OPEN_THRESHOLD] = None
            self._infos[CONF_WINDOW_AUTO_MAX_DURATION] = None
        if not self._infos[CONF_USE_MOTION_FEATURE]:
            self._infos[CONF_MOTION_SENSOR] = None
        if not self._infos[CONF_USE_POWER_FEATURE]:
            self._infos[CONF_POWER_SENSOR] = None
            self._infos[CONF_MAX_POWER_SENSOR] = None
        if not self._infos[CONF_USE_PRESENCE_FEATURE]:
            self._infos[CONF_PRESENCE_SENSOR] = None

        _LOGGER.info(
            "Recreating entry %s due to configuration change. New config is now: %s",
            self.config_entry.entry_id,
            self._infos,
        )
        self.hass.config_entries.async_update_entry(self.config_entry, data=self._infos)
        return self.async_create_entry(title=None, data=None)
