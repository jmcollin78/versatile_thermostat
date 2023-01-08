"""Constants for the Versatile Thermostat integration."""

from homeassistant.const import CONF_NAME
from homeassistant.components.climate.const import (
    # PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SUPPORT_TARGET_TEMPERATURE,
)

from .prop_algorithm import (
    PROPORTIONAL_FUNCTION_ATAN,
    PROPORTIONAL_FUNCTION_LINEAR,
    PROPORTIONAL_FUNCTION_TPI,
)

PRESET_POWER = "power"

DOMAIN = "versatile_thermostat"

CONF_HEATER = "heater_entity_id"
CONF_TEMP_SENSOR = "temperature_sensor_entity_id"
CONF_EXTERNAL_TEMP_SENSOR = "external_temperature_sensor_entity_id"
CONF_POWER_SENSOR = "power_sensor_entity_id"
CONF_MAX_POWER_SENSOR = "max_power_sensor_entity_id"
CONF_WINDOW_SENSOR = "window_sensor_entity_id"
CONF_MOTION_SENSOR = "motion_sensor_entity_id"
CONF_DEVICE_POWER = "device_power"
CONF_CYCLE_MIN = "cycle_min"
CONF_PROP_FUNCTION = "proportional_function"
CONF_PROP_BIAS = "proportional_bias"
CONF_WINDOW_DELAY = "window_delay"
CONF_MOTION_DELAY = "motion_delay"
CONF_MOTION_PRESET = "motion_preset"
CONF_NO_MOTION_PRESET = "no_motion_preset"
CONF_TPI_COEF_C = "tpi_coefc"
CONF_TPI_COEF_T = "tpi_coeft"
CONF_PRESENCE_SENSOR = "presence_sensor_entity_id"
CONF_NO_PRESENCE_PRESET = "no_presence_preset"
CONF_NO_PRESENCE_TEMP_OFFSET = "no_presence_temp_offset"

CONF_PRESETS = {
    p: f"{p}_temp"
    for p in (
        PRESET_ECO,
        PRESET_AWAY,
        PRESET_BOOST,
        PRESET_COMFORT,
        PRESET_POWER,
    )
}

CONF_PRESETS_SELECTIONABLE = [PRESET_ECO, PRESET_COMFORT, PRESET_AWAY, PRESET_BOOST]

CONF_PRESETS_VALUES = list(CONF_PRESETS.values())

ALL_CONF = (
    [
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
        CONF_PROP_FUNCTION,
        CONF_PROP_BIAS,
        CONF_TPI_COEF_C,
        CONF_TPI_COEF_T,
        CONF_PRESENCE_SENSOR,
        CONF_NO_PRESENCE_PRESET,
        CONF_NO_PRESENCE_TEMP_OFFSET,
    ]
    + CONF_PRESETS_VALUES,
)

CONF_FUNCTIONS = [
    PROPORTIONAL_FUNCTION_LINEAR,
    PROPORTIONAL_FUNCTION_ATAN,
    PROPORTIONAL_FUNCTION_TPI,
]

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
