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

from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)

from homeassistant.components.input_select import (
    DOMAIN as INPUT_SELECT_DOMAIN,
)

from homeassistant.components.input_datetime import (
    DOMAIN as INPUT_DATETIME_DOMAIN,
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
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN, NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_LAST_SEEN_TEMP_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_DATETIME_DOMAIN, NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_CYCLE_MIN, default=5): selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=1000, step=1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_DEVICE_POWER, default="1"): vol.Coerce(float),
        vol.Required(CONF_USE_MAIN_CENTRAL_CONFIG, default=True): cv.boolean,
        vol.Optional(CONF_USE_CENTRAL_MODE, default=True): cv.boolean,
        vol.Required(CONF_USED_BY_CENTRAL_BOILER, default=False): cv.boolean,
    }
)

STEP_FEATURES_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
    }
)

STEP_CLIMATE_FEATURES_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_AUTO_START_STOP_FEATURE, default=False): cv.boolean,
    }
)

STEP_CLIMATE_VALVE_FEATURES_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
    }
)

STEP_CENTRAL_FEATURES_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_USE_WINDOW_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_MOTION_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_POWER_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_PRESENCE_FEATURE, default=False): cv.boolean,
        vol.Optional(CONF_USE_CENTRAL_BOILER_FEATURE, default=False): cv.boolean,
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
        vol.Required(CONF_CENTRAL_BOILER_ACTIVATION_DELAY_SEC, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=600, step=10, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_CENTRAL_BOILER_ACTIVATION_SRV, default=""): str,
        vol.Optional(CONF_CENTRAL_BOILER_DEACTIVATION_SRV, default=""): str,
    }
)

STEP_THERMOSTAT_SWITCH = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_UNDERLYING_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN, SELECT_DOMAIN, INPUT_SELECT_DOMAIN, CLIMATE_DOMAIN], multiple=True),
        ),
        vol.Optional(CONF_HEATER_KEEP_ALIVE): cv.positive_int,
        vol.Required(CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI): vol.In(
            [
                PROPORTIONAL_FUNCTION_TPI,
            ]
        ),
        vol.Optional(CONF_AC_MODE, default=False): cv.boolean,
        vol.Optional(CONF_INVERSE_SWITCH, default=False): cv.boolean,
        vol.Optional("on_command_text"): vol.In([]),
        vol.Optional(CONF_VSWITCH_ON_CMD_LIST): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT, multiple=True)),
        vol.Optional("off_command_text"): vol.In([]),
        vol.Optional(CONF_VSWITCH_OFF_CMD_LIST): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT, multiple=True)),
    }
)

STEP_THERMOSTAT_CLIMATE = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_UNDERLYING_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True),
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
        vol.Optional(CONF_AUTO_REGULATION_USE_DEVICE_TEMP, default=False): cv.boolean,
    }
)

STEP_THERMOSTAT_VALVE = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_UNDERLYING_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN], multiple=True
            ),
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

STEP_AUTO_START_STOP = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(
            CONF_AUTO_START_STOP_LEVEL, default=AUTO_START_STOP_LEVEL_NONE
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_AUTO_START_STOP_LEVELS,
                translation_key="auto_start_stop",
                mode="dropdown",
            )
        ),
    }
)

STEP_VALVE_REGULATION = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_OPENING_DEGREE_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN], multiple=True),
        ),
        vol.Optional(CONF_OFFSET_CALIBRATION_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN], multiple=True),
        ),
        vol.Optional(CONF_CLOSING_DEGREE_LIST): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[NUMBER_DOMAIN, INPUT_NUMBER_DOMAIN], multiple=True),
        ),
        vol.Required(CONF_PROP_FUNCTION, default=PROPORTIONAL_FUNCTION_TPI): vol.In(
            [
                PROPORTIONAL_FUNCTION_TPI,
            ]
        ),
        vol.Optional(CONF_OPENING_THRESHOLD_DEGREE, default=0): cv.positive_int,
        vol.Optional(CONF_MIN_OPENING_DEGREES, default=""): str,
        vol.Optional(CONF_MAX_CLOSING_DEGREE, default=100): cv.positive_int,
    }
)

