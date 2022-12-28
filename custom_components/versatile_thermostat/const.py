"""Constants for the Versatile Thermostat integration."""

from homeassistant.const import CONF_NAME
from homeassistant.components.climate.const import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SUPPORT_TARGET_TEMPERATURE,
)

PRESET_POWER = "power"

DOMAIN = "versatile_thermostat"

CONF_HEATER = "heater_entity_id"
CONF_TEMP_SENSOR = "temperature_sensor_entity_id"
CONF_POWER_SENSOR = "power_sensor_entity_id"
CONF_MAX_POWER_SENSOR = "max_power_sensor_entity_id"
CONF_WINDOW_SENSOR = "window_sensor_entity_id"
CONF_MOTION_SENSOR = "motion_sensor_entity_id"
CONF_DEVICE_POWER = "device_power"

ALL_CONF = [
    CONF_NAME,
    CONF_HEATER,
    CONF_TEMP_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_MOTION_SENSOR,
    CONF_DEVICE_POWER,
]

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

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
