""" All the schemas for ConfigFlow validation"""

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.input_boolean import (
    DOMAIN as INPUT_BOOLEAN_DOMAIN,
)

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_number import (
    DOMAIN as INPUT_NUMBER_DOMAIN,
)

from homeassistant.components.person import DOMAIN as PERSON_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN


from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

STEP_USER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(
            CONF_THERMOSTAT_TYPE, default=CONF_THERMOSTAT_SWITCH
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_THERMOSTAT_TYPES,
                translation_key="thermostat_type",
                mode="list",
            )
        )
    }
)

STEP_MAIN_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_CYCLE_MIN, default=5): cv.positive_int,
        vol.Optional(CONF_DEVICE_POWER, default="1"): vol.Coerce(float),
        vol.Optional(CONF_USE_CENTRAL_MODE, default=True): cv.boolean,
        vol.Required(CONF_USE_MAIN_CENTRAL_CONFIG, default=True): cv.boolean,
        vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
        vol.Required(CONF_USED_BY_CENTRAL_BOILER, default=False): cv.boolean,
    }
)

STEP_CENTRAL_MAIN_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_EXTERNAL_TEMP_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_TEMP_MIN, default=7): vol.Coerce(float),
        vol.Required(CONF_TEMP_MAX, default=35): vol.Coerce(float),
        vol.Required(CONF_STEP_TEMPERATURE, default=0.1): vol.Coerce(float),
        vol.Required(CONF_ADD_CENTRAL_BOILER_CONTROL, default=False): cv.boolean,
    }
)

STEP_CENTRAL_SPEC_MAIN_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_EXTERNAL_TEMP_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_TEMP_MIN, default=7): vol.Coerce(float),
        vol.Required(CONF_TEMP_MAX, default=35): vol.Coerce(float),
        vol.Required(CONF_STEP_TEMPERATURE, default=0.1): vol.Coerce(float),
    }
)

STEP_CENTRAL_BOILER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CENTRAL_BOILER_ACTIVATION_SRV, default=""): str,
        vol.Optional(CONF_CENTRAL_BOILER_DEACTIVATION_SRV, default=""): str,
    }
)

STEP_THERMOSTAT_SWITCH = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_HEATER): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]),
        ),
        vol.Optional(CONF_HEATER_2): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]),
        ),
        vol.Optional(CONF_HEATER_3): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]),
        ),
        vol.Optional(CONF_HEATER_4): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN]),
        ),
        vol.Optional(CONF_HEATER_KEEP_ALIVE): cv.positive_int,
        vol.Required(CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI): vol.In(
            [
                PROPORTIONAL_FUNCTION_TPI,
            ]
        ),
        vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
        vol.Optional(CONF_INVERSE_SWITCH, default=False): cv.boolean,
    }
)

STEP_THERMOSTAT_CLIMATE = vol.Schema(  # pylint: disable=invalid-name
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
                mode="dropdown",
            )
        ),
        vol.Optional(CONF_AUTO_REGULATION_DTEMP, default=0.5): vol.Coerce(float),
        vol.Optional(CONF_AUTO_REGULATION_PERIOD_MIN, default=5): cv.positive_int,
        vol.Optional(
            CONF_AUTO_FAN_MODE, default=CONF_AUTO_FAN_HIGH
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_AUTO_FAN_MODES,
                translation_key="auto_fan_mode",
                mode="dropdown",
            )
        ),
        vol.Optional(CONF_AUTO_REGULATION_USE_INTERNAL_TEMP, default=False): cv.boolean,
    }
)

STEP_THERMOSTAT_VALVE = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_VALVE): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_VALVE_2): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_VALVE_3): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_VALVE_4): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI): vol.In(
            [
                PROPORTIONAL_FUNCTION_TPI,
            ]
        ),
        vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
        vol.Optional(CONF_AUTO_REGULATION_DTEMP, default=10): vol.Coerce(float),
        vol.Optional(CONF_AUTO_REGULATION_PERIOD_MIN, default=5): cv.positive_int,
    }
)

STEP_TPI_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_TPI_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_TPI_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_TPI_COEF_INT, default=0.6): vol.Coerce(float),
        vol.Required(CONF_TPI_COEF_EXT, default=0.01): vol.Coerce(float),
    }
)

STEP_PRESETS_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_PRESETS_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_PRESETS_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {vol.Optional(v, default=0): vol.Coerce(float) for (k, v) in CONF_PRESETS.items()}
)

STEP_CENTRAL_PRESETS_WITH_AC_DATA_SCHEMA = (
    vol.Schema(  # pylint: disable=invalid-name  # pylint: disable=invalid-name
        {
            vol.Optional(v, default=0): vol.Coerce(float)
            for (k, v) in CONF_PRESETS_WITH_AC.items()
        }
    )
)

STEP_WINDOW_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_WINDOW_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN]
            ),
        ),
        vol.Required(CONF_USE_WINDOW_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_WINDOW_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_WINDOW_DELAY, default=30): cv.positive_int,
        vol.Optional(CONF_WINDOW_AUTO_OPEN_THRESHOLD, default=3): vol.Coerce(float),
        vol.Optional(CONF_WINDOW_AUTO_CLOSE_THRESHOLD, default=0): vol.Coerce(float),
        vol.Optional(CONF_WINDOW_AUTO_MAX_DURATION, default=30): cv.positive_int,
        vol.Optional(
            CONF_WINDOW_ACTION, default=CONF_WINDOW_TURN_OFF
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_WINDOW_ACTIONS,
                translation_key="window_action",
                mode="dropdown",
            )
        ),
    }
)

STEP_CENTRAL_WINDOW_WO_AUTO_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_WINDOW_DELAY, default=30): cv.positive_int,
        vol.Optional(
            CONF_WINDOW_ACTION, default=CONF_WINDOW_TURN_OFF
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_WINDOW_ACTIONS,
                translation_key="window_action",
                mode="dropdown",
            )
        ),
    }
)

STEP_MOTION_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_MOTION_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN]
            ),
        ),
        vol.Required(CONF_USE_MOTION_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_MOTION_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_MOTION_DELAY, default=30): cv.positive_int,
        vol.Optional(CONF_MOTION_OFF_DELAY, default=300): cv.positive_int,
        vol.Optional(CONF_MOTION_PRESET, default="comfort"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_PRESETS_SELECTIONABLE,
                translation_key="presets",
                mode="dropdown",
            )
        ),
        vol.Optional(CONF_NO_MOTION_PRESET, default="eco"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_PRESETS_SELECTIONABLE,
                translation_key="presets",
                mode="dropdown",
            )
        ),
    }
)

STEP_CENTRAL_POWER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_POWER_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_MAX_POWER_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_PRESET_POWER, default="13"): vol.Coerce(float),
    }
)

STEP_POWER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_POWER_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_PRESENCE_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(v, default=17): vol.Coerce(float)
        for (k, v) in CONF_PRESETS_AWAY.items()
    }
)

STEP_CENTRAL_PRESENCE_WITH_AC_DATA_SCHEMA = {  # pylint: disable=invalid-name
    vol.Optional(v, default=17): vol.Coerce(float)
    for (k, v) in CONF_PRESETS_AWAY_WITH_AC.items()
}

STEP_PRESENCE_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
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
        vol.Required(CONF_USE_PRESENCE_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_ADVANCED_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_MINIMAL_ACTIVATION_DELAY, default=10): cv.positive_int,
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

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_ADVANCED_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)