STEP_TPI_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_TPI_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_TPI_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_TPI_COEF_INT, default=0.6): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=10.0, step=0.000001, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_TPI_COEF_EXT, default=0.01): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=1.0, step=0.000001, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_MINIMAL_ACTIVATION_DELAY, default=10): cv.positive_int,
        vol.Required(CONF_MINIMAL_DEACTIVATION_DELAY, default=0): cv.positive_int,
        vol.Optional(CONF_TPI_THRESHOLD_LOW, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(CONF_TPI_THRESHOLD_HIGH, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(CONF_AUTO_TPI_MODE, default=False): cv.boolean,
    }
)
# Duplicating schema for central config
# as we don't want to display the use_auto_tpi checkbox
# in central config but only in device config.
STEP_CENTRAL_TPI_DATA_SCHEMA_CENTRAL = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_TPI_COEF_INT, default=0.6): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=10.0, step=0.000001, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_TPI_COEF_EXT, default=0.01): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=1.0, step=0.000001, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_MINIMAL_ACTIVATION_DELAY, default=10): cv.positive_int,
        vol.Required(CONF_MINIMAL_DEACTIVATION_DELAY, default=0): cv.positive_int,
        vol.Optional(CONF_TPI_THRESHOLD_LOW, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(CONF_TPI_THRESHOLD_HIGH, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-10.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
)

STEP_PRESETS_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_PRESETS_CENTRAL_CONFIG, default=True): cv.boolean,
    }
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
        vol.Optional(CONF_WINDOW_OFF_DELAY, default=30): cv.positive_int,
        vol.Optional(CONF_WINDOW_AUTO_OPEN_THRESHOLD, default=3): vol.Coerce(float),
        vol.Optional(CONF_WINDOW_AUTO_CLOSE_THRESHOLD, default=0): vol.Coerce(float),
        vol.Optional(CONF_WINDOW_AUTO_MAX_DURATION, default=30): cv.positive_int,
        vol.Optional(CONF_WINDOW_ACTION, default=CONF_WINDOW_TURN_OFF): selector.SelectSelector(
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
        vol.Optional(CONF_WINDOW_OFF_DELAY, default=30): cv.positive_int,
        vol.Optional(CONF_WINDOW_ACTION, default=CONF_WINDOW_TURN_OFF): selector.SelectSelector(
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
        vol.Required(CONF_MOTION_SENSOR): selector.EntitySelector(
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
        vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Required(CONF_MAX_POWER_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN]),
        ),
        vol.Optional(CONF_PRESET_POWER, default="13"): vol.Coerce(float),
    }
)

STEP_NON_CENTRAL_POWER_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
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
        vol.Required(CONF_PRESENCE_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[
                    PERSON_DOMAIN,
                    BINARY_SENSOR_DOMAIN,
                    INPUT_BOOLEAN_DOMAIN,
                ]
            ),
        )
    },
)

STEP_PRESENCE_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_PRESENCE_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_ADVANCED_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_SAFETY_DELAY_MIN, default=60): cv.positive_int,
        vol.Required(
            CONF_SAFETY_MIN_ON_PERCENT,
            default=DEFAULT_SAFETY_MIN_ON_PERCENT,
        ): vol.Coerce(float),
        vol.Required(
            CONF_SAFETY_DEFAULT_ON_PERCENT,
            default=DEFAULT_SAFETY_DEFAULT_ON_PERCENT,
        ): vol.Coerce(float),
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_ADVANCED_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_LOCK_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Required(CONF_USE_LOCK_CENTRAL_CONFIG, default=True): cv.boolean,
    }
)

STEP_CENTRAL_LOCK_DATA_SCHEMA = vol.Schema(  # pylint: disable=invalid-name
    {
        vol.Optional(CONF_LOCK_CODE): cv.string,
        vol.Optional(CONF_LOCK_USERS, default=True): cv.boolean,
        vol.Optional(CONF_LOCK_AUTOMATIONS, default=True): cv.boolean,
    }
)

STEP_AUTO_TPI_1_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTO_TPI_ENABLE_UPDATE_CONFIG, default=True): cv.boolean,
        vol.Required(CONF_AUTO_TPI_ENABLE_NOTIFICATION, default=True): cv.boolean,
        vol.Optional(CONF_AUTO_TPI_KEEP_EXT_LEARNING, default=True): cv.boolean,
        vol.Optional(CONF_AUTO_TPI_CONTINUOUS_LEARNING, default=False): cv.boolean,
        vol.Optional(CONF_AUTO_TPI_HEATER_HEATING_TIME, default=0): cv.positive_int,
        vol.Optional(CONF_AUTO_TPI_HEATER_COOLING_TIME, default=0): cv.positive_int,
        vol.Required(CONF_AUTO_TPI_HEATING_POWER, default=1.0): cv.positive_float,
        vol.Required(CONF_AUTO_TPI_COOLING_POWER, default=1.0): cv.positive_float,
        vol.Required(CONF_AUTO_TPI_MAX_COEF_INT, default=1.0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=3.0, step=0.01, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
)

STEP_AUTO_TPI_2_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_AUTO_TPI_CALCULATION_METHOD, default=AUTO_TPI_METHOD_AVG
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_AUTO_TPI_CALCULATION_METHODS,
                translation_key="auto_tpi_calculation_method",
                mode="dropdown",
            )
        ),
    }
)

STEP_AUTO_TPI_3_AVG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTO_TPI_AVG_INITIAL_WEIGHT, default=1): cv.positive_int,
    }
)

STEP_AUTO_TPI_3_EMA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTO_TPI_EMA_ALPHA, default=0.15): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=1.0, step=0.01, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_AUTO_TPI_EMA_DECAY_RATE, default=0.08
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=1.0, step=0.01, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
)
