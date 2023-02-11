"""Constants for the Versatile Thermostat integration."""

from enum import Enum
from homeassistant.const import CONF_NAME
from homeassistant.components.climate.const import (
    # PRESET_ACTIVITY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.exceptions import HomeAssistantError

from .prop_algorithm import (
    PROPORTIONAL_FUNCTION_TPI,
)

PRESET_POWER = "power"
PRESET_SECURITY = "security"

HIDDEN_PRESETS = [PRESET_POWER, PRESET_SECURITY]

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
CONF_MINIMAL_ACTIVATION_DELAY = "minimal_activation_delay"
CONF_TEMP_MIN = "temp_min"
CONF_TEMP_MAX = "temp_max"
CONF_SECURITY_DELAY_MIN = "security_delay_min"
CONF_SECURITY_MIN_ON_PERCENT = "security_min_on_percent"
CONF_SECURITY_DEFAULT_ON_PERCENT = "security_default_on_percent"
CONF_THERMOSTAT_TYPE = "thermostat_type"
CONF_THERMOSTAT_SWITCH = "thermostat_over_switch"
CONF_THERMOSTAT_CLIMATE = "thermostat_over_climate"
CONF_CLIMATE = "climate_entity_id"
CONF_USE_WINDOW_FEATURE = "use_window_feature"
CONF_USE_MOTION_FEATURE = "use_motion_feature"
CONF_USE_PRESENCE_FEATURE = "use_presence_feature"
CONF_USE_POWER_FEATURE = "use_power_feature"

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
        CONF_MINIMAL_ACTIVATION_DELAY,
        CONF_TEMP_MIN,
        CONF_TEMP_MAX,
        CONF_SECURITY_DELAY_MIN,
        CONF_SECURITY_MIN_ON_PERCENT,
        CONF_SECURITY_DEFAULT_ON_PERCENT,
        CONF_THERMOSTAT_TYPE,
        CONF_THERMOSTAT_SWITCH,
        CONF_THERMOSTAT_CLIMATE,
        CONF_CLIMATE,
        CONF_USE_WINDOW_FEATURE,
        CONF_USE_MOTION_FEATURE,
        CONF_USE_PRESENCE_FEATURE,
        CONF_USE_POWER_FEATURE,
    ]
    + CONF_PRESETS_VALUES
    + CONF_PRESETS_AWAY_VALUES,
)

CONF_FUNCTIONS = [
    PROPORTIONAL_FUNCTION_TPI,
]

CONF_THERMOSTAT_TYPES = [CONF_THERMOSTAT_SWITCH, CONF_THERMOSTAT_CLIMATE]

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE

SERVICE_SET_PRESENCE = "set_presence"
SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
SERVICE_SET_SECURITY = "set_security"

DEFAULT_SECURITY_MIN_ON_PERCENT = 0.5
DEFAULT_SECURITY_DEFAULT_ON_PERCENT = 0.1


class EventType(Enum):
    """The event type that can be sent"""

    SECURITY_EVENT: str = "versatile_thermostat_security_event"
    POWER_EVENT: str = "versatile_thermostat_power_event"
    TEMPERATURE_EVENT: str = "versatile_thermostat_temperature_event"
    HVAC_MODE_EVENT: str = "versatile_thermostat_hvac_mode_event"
    PRESET_EVENT: str = "versatile_thermostat_preset_event"


class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""
