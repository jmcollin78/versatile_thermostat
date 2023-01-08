"""Config flow for Versatile Thermostat integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    OptionsFlow,
)
from homeassistant.data_entry_flow import FlowHandler
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_HEATER,
    CONF_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_WINDOW_DELAY,
    CONF_MOTION_SENSOR,
    CONF_MOTION_DELAY,
    CONF_MOTION_PRESET,
    CONF_NO_MOTION_PRESET,
    CONF_DEVICE_POWER,
    CONF_CYCLE_MIN,
    CONF_PRESETS,
    CONF_PRESETS_SELECTIONABLE,
    CONF_PROP_FUNCTION,
    CONF_PROP_BIAS,
    CONF_TPI_COEF_T,
    CONF_TPI_COEF_C,
    CONF_PRESENCE_SENSOR,
    CONF_NO_PRESENCE_PRESET,
    CONF_NO_PRESENCE_TEMP_OFFSET,
    PROPORTIONAL_FUNCTION_ATAN,
    PROPORTIONAL_FUNCTION_LINEAR,
    PROPORTIONAL_FUNCTION_TPI,
)

# from .climate import VersatileThermostat

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HEATER): cv.string,
        vol.Required(CONF_TEMP_SENSOR): cv.string,
        vol.Required(CONF_CYCLE_MIN, default=5): cv.positive_int,
        vol.Required(CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_LINEAR): vol.In(
            [
                PROPORTIONAL_FUNCTION_TPI,
                PROPORTIONAL_FUNCTION_LINEAR,
                PROPORTIONAL_FUNCTION_ATAN,
            ]
        ),
    }
)
# USER_DATA_CONF = [
#     CONF_NAME,
#     CONF_HEATER,
#     CONF_TEMP_SENSOR,
#     CONF_EXTERNAL_TEMP_SENSOR,
#     CONF_CYCLE_MIN,
#     CONF_PROP_FUNCTION,
# ]

STEP_P_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROP_BIAS, default=0.25): vol.Coerce(float),
    }
)
# P_DATA_CONF = [
#     CONF_PROP_BIAS,
# ]

STEP_TPI_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EXTERNAL_TEMP_SENSOR): cv.string,
        vol.Required(CONF_TPI_COEF_C, default=0.6): vol.Coerce(float),
        vol.Required(CONF_TPI_COEF_T, default=0.01): vol.Coerce(float),
    }
)
# TPI_DATA_CONF = [
#     CONF_EXTERNAL_TEMP_SENSOR,
#     CONF_TPI_COEF_C,
#     CONF_TPI_COEF_T,
# ]

STEP_PRESETS_DATA_SCHEMA = vol.Schema(
    {vol.Optional(v, default=17): vol.Coerce(float) for (k, v) in CONF_PRESETS.items()}
)
# PRESETS_DATA_CONF = [v for (_, v) in CONF_PRESETS.items()]

STEP_WINDOW_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_WINDOW_SENSOR): cv.string,
        vol.Optional(CONF_WINDOW_DELAY, default=30): cv.positive_int,
    }
)
# WINDOW_DATA_CONF = [CONF_WINDOW_SENSOR, CONF_WINDOW_DELAY]

STEP_MOTION_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MOTION_SENSOR): cv.string,
        vol.Optional(CONF_MOTION_DELAY, default=30): cv.positive_int,
        vol.Optional(CONF_MOTION_PRESET, default="comfort"): vol.In(
            CONF_PRESETS_SELECTIONABLE
        ),
        vol.Optional(CONF_NO_MOTION_PRESET, default="eco"): vol.In(
            CONF_PRESETS_SELECTIONABLE
        ),
    }
)
# MOTION_DATA_CONF = [
#    CONF_MOTION_SENSOR,
#    CONF_MOTION_DELAY,
#    CONF_MOTION_PRESET,
#    CONF_NO_MOTION_PRESET,
# ]

STEP_POWER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_POWER_SENSOR): cv.string,
        vol.Optional(CONF_MAX_POWER_SENSOR): cv.string,
        vol.Optional(CONF_DEVICE_POWER): vol.Coerce(float),
    }
)
# POWER_DATA_CONF = [CONF_POWER_SENSOR, CONF_MAX_POWER_SENSOR, CONF_DEVICE_POWER]

STEP_PRESENCE_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PRESENCE_SENSOR): cv.string,
        vol.Optional(CONF_NO_PRESENCE_PRESET): vol.In(CONF_PRESETS_SELECTIONABLE),
        vol.Optional(CONF_NO_PRESENCE_TEMP_OFFSET): vol.Coerce(float),
    }
)
# PRESENCE_DATA_CONF = [CONF_PRESENCE_SENSOR, CONF_NO_PRESENCE_PRESET, CONF_NO_PRESENCE_TEMP_OFFSET]


def schema_defaults(schema, **defaults):
    """Create a new schema with default values filled in."""
    copy = schema.extend({})
    for field, field_type in copy.schema.items():
        if isinstance(field_type, vol.In):
            value = None
            # for dps in dps_list or []:
            #    if dps.startswith(f"{defaults.get(field)} "):
            #        value = dps
            #        break

            if value in field_type.container:
                field.default = vol.default_factory(value)
                continue

        if field.schema in defaults:
            field.default = vol.default_factory(defaults[field])
    return copy


class VersatileThermostatBaseConfigFlow(FlowHandler):
    """The base Config flow class. Used to put some code in commons."""

    VERSION = 1
    _infos: dict

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos = infos

    async def validate_input(self, data: dict) -> dict[str]:
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
        ]:
            d = data.get(conf, None)  # pylint: disable=invalid-name
            if d is not None and self.hass.states.get(d) is None:
                _LOGGER.error(
                    "Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration",  # pylint: disable=line-too-long
                    d,
                )
                raise UnknownEntity(conf)

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
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self._infos.update(user_input)
                _LOGGER.debug("_info is now: %s", self._infos)
                return await next_step_function()

        ds = schema_defaults(data_schema, **defaults)  # pylint: disable=invalid-name

        return self.async_show_form(step_id=step_id, data_schema=ds, errors=errors)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        async def choose_next_step():
            """Choose next configuration flow"""
            _LOGGER.debug("function is %s", self._infos.get(CONF_PROP_FUNCTION, None))
            if self._infos.get(CONF_PROP_FUNCTION, None) == PROPORTIONAL_FUNCTION_TPI:
                return await self.async_step_tpi()
            else:
                return await self.async_step_p()

        return await self.generic_step(
            "user", STEP_USER_DATA_SCHEMA, user_input, choose_next_step
        )

    async def async_step_p(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_p user_input=%s", user_input)

        return await self.generic_step(
            "p", STEP_P_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_tpi user_input=%s", user_input)

        return await self.generic_step(
            "tpi", STEP_TPI_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presets user_input=%s", user_input)

        return await self.generic_step(
            "presets", STEP_PRESETS_DATA_SCHEMA, user_input, self.async_step_window
        )

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_window user_input=%s", user_input)

        return await self.generic_step(
            "window", STEP_WINDOW_DATA_SCHEMA, user_input, self.async_step_motion
        )

    async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window and motion sensor flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_motion user_input=%s", user_input)

        return await self.generic_step(
            "motion", STEP_MOTION_DATA_SCHEMA, user_input, self.async_step_power
        )

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_power user_input=%s", user_input)

        return await self.generic_step(
            "power",
            STEP_POWER_DATA_SCHEMA,
            user_input,
            self.async_step_presence,
        )

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug("Into ConfigFlow.async_step_presence user_input=%s", user_input)

        return await self.generic_step(
            "presence",
            STEP_PRESENCE_DATA_SCHEMA,
            user_input,
            self.async_finalize,  # pylint: disable=no-member
        )


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
        _LOGGER.debug("CTOR ConfigFlow.async_finalize")
        return self.async_create_entry(title=self._infos[CONF_NAME], data=self._infos)


class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""


class VersatileThermostatOptionsFlowHandler(
    VersatileThermostatBaseConfigFlow, OptionsFlow
):
    """Handle options flow for Versatile Thermostat integration."""

    def __init__(self, config_entry: ConfigEntry):
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

        async def choose_next_step():
            """Choose next configuration flow"""
            _LOGGER.debug("function is %s", self._infos.get(CONF_PROP_FUNCTION, None))
            if self._infos.get(CONF_PROP_FUNCTION, None) == PROPORTIONAL_FUNCTION_TPI:
                return await self.async_step_tpi()
            else:
                return await self.async_step_p()

        return await self.generic_step(
            "user", STEP_USER_DATA_SCHEMA, user_input, choose_next_step
        )

    async def async_step_p(self, user_input: dict | None = None) -> FlowResult:
        """Handle the p flow steps"""
        _LOGGER.debug("Into OptionsFlowHandler.async_step_p user_input=%s", user_input)

        return await self.generic_step(
            "p", STEP_P_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_tpi(self, user_input: dict | None = None) -> FlowResult:
        """Handle the tpi flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_tpi user_input=%s", user_input
        )

        return await self.generic_step(
            "tpi", STEP_TPI_DATA_SCHEMA, user_input, self.async_step_presets
        )

    async def async_step_presets(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presets flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_presets user_input=%s", user_input
        )

        return await self.generic_step(
            "presets", STEP_PRESETS_DATA_SCHEMA, user_input, self.async_step_window
        )

    async def async_step_window(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window  sensor flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_window user_input=%s", user_input
        )

        return await self.generic_step(
            "window", STEP_WINDOW_DATA_SCHEMA, user_input, self.async_step_motion
        )

    async def async_step_motion(self, user_input: dict | None = None) -> FlowResult:
        """Handle the window and motion sensor flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_motion user_input=%s", user_input
        )

        return await self.generic_step(
            "motion", STEP_MOTION_DATA_SCHEMA, user_input, self.async_step_power
        )

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the power management flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_power user_input=%s", user_input
        )

        return await self.generic_step(
            "power",
            STEP_POWER_DATA_SCHEMA,
            user_input,
            self.async_step_presence,  # pylint: disable=no-member
        )

    async def async_step_presence(self, user_input: dict | None = None) -> FlowResult:
        """Handle the presence management flow steps"""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_presence user_input=%s", user_input
        )

        return await self.generic_step(
            "presence",
            STEP_PRESENCE_DATA_SCHEMA,
            user_input,
            self.async_finalize,  # pylint: disable=no-member
        )

    async def async_finalize(self):
        """Finalization of the ConfigEntry creation"""
        _LOGGER.debug(
            "CTOR ConfigFlow.async_finalize - updating entry with: %s", self._infos
        )
        self.hass.config_entries.async_update_entry(self.config_entry, data=self._infos)
        return self.async_create_entry(title=None, data=None)
