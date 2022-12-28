"""Config flow for Versatile Thermostat integration."""
from __future__ import annotations
from homeassistant.core import callback

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_HEATER,
    CONF_TEMP_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_MOTION_SENSOR,
    CONF_DEVICE_POWER,
    ALL_CONF,
    CONF_PRESETS,
)

# from .climate import VersatileThermostat

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HEATER): cv.string,
        vol.Required(CONF_TEMP_SENSOR): cv.string,
        vol.Optional(CONF_POWER_SENSOR): cv.string,
        vol.Optional(CONF_MAX_POWER_SENSOR): cv.string,
        vol.Optional(CONF_WINDOW_SENSOR): cv.string,
        vol.Optional(CONF_MOTION_SENSOR): cv.string,
        vol.Optional(CONF_DEVICE_POWER): vol.Coerce(float),
    }
).extend(
    {vol.Optional(v, default=17): vol.Coerce(float) for (k, v) in CONF_PRESETS.items()}
)


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


# class PlaceholderHub:
#    """Placeholder class to make tests pass.
#
#    TODO Remove this placeholder class and replace with things from your PyPI package.
#    """
#
#    def __init__(self, name: str, heater_entity_id: str) -> None:
#        """Initialize."""
#        self.name = name
#        self.heater_entity_id = heater_entity_id
#
#    # async def authenticate(self, username: str, password: str) -> bool:
#    #    """Test if we can authenticate with the host."""
#    #    return True


async def validate_input(
    hass: HomeAssistant, data: dict[str, str, str, Any]
) -> dict[str]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    # hub = PlaceholderHub(data["name"], data["heater_id"])

    # if not await hub.authenticate(data["username"], data["password"]):
    #    raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data["name"]}


class VersatileThermostatConfigFlow(HAConfigFlow, domain=DOMAIN):
    """Handle a config flow for Versatile Thermostat."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get options flow for this handler."""
        return VersatileThermostatOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class VersatileThermostatOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Versatile Thermostat integration."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        _LOGGER.debug(
            "CTOR VersatileThermostatOptionsFlowHandler config_entry.data: %s, entry_id: %s",
            config_entry.data,
            config_entry.entry_id,
        )

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        _LOGGER.debug(
            "Into VersatileThermostatOptionsFlowHandler.async_step_init user_input =%s, config_entry.data=%s",
            user_input,
            self.config_entry.data,
        )
        if user_input is not None:
            _LOGGER.debug("We receive the new values: %s", user_input)
            data = dict(self.config_entry.data)
            for conf in ALL_CONF:
                data[conf] = user_input.get(conf)
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title=None, data=None)
        else:
            defaults = self.config_entry.data.copy()
            defaults.update(user_input or {})
            user_data_schema = schema_defaults(STEP_USER_DATA_SCHEMA, **defaults)

            return self.async_show_form(
                step_id="init",
                data_schema=user_data_schema,
            )
