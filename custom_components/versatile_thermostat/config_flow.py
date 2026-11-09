# pylint: disable=line-too-long, too-many-lines, invalid-name

"""Config flow for Versatile Thermostat integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re
from vtherm_api.log_collector import get_vtherm_logger
import copy
from collections.abc import Mapping  # pylint: disable=import-error
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    OptionsFlow,
)
from homeassistant.const import UnitOfTemperature

from homeassistant.data_entry_flow import FlowHandler, FlowResult, section
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template
from homeassistant.helpers.translation import async_get_translations

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_central_api import VersatileThermostatAPI
from .commons import check_and_extract_service_configuration
from .humidity import find_humidity_sensor_candidates

COMES_FROM = "comes_from"
PLUGINS_LINK_PLACEHOLDER = "plugins_link"
PLUGINS_LINK = "[plugins](https://www.versatile-thermostat.org/en/plugins/)"

_LOGGER = get_vtherm_logger(__name__)


@dataclass
class MissingItem:
    """A missing mandatory setting: the step to open to fix it and the fields involved"""

    step_id: str
    fields: list[str] = field(default_factory=list)
    device: str | None = None


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

    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION
    TRANSLATION_CATEGORY = "config"

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos: dict = infos
        self._learning_type_changed = False
        # The device being edited (index in the underlyings) or added (entity) in the underlying steps
        self._underlying_idx: int | None = None
        self._underlying_entity: str | None = None
        # The creation wizard (only used by the config flow): the steps already displayed and the steps displayed to fix a missing setting
        self._wizard_active = False
        self._wizard_visited: set[str] = set()
        self._wizard_fixed: set[str] = set()
        self._placeholders = {
            CONF_NAME: "",
            PLUGINS_LINK_PLACEHOLDER: PLUGINS_LINK,
        }

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
        is_central_config = (
            self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG
        )

        self._infos[CONF_USE_WINDOW_FEATURE] = (
            self._infos.get(CONF_USE_WINDOW_CENTRAL_CONFIG, False)
            or self._infos.get(CONF_WINDOW_SENSOR) is not None
            or self._infos.get(CONF_WINDOW_AUTO_OPEN_THRESHOLD) is not None
        )
        self._infos[CONF_USE_MOTION_FEATURE] = self._infos.get(
            CONF_USE_MOTION_FEATURE, False
        ) and (self._infos.get(CONF_MOTION_SENSOR) is not None or is_central_config)

        self._infos[CONF_USE_POWER_FEATURE] = (
            self._infos.get(CONF_USE_POWER_CENTRAL_CONFIG, False)
            or self._infos.get(CONF_USE_POWER_FEATURE, False)
            or (is_central_config and self._infos.get(CONF_POWER_SENSOR) is not None and self._infos.get(CONF_MAX_POWER_SENSOR) is not None)
        )
        self._infos[CONF_USE_PRESENCE_FEATURE] = (
            self._infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False)
            or self._infos.get(CONF_PRESENCE_SENSOR) is not None
        )

        self._infos[CONF_USE_CENTRAL_BOILER_FEATURE] = (
            self._infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV) is not None
            and self._infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV) is not None
        )

        self._infos[CONF_USE_AUTO_START_STOP_FEATURE] = (
            self._infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False) is True
            and self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE
        )

        self._infos[CONF_USE_HEATING_FAILURE_DETECTION_FEATURE] = self._infos.get(
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE, False
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
            CONF_USE_LOCK_CENTRAL_CONFIG,
            CONF_USE_CENTRAL_MODE,
        ):
            if not is_empty:
                current_config = self._infos.get(config, None)

                self._infos[config] = self._central_config is not None and (
                    current_config is True or current_config is None
                )
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

    def is_sync_device_internal_temp_selected(self, infos) -> bool:
        """True if the synchronize device internal temperature mode is selected"""
        return infos.get(CONF_SYNC_DEVICE_INTERNAL_TEMP, False) is True

    async def validate_input(self, data: dict, step_id) -> None:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_*_DATA_SCHEMA with values provided by the user.
        """

        # check the entity_ids
        for conf in [
            CONF_UNDERLYING_LIST,
            CONF_TEMP_SENSOR,
            CONF_HUMIDITY_SENSOR,
            CONF_EXTERNAL_TEMP_SENSOR,
            CONF_WINDOW_SENSOR,
            CONF_MOTION_SENSOR,
            CONF_POWER_SENSOR,
            CONF_MAX_POWER_SENSOR,
            CONF_PRESENCE_SENSOR,
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
                CONF_USE_LOCK_CENTRAL_CONFIG,
                CONF_USE_CENTRAL_MODE,
                # CONF_USE_CENTRAL_BOILER_FEATURE, this is for Central Config
                CONF_USED_BY_CENTRAL_BOILER,
            ]:
                if data.get(conf) is True:
                    _LOGGER.error(
                        "The use of central configuration need a central configuration Versatile Thermostat instance"
                    )
                    raise NoCentralConfig(conf)

        # Check the service for central boiler format
        if self._infos.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            for conf in [
                CONF_CENTRAL_BOILER_ACTIVATION_SRV,
                CONF_CENTRAL_BOILER_DEACTIVATION_SRV,
            ]:
                try:
                    service_config = check_and_extract_service_configuration(data.get(conf))
                    if service_config.get("is_template"):
                        Template(service_config["attribute_value"], self.hass).ensure_valid()
                except (ServiceConfigurationError, TemplateError) as err:
                    raise ServiceConfigurationError(conf) from err

        if data.get(CONF_LOCK_CODE) is not None:
            if not re.match(r"^\d{4}$", str(data.get(CONF_LOCK_CODE))):
                raise LockCodeIncorrect()

    def get_missing_config(self, infos) -> list[MissingItem]:
        """Return the missing mandatory settings (an empty list means that the config is complete).
        Each item gives the step to open to fix it and the fields involved"""
        missing: list[MissingItem] = []

        is_central_config = infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG
        if is_central_config:
            main_fields = [conf for conf in (CONF_NAME, CONF_EXTERNAL_TEMP_SENSOR) if infos.get(conf) is None]
            if main_fields:
                missing.append(MissingItem("main", main_fields))

            if infos.get(CONF_USE_POWER_FEATURE, False) is True:
                power_fields = [conf for conf in (CONF_POWER_SENSOR, CONF_MAX_POWER_SENSOR) if infos.get(conf, None) is None]
                if power_fields:
                    missing.append(MissingItem("power", power_fields))

            if infos.get(CONF_USE_PRESENCE_FEATURE, False) is True and infos.get(CONF_PRESENCE_SENSOR, None) is None:
                missing.append(MissingItem("presence", [CONF_PRESENCE_SENSOR]))

            if infos.get(CONF_USE_CENTRAL_BOILER_FEATURE, False):
                boiler_fields = [conf for conf in (CONF_CENTRAL_BOILER_ACTIVATION_SRV, CONF_CENTRAL_BOILER_DEACTIVATION_SRV) if not infos.get(conf)]
                if boiler_fields:
                    missing.append(MissingItem("central_boiler", boiler_fields))
        else:
            main_fields = [conf for conf in (CONF_NAME, CONF_TEMP_SENSOR, CONF_CYCLE_MIN) if infos.get(conf) is None]
            if infos.get(CONF_USE_MAIN_CENTRAL_CONFIG, False) is False and infos.get(CONF_EXTERNAL_TEMP_SENSOR) is None:
                main_fields.append(CONF_EXTERNAL_TEMP_SENSOR)
            if main_fields:
                missing.append(MissingItem("main", main_fields))

            # checks that at least one underlying is set and that each device has its mandatory settings
            missing += self._get_underlying_missing_items(infos)

            if infos.get(CONF_USE_MOTION_FEATURE, False) is True and infos.get(CONF_MOTION_SENSOR, None) is None:
                missing.append(MissingItem("motion", [CONF_MOTION_SENSOR]))

            if infos.get(CONF_USE_POWER_FEATURE, False) is True and infos.get(CONF_USE_POWER_CENTRAL_CONFIG, False) is False and infos.get(CONF_PRESET_POWER, None) is None:
                missing.append(MissingItem("power", [CONF_PRESET_POWER]))

            if (
                infos.get(CONF_USE_PRESENCE_FEATURE, False) is True
                and infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False) is False
                and infos.get(CONF_PRESENCE_SENSOR, None) is None
            ):
                missing.append(MissingItem("presence", [CONF_PRESENCE_SENSOR]))

            if infos.get(CONF_USE_ADVANCED_CENTRAL_CONFIG, False) is False:
                advanced_fields = [conf for conf in (CONF_SAFETY_DELAY_MIN, CONF_SAFETY_MIN_ON_PERCENT, CONF_SAFETY_DEFAULT_ON_PERCENT) if infos.get(conf, -1) in (-1, None)]
                if advanced_fields:
                    missing.append(MissingItem("advanced", advanced_fields))

            if infos.get(CONF_PROP_FUNCTION, None) == PROPORTIONAL_FUNCTION_TPI and infos.get(CONF_USE_TPI_CENTRAL_CONFIG, False) is False:
                tpi_fields = [conf for conf in (CONF_TPI_COEF_INT, CONF_TPI_COEF_EXT) if infos.get(conf, None) is None]
                if tpi_fields:
                    missing.append(MissingItem("tpi", tpi_fields))

            if infos.get(CONF_USE_PRESETS_CENTRAL_CONFIG, False) is True and self._central_config is None:
                missing.append(MissingItem("presets", [CONF_USE_PRESETS_CENTRAL_CONFIG]))

        return missing

    def check_config_complete(self, infos) -> bool:
        """True if the config is now complete (ie all mandatory attributes are set)"""
        return not self.get_missing_config(infos)

    async def _async_get_translations(self) -> dict[str, str]:
        """Return the translations of this flow (config or options category) in the language of the server"""
        try:
            return await async_get_translations(self.hass, self.hass.config.language, self.TRANSLATION_CATEGORY, [DOMAIN])
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug("Unable to load the translations of the flow", exc_info=True)
            return {}

    def _get_field_label(self, translations: dict[str, str], step_id: str, conf: str) -> str:
        """Return the translated label of a field. Falls back on the label of the same field in another step then on the field name"""
        prefix = f"component.{DOMAIN}.{self.TRANSLATION_CATEGORY}.step."
        label = translations.get(f"{prefix}{step_id}.data.{conf}")
        if label is None:
            suffix = f".data.{conf}"
            label = next((value for key, value in translations.items() if key.startswith(prefix) and key.endswith(suffix)), conf)
        return label

    async def _async_missing_config_to_text(self, missing: list[MissingItem]) -> str:
        """Build the bulleted list (markdown) of the missing items from the translated labels"""
        translations = await self._async_get_translations()
        prefix = f"component.{DOMAIN}.{self.TRANSLATION_CATEGORY}.step."
        lines = []
        for item in missing:
            step_label = translations.get(f"{prefix}menu.menu_options.{item.step_id}", item.step_id)
            labels = ", ".join(self._get_field_label(translations, item.step_id, conf) for conf in item.fields)
            if item.device:
                labels = f"{item.device} - {labels}"
            lines.append(f"- **{step_label}**: {labels}")
        return "\n".join(lines)

    async def _async_missing_config_summary(self, missing: list[MissingItem]) -> str:
        """Build the sentence summarizing the number of settings to complete. Empty if the configuration is complete"""
        if not missing:
            return ""
        translations = await self._async_get_translations()
        template = translations.get(f"component.{DOMAIN}.{self.TRANSLATION_CATEGORY}.error.missing_settings_summary", "{count} setting(s) to complete")
        return template.replace("{count}", str(len(missing)))

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

    def _get_wizard_steps(self) -> list[str]:
        """Return the steps of the creation wizard. The list depends on what has been chosen in the previous steps (type, algorithm, features)"""
        infos = self._infos
        is_central_config = infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG

        feature_steps = []
        for conf, step_id in (
            (CONF_USE_WINDOW_FEATURE, "window"),
            (CONF_USE_MOTION_FEATURE, "motion"),
            (CONF_USE_POWER_FEATURE, "power"),
            (CONF_USE_PRESENCE_FEATURE, "presence"),
        ):
            if infos.get(conf, False) is True:
                feature_steps.append(step_id)
        if is_central_config:
            if infos.get(CONF_USE_CENTRAL_BOILER_FEATURE, False) is True:
                feature_steps.append("central_boiler")
        elif (
            infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False) is True
            and infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE
            and not self.is_valve_regulation_selected(infos)
        ):
            feature_steps.append("auto_start_stop")
        if infos.get(CONF_USE_HEATING_FAILURE_DETECTION_FEATURE, False) is True:
            feature_steps.append("heating_failure_detection")

        if is_central_config:
            return ["main", "features"] + feature_steps + ["tpi", "advanced"]

        steps = ["main", "type"]
        if infos.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI or self.is_valve_regulation_selected(infos):
            steps.append("tpi")
        return steps + ["features"] + feature_steps + ["advanced"]

    async def _start_wizard(self) -> FlowResult:
        """Called when the type of VTherm is chosen. Outside of the creation, the menu is displayed"""
        return await self.async_step_menu()

    async def _next_step(self) -> FlowResult:
        """Return the next step: the next screen of the creation wizard or, outside of the wizard, the menu"""
        if not self._wizard_active:
            return await self.async_step_menu()

        # The list is computed again each time because it depends on the previous answers
        for step_id in self._get_wizard_steps():
            if step_id not in self._wizard_visited:
                self._wizard_visited.add(step_id)
                _LOGGER.debug("Wizard: next step is %s", step_id)
                if step_id == "type":
                    # The underlyings start with their common settings
                    return await self.async_step_underlying_common()
                return await getattr(self, f"async_step_{step_id}")()

        # End of the wizard: the configuration should be complete. If not, the screens to fix are displayed (once each) before the menu
        for item in self.get_missing_config(self._infos):
            if item.step_id not in self._wizard_fixed:
                _LOGGER.debug("Wizard: the configuration is not complete, step %s is displayed again", item.step_id)
                self._wizard_fixed.add(item.step_id)
                return await getattr(self, f"async_step_{item.step_id}")()

        self._wizard_active = False
        return await self.async_step_menu()

    async def _async_get_placeholders(self, step_id: str) -> dict:
        """Return the description placeholders of a step. During the creation wizard they include the progress"""
        placeholders = self._placeholders | {"wizard_progress": ""}
        if self._wizard_active:
            steps = self._get_wizard_steps()
            # All the screens of the underlyings are one step of the wizard. The type of VTherm is the first step
            wizard_step = "type" if step_id.startswith("underlying") else step_id
            if wizard_step in steps:
                translations = await self._async_get_translations()
                template = translations.get(
                    f"component.{DOMAIN}.{self.TRANSLATION_CATEGORY}.error.wizard_progress", "Step {current} / {total}\n\n"
                )
                placeholders["wizard_progress"] = template.replace("{current}", str(steps.index(wizard_step) + 2)).replace("{total}", str(len(steps) + 1))
        return placeholders

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
        ds = add_suggested_values_to_schema(
            data_schema=data_schema, suggested_values=defaults
        )  # pylint: disable=invalid-name

        return self.async_show_form(
            step_id=step_id,
            data_schema=ds,
            errors=errors,
            description_placeholders=await self._async_get_placeholders(step_id),
        )

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        # Always do a fresh lookup (not from __init__ cache) to handle same-session deletions
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        central_config = vtherm_api.find_central_configuration() if vtherm_api else None

        # Exclude the central config type if one already exists (it must be unique)
        if central_config is not None:
            available_types = [t for t in CONF_THERMOSTAT_TYPES if t != CONF_THERMOSTAT_CENTRAL_CONFIG]
            schema = vol.Schema(
                {
                    vol.Required(CONF_THERMOSTAT_TYPE, default=CONF_THERMOSTAT_SWITCH): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=available_types,
                            translation_key="thermostat_type",
                            mode="list",
                        )
                    )
                }
            )
        else:
            schema = STEP_USER_DATA_SCHEMA

        return await self.generic_step("user", schema, user_input, self._start_wizard)

    async def async_step_configuration_not_complete(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """List the missing settings and propose the steps to fix them"""
        _LOGGER.debug("Into ConfigFlow.async_step_configuration_not_complete user_input=%s", user_input)

        missing = self.get_missing_config(self._infos)
        if not missing:
            return await self.async_step_menu()

        # one menu option per step to fix (without duplicates)
        menu_options = list(dict.fromkeys(item.step_id for item in missing))
        menu_options.append("menu")

        placeholders = self._placeholders | {"missing_items": await self._async_missing_config_to_text(missing)}
        return self.async_show_menu(
            step_id="configuration_not_complete",
            menu_options=menu_options,
            description_placeholders=placeholders,
        )

    async def async_step_menu(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_menu user_input=%s", user_input)

        is_central_config = self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG

        menu_options = ["main", "features"]
        if not is_central_config:
            menu_options.append("type")

        if (
            self._infos.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI
            or is_central_config
            or self.is_valve_regulation_selected(self._infos)
        ):
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

        if (
            self._infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False) is True
            and self._infos[CONF_THERMOSTAT_TYPE]
            in [
                CONF_THERMOSTAT_CLIMATE,
            ]
            and not self.is_valve_regulation_selected(self._infos)
        ):
            menu_options.append("auto_start_stop")

        menu_options.append("advanced")
        menu_options.append("lock")
        if not is_central_config:
            menu_options.append("humidity")

        # Add heating failure detection menu if feature is enabled
        if self._infos.get(CONF_USE_HEATING_FAILURE_DETECTION_FEATURE, False) is True:
            menu_options.append("heating_failure_detection")

        missing = self.get_missing_config(self._infos)
        if not missing:
            menu_options.append("finalize")
        else:
            _LOGGER.info("The configuration is not terminated. Missing: %s", missing)
            menu_options.append("configuration_not_complete")

        placeholders = self._placeholders | {
            "missing_count": str(len(missing)),
            "missing_summary": await self._async_missing_config_summary(missing),
        }
        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options,
            description_placeholders=placeholders,
        )

    async def async_step_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_main user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            self._infos[CONF_NAME] = CENTRAL_CONFIG_NAME
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
        else:
            schema = STEP_MAIN_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_MAIN_CENTRAL_CONFIG, False) is False
            ):
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_main":
                    schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_main

        # Add default values for temperature if not set
        if self._infos.get(CONF_TEMP_MIN) is None:
            # We use the system default unit
            unit = self.hass.config.units.temperature_unit
            if unit == UnitOfTemperature.FAHRENHEIT:
                self._infos[CONF_TEMP_MIN] = 45
                self._infos[CONF_TEMP_MAX] = 95
                self._infos[CONF_STEP_TEMPERATURE] = 1.0
            else:
                self._infos[CONF_TEMP_MIN] = 7
                self._infos[CONF_TEMP_MAX] = 35
                self._infos[CONF_STEP_TEMPERATURE] = 0.1

        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_spec_main(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific main flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_main user_input=%s", user_input)

        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_MAIN_DATA_SCHEMA
        else:
            schema = STEP_CENTRAL_SPEC_MAIN_DATA_SCHEMA
        next_step = self._next_step

        self._infos[COMES_FROM] = "async_step_spec_main"

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("main", schema, user_input, next_step)

    async def async_step_central_boiler(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the central boiler flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_central_boiler user_input=%s", user_input
        )

        schema = STEP_CENTRAL_BOILER_SCHEMA
        next_step = self._next_step

        return await self.generic_step("central_boiler", schema, user_input, next_step)

    # ------------------------------------------------------------------
    # Underlyings: the devices controlled by the VTherm.
    # The data are kept in the parallel lists of the configuration (underlying_entity_ids, opening_degree_entity_ids,
    # ...). The device forms read and write the position of the device in each list.
    # ------------------------------------------------------------------

    def _get_entity_name(self, entity_id: str) -> str:
        """Return the friendly name of an entity or its entity_id"""
        state = self.hass.states.get(entity_id) if self.hass is not None else None
        if state is not None and state.attributes.get("friendly_name"):
            return state.attributes["friendly_name"]
        return entity_id

    def _get_underlying_form_fields(self, entity_id: str) -> list[str]:
        """Return the fields of the form of a device. It depends on the type of VTherm, on the entity and on the common settings"""
        thermostat_type = self._infos.get(CONF_THERMOSTAT_TYPE)
        if thermostat_type == CONF_THERMOSTAT_SWITCH:
            return [CONF_VSWITCH_ON_CMD, CONF_VSWITCH_OFF_CMD]
        if thermostat_type == CONF_THERMOSTAT_VALVE:
            return [CONF_MIN_OPENING_DEGREE, CONF_MAX_OPENING_DEGREE]
        fields = []
        if self.is_valve_regulation_selected(self._infos):
            fields += [CONF_OPENING_DEGREE_ENTITY, CONF_CLOSING_DEGREE_ENTITY, CONF_MIN_OPENING_DEGREE, CONF_MAX_OPENING_DEGREE]
        if self.is_sync_device_internal_temp_selected(self._infos):
            fields.append(CONF_SYNC_ENTITY)
        return fields

    def _is_commands_required(self, entity_id: str) -> bool:
        """True if the commands to turn on / off are required: it is the case if the entity is not a switch"""
        return self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_SWITCH and entity_id.split(".")[0] not in (SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN)

    def _get_list_value(self, key: str, idx: int, infos: dict | None = None):
        """Return the value at the position of a device in one of the lists of the configuration"""
        values = (infos if infos is not None else self._infos).get(key) or []
        return values[idx] if idx < len(values) else None

    def _set_list_value(self, key: str, idx: int, value: str) -> None:
        """Set the value at the position of a device in one of the lists of the configuration. The lists are copied
        before the modification (they can be shared with the config entry)"""
        values = list(self._infos.get(key) or [])
        values += [""] * (idx + 1 - len(values))
        values[idx] = value or ""
        self._infos[key] = values

    def _get_csv_list(self, key: str) -> list[int]:
        """Return the content of a comma separated list of integers of the configuration. A malformed list is ignored"""
        raw = self._infos.get(key)
        if not raw:
            return []
        try:
            return [int(x.strip()) for x in str(raw).split(",")]
        except ValueError:
            return []

    def _get_valve_entity(self, idx: int | None, values: dict | None = None) -> str | None:
        """Return the entity of the valve of a device: the device itself for an over_valve, the opening entity for an over_climate"""
        if self._infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_VALVE:
            return self._get_list_value(CONF_UNDERLYING_LIST, idx) if idx is not None else self._underlying_entity
        if values and values.get(CONF_OPENING_DEGREE_ENTITY):
            return values[CONF_OPENING_DEGREE_ENTITY]
        return self._get_list_value(CONF_OPENING_DEGREE_LIST, idx) if idx is not None else None

    def _get_valve_max(self, valve_entity: str | None) -> int:
        """Return the maximum opening of a valve"""
        state = self.hass.states.get(valve_entity) if valve_entity else None
        try:
            return int(state.attributes.get("max", 100)) if state is not None else 100
        except (TypeError, ValueError):
            return 100

    def _get_underlying_values(self, idx: int) -> dict:
        """Return the values of the form fields of the device at idx (None when the value is not set)"""
        values = {
            CONF_OPENING_DEGREE_ENTITY: self._get_list_value(CONF_OPENING_DEGREE_LIST, idx),
            CONF_CLOSING_DEGREE_ENTITY: self._get_list_value(CONF_CLOSING_DEGREE_LIST, idx),
            CONF_SYNC_ENTITY: self._get_list_value(CONF_SYNC_ENTITY_LIST, idx),
            CONF_VSWITCH_ON_CMD: self._get_list_value(CONF_VSWITCH_ON_CMD_LIST, idx),
            CONF_VSWITCH_OFF_CMD: self._get_list_value(CONF_VSWITCH_OFF_CMD_LIST, idx),
        }
        min_list = self._get_csv_list(CONF_MIN_OPENING_DEGREES)
        max_list = self._get_csv_list(CONF_MAX_OPENING_DEGREES)
        values[CONF_MIN_OPENING_DEGREE] = min_list[idx] if idx < len(min_list) else 0
        values[CONF_MAX_OPENING_DEGREE] = max_list[idx] if idx < len(max_list) else self._get_valve_max(self._get_valve_entity(idx, values))
        return values

    def _get_underlying_missing_fields(self, infos: dict, idx: int) -> list[str]:
        """Return the fields which are still mandatory for the device at idx"""
        entity_id = infos[CONF_UNDERLYING_LIST][idx]
        thermostat_type = infos.get(CONF_THERMOSTAT_TYPE)
        missing = []
        if thermostat_type == CONF_THERMOSTAT_SWITCH:
            # The commands are given for all the devices or for none. They are always mandatory for the entities which are not switches
            required = entity_id.split(".")[0] not in (SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN)
            for conf, key in ((CONF_VSWITCH_ON_CMD, CONF_VSWITCH_ON_CMD_LIST), (CONF_VSWITCH_OFF_CMD, CONF_VSWITCH_OFF_CMD_LIST)):
                if (required or any(infos.get(key) or [])) and not self._get_list_value(key, idx, infos):
                    missing.append(conf)
        elif thermostat_type == CONF_THERMOSTAT_CLIMATE:
            if self.is_valve_regulation_selected(infos):
                if not self._get_list_value(CONF_OPENING_DEGREE_LIST, idx, infos):
                    missing.append(CONF_OPENING_DEGREE_ENTITY)
                # The closing entities are given for all the devices or for none
                if any(infos.get(CONF_CLOSING_DEGREE_LIST) or []) and not self._get_list_value(CONF_CLOSING_DEGREE_LIST, idx, infos):
                    missing.append(CONF_CLOSING_DEGREE_ENTITY)
            if self.is_sync_device_internal_temp_selected(infos) and not self._get_list_value(CONF_SYNC_ENTITY_LIST, idx, infos):
                missing.append(CONF_SYNC_ENTITY)
        return missing

    def _get_underlying_missing_items(self, infos: dict) -> list[MissingItem]:
        """Return the missing items of the underlyings (no device or a device with mandatory fields not filled)"""
        underlyings = infos.get(CONF_UNDERLYING_LIST, [])
        if len(underlyings) < 1:
            return [MissingItem("type", [CONF_UNDERLYING_ENTITY])]
        items = []
        for idx, entity_id in enumerate(underlyings):
            fields = self._get_underlying_missing_fields(infos, idx)
            if fields:
                items.append(MissingItem("type", fields, device=self._get_entity_name(entity_id)))
        return items

    def _store_csv_value(self, key: str, idx: int, value: int, get_default) -> None:
        """Store the value of a device in a comma separated list. The list is removed if all the values are the default ones"""
        values = self._get_csv_list(key)
        nb_values = max(len(self._infos.get(CONF_UNDERLYING_LIST, [])), idx + 1)
        values += [get_default(i) for i in range(len(values), nb_values)]
        values[idx] = value
        if all(val == get_default(i) for i, val in enumerate(values)):
            self._infos.pop(key, None)
        else:
            self._infos[key] = ", ".join(str(val) for val in values)

    def _set_underlying_values(self, idx: int, values: dict) -> None:
        """Write the values of the form of the device at idx in the lists of the configuration"""
        if CONF_OPENING_DEGREE_ENTITY in values or CONF_CLOSING_DEGREE_ENTITY in values:
            self._set_list_value(CONF_OPENING_DEGREE_LIST, idx, values.get(CONF_OPENING_DEGREE_ENTITY))
            self._set_list_value(CONF_CLOSING_DEGREE_LIST, idx, values.get(CONF_CLOSING_DEGREE_ENTITY))
            if not any(self._infos[CONF_CLOSING_DEGREE_LIST]):
                self._infos[CONF_CLOSING_DEGREE_LIST] = []
        if CONF_SYNC_ENTITY in values:
            self._set_list_value(CONF_SYNC_ENTITY_LIST, idx, values[CONF_SYNC_ENTITY])
        if CONF_VSWITCH_ON_CMD in values or CONF_VSWITCH_OFF_CMD in values:
            for conf, key in ((CONF_VSWITCH_ON_CMD, CONF_VSWITCH_ON_CMD_LIST), (CONF_VSWITCH_OFF_CMD, CONF_VSWITCH_OFF_CMD_LIST)):
                self._set_list_value(key, idx, (values.get(conf) or "").strip())
                if not any(self._infos[key]):
                    self._infos.pop(key)
        if CONF_MIN_OPENING_DEGREE in values:
            self._store_csv_value(CONF_MIN_OPENING_DEGREES, idx, int(values[CONF_MIN_OPENING_DEGREE]), lambda i: 0)
        if CONF_MAX_OPENING_DEGREE in values:
            self._store_csv_value(
                CONF_MAX_OPENING_DEGREES,
                idx,
                int(values[CONF_MAX_OPENING_DEGREE]),
                lambda i: self._get_valve_max(self._get_valve_entity(i, None)),
            )

    def _remove_underlying(self, idx: int) -> None:
        """Remove the device at idx from all the lists of the configuration"""
        for key in (
            CONF_UNDERLYING_LIST,
            CONF_OPENING_DEGREE_LIST,
            CONF_CLOSING_DEGREE_LIST,
            CONF_SYNC_ENTITY_LIST,
            CONF_VSWITCH_ON_CMD_LIST,
            CONF_VSWITCH_OFF_CMD_LIST,
        ):
            values = list(self._infos.get(key) or [])
            if idx < len(values):
                values.pop(idx)
                self._infos[key] = values
        for key in (CONF_VSWITCH_ON_CMD_LIST, CONF_VSWITCH_OFF_CMD_LIST):
            if key in self._infos and not any(self._infos[key]):
                self._infos.pop(key)
        for key in (CONF_MIN_OPENING_DEGREES, CONF_MAX_OPENING_DEGREES):
            values = self._get_csv_list(key)
            if idx < len(values):
                values.pop(idx)
                if values:
                    self._infos[key] = ", ".join(str(val) for val in values)
                else:
                    self._infos.pop(key, None)

    def _suggest_same_device_entity(self, entity_id: str, keyword: str) -> str | None:
        """Return a number entity of the same device than entity_id with keyword in its entity_id, if any"""
        try:
            registry = er.async_get(self.hass)
            entry = registry.async_get(entity_id)
            if entry is None or entry.device_id is None:
                return None
            for candidate in er.async_entries_for_device(registry, entry.device_id):
                if candidate.domain in (NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN) and keyword in candidate.entity_id:
                    return candidate.entity_id
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug("Unable to search the entities of the device of %s", entity_id, exc_info=True)
        return None

    def _build_underlying_schema(self, entity_id: str, idx: int | None) -> vol.Schema:
        """Build the form of a device: only the fields which apply are included. A new device (idx is None) has no replace nor remove field"""
        fields = self._get_underlying_form_fields(entity_id)
        values = self._get_underlying_values(idx) if idx is not None else {}
        suggested = {key: value for key, value in values.items() if value not in (None, "")}
        number_domains = [NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]
        # The mandatory entities are required for a new device. For an existing one they are not, so that an incomplete device can still be removed
        marker = vol.Required if idx is None else vol.Optional

        schema = {}
        if CONF_OPENING_DEGREE_ENTITY in fields:
            schema[marker(CONF_OPENING_DEGREE_ENTITY)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=number_domains))
            schema[vol.Optional(CONF_CLOSING_DEGREE_ENTITY)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=number_domains))
            for conf, keyword in ((CONF_OPENING_DEGREE_ENTITY, "opening"), (CONF_CLOSING_DEGREE_ENTITY, "closing")):
                if conf not in suggested and (candidate := self._suggest_same_device_entity(entity_id, keyword)):
                    suggested[conf] = candidate
        if CONF_SYNC_ENTITY in fields:
            schema[marker(CONF_SYNC_ENTITY)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=number_domains))
            keyword = "calibration" if self._infos.get(CONF_SYNC_WITH_CALIBRATION, True) else "temperature"
            if CONF_SYNC_ENTITY not in suggested and (candidate := self._suggest_same_device_entity(entity_id, keyword)):
                suggested[CONF_SYNC_ENTITY] = candidate
        if CONF_MIN_OPENING_DEGREE in fields:
            valve_max = self._get_valve_max(self._get_valve_entity(idx, suggested))
            schema[vol.Optional(CONF_MIN_OPENING_DEGREE, default=0)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=valve_max, step=1, mode=selector.NumberSelectorMode.BOX)
            )
            schema[vol.Optional(CONF_MAX_OPENING_DEGREE, default=valve_max)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=valve_max, step=1, mode=selector.NumberSelectorMode.BOX)
            )
        if CONF_VSWITCH_ON_CMD in fields:
            on_off_schema = vol.Schema(
                {
                    vol.Required(CONF_VSWITCH_ON_CMD) if self._is_commands_required(entity_id) else vol.Optional(CONF_VSWITCH_ON_CMD): selector.TextSelector(),
                    vol.Required(CONF_VSWITCH_OFF_CMD) if self._is_commands_required(entity_id) else vol.Optional(CONF_VSWITCH_OFF_CMD): selector.TextSelector(),
                }
            )
            if self._is_commands_required(entity_id):
                schema.update(on_off_schema.schema)
            else:
                # the custom commands of a switch are optional: they are in a collapsed section
                on_off_schema = add_suggested_values_to_schema(on_off_schema, suggested)
                schema[vol.Optional(CONF_VSWITCH_COMMANDS_SECTION)] = section(on_off_schema, {"collapsed": not (suggested.get(CONF_VSWITCH_ON_CMD) or suggested.get(CONF_VSWITCH_OFF_CMD))})
        if idx is not None:
            schema[vol.Optional(CONF_REPLACE_ENTITY)] = build_underlying_entity_selector(self._infos.get(CONF_THERMOSTAT_TYPE))
            schema[vol.Optional(CONF_REMOVE_UNDERLYING, default=False)] = cv.boolean
            suggested[CONF_REPLACE_ENTITY] = entity_id

        return add_suggested_values_to_schema(vol.Schema(schema), suggested)

    def _validate_underlying_input(self, entity_id: str, idx: int | None, user_input: dict) -> dict:
        """Validate the input of the form of a device. Returns the errors"""
        errors = {}
        for conf in (CONF_OPENING_DEGREE_ENTITY, CONF_CLOSING_DEGREE_ENTITY, CONF_SYNC_ENTITY, CONF_REPLACE_ENTITY):
            value = user_input.get(conf)
            if value and self.hass.states.get(value) is None:
                _LOGGER.error("Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration", value)
                errors[conf] = "unknown_entity"

        replace = user_input.get(CONF_REPLACE_ENTITY)
        if replace and replace != entity_id and replace in self._infos.get(CONF_UNDERLYING_LIST, []):
            errors[CONF_REPLACE_ENTITY] = "underlying_already_added"

        # check format of the commands
        pattern = r"^(?P<command>[^\s/]+)(?:/(?P<argument>[^\s:]+)(?::(?P<value>[^\s]+))?)?$"
        commands = [(user_input.get(conf) or "").strip() for conf in (CONF_VSWITCH_ON_CMD, CONF_VSWITCH_OFF_CMD)]
        if any(command and not re.match(pattern, command) for command in commands):
            errors["base"] = "vswitch_configuration_incorrect"
        if self._is_commands_required(entity_id) and not all(commands):
            errors["base"] = "vswitch_configuration_incorrect"

        if CONF_MAX_OPENING_DEGREE in user_input:
            min_opening = int(user_input.get(CONF_MIN_OPENING_DEGREE, 0))
            max_opening = int(user_input[CONF_MAX_OPENING_DEGREE])
            valve_max = self._get_valve_max(self._get_valve_entity(idx, user_input))
            if max_opening <= 0 or max_opening > valve_max:
                errors[CONF_MAX_OPENING_DEGREE] = "max_opening_degree_out_of_range"
            elif max_opening <= min_opening:
                errors[CONF_MAX_OPENING_DEGREE] = "min_max_opening_degrees_inconsistent"
        return errors

    async def _async_get_underlying_placeholders(self, step_id: str, entity_id: str | None = None) -> dict:
        """Return the description placeholders of the underlying steps"""
        placeholders = await self._async_get_placeholders(step_id)
        if entity_id is not None:
            placeholders["underlying_name"] = self._get_entity_name(entity_id)
            placeholders["underlying_entity"] = entity_id
        return placeholders

    def _format_value(self, translations: dict[str, str], conf: str, value: Any) -> str:
        """Format a value of the common settings for the details displayed in the underlyings menu"""
        if isinstance(value, bool):
            return "✓" if value else "✗"
        selector_key = {CONF_AUTO_REGULATION_MODE: "auto_regulation_mode", CONF_AUTO_FAN_MODE: "auto_fan_mode"}.get(conf)
        if selector_key is not None:
            return translations.get(f"component.{DOMAIN}.selector.{selector_key}.options.{value}", str(value))
        return str(value)

    def _get_underlying_common_details(self, translations: dict[str, str]) -> str:
        """Summary of the common settings, displayed under the 'Common settings' entry of the underlyings menu"""
        thermostat_type = self._infos.get(CONF_THERMOSTAT_TYPE)
        if thermostat_type == CONF_THERMOSTAT_SWITCH:
            schema = build_step_thermostat_switch_schema()
        elif thermostat_type == CONF_THERMOSTAT_VALVE:
            schema = build_step_thermostat_valve_schema()
        else:
            schema = STEP_THERMOSTAT_CLIMATE
        confs = [str(key) for key in schema.schema]
        if thermostat_type == CONF_THERMOSTAT_CLIMATE:
            confs += [str(key) for key in build_step_underlying_extra_schema(self.is_valve_regulation_selected(self._infos), self.is_sync_device_internal_temp_selected(self._infos)).schema]
        parts = []
        for conf in dict.fromkeys(confs):
            value = self._infos.get(conf)
            if value is not None and value != "":
                parts.append(f"{self._get_field_label(translations, 'underlying_common', conf)}: {self._format_value(translations, conf, value)}")
        return " · ".join(parts)

    def _get_underlying_details(self, translations: dict[str, str], idx: int) -> str:
        """Summary of a device, displayed under its entry of the underlyings menu"""
        entity_id = self._infos[CONF_UNDERLYING_LIST][idx]
        missing_fields = self._get_underlying_missing_fields(self._infos, idx)
        if missing_fields:
            template = translations.get(f"component.{DOMAIN}.{self.TRANSLATION_CATEGORY}.error.underlying_field_missing", "{field} is missing")
            labels = (template.replace("{field}", self._get_field_label(translations, "underlying", conf)) for conf in missing_fields)
            return f"⚠ {entity_id} · " + ", ".join(labels)
        parts = [entity_id]
        for conf, value in self._get_underlying_values(idx).items():
            if conf in self._get_underlying_form_fields(entity_id) and value not in (None, ""):
                parts.append(f"{self._get_field_label(translations, 'underlying', conf)}: {value}")
        return " · ".join(parts)

    async def async_step_type(self, user_input: dict | None = None) -> FlowResult:
        """Handle the list of the underlyings: the common settings, one entry per device and the add of a device"""
        _LOGGER.debug("Into ConfigFlow.async_step_type user_input=%s", user_input)

        underlyings = self._infos.get(CONF_UNDERLYING_LIST, [])
        if len(underlyings) > MAX_UNDERLYINGS:
            _LOGGER.warning("%s has more than %d underlyings. Only the first ones can be edited in the configuration", self._infos.get(CONF_NAME), MAX_UNDERLYINGS)

        if self._wizard_active and not underlyings:
            # The first device is added at once
            return await self.async_step_underlying_add()

        translations = await self._async_get_translations()
        placeholders = await self._async_get_placeholders("type")
        placeholders["underlying_common_details"] = self._get_underlying_common_details(translations)

        menu_options = ["underlying_common"]
        for idx in range(min(len(underlyings), MAX_UNDERLYINGS)):
            menu_options.append(f"underlying_{idx + 1}")
            placeholders[f"underlying_{idx + 1}"] = self._get_entity_name(underlyings[idx])
            placeholders[f"underlying_{idx + 1}_details"] = self._get_underlying_details(translations, idx)
        if len(underlyings) < MAX_UNDERLYINGS:
            menu_options.append("underlying_add")
        if not self._wizard_active:
            menu_options.append("menu")
        elif not self._get_underlying_missing_items(self._infos):
            # In the wizard, the user continues when all the devices are complete
            menu_options.append("underlying_continue")

        return self.async_show_menu(step_id="type", menu_options=menu_options, description_placeholders=placeholders)

    async def async_step_underlying_common(self, user_input: dict | None = None) -> FlowResult:
        """Handle the settings which are common to all the devices"""
        _LOGGER.debug("Into ConfigFlow.async_step_underlying_common user_input=%s", user_input)

        thermostat_type = self._infos[CONF_THERMOSTAT_TYPE]
        if thermostat_type == CONF_THERMOSTAT_VALVE:
            values = user_input if user_input is not None else self._infos
            if CONF_OPENING_THRESHOLD_DEGREE in values:
                regulation_threshold = values.get(CONF_AUTO_REGULATION_DTEMP, 0)
                values[CONF_OPENING_THRESHOLD_DEGREE] = max(values[CONF_OPENING_THRESHOLD_DEGREE], regulation_threshold)

        if thermostat_type == CONF_THERMOSTAT_CLIMATE and user_input is not None and not self.is_valve_regulation_selected(user_input):
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

        if thermostat_type == CONF_THERMOSTAT_SWITCH:
            schema = build_step_thermostat_switch_schema()
        elif thermostat_type == CONF_THERMOSTAT_VALVE:
            schema = build_step_thermostat_valve_schema()
        else:
            schema = STEP_THERMOSTAT_CLIMATE

        return await self.generic_step("underlying_common", schema, user_input, self._after_underlying_common)

    async def _after_underlying_common(self) -> FlowResult:
        """After the common settings of an over_climate, the valve regulation and synchronization settings are asked if needed"""
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CLIMATE and (
            self.is_valve_regulation_selected(self._infos) or self.is_sync_device_internal_temp_selected(self._infos)
        ):
            return await self.async_step_underlying_common_extra()
        return await self.async_step_type()

    async def async_step_underlying_common_extra(self, user_input: dict | None = None) -> FlowResult:
        """Handle the common settings of the valve regulation and of the synchronization of the internal temperature"""
        _LOGGER.debug("Into ConfigFlow.async_step_underlying_common_extra user_input=%s", user_input)

        valve_regulation = self.is_valve_regulation_selected(self._infos)
        schema = build_step_underlying_extra_schema(valve_regulation, self.is_sync_device_internal_temp_selected(self._infos))
        if not schema.schema:
            return await self.async_step_type()

        values = user_input if user_input is not None else self._infos
        if CONF_OPENING_THRESHOLD_DEGREE in values:
            regulation_threshold = self._infos.get(CONF_AUTO_REGULATION_DTEMP, 0)
            values[CONF_OPENING_THRESHOLD_DEGREE] = max(values[CONF_OPENING_THRESHOLD_DEGREE], regulation_threshold)

        return await self.generic_step("underlying_common_extra", schema, user_input, self.async_step_type)

    async def async_step_underlying_add(self, user_input: dict | None = None) -> FlowResult:
        """Handle the first screen of the add of a device: the choice of the entity"""
        _LOGGER.debug("Into ConfigFlow.async_step_underlying_add user_input=%s", user_input)

        errors = {}
        if user_input is not None:
            entity_id = user_input[CONF_UNDERLYING_ENTITY]
            if self.hass.states.get(entity_id) is None:
                _LOGGER.error("Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration", entity_id)
                errors[CONF_UNDERLYING_ENTITY] = "unknown_entity"
            elif entity_id in self._infos.get(CONF_UNDERLYING_LIST, []):
                errors[CONF_UNDERLYING_ENTITY] = "underlying_already_added"
            else:
                self._underlying_idx = None
                self._underlying_entity = entity_id
                if self._get_underlying_form_fields(entity_id):
                    return await self.async_step_underlying()
                # nothing else to ask for this device
                self._infos[CONF_UNDERLYING_LIST] = list(self._infos.get(CONF_UNDERLYING_LIST, [])) + [entity_id]
                self._underlying_entity = None
                return await self.async_step_type()

        return self.async_show_form(
            step_id="underlying_add",
            data_schema=add_suggested_values_to_schema(build_step_underlying_add_schema(self._infos[CONF_THERMOSTAT_TYPE]), user_input or {}),
            errors=errors,
            description_placeholders=await self._async_get_placeholders("type"),
        )

    async def async_step_underlying(self, user_input: dict | None = None) -> FlowResult:
        """Handle the settings of one device (a new one or the one at self._underlying_idx)"""
        _LOGGER.debug("Into ConfigFlow.async_step_underlying idx=%s user_input=%s", self._underlying_idx, user_input)

        underlyings = self._infos.get(CONF_UNDERLYING_LIST, [])
        idx = self._underlying_idx
        if idx is not None and idx < len(underlyings):
            entity_id = underlyings[idx]
        elif idx is None and self._underlying_entity is not None:
            entity_id = self._underlying_entity
        else:
            return await self.async_step_type()

        errors = {}
        if user_input is not None:
            # flatten the section of the custom commands
            user_input = {key: value for key, value in user_input.items() if key != CONF_VSWITCH_COMMANDS_SECTION} | (user_input.get(CONF_VSWITCH_COMMANDS_SECTION) or {})
            if idx is not None and user_input.get(CONF_REMOVE_UNDERLYING):
                self._remove_underlying(idx)
                self._underlying_idx = None
                return await self.async_step_type()

            errors = self._validate_underlying_input(entity_id, idx, user_input)
            if not errors:
                new_entity_id = user_input.get(CONF_REPLACE_ENTITY)
                if idx is None:
                    underlyings = list(underlyings) + [entity_id]
                    self._infos[CONF_UNDERLYING_LIST] = underlyings
                    idx = len(underlyings) - 1
                elif new_entity_id and new_entity_id != entity_id:
                    # the entity is replaced
                    underlyings = list(underlyings)
                    underlyings[idx] = new_entity_id
                    self._infos[CONF_UNDERLYING_LIST] = underlyings
                    if self._is_commands_required(new_entity_id) != self._is_commands_required(entity_id):
                        # the fields of the form are not the same for this kind of entity: ask again
                        return await self.async_step_underlying()
                    entity_id = new_entity_id
                self._set_underlying_values(idx, user_input)
                self._underlying_idx = None
                self._underlying_entity = None
                return await self.async_step_type()

        schema = self._build_underlying_schema(entity_id, idx)
        if user_input is not None:
            # keep what the user entered
            schema = add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="underlying",
            data_schema=schema,
            errors=errors,
            description_placeholders=await self._async_get_underlying_placeholders("type", entity_id),
        )

    async def async_step_underlying_continue(self, user_input: dict | None = None) -> FlowResult:
        """Go to the next step of the creation wizard when the underlyings are configured"""
        return await self._next_step()

    async def _async_open_underlying(self, idx: int) -> FlowResult:
        """Open the settings of the device at idx. Called by the generated steps async_step_underlying_<n>"""
        if idx >= len(self._infos.get(CONF_UNDERLYING_LIST, [])):
            return await self.async_step_type()
        self._underlying_idx = idx
        self._underlying_entity = None
        return await self.async_step_underlying()

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
            self._next_step,
        )

    async def async_step_auto_start_stop(self, user_input: dict | None = None) -> FlowResult:
        """ Handle the Auto start stop step"""
        _LOGGER.debug("Into ConfigFlow.async_step_auto_start_stop user_input=%s", user_input)

        schema = STEP_AUTO_START_STOP
        self._infos[COMES_FROM] = None
        next_step = self._next_step

        return await self.generic_step("auto_start_stop", schema, user_input, next_step)

    async def async_step_humidity(self, user_input: dict | None = None) -> FlowResult:
        """Handle the optional external humidity sensor configuration."""
        _LOGGER.debug("Into ConfigFlow.async_step_humidity user_input=%s", user_input)

        if user_input is not None and not user_input.get(CONF_USE_HUMIDITY_FEATURE):
            user_input = user_input.copy()
            user_input.pop(CONF_HUMIDITY_SENSOR, None)

        candidates = find_humidity_sensor_candidates(self.hass, self._infos.get(CONF_TEMP_SENSOR))
        detected_sensor = candidates[0] if candidates else None
        self._placeholders["humidity_detected"] = detected_sensor or "none"
        schema = STEP_HUMIDITY_DATA_SCHEMA
        if user_input is None and self._infos.get(CONF_HUMIDITY_SENSOR) is None:
            schema = add_suggested_values_to_schema(schema, {CONF_HUMIDITY_SENSOR: detected_sensor})

        return await self.generic_step("humidity", schema, user_input, self._next_step)

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_tpi user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_TPI_DATA_SCHEMA_CENTRAL
        else:
            schema = STEP_TPI_DATA_SCHEMA

            if user_input:
                if user_input.get(CONF_USE_TPI_CENTRAL_CONFIG, False) is False:
                    if self._infos.get(COMES_FROM) == "async_step_spec_tpi":
                        schema = STEP_CENTRAL_TPI_DATA_SCHEMA
                        del self._infos[COMES_FROM]
                        if user_input.get(CONF_AUTO_TPI_MODE) is True:
                            next_step = self.async_step_auto_tpi_configuration
                    else:
                        next_step = self.async_step_spec_tpi
                elif user_input.get(CONF_AUTO_TPI_MODE) is True:
                    next_step = self.async_step_auto_tpi_configuration

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_spec_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific TPI flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_tpi user_input=%s", user_input)

        schema = STEP_CENTRAL_TPI_DATA_SCHEMA
        self._infos[COMES_FROM] = "async_step_spec_tpi"
        next_step = self._next_step

        if user_input and user_input.get(CONF_AUTO_TPI_MODE) is True:
            next_step = self.async_step_auto_tpi_configuration

        return await self.generic_step("tpi", schema, user_input, next_step)

    async def async_step_auto_tpi_configuration(self, user_input: dict | None = None) -> FlowResult:
        """Handle the Auto TPI configuration step"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_auto_tpi_configuration user_input=%s", user_input
        )
        schema = STEP_AUTO_TPI_CONFIGURATION_SCHEMA

        # Logic for next step
        next_step = self._step_auto_tpi_after_configuration

        # Update placeholders with unit
        self._placeholders["temperature_unit"] = self.hass.config.units.temperature_unit
        self._placeholders["unit"] = self.hass.config.units.temperature_unit

        if user_input is not None:
            new_type = user_input.get(CONF_AUTO_TPI_LEARNING_TYPE)
            old_type = self._infos.get(CONF_AUTO_TPI_LEARNING_TYPE)
            if new_type != old_type:
                self._learning_type_changed = True

        return await self.generic_step("auto_tpi_configuration", schema, user_input, next_step)

    async def _step_auto_tpi_after_configuration(self, user_input: dict | None = None) -> FlowResult:
        """Logic after step 1"""
        # Apply defaults if learning type changed or method not set
        if getattr(self, "_learning_type_changed", False) or self._infos.get(CONF_AUTO_TPI_CALCULATION_METHOD) is None:
            self._apply_learning_type_defaults()
            self._learning_type_changed = False

        if self._infos.get(CONF_AUTO_TPI_ENABLE_ADVANCED_SETTINGS, False):
            # Direct jump to method step
            if self._infos.get(CONF_AUTO_TPI_CALCULATION_METHOD) == AUTO_TPI_METHOD_EMA:
                return await self.async_step_auto_tpi_ema_settings()
            else:
                return await self.async_step_auto_tpi_avg_settings()
        else:
            return await self._next_step()

    def _apply_learning_type_defaults(self):
        """Apply defaults based on learning type"""
        learning_type = self._infos.get(CONF_AUTO_TPI_LEARNING_TYPE)

        if learning_type == AUTO_TPI_LEARNING_TYPE_DISCOVERY:
            # Discovery -> Weighted Average, Weight 1
            self._infos[CONF_AUTO_TPI_CALCULATION_METHOD] = AUTO_TPI_METHOD_AVG
            self._infos[CONF_AUTO_TPI_AVG_INITIAL_WEIGHT] = 1
        elif learning_type == AUTO_TPI_LEARNING_TYPE_FINE_TUNING:
            # Fine Tuning -> EMA, Alpha 0.08, Decay 0.12
            self._infos[CONF_AUTO_TPI_CALCULATION_METHOD] = AUTO_TPI_METHOD_EMA
            self._infos[CONF_AUTO_TPI_EMA_ALPHA] = 0.08
            self._infos[CONF_AUTO_TPI_EMA_DECAY_RATE] = 0.12

    async def async_step_auto_tpi_avg_settings(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the Auto TPI average settings step"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_auto_tpi_avg_settings user_input=%s", user_input
        )
        schema = STEP_AUTO_TPI_AVG_SETTINGS_SCHEMA
        next_step = self._next_step

        # Update placeholders with unit
        self._placeholders["temperature_unit"] = self.hass.config.units.temperature_unit
        self._placeholders["unit"] = self.hass.config.units.temperature_unit

        return await self.generic_step("auto_tpi_avg_settings", schema, user_input, next_step)

    async def async_step_auto_tpi_ema_settings(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the Auto TPI EMA settings step"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_auto_tpi_ema_settings user_input=%s", user_input
        )
        schema = STEP_AUTO_TPI_EMA_SETTINGS_SCHEMA
        next_step = self._next_step
        return await self.generic_step("auto_tpi_ema_settings", schema, user_input, next_step)

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presets user_input=%s", user_input)

        next_step = self._next_step  # advanced
        schema = STEP_PRESETS_DATA_SCHEMA

        # In Central config -> display the next step immedialty
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            # Call directly the next step, we have nothing to display here
            return await self.async_step_window()  #  = self.async_step_window

        return await self.generic_step("presets", schema, user_input, next_step)

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_window user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
        else:
            schema = STEP_WINDOW_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_WINDOW_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_window"
                ):
                    if self._infos.get(CONF_WINDOW_SENSOR) is not None:
                        schema = STEP_CENTRAL_WINDOW_WO_AUTO_DATA_SCHEMA
                    else:
                        schema = STEP_CENTRAL_WINDOW_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
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

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
        else:
            schema = STEP_MOTION_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_MOTION_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_motion"
                ):
                    schema = STEP_CENTRAL_MOTION_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
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

        next_step = self._next_step

        # This will return to async_step_main (to keep the "main" step)
        return await self.generic_step("motion", schema, user_input, next_step)

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_power user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_POWER_DATA_SCHEMA
        else:
            schema = STEP_POWER_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_POWER_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_power"
                ):
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

        next_step = self._next_step

        # This will return to async_step_power (to keep the "power" step)
        return await self.generic_step("power", schema, user_input, next_step)

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presence user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
        else:
            schema = STEP_PRESENCE_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_presence"
                ):
                    schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_presence

        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_spec_presence(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific power flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_presence user_input=%s", user_input
        )

        schema = STEP_CENTRAL_PRESENCE_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_presence"

        next_step = self._next_step

        # This will return to async_step_power (to keep the "power" step)
        return await self.generic_step("presence", schema, user_input, next_step)

    async def async_step_advanced(self, user_input: dict | None = None) -> FlowResult:
        """Handle the advanced parameter flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_advanced user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
        else:
            schema = STEP_ADVANCED_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_ADVANCED_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_advanced"
                ):
                    schema = STEP_CENTRAL_ADVANCED_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
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

    async def async_step_lock(self, user_input: dict | None = None) -> FlowResult:
        """Handle the lock flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_lock user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_LOCK_DATA_SCHEMA
        else:
            schema = STEP_LOCK_DATA_SCHEMA

            if (
                user_input
                and user_input.get(CONF_USE_LOCK_CENTRAL_CONFIG, False) is False
            ):
                if (
                    user_input
                    and self._infos.get(COMES_FROM) == "async_step_spec_lock"
                ):
                    schema = STEP_CENTRAL_LOCK_DATA_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_lock

        return await self.generic_step("lock", schema, user_input, next_step)

    async def async_step_spec_lock(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the specific lock flow steps"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_spec_lock user_input=%s", user_input
        )

        schema = STEP_CENTRAL_LOCK_DATA_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_lock"

        next_step = self._next_step

        return await self.generic_step("lock", schema, user_input, next_step)

    async def async_step_heating_failure_detection(self, user_input: dict | None = None) -> FlowResult:
        """Handle the heating failure detection flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_heating_failure_detection user_input=%s", user_input)

        next_step = self._next_step
        if self._infos[CONF_THERMOSTAT_TYPE] == CONF_THERMOSTAT_CENTRAL_CONFIG:
            schema = STEP_CENTRAL_HEATING_FAILURE_DETECTION_SCHEMA
        else:
            schema = STEP_HEATING_FAILURE_DETECTION_SCHEMA

            if user_input and user_input.get(CONF_USE_HEATING_FAILURE_DETECTION_CENTRAL_CONFIG, False) is False:
                if user_input and self._infos.get(COMES_FROM) == "async_step_spec_heating_failure_detection":
                    schema = STEP_CENTRAL_HEATING_FAILURE_DETECTION_SCHEMA
                    del self._infos[COMES_FROM]
                else:
                    next_step = self.async_step_spec_heating_failure_detection

        return await self.generic_step("heating_failure_detection", schema, user_input, next_step)

    async def async_step_spec_heating_failure_detection(self, user_input: dict | None = None) -> FlowResult:
        """Handle the specific heating failure detection flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_spec_heating_failure_detection user_input=%s", user_input)

        # here we reuse the central schema because it is the same for non central config
        schema = STEP_CENTRAL_HEATING_FAILURE_DETECTION_SCHEMA

        self._infos[COMES_FROM] = "async_step_spec_heating_failure_detection"

        next_step = self.async_step_heating_failure_detection

        return await self.generic_step("heating_failure_detection", schema, user_input, next_step)

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


def _make_underlying_step(slot: int):
    """Build the step which opens the settings of the device at the position slot of the underlyings menu"""

    async def _step(self, user_input: dict | None = None) -> FlowResult:  # pylint: disable=unused-argument
        return await self._async_open_underlying(slot - 1)  # pylint: disable=protected-access

    _step.__name__ = f"async_step_underlying_{slot}"
    return _step


# Each option of a menu needs a step: one step is generated for each device which can be displayed
for _slot in range(1, MAX_UNDERLYINGS + 1):
    setattr(VersatileThermostatBaseConfigFlow, f"async_step_underlying_{_slot}", _make_underlying_step(_slot))


class VersatileThermostatConfigFlow(  # pylint: disable=abstract-method
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
        # #713 doesn't work as explained here:https://developers.home-assistant.io/blog/2024/11/12/options-flow
        #  should be - return VersatileThermostatOptionsFlowHandler() but hass is not initialized
        return VersatileThermostatOptionsFlowHandler(config_entry)

    async def _start_wizard(self) -> FlowResult:
        """The type of VTherm is chosen: the creation wizard starts and leads the user through the screens to fill"""
        self._wizard_active = True
        return await self._next_step()

    async def async_step_finalize(self, _):
        """Finalization of the ConfigEntry creation"""
        _LOGGER.debug("ConfigFlow.async_finalize")
        await super().async_step_finalize(_)

        return self.async_create_entry(title=self._infos[CONF_NAME], data=self._infos)


class VersatileThermostatOptionsFlowHandler(
    VersatileThermostatBaseConfigFlow, OptionsFlow
):
    """Handle options flow for Versatile Thermostat integration."""

    TRANSLATION_CATEGORY = "options"

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
            PLUGINS_LINK_PLACEHOLDER: PLUGINS_LINK,
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
