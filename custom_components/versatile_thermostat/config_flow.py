# pylint: disable=line-too-long, too-many-lines, invalid-name

"""Config flow for Versatile Thermostat integration."""
from __future__ import annotations

from typing import Any
import re
import logging
import copy
from collections.abc import Mapping  # pylint: disable=import-error
import voluptuous as vol

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
from .commons import check_and_extract_service_configuration

COMES_FROM = "comes_from"

_LOGGER = logging.getLogger(__name__)


def add_suggested_values_to_schema(data_schema: vol.Schema, suggested_values: Mapping[str, Any]) -> vol.Schema:
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

    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    _placeholders = {
        CONF_NAME: "",
    }

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos: dict = infos

        # VTherm API should have been initialized before arriving here
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if vtherm_api is not None:
            self._central_config = vtherm_api.find_central_configuration()
        else:
            self._central_config = None

        self._init_central_config_flags(infos)
        self._init_feature_flags(infos)

    def _init_feature_flags(self, _):
        """Fix features selection depending to infos"""
        is_central_config = self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG

        self._infos[CONF_USE_WINDOW_FEATURE] = (
            self._infos.get(CONF_USE_WINDOW_CENTRAL_CONFIG, False)
            or self._infos.get(CONF_WINDOW_SENSOR) is not None
            or self._infos.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD) is not None
        )
        self._infos[CONF_USE_MOTION_FEATURE] = self._infos.get(CONF_USE_MOTION_FEATURE, False) and (self._infos.get(CONF_MOTION_SENSOR) is not None or is_central_config)

        self._infos[CONF_USE_POWER_FEATURE] = (
            self._infos.get(CONF_USE_POWER_CENTRAL_CONFIG, False)
            or self._infos.get(CONF_USE_POWER_FEATURE, False)
            or (is_central_config and self._infos.get(CONF_POWER_SENSOR) is not None and self._infos.get(CONF_MAX_POWER_SENSOR) is not None)
        )
        self._infos[CONF_USE_PRESENCE_FEATURE] = self._infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False) or self._infos.get(CONF_PRESENCE_SENSOR) is not None

        self._infos[CONF_USE_HUMIDITY_FEATURE] = self._infos.get(CONF_USE_HUMIDITY_CENTRAL_CONFIG, False) or self._infos.get(CONF_HUMIDITY_SENSOR) is not None

        self._infos[CONF_USE_CENTRAL_BOILER_FEATURE] = (
            self._infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV) is not None and self._infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV) is not None
        )

        self._infos[CONF_USE_AUTO_START_STOP_FEATURE] = (
            self._infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False) is True and self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE
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
            CONF_USE_HUMIDITY_CENTRAL_CONFIG,
            CONF_USE_ADVANCED_CENTRAL_CONFIG,
            CONF_USE_LOCK_CENTRAL_CONFIG,
            CONF_USE_CENTRAL_MODE,
        ):
            if not is_empty:
                current_config = self._infos.get(config, None)

                self._infos[config] = self._central_config is not None and (current_config is True or current_config is None)
                # self._infos[config] = current_config is True or (
                #     current_config is None and self._central_config is not None
                # )
            else:
                self._infos[config] = self._central_config is not None

        if COMES_FROM in self._infos:
            del self._infos[COMES_FROM]

    def is_valve_regulation_selected(self, infos) -> bool:
        """True of the valve regulation mode is selected"""
        return infos.get(CONF_AUTO_REGULATION_MODE, None) == CONF_AUTO_REGULATION_VALVE

    def check_valve_regulation_nb_entities(self, data: dict, step_id=None) -> bool:
        """Check the number of entities for Valve regulation"""
        if step_id not in ["type", "valve_regulation", "check_complete"]:
            return True

        underlyings_to_check = data if step_id == "type" else self._infos
        # underlyings_to_check = self._infos  # data if step_id == "type" else self._infos
        regulation_infos_to_check = data if step_id == "valve_regulation" else self._infos

        ret = True
        if self.is_valve_regulation_selected(underlyings_to_check) and step_id != "type":
            nb_unders = len(underlyings_to_check.get(CONF_UNDERLYING_LIST))
            nb_offset = len(regulation_infos_to_check.get(CONF_OFFSET_CALIBRATION_LIST, []))
            nb_opening = len(regulation_infos_to_check.get(CONF_OPENING_DEGREE_LIST, []))
            nb_closing = len(regulation_infos_to_check.get(CONF_CLOSING_DEGREE_LIST, []))
            if nb_unders != nb_opening or (nb_unders != nb_offset and nb_offset > 0) or (nb_unders != nb_closing and nb_closing > 0):
                ret = False
        return ret

    async def validate_input(self, data: dict, step_id) -> None:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_*_DATA_SCHEMA with values provided by the user.
        """

        # check the entity_ids
        for conf in [
            CONF_UNDERLYING_LIST,
            CONF_TEMP_SENSOR,
            CONF_EXTERNAL_TEMP_SENSOR,
            CONF_WINDOW_SENSOR,
            CONF_MOTION_SENSOR,
            CONF_POWER_SENSOR,
            CONF_MAX_POWER_SENSOR,
            CONF_PRESENCE_SENSOR,
            CONF_HUMIDITY_SENSOR,
            CONF_OFFSET_CALIBRATION_LIST,
            CONF_OPENING_DEGREE_LIST,
            CONF_CLOSING_DEGREE_LIST,
        ]:
            d = data.get(conf, None)  # pylint: disable=invalid-name
            if not isinstance(d, list):
                d = [d]
            for e in d:
                if e is not None and self.hass.states.get(e) is None:
                    _LOGGER.error(
                        "Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration",  # pylint: disable=line-too-long
                        e,
                    )
                    raise UnknownEntity(conf)

        # Check that only one window feature is used
        ws = self._infos.get(CONF_WINDOW_SENSOR)  # pylint: disable=invalid-name
        waot = data.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD)
        wact = data.get(CONF_WINDOW_AUTO_CLOSE_THRESHOLD)
        wamd = data.get(CONF_WINDOW_AUTO_MAX_DURATION)
        if ws is not None and (waot is not None or wact is not None or wamd is not None):
            _LOGGER.error("Only one window detection method should be used. Use window_sensor or auto window open detection but not both")
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
                CONF_USE_HUMIDITY_CENTRAL_CONFIG,
                CONF_USE_PRESETS_CENTRAL_CONFIG,
                CONF_USE_ADVANCED_CENTRAL_CONFIG,
                CONF_USE_CENTRAL_MODE,
                # CONF_USE_CENTRAL_BOILER_FEATURE, this is for Central Config
                CONF_USED_BY_CENTRAL_BOILER,
            ]:
                if data.get(conf) is True:
                    _LOGGER.error("The use of central configuration need a central configuration Versatile Thermostat instance")
                    raise NoCentralConfig(conf)

        # Check the service for central boiler format
        if self._infos.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            for conf in [
                CONF_CENTRAL_BOILER_ACTIVATION_SRV,
                CONF_CENTRAL_BOILER_DEACTIVATION_SRV,
            ]:
                try:
                    check_and_extract_service_configuration(data.get(conf))
                except ServiceConfigurationError as err:
                    raise ServiceConfigurationError(conf) from err

        # Check that the number of offet_calibration and opening_degree and closing_degree are equals
        # to the number of underlying entities
        if not self.check_valve_regulation_nb_entities(data, step_id):
            raise ValveRegulationNbEntitiesIncorrect()

        # Check that the min_opening_degrees is correctly set
        raw_list = data.get(CONF_MIN_OPENING_DEGREES, None)
        if raw_list:
            try:
                # Validation : Convertir la liste saisie
                int_list = [int(x.strip()) for x in raw_list.split(",")]

                # Optionnel : Vérifiez des conditions supplémentaires sur la liste
                if any(x < 0 for x in int_list):
                    raise ValueError
            except ValueError as exc:
                raise ValveRegulationMinOpeningDegreesIncorrect(CONF_MIN_OPENING_DEGREES) from exc

        # Check the VSWITCH configuration. There should be the same number of vswitch_on (resp. vswitch_off) than the number of underlying entity
        if self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_SWITCH and step_id == "type":
            if not self.check_vswitch_configuration(data):
                raise VirtualSwitchConfigurationIncorrect(CONF_VSWITCH_ON_CMD_LIST)

        # Check the lock code format
        if data.get(CONF_LOCK_CODE) is not None:
            if not re.match(r"^\d{4}$", str(data.get(CONF_LOCK_CODE))):
                raise LockCodeIncorrect()

    def check_vswitch_configuration(self, data) -> bool:
        """Check the Virtual switch configuration and return True if the configuration is correct"""
        nb_under = len(data.get(CONF_UNDERLYING_LIST, []))

        # check format of each command_on
        for command in data.get(CONF_VSWITCH_ON_CMD_LIST, []) + data.get(CONF_VSWITCH_OFF_CMD_LIST, []):
            pattern = r"^(?P<command>[a-zA-Z0-9_]+)(?:/(?P<argument>[a-zA-Z0-9_]+)(?::(?P<value>[a-zA-Z0-9_]+))?)?$"
            if not re.match(pattern, command):
                return False

        nb_command_on = len(data.get(CONF_VSWITCH_ON_CMD_LIST, []))
        nb_command_off = len(data.get(CONF_VSWITCH_OFF_CMD_LIST, []))
        if (nb_command_on == nb_under or nb_command_on == 0) and (nb_command_off == nb_under or nb_command_off == 0):
            # There is enough command_on and off
            # Check if one under is not a switch (which have default command).
            if any(
                not thermostat_type.startswith(SWITCH_DOMAIN) and not thermostat_type.startswith(INPUT_BOOLEAN_DOMAIN) for thermostat_type in data.get(CONF_UNDERLYING_LIST, [])
            ):
                if nb_command_on != nb_under or nb_command_off != nb_under:
                    return False
            return True
        return False

    def check_config_complete(self, infos) -> bool:
        """True if the config is now complete (ie all mandatory attributes are set)"""
        is_central_config = infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG
        if is_central_config:
            if infos.get(CONF_NAME) is None or infos.get(CONF_EXTERNAL_TEMP_SENSOR) is None:
                return False

            if infos.get(CONF_USE_POWER_FEATURE, False) is True and (infos.get(CONF_POWER_SENSOR, None) is None or infos.get(CONF_MAX_POWER_SENSOR, None) is None):
                return False

            if infos.get(CONF_USE_PRESENCE_FEATURE, False) is True and infos.get(CONF_PRESENCE_SENSOR, None) is None:
                return False

            if self._infos[CONF_USE_CENTRAL_BOILER_FEATURE] and (
                not self._infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV, False)
                or len(self._infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV)) <= 0
                or not self._infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV, False)
                or len(self._infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV)) <= 0
            ):
                return False
        else:
            if infos.get(CONF_NAME) is None or infos.get(CONF_TEMP_SENSOR) is None or infos.get(CONF_CYCLE_MIN) is None:
                return False

            if infos.get(CONF_USE_MAIN_CENTRAL_CONFIG, False) is False and infos.get(CONF_EXTERNAL_TEMP_SENSOR) is None:
                return False

            # checks that at least one underlying is set but not it central configuration
            if len(infos.get(CONF_UNDERLYING_LIST, [])) < 1:
                return False

            if infos.get(CONF_USE_MOTION_FEATURE, False) is True and infos.get(CONF_MOTION_SENSOR, None) is None:
                return False

            if infos.get(CONF_USE_POWER_FEATURE, False) is True and infos.get(CONF_USE_POWER_CENTRAL_CONFIG, False) is False and infos.get(CONF_PRESET_POWER, None) is None:
                return False

            if (
                infos.get(CONF_USE_PRESENCE_FEATURE, False) is True
                and infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False) is False
                and infos.get(CONF_PRESENCE_SENSOR, None) is None
            ):
                return False

            if (
                infos.get(CONF_USE_HUMIDITY_FEATURE, False) is True
                and infos.get(CONF_USE_HUMIDITY_CENTRAL_CONFIG, False) is False
                and infos.get(CONF_HUMIDITY_SENSOR, None) is None
            ):
                return False

            if infos.get(CONF_USE_ADVANCED_CENTRAL_CONFIG, False) is False and (
                infos.get(CONF_SAFETY_DELAY_MIN, -1) == -1 or infos.get(CONF_SAFETY_MIN_ON_PERCENT, -1) == -1 or infos.get(CONF_SAFETY_DEFAULT_ON_PERCENT, -1) == -1
            ):
                return False

            if (
                infos.get(CONF_PROP_FUNCTION, None) == PROPORTIONAL_FUNCTION_TPI
                and infos.get(CONF_USE_TPI_CENTRAL_CONFIG, False) is False
                and (infos.get(CONF_TPI_COEF_INT, None) is None or infos.get(CONF_TPI_COEF_EXT) is None)
            ):
                return False

            if infos.get(CONF_USE_PRESETS_CENTRAL_CONFIG, False) is True and self._central_config is None:
                return False

            if not self.check_valve_regulation_nb_entities(infos, "check_complete"):
                return False

        return True

    def merge_user_input(self, data_schema: vol.Schema, user_input: dict):
        """For each schema entry not in user_input, set or remove values in infos"""
        self._infos.update(user_input)
        for key, _ in data_schema.schema.items():
            if key not in user_input and isinstance(key, vol.Marker):
                _LOGGER.debug("add_empty_values_to_user_input: %s is not in user_input", key)
                if key in self._infos:
                    self._infos.pop(key)
            # else:  This don't work but I don't know why. _infos seems broken after this (Not serializable exactly)
            #     self._infos[key] = user_input[key]

        _LOGGER.debug("merge_user_input: infos is now %s", self._infos)

    async def generic_step(self, step_id, data_schema, user_input, next_step_function):
        """A generic method step"""
        _LOGGER.debug("Into ConfigFlow.async_step_%s user_input=%s", step_id, user_input)

        defaults = self._infos.copy()
        errors = {}

        if user_input is not None:
            defaults.update(user_input or {})
            try:
                await self.validate_input(user_input, step_id)
            except UnknownEntity as err:
                errors[str(err)] = "unknown_entity"
            except WindowOpenDetectionMethod as err:
                errors[str(err)] = "window_open_detection_method"
            except NoCentralConfig as err:
                errors[str(err)] = "no_central_config"
            except ServiceConfigurationError as err:
                errors[str(err)] = "service_configuration_format"
            except ConfigurationNotCompleteError as err:
                errors["base"] = "configuration_not_complete"
            except ValveRegulationNbEntitiesIncorrect as err:
                errors["base"] = "valve_regulation_nb_entities_incorrect"
            except ValveRegulationMinOpeningDegreesIncorrect as err:
                errors[str(err)] = "min_opening_degrees_format"
            except VirtualSwitchConfigurationIncorrect as err:
                errors["base"] = "vswitch_configuration_incorrect"
            except LockCodeIncorrect:
                errors["base"] = "lock_code_incorrect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.merge_user_input(data_schema, user_input)
                # Add default values for central config flags
                self._init_central_config_flags(self._infos)
                _LOGGER.debug("_info is now: %s", self._infos)
                return await next_step_function()

        # ds = schema_defaults(data_schema, **defaults)  # pylint: disable=invalid-name
        ds = add_suggested_values_to_schema(data_schema=data_schema, suggested_values=defaults)  # pylint: disable=invalid-name

        return self.async_show_form(
            step_id=step_id,
            data_schema=ds,
            errors=errors,
            description_placeholders=self._placeholders,
        )

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        return await self.generic_step("user", STEP_USER_DATA_SCHEMA, user_input, self.async_step_menu)

    async def async_step_configuration_not_complete(self, user_input: dict | None = None) -> FlowResult:
        """A fake step to handle the incomplete configuration flow"""
        return await self.async_step_menu(user_input)

    async def async_step_menu(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_menu user_input=%s", user_input)

        is_central_config = self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG

        menu_options = ["main", "features"]
        if not is_central_config:
            menu_options.append("type")

        if self._infos.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI or is_central_config or self.is_valve_regulation_selected(self._infos):
            menu_options.append("tpi")

        if self._infos.get(CONF_THERMOSTAT_TYPE) in [
            CONF_THERMOSTAT_SWITCH,
            CONF_THERMOSTAT_VALVE,
            CONF_THERMOSTAT_CLIMATE,
        ]:
            menu_options.append("presets")

        if is_central_config and self._infos.get(CONF_USE_CENTRAL_BOILER_FEATURE, False) is True:
            menu_options.append("central_boiler")

        if self._infos.get(CONF_USE_WINDOW_FEATURE, False) is True:
            menu_options.append("window")

        if self._infos.get(CONF_USE_MOTION_FEATURE, False) is True:
            menu_options.append("motion")

        if self._infos.get(CONF_USE_POWER_FEATURE, False) is True:
            menu_options.append("power")

        if self._infos.get(CONF_USE_PRESENCE_FEATURE, False) is True:
            menu_options.append("presence")
        if self._infos.get(CONF_USE_HUMIDITY_FEATURE, False) is True:
            menu_options.append("humidity")

        if (
            self._infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False) is True
            and self._infos[CONF_THERMOSTAT_TYPE]
            in [
                CONF_THERMOSTAT_CLIMATE,
            ]
            and not self.is_valve_regulation_selected(self._infos)
        ):
            menu_options.append("auto_start_stop")

        if self.is_valve_regulation_selected(self._infos):
            menu_options.append("valve_regulation")

        menu_options.append("advanced")
        menu_options.append("lock")

        if self.check_config_complete(self._infos):
            menu_options.append("finalize")
        else:
            _LOGGER.info("The configuration is not terminated")
            menu_options.append("configuration_not_complete")

        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options,
            description_placeholders=self._placeholders,
        )

    async def async_step_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_main user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            self._infos[CONF_NAME] = CENTRAL_CONFIG_NAME
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
        else:
            schema = STEP_MAIN_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_MAIN_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_main":
                    schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_main

        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_spec_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific main flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_main user_input=%s", user_input)

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
        else:
            schema = STEP_CENTRAL_SPEC_MAIN_DATA_SCHEMA
        next_step = self.async_step_menu

        self._infos[COMES_FROM] = "async_step_spec_main"

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_central_boiler(self, user_input: dict | None = None) -> FlowResult:
        """Handle the central boiler flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_central_boiler user_input=%s", user_input)

        schema = STEP_CENTRAL_BOILER_SCHEMA
        next_step = self.async_step_menu

        return await self.generic_step("central_boiler", schema, user_input, next_step)

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle the Type flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_type user_input=%s", user_input)

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CLIMATE and user_input is not None and not self.is_valve_regulation_selected(user_input):
            # Remove TPI info
            for key in [
                CONF_PROP_FUNCTION,
                CONF_TPI_COEF_INT,
                CONF_TPI_COEF_EXT,
                CONF_OFFSET_CALIBRATION_LIST,
                CONF_OPENING_DEGREE_LIST,
                CONF_CLOSING_DEGREE_LIST,
            ]:
                if self._infos.get(key):
                    del self._infos[key]

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_SWITCH:
            return await self.generic_step("type", STEP_THERMOSTAT_SWITCH, user_input, self.async_step_menu)
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_VALVE:
            return await self.generic_step("type", STEP_THERMOSTAT_VALVE, user_input, self.async_step_menu)
        else:
            return await self.generic_step(
                "type",
                STEP_THERMOSTAT_CLIMATE,
                user_input,
                self.async_step_menu,
            )

    async def async_step_features(self, user_input: dict | None = None) -> FlowResult:
        """Handle the Type flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_features user_input=%s", user_input)

        schema = STEP_FEATURES_DATA_SCHEMA
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_FEATURES_DATA_SCHEMA
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CLIMATE and not self.is_valve_regulation_selected(self._infos):
            schema = STEP_CLIMATE_FEATURES_DATA_SCHEMA
        elif self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CLIMATE and self.is_valve_regulation_selected(self._infos):
            schema = STEP_CLIMATE_VALVE_FEATURES_DATA_SCHEMA

        return await self.generic_step(
            "features",
            schema,
            user_input,
            self.async_step_menu,
        )

    async def async_step_auto_start_stop(self, user_input: dict | None = None) -> FlowResult:
        """Handle the Auto start stop step"""
        _LOGGER.debug("Into ConfigFlow.async_step_auto_start_stop user_input=%s", user_input)

        schema = STEP_AUTO_START_STOP
        self._infos[COMES_FROM] = None
        next_step = self.async_step_menu

        return await self.generic_step("auto_start_stop", schema, user_input, next_step)

    async def async_step_valve_regulation(self, user_input: dict | None = None) -> FlowResult:
        """Handle the valve regulation configuration step"""
        _LOGGER.debug("Into ConfigFlow.async_step_valve_regulation user_input=%s", user_input)

        schema = STEP_VALVE_REGULATION
        self._infos[COMES_FROM] = None
        next_step = self.async_step_menu

        return await self.generic_step("valve_regulation", schema, user_input, next_step)

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_tpi user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_TPI_DATA_SCHEMA
        else:
            schema = STEP_TPI_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_TPI_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_tpi":
                    schema = STEP_CENTRAL_TPI_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_tpi

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_spec_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_tpi user_input=%s", user_input)

        schema = STEP_CENTRAL_TPI_DATA_SCHEMA
        self._infos[COMES_FROM] = "async_step_spec_tpi"
        next_step = self.async_step_menu

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presets user_input=%s", user_input)

        next_step = self.async_step_menu  # advanced
        schema = STEP_PRESETS_DATA_SCHEMA

        # In Central config -> display the next step immedialty
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            # Call directly the next step, we have nothing to display here
            return await self.async_step_window()  #  = self.async_step_window

        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_window user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
        else:
            schema = STEP_WINDOW_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_WINDOW_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_window":
                    if self._infos.get(CONF_WINDOW_SENSOR) is not None:
                        schema = STEP_CENTRAL_WINDOW_WO_AUTO_DATA_SCHEMA
                    else:
                        schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_window

        return await self.generic_step("window", schema, user_input, next_step)

    async def async_step_spec_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific window flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_window user_input=%s", user_input)

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

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
        else:
            schema = STEP_MOTION_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_MOTION_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_motion":
                    schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_motion

        return await self.generic_step("motion", schema, user_input, next_step)

    async def async_step_spec_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific motion flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_motion user_input=%s", user_input)

        schema = STEP_CENTRAL_MOTION_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_motion"

        next_step = self.async_step_menu

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("motion", schema, user_input, next_step)

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_power user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_POWER_DATA_SCHEMA
        else:
            schema = STEP_POWER_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_POWER_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_power":
                    schema = STEP_CENTRAL_POWER_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_power

        return await self.generic_step("power", schema, user_input, next_step)

    async def async_step_spec_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific power flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_power user_input=%s", user_input)

        schema = STEP_NON_CENTRAL_POWER_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_power"

        next_step = self.async_step_menu

        # This will return to async_step_power (to keep the "power" step)
        return await self.generic_step("power", schema, user_input, next_step)

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presence user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
        else:
            schema = STEP_PRESENCE_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_presence":
                    schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_presence

        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_spec_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific power flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_presence user_input=%s", user_input)

        schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_presence"

        next_step = self.async_step_menu

        # This will return to async_step_power (to keep the "power" step)
        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_humidity(self, user_input: dict | None = None) -> FlowResult:
        """Handle the humidity management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_humidity user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_HUMIDITY_DATA_SCHEMA
        else:
            schema = STEP_HUMIDITY_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_HUMIDITY_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_humidity":
                    schema = STEP_CENTRAL_HUMIDITY_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_humidity

        return await self.generic_step("humidity", schema, user_input, next_step)

    async def async_step_spec_humidity(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific humidity flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_humidity user_input=%s", user_input)

        schema = STEP_CENTRAL_HUMIDITY_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_humidity"

        next_step = self.async_step_menu

        # This will return to async_step_humidity (to keep the "humidity" step)
        return await self.generic_step("humidity", schema, user_input, next_step)

    async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the advanced parameter flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_advanced user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
        else:
            schema = STEP_ADVANCED_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_ADVANCED_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_advanced":
                    schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_advanced

        return await self.generic_step("advanced", schema, user_input, next_step)

    async def async_step_spec_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific advanced flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_advanced user_input=%s", user_input)

        schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_advanced"

        next_step = self.async_step_advanced

        # This will return to async_step_presence (to keep the "presence" step)
        return await self.generic_step("advanced", schema, user_input, next_step)

    async def async_step_lock(self, user_input: dict | None = None) -> FlowResult:
        """Handle the lock flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_lock user_input=%s", user_input)

        next_step = self.async_step_menu
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_LOCK_DATA_SCHEMA
        else:
            schema = STEP_LOCK_DATA_SCHEMA

            if user_input and user_input.get(CONF_USE_LOCK_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_lock":
                    schema = STEP_CENTRAL_LOCK_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_lock

        return await self.generic_step("lock", schema, user_input, next_step)

    async def async_step_spec_lock(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific lock flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_lock user_input=%s", user_input)

        schema = STEP_CENTRAL_LOCK_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_lock"

        next_step = self.async_step_menu

        return await self.generic_step("lock", schema, user_input, next_step)

    async def async_step_finalize(self, _):
        """Finalize the creation. Should be overriden by underlyings"""
        if not self._infos[CONF_USE_WINDOW_FEATURE]:
            self._infos[CONF_USE_WINDOW_CENTRAL_CONFIG] = False
            if CONF_WINDOW_SENSOR in self._infos:
                del self._infos[CONF_WINDOW_SENSOR]
            if CONF_WINDOW_AUTO_CLOSE_THRESHOLD in self._infos:
                del self._infos[CONF_WINDOW_AUTO_CLOSE_THRESHOLD]
            if CONF_WINDOW_AUTO_OPEN_THRESHOLD in self._infos:
                del self._infos[CONF_WINDOW_AUTO_OPEN_THRESHOLD]
            if CONF_WINDOW_AUTO_MAX_DURATION in self._infos:
                del self._infos[CONF_WINDOW_AUTO_MAX_DURATION]
        if not self._infos[CONF_USE_MOTION_FEATURE]:
            self._infos[CONF_USE_MOTION_CENTRAL_CONFIG] = False
            if CONF_MOTION_SENSOR in self._infos:
                del self._infos[CONF_MOTION_SENSOR]
        if not self._infos[CONF_USE_POWER_FEATURE]:
            self._infos[CONF_USE_POWER_CENTRAL_CONFIG] = False
            if CONF_POWER_SENSOR in self._infos:
                del self._infos[CONF_POWER_SENSOR]
            if CONF_MAX_POWER_SENSOR in self._infos:
                del self._infos[CONF_MAX_POWER_SENSOR]
        if not self._infos[CONF_USE_PRESENCE_FEATURE]:
            self._infos[CONF_USE_PRESENCE_CENTRAL_CONFIG] = False
            if CONF_PRESENCE_SENSOR in self._infos:
                del self._infos[CONF_PRESENCE_SENSOR]
        if not self._infos[CONF_USE_HUMIDITY_FEATURE]:
            self._infos[CONF_USE_HUMIDITY_CENTRAL_CONFIG] = False
            if CONF_HUMIDITY_SENSOR in self._infos:
                del self._infos[CONF_HUMIDITY_SENSOR]
            if CONF_HUMIDITY_THRESHOLD in self._infos:
                del self._infos[CONF_HUMIDITY_THRESHOLD]
        if not self._infos[CONF_USE_CENTRAL_BOILER_FEATURE]:
            if CONF_CENTRAL_BOILER_ACTIVATION_SRV in self._infos:
                del self._infos[CONF_CENTRAL_BOILER_ACTIVATION_SRV]
            if CONF_CENTRAL_BOILER_DEACTIVATION_SRV in self._infos:
                del self._infos[CONF_CENTRAL_BOILER_DEACTIVATION_SRV]
        if not self._infos[CONF_USE_AUTO_START_STOP_FEATURE]:
            self._infos[CONF_AUTO_START_STOP_LEVEL] = AUTO_START_STOP_LEVEL_NONE

        # Removes temporary value
        if COMES_FROM in self._infos:
            del self._infos[COMES_FROM]


class VersatileThermostatConfigFlow(VersatileThermostatBaseConfigFlow, HAConfigFlow, domain=DOMAIN):  # pylint: disable=abstract-method
    """Handle a config flow for Versatile Thermostat."""

    def __init__(self) -> None:
        # self._info = dict()
        super().__init__(dict())
        _LOGGER.debug("CTOR ConfigFlow")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get options flow for this handler"""
        # #713 doesn't work as explained here:https://developers.home-assistant.io/blog/2024/11/12/options-flow
        #  should be - return VersatileThermostatOptionsFlowHandler() but hass is not initialized
        return VersatileThermostatOptionsFlowHandler(config_entry)

    async def async_step_finalize(self, _):
        """Finalization of the ConfigEntry creation"""
        _LOGGER.debug("ConfigFlow.async_finalize")
        await super().async_step_finalize(_)

        return self.async_create_entry(title=self._infos[CONF_NAME], data=self._infos)


class VersatileThermostatOptionsFlowHandler(VersatileThermostatBaseConfigFlow, OptionsFlow):
    """Handle options flow for Versatile Thermostat integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""

        self._conf_app_id: str | None = None

        super().__init__(config_entry.data.copy())
        # #713
        # self.config_entry = config_entry
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

        return await self.async_step_menu(user_input)

    async def async_step_finalize(self, _):
        """Finalization of the ConfigEntry creation"""

        _LOGGER.info(
            "Recreating entry %s due to configuration change. New config is now: %s",
            self.config_entry.entry_id,
            self._infos,
        )
        await super().async_step_finalize(_)

        self.hass.config_entries.async_update_entry(self.config_entry, data=self._infos)
        return self.async_create_entry(title=None, data=None)
