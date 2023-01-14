"""Constants for the Versatile Thermostat integration."""

from homeassistant.const import CONF_NAME
from homeassistant.components.climate.const import (
    # PRESET_ACTIVITY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SUPPORT_TARGET_TEMPERATURE,
)

from .prop_algorithm import (
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
CONF_WINDOW_DELAY = "window_delay"
CONF_MOTION_DELAY = "motion_delay"
CONF_MOTION_PRESET = "motion_preset"
CONF_NO_MOTION_PRESET = "no_motion_preset"
CONF_TPI_COEF_INT = "tpi_coef_int"
CONF_TPI_COEF_EXT = "tpi_coef_ext"
CONF_PRESENCE_SENSOR = "presence_sensor_entity_id"
CONF_PRESET_POWER = "power_temp"

CONF_PRESETS = {
    p: f"{p}_temp"
    for p in (
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    )
}

PRESET_AWAY_SUFFIX = "_away"

CONF_PRESETS_AWAY = {
    p: f"{p}_temp"
    for p in (
        PRESET_ECO + PRESET_AWAY_SUFFIX,
        PRESET_BOOST + PRESET_AWAY_SUFFIX,
        PRESET_COMFORT + PRESET_AWAY_SUFFIX,
    )
}

CONF_PRESETS_SELECTIONABLE = [PRESET_ECO, PRESET_COMFORT, PRESET_BOOST]

CONF_PRESETS_VALUES = list(CONF_PRESETS.values())
CONF_PRESETS_AWAY_VALUES = list(CONF_PRESETS_AWAY.values())

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
        CONF_TPI_COEF_INT,
        CONF_TPI_COEF_EXT,
        CONF_PRESENCE_SENSOR,
    ]
    + CONF_PRESETS_VALUES
    + CONF_PRESETS_AWAY_VALUES,
)

CONF_FUNCTIONS = [
    PROPORTIONAL_FUNCTION_TPI,
]

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE

SERVICE_SET_PRESENCE = "set_presence"
SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
