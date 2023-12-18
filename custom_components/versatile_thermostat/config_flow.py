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

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_api import VersatileThermostatAPI

COMES_FROM = "comes_from"

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
    _placeholders = {
        CONF_NAME: "",
    }

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos = infos

        # VTherm API should have been initialized before arriving here
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if vtherm_api is not None:
            self._central_config = vtherm_api.find_central_configuration()
        else:
            self._central_config = None

        self._init_feature_flags(infos)
        self._init_central_config_flags(infos)

    def _init_feature_flags(self, infos):
        """Fix features selection depending to infos"""
        is_empty: bool = not bool(infos)
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

    def _init_central_config_flags(self, infos):
        """Initialisation of central configuration flags"""
        is_empty: bool = not bool(infos)
        for config in (
            CONF_USE_MAIN_CENTRAL_CONFIG,
            CONF_USE_TPI_CENTRAL_CONFIG,
            CONF_USE_WINDOW_CENTRAL_CONFIG,
            CONF_USE_MOTION_CENTRAL_CONFIG,
            CONF_USE_POWER_CENTRAL_CONFIG,
            CONF_USE_PRESETS_CENTRAL_CONFIG,
            CONF_USE_PRESENCE_CENTRAL_CONFIG,
            CONF_USE_ADVANCED_CENTRAL_CONFIG,
        ):
            if not is_empty:
                self._infos[config] = self._infos.get(config) is True
            else:
                self._infos[config] = self._central_config is not None

        if COMES_FROM in self._infos:
            del self._infos[COMES_FROM]

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
        ws = self._infos.get(CONF_WINDOW_SENSOR)  # pylint: disable=invalid-name
        waot = data.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD)
        wact = data.get(CONF_WINDOW_AUTO_CLOSE_THRESHOLD)
        wamd = data.get(CONF_WINDOW_AUTO_MAX_DURATION)
        if ws is not None and (
            waot is not None or wact is not None or wamd is not None
        ):
            _LOGGER.error(
                "Only one window detection method should be used. Use window_sensor or auto window open detection but not both"
            )
            raise WindowOpenDetectionMethod(CONF_WINDOW_AUTO_OPEN_THRESHOLD)

        # Check that is USE_CENTRAL config is used, that a central config exists
        if self._central_config is None:
            for conf in [
                CONF_USE_MAIN_CENTRAL_CONFIG,
                CONF_USE_TPI_CENTRAL_CONFIG,
                CONF_USE_WINDOW_CENTRAL_CONFIG,
                CONF_USE_MOTION_CENTRAL_CONFIG,
                CONF_USE_POWER_CENTRAL_CONFIG,
                CONF_USE_PRESENCE_CENTRAL_CONFIG,
                CONF_USE_PRESETS_CENTRAL_CONFIG,
                CONF_USE_ADVANCED_CENTRAL_CONFIG,
            ]:
                if data.get(conf) is True:
                    _LOGGER.error(
                        "The use of central configuration need a central configuration Versatile Thermostat instance"
                    )
                    raise NoCentralConfig(conf)

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
            except NoCentralConfig as err:
                errors[str(err)] = "no_central_config"
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

        return self.async_show_form(
            step_id=step_id,
            data_schema=ds,
            errors=errors,
            description_placeholders=self._placeholders,
        )

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        return await self.generic_step(
            "user", STEP_USER_DATA_SCHEMA, user_input, self.async_step_main
        )

    async def async_step_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_main user_input=%s", user_input)

        schema = STEP_MAIN_DATA_SCHEMA
        next_step = self.async_step_type

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            self._infos[CONF_NAME] = CENTRAL_CONFIG_NAME
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
            next_step = self.async_step_tpi
        elif user_input and user_input.get(CONF_USE_MAIN_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_main
            schema = STEP_MAIN_DATA_SCHEMA
        # If we come from async_step_spec_main
        elif self._infos.get(COMES_FROM) == "async_step_spec_main":
            next_step = self.async_step_type
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA

        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_spec_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific main flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_main user_input=%s", user_input)

        schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
        next_step = self.async_step_type

        self._infos[COMES_FROM] = "async_step_spec_main"

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle the Type flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_type user_input=%s", user_input)

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_SWITCH:
            return await self.generic_step(
                "type", STEP_THERMOSTAT_SWITCH, user_input, self.async_step_tpi
            )
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_VALVE:
            return await self.generic_step(
                "type", STEP_THERMOSTAT_VALVE, user_input, self.async_step_tpi
            )
        else:
            return await self.generic_step(
                "type",
                STEP_THERMOSTAT_CLIMATE,
                user_input,
                self.async_step_presets,
            )

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_tpi user_input=%s", user_input)

        schema = STEP_TPI_DATA_SCHEMA
        next_step = (
            self.async_step_spec_tpi
            if user_input and user_input.get(CONF_USE_TPI_CENTRAL_CONFIG) is False
            else self.async_step_presets
        )

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_TPI_DATA_SCHEMA
            next_step = self.async_step_presets
        elif self._infos.get(COMES_FROM) == "async_step_spec_tpi":
            schema = STEP_CENTRAL_TPI_DATA_SCHEMA

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_spec_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_tpi user_input=%s", user_input)

        schema = STEP_CENTRAL_TPI_DATA_SCHEMA
        self._infos[COMES_FROM] = "async_step_spec_tpi"
        next_step = self.async_step_presets

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presets user_input=%s", user_input)

        if self._infos.get(CONF_AC_MODE) is True:
            schema_ac_or_not = STEP_CENTRAL_PRESETS_WITH_AC_DATA_SCHEMA
        else:
            schema_ac_or_not = STEP_CENTRAL_PRESETS_DATA_SCHEMA

        next_step = self.async_step_advanced
        schema = STEP_PRESETS_DATA_SCHEMA
        if self._infos[CONF_USE_WINDOW_FEATURE]:
            next_step = self.async_step_window
        elif self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_PRESETS_WITH_AC_DATA_SCHEMA
            next_step = self.async_step_window
        # If comes from async_step_spec_presets
        elif self._infos.get(COMES_FROM) == "async_step_spec_presets":
            schema = schema_ac_or_not
        elif user_input and user_input.get(CONF_USE_PRESETS_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_presets
            schema = schema_ac_or_not

        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_spec_presets(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific presets flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_presets user_input=%s", user_input
        )

        if self._infos.get(CONF_AC_MODE) is True:
            schema = STEP_CENTRAL_PRESETS_WITH_AC_DATA_SCHEMA
        else:
            schema = STEP_CENTRAL_PRESETS_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_presets"

        next_step = self.async_step_window

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_window user_input=%s", user_input)

        schema = STEP_WINDOW_DATA_SCHEMA
        next_step = self.async_step_advanced

        if self._infos[CONF_USE_MOTION_FEATURE]:
            next_step = self.async_step_motion
        elif self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
            next_step = self.async_step_motion
        # If comes from async_step_spec_window
        elif self._infos.get(COMES_FROM) == "async_step_spec_window":
            # If we have a window sensor don't display the auto window parameters
            if self._infos.get(CONF_WINDOW_SENSOR) is not None:
                schema = STEP_CENTRAL_WINDOW_WO_AUTO_DATA_SCHEMA
            else:
                schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
        elif user_input and user_input.get(CONF_USE_WINDOW_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_window

        return await self.generic_step("window", schema, user_input, next_step)

    async def async_step_spec_window(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific window flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_window user_input=%s", user_input
        )

        schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
        if self._infos.get(CONF_WINDOW_SENSOR) is not None:
            schema = STEP_CENTRAL_WINDOW_WO_AUTO_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_window"

        next_step = self.async_step_motion

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("window", schema, user_input, next_step)

    async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window and motion sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_motion user_input=%s", user_input)

        schema = STEP_MOTION_DATA_SCHEMA
        next_step = self.async_step_advanced

        if self._infos[CONF_USE_POWER_FEATURE]:
            next_step = self.async_step_power
        elif self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
            next_step = self.async_step_power
        # If comes from async_step_spec_motion
        elif self._infos.get(COMES_FROM) == "async_step_spec_motion":
            schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
        elif user_input and user_input.get(CONF_USE_MOTION_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_motion

        return await self.generic_step("motion", schema, user_input, next_step)

    async def async_step_spec_motion(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific motion flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_motion user_input=%s", user_input
        )

        schema = STEP_CENTRAL_MOTION_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_motion"

        next_step = self.async_step_power

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("motion", schema, user_input, next_step)

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_power user_input=%s", user_input)

        schema = STEP_POWER_DATA_SCHEMA
        next_step = self.async_step_advanced

        if self._infos[CONF_USE_PRESENCE_FEATURE]:
            next_step = self.async_step_presence

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_POWER_DATA_SCHEMA
            next_step = self.async_step_presence
        # If comes from async_step_spec_motion
        elif self._infos.get(COMES_FROM) == "async_step_spec_power":
            schema = STEP_CENTRAL_POWER_DATA_SCHEMA
        elif user_input and user_input.get(CONF_USE_POWER_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_power

        return await self.generic_step("power", schema, user_input, next_step)

    async def async_step_spec_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific power flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_power user_input=%s", user_input)

        schema = STEP_CENTRAL_POWER_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_power"

        next_step = self.async_step_presence

        # This will return to async_step_power (to keep the "power" step)
        return await self.generic_step("power", schema, user_input, next_step)

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presence user_input=%s", user_input)

        schema = STEP_PRESENCE_DATA_SCHEMA
        next_step = self.async_step_advanced

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
            next_step = self.async_step_advanced
        # If comes from async_step_spec_presence
        elif self._infos.get(COMES_FROM) == "async_step_spec_presence":
            schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
        elif user_input and user_input.get(CONF_USE_PRESENCE_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_presence

        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_spec_presence(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific preseence flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_presence user_input=%s", user_input
        )

        schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_presence"

        next_step = self.async_step_advanced

        # This will return to async_step_presence (to keep the "presence" step)
        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the advanced parameter flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_advanced user_input=%s", user_input)

        schema = STEP_ADVANCED_DATA_SCHEMA
        next_step = self.async_finalize

        # In Central config -> display the presets_with_ac and goto windows
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
        # If comes from async_step_spec_presence
        elif self._infos.get(COMES_FROM) == "async_step_spec_advanced":
            schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
        elif user_input and user_input.get(CONF_USE_ADVANCED_CENTRAL_CONFIG) is False:
            next_step = self.async_step_spec_advanced

        return await self.generic_step("advanced", schema, user_input, next_step)

    async def async_step_spec_advanced(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific advanced flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_advanced user_input=%s", user_input
        )

        schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_advanced"

        next_step = self.async_step_advanced

        # This will return to async_step_presence (to keep the "presence" step)
        return await self.generic_step("advanced", schema, user_input, next_step)

    async def async_finalize(self):
        """Should be implemented by Leaf classes"""
        raise HomeAssistantError(
            "async_finalize not implemented on VersatileThermostat sub-class"
        )

    # Not used but can be useful in the future
    # def find_all_climates(self) -> list(str):
    #     """Find all climate known by HA"""
    #     component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
    #     ret: list(str) = list()
    #     for entity in component.entities:
    #         ret.append(entity.entity_id)
    #     _LOGGER.debug("Found all climate entities: %s", ret)
    #     return ret


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
        # Removes temporary value
        if COMES_FROM in self._infos:
            del self._infos[COMES_FROM]
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

        self._placeholders = {
            CONF_NAME: self._infos[CONF_NAME],
        }

        return await self.async_step_main(user_input)

    # async def async_step_main(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_user user_input=%s", user_input
    #     )

    #     return await self.generic_step(
    #         "user", STEP_USER_DATA_SCHEMA, user_input, self.async_step_type
    #     )

    # async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_user user_input=%s", user_input
    #     )

    #     if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_SWITCH:
    #         return await self.generic_step(
    #             "type", STEP_THERMOSTAT_SWITCH, user_input, self.async_step_tpi
    #         )
    #     elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_VALVE:
    #         return await self.generic_step(
    #             "type", STEP_THERMOSTAT_VALVE, user_input, self.async_step_tpi
    #         )
    #     else:
    #         return await self.generic_step(
    #             "type",
    #             STEP_THERMOSTAT_CLIMATE,
    #             user_input,
    #             self.async_step_presets,
    #         )

    # async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the tpi flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_tpi user_input=%s", user_input
    #     )

    #     return await self.generic_step(
    #         "tpi", STEP_TPI_DATA_SCHEMA, user_input, self.async_step_presets
    #     )

    # async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the presets flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_presets user_input=%s", user_input
    #     )

    #     next_step = self.async_step_advanced
    #     if self._infos[CONF_USE_WINDOW_FEATURE]:
    #         next_step = self.async_step_window
    #     elif self._infos[CONF_USE_MOTION_FEATURE]:
    #         next_step = self.async_step_motion
    #     elif self._infos[CONF_USE_POWER_FEATURE]:
    #         next_step = self.async_step_power
    #     elif self._infos[CONF_USE_PRESENCE_FEATURE]:
    #         next_step = self.async_step_presence

    #     if self._infos.get(CONF_AC_MODE) is True:
    #         schema = STEP_PRESETS_WITH_AC_DATA_SCHEMA
    #     else:
    #         schema = STEP_PRESETS_DATA_SCHEMA

    #     return await self.generic_step("presets", schema, user_input, next_step)

    # async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the window  sensor flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_window user_input=%s", user_input
    #     )

    #     next_step = self.async_step_advanced
    #     if self._infos[CONF_USE_MOTION_FEATURE]:
    #         next_step = self.async_step_motion
    #     elif self._infos[CONF_USE_POWER_FEATURE]:
    #         next_step = self.async_step_power
    #     elif self._infos[CONF_USE_PRESENCE_FEATURE]:
    #         next_step = self.async_step_presence
    #     return await self.generic_step(
    #         "window", STEP_WINDOW_DATA_SCHEMA, user_input, next_step
    #     )

    # async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the window and motion sensor flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_motion user_input=%s", user_input
    #     )

    #     next_step = self.async_step_advanced
    #     if self._infos[CONF_USE_POWER_FEATURE]:
    #         next_step = self.async_step_power
    #     elif self._infos[CONF_USE_PRESENCE_FEATURE]:
    #         next_step = self.async_step_presence

    #     return await self.generic_step(
    #         "motion", STEP_MOTION_DATA_SCHEMA, user_input, next_step
    #     )

    # async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the power management flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_power user_input=%s", user_input
    #     )

    #     next_step = self.async_step_advanced
    #     if self._infos[CONF_USE_PRESENCE_FEATURE]:
    #         next_step = self.async_step_presence

    #     return await self.generic_step(
    #         "power",
    #         STEP_POWER_DATA_SCHEMA,
    #         user_input,
    #         next_step,
    #     )

    # async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the presence management flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_presence user_input=%s", user_input
    #     )

    #     if self._infos.get(CONF_AC_MODE) is True:
    #         schema = STEP_PRESENCE_WITH_AC_DATA_SCHEMA
    #     else:
    #         schema = STEP_PRESENCE_DATA_SCHEMA

    #     return await self.generic_step(
    #         "presence",
    #         schema,
    #         user_input,
    #         self.async_step_advanced,
    #     )

    # async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
    #     """Handle the advanced flow steps"""
    #     _LOGGER.debug(
    #         "Into OptionsFlowHandler.async_step_advanced user_input=%s", user_input
    #     )

    #     return await self.generic_step(
    #         "advanced",
    #         STEP_ADVANCED_DATA_SCHEMA,
    #         user_input,
    #         self.async_end,
    #     )

    async def async_finalize(self):
        """Finalization of the ConfigEntry creation"""
        if not self._infos[CONF_USE_WINDOW_FEATURE]:
            self._infos[CONF_USE_WINDOW_CENTRAL_CONFIG] = False
            self._infos[CONF_WINDOW_SENSOR] = None
            self._infos[CONF_WINDOW_AUTO_CLOSE_THRESHOLD] = None
            self._infos[CONF_WINDOW_AUTO_OPEN_THRESHOLD] = None
            self._infos[CONF_WINDOW_AUTO_MAX_DURATION] = None
        if not self._infos[CONF_USE_MOTION_FEATURE]:
            self._infos[CONF_USE_MOTION_CENTRAL_CONFIG] = False
            self._infos[CONF_MOTION_SENSOR] = None
        if not self._infos[CONF_USE_POWER_FEATURE]:
            self._infos[CONF_USE_POWER_CENTRAL_CONFIG] = False
            self._infos[CONF_POWER_SENSOR] = None
            self._infos[CONF_MAX_POWER_SENSOR] = None
        if not self._infos[CONF_USE_PRESENCE_FEATURE]:
            self._infos[CONF_USE_PRESENCE_CENTRAL_CONFIG] = False
            self._infos[CONF_PRESENCE_SENSOR] = None

        _LOGGER.info(
            "Recreating entry %s due to configuration change. New config is now: %s",
            self.config_entry.entry_id,
            self._infos,
        )

        # Removes temporary value
        if COMES_FROM in self._infos:
            del self._infos[COMES_FROM]

        self.hass.config_entries.async_update_entry(self.config_entry, data=self._infos)
        return self.async_create_entry(title=None, data=None)
