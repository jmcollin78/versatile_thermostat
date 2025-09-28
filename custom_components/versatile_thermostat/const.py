# pylint: disable=line-too-long
"""Constants for the Versatile Thermostat integration."""

import logging
import math
from typing import Literal

from datetime import datetime

from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME, Platform

from homeassistant.components.climate import (
    # PRESET_ACTIVITY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntityFeature,
)

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .prop_algorithm import (
    PROPORTIONAL_FUNCTION_TPI,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_VERSION = 2
CONFIG_MINOR_VERSION = 1

PRESET_TEMP_SUFFIX = "_temp"
PRESET_AC_SUFFIX = "_ac"
PRESET_ECO_AC = PRESET_ECO + PRESET_AC_SUFFIX
PRESET_COMFORT_AC = PRESET_COMFORT + PRESET_AC_SUFFIX
PRESET_BOOST_AC = PRESET_BOOST + PRESET_AC_SUFFIX


DEVICE_MANUFACTURER = "JMCOLLIN"
DEVICE_MODEL = "Versatile Thermostat"

PRESET_POWER = "power"
PRESET_SAFETY = "security"
PRESET_FROST_PROTECTION = "frost"

HIDDEN_PRESETS = [PRESET_POWER, PRESET_SAFETY]

DOMAIN = "versatile_thermostat"

# The order is important.
PLATFORMS: list[Platform] = [
    Platform.SELECT,
    Platform.CLIMATE,
    Platform.SENSOR,
    # Number should be after CLIMATE
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]

CONF_UNDERLYING_LIST = "underlying_entity_ids"
CONF_HEATER_KEEP_ALIVE = "heater_keep_alive"
CONF_TEMP_SENSOR = "temperature_sensor_entity_id"
CONF_LAST_SEEN_TEMP_SENSOR = "last_seen_temperature_sensor_entity_id"
CONF_EXTERNAL_TEMP_SENSOR = "external_temperature_sensor_entity_id"
CONF_POWER_SENSOR = "power_sensor_entity_id"
CONF_MAX_POWER_SENSOR = "max_power_sensor_entity_id"
CONF_WINDOW_SENSOR = "window_sensor_entity_id"
CONF_MOTION_SENSOR = "motion_sensor_entity_id"
CONF_DEVICE_POWER = "device_power"
CONF_CYCLE_MIN = "cycle_min"
CONF_PROP_FUNCTION = "proportional_function"
CONF_WINDOW_DELAY = "window_delay"
CONF_WINDOW_OFF_DELAY = "window_off_delay"
CONF_MOTION_DELAY = "motion_delay"
CONF_MOTION_OFF_DELAY = "motion_off_delay"
CONF_MOTION_PRESET = "motion_preset"
CONF_NO_MOTION_PRESET = "no_motion_preset"
CONF_TPI_COEF_INT = "tpi_coef_int"
CONF_TPI_COEF_EXT = "tpi_coef_ext"
CONF_TPI_THRESHOLD_LOW = "tpi_threshold_low"
CONF_TPI_THRESHOLD_HIGH = "tpi_threshold_high"
CONF_PRESENCE_SENSOR = "presence_sensor_entity_id"
CONF_PRESET_POWER = "power_temp"
CONF_MINIMAL_ACTIVATION_DELAY = "minimal_activation_delay"
CONF_MINIMAL_DEACTIVATION_DELAY = "minimal_deactivation_delay"
CONF_TEMP_MIN = "temp_min"
CONF_TEMP_MAX = "temp_max"
CONF_SAFETY_DELAY_MIN = "safety_delay_min"
CONF_SAFETY_MIN_ON_PERCENT = "safety_min_on_percent"
CONF_SAFETY_DEFAULT_ON_PERCENT = "safety_default_on_percent"
CONF_THERMOSTAT_TYPE = "thermostat_type"
CONF_THERMOSTAT_CENTRAL_CONFIG = "thermostat_central_config"
CONF_THERMOSTAT_SWITCH = "thermostat_over_switch"
CONF_THERMOSTAT_CLIMATE = "thermostat_over_climate"
CONF_THERMOSTAT_VALVE = "thermostat_over_valve"
CONF_USE_WINDOW_FEATURE = "use_window_feature"
CONF_USE_MOTION_FEATURE = "use_motion_feature"
CONF_USE_PRESENCE_FEATURE = "use_presence_feature"
CONF_USE_POWER_FEATURE = "use_power_feature"
CONF_USE_CENTRAL_BOILER_FEATURE = "use_central_boiler_feature"
CONF_USE_AUTO_START_STOP_FEATURE = "use_auto_start_stop_feature"
CONF_AC_MODE = "ac_mode"
CONF_WINDOW_AUTO_OPEN_THRESHOLD = "window_auto_open_threshold"
CONF_WINDOW_AUTO_CLOSE_THRESHOLD = "window_auto_close_threshold"
CONF_WINDOW_AUTO_MAX_DURATION = "window_auto_max_duration"
CONF_AUTO_REGULATION_MODE = "auto_regulation_mode"
CONF_AUTO_REGULATION_NONE = "auto_regulation_none"
CONF_AUTO_REGULATION_VALVE = "auto_regulation_valve"
CONF_AUTO_REGULATION_SLOW = "auto_regulation_slow"
CONF_AUTO_REGULATION_LIGHT = "auto_regulation_light"
CONF_AUTO_REGULATION_MEDIUM = "auto_regulation_medium"
CONF_AUTO_REGULATION_STRONG = "auto_regulation_strong"
CONF_AUTO_REGULATION_EXPERT = "auto_regulation_expert"
CONF_AUTO_REGULATION_DTEMP = "auto_regulation_dtemp"
CONF_AUTO_REGULATION_PERIOD_MIN = "auto_regulation_periode_min"
CONF_AUTO_REGULATION_USE_DEVICE_TEMP = "auto_regulation_use_device_temp"
CONF_INVERSE_SWITCH = "inverse_switch_command"
CONF_AUTO_FAN_MODE = "auto_fan_mode"
CONF_AUTO_FAN_NONE = "auto_fan_none"
CONF_AUTO_FAN_LOW = "auto_fan_low"
CONF_AUTO_FAN_MEDIUM = "auto_fan_medium"
CONF_AUTO_FAN_HIGH = "auto_fan_high"
CONF_AUTO_FAN_TURBO = "auto_fan_turbo"
CONF_STEP_TEMPERATURE = "step_temperature"
CONF_OFFSET_CALIBRATION_LIST = "offset_calibration_entity_ids"
CONF_OPENING_DEGREE_LIST = "opening_degree_entity_ids"
CONF_CLOSING_DEGREE_LIST = "closing_degree_entity_ids"
CONF_MIN_OPENING_DEGREES = "min_opening_degrees"

CONF_VSWITCH_ON_CMD_LIST = "vswitch_on_command"
CONF_VSWITCH_OFF_CMD_LIST = "vswitch_off_command"

# Deprecated
CONF_HEATER = "heater_entity_id"
CONF_HEATER_2 = "heater_entity2_id"
CONF_HEATER_3 = "heater_entity3_id"
CONF_HEATER_4 = "heater_entity4_id"
CONF_CLIMATE = "climate_entity_id"
CONF_CLIMATE_2 = "climate_entity2_id"
CONF_CLIMATE_3 = "climate_entity3_id"
CONF_CLIMATE_4 = "climate_entity4_id"
CONF_VALVE = "valve_entity_id"
CONF_VALVE_2 = "valve_entity2_id"
CONF_VALVE_3 = "valve_entity3_id"
CONF_VALVE_4 = "valve_entity4_id"

# Global params into configuration.yaml
CONF_SHORT_EMA_PARAMS = "short_ema_params"
CONF_SAFETY_MODE = "safety_mode"
CONF_MAX_ON_PERCENT = "max_on_percent"

CONF_USE_MAIN_CENTRAL_CONFIG = "use_main_central_config"
CONF_USE_TPI_CENTRAL_CONFIG = "use_tpi_central_config"
CONF_USE_WINDOW_CENTRAL_CONFIG = "use_window_central_config"
CONF_USE_MOTION_CENTRAL_CONFIG = "use_motion_central_config"
CONF_USE_POWER_CENTRAL_CONFIG = "use_power_central_config"
CONF_USE_PRESENCE_CENTRAL_CONFIG = "use_presence_central_config"
CONF_USE_PRESETS_CENTRAL_CONFIG = "use_presets_central_config"
CONF_USE_ADVANCED_CENTRAL_CONFIG = "use_advanced_central_config"

CONF_USE_CENTRAL_MODE = "use_central_mode"

CONF_CENTRAL_BOILER_ACTIVATION_SRV = "central_boiler_activation_service"
CONF_CENTRAL_BOILER_DEACTIVATION_SRV = "central_boiler_deactivation_service"

CONF_USED_BY_CENTRAL_BOILER = "used_by_controls_central_boiler"
CONF_WINDOW_ACTION = "window_action"

CONF_AUTO_START_STOP_LEVEL = "auto_start_stop_level"
AUTO_START_STOP_LEVEL_NONE = "auto_start_stop_none"
AUTO_START_STOP_LEVEL_VERY_SLOW = "auto_start_stop_very_slow"
AUTO_START_STOP_LEVEL_SLOW = "auto_start_stop_slow"
AUTO_START_STOP_LEVEL_MEDIUM = "auto_start_stop_medium"
AUTO_START_STOP_LEVEL_FAST = "auto_start_stop_fast"
CONF_AUTO_START_STOP_LEVELS = [
    AUTO_START_STOP_LEVEL_NONE,
    AUTO_START_STOP_LEVEL_VERY_SLOW,
    AUTO_START_STOP_LEVEL_SLOW,
    AUTO_START_STOP_LEVEL_MEDIUM,
    AUTO_START_STOP_LEVEL_FAST,
]

# For explicit typing purpose only
TYPE_AUTO_START_STOP_LEVELS = Literal[  # pylint: disable=invalid-name
    AUTO_START_STOP_LEVEL_FAST,
    AUTO_START_STOP_LEVEL_MEDIUM,
    AUTO_START_STOP_LEVEL_SLOW,
    AUTO_START_STOP_LEVEL_VERY_SLOW,
    AUTO_START_STOP_LEVEL_NONE,
]

HVAC_OFF_REASON_NAME = "hvac_off_reason"
HVAC_OFF_REASON_MANUAL = "manual"
HVAC_OFF_REASON_AUTO_START_STOP = "auto_start_stop"
HVAC_OFF_REASON_WINDOW_DETECTION = "window_detection"
HVAC_OFF_REASONS = Literal[  # pylint: disable=invalid-name
    HVAC_OFF_REASON_MANUAL,
    HVAC_OFF_REASON_AUTO_START_STOP,
    HVAC_OFF_REASON_WINDOW_DETECTION,
]

DEFAULT_SHORT_EMA_PARAMS = {
    "max_alpha": 0.5,
    # In sec
    "halflife_sec": 300,
    "precision": 2,
}

CONF_PRESETS = {
    p: f"{p}{PRESET_TEMP_SUFFIX}"
    for p in (
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    )
}

CONF_PRESETS_WITH_AC = {
    p: f"{p}{PRESET_TEMP_SUFFIX}"
    for p in (
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
        PRESET_ECO_AC,
        PRESET_COMFORT_AC,
        PRESET_BOOST_AC,
    )
}


PRESET_AWAY_SUFFIX = "_away"

CONF_PRESETS_AWAY = {
    p: f"{p}{PRESET_TEMP_SUFFIX}"
    for p in (
        PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX,
        PRESET_ECO + PRESET_AWAY_SUFFIX,
        PRESET_COMFORT + PRESET_AWAY_SUFFIX,
        PRESET_BOOST + PRESET_AWAY_SUFFIX,
    )
}

CONF_PRESETS_AWAY_WITH_AC = {
    p: f"{p}{PRESET_TEMP_SUFFIX}"
    for p in (
        PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX,
        PRESET_ECO + PRESET_AWAY_SUFFIX,
        PRESET_COMFORT + PRESET_AWAY_SUFFIX,
        PRESET_BOOST + PRESET_AWAY_SUFFIX,
        PRESET_ECO_AC + PRESET_AWAY_SUFFIX,
        PRESET_COMFORT_AC + PRESET_AWAY_SUFFIX,
        PRESET_BOOST_AC + PRESET_AWAY_SUFFIX,
    )
}

CONF_PRESETS_SELECTIONABLE = [
    PRESET_FROST_PROTECTION,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_BOOST,
]

CONF_PRESETS_VALUES = list(CONF_PRESETS.values())
CONF_PRESETS_AWAY_VALUES = list(CONF_PRESETS_AWAY.values())
CONF_PRESETS_WITH_AC_VALUES = list(CONF_PRESETS_WITH_AC.values())
CONF_PRESETS_AWAY_WITH_AC_VALUES = list(CONF_PRESETS_AWAY_WITH_AC.values())

ALL_CONF = (
    [
        CONF_NAME,
        CONF_HEATER_KEEP_ALIVE,
        CONF_TEMP_SENSOR,
        CONF_EXTERNAL_TEMP_SENSOR,
        CONF_POWER_SENSOR,
        CONF_MAX_POWER_SENSOR,
        CONF_WINDOW_SENSOR,
        CONF_WINDOW_DELAY,
        CONF_WINDOW_OFF_DELAY,
        CONF_WINDOW_AUTO_OPEN_THRESHOLD,
        CONF_WINDOW_AUTO_CLOSE_THRESHOLD,
        CONF_WINDOW_AUTO_MAX_DURATION,
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
        CONF_MINIMAL_DEACTIVATION_DELAY,
        CONF_TEMP_MIN,
        CONF_TEMP_MAX,
        CONF_SAFETY_DELAY_MIN,
        CONF_SAFETY_MIN_ON_PERCENT,
        CONF_SAFETY_DEFAULT_ON_PERCENT,
        CONF_THERMOSTAT_TYPE,
        CONF_THERMOSTAT_SWITCH,
        CONF_THERMOSTAT_CLIMATE,
        CONF_USE_WINDOW_FEATURE,
        CONF_USE_MOTION_FEATURE,
        CONF_USE_PRESENCE_FEATURE,
        CONF_USE_POWER_FEATURE,
        CONF_USE_CENTRAL_BOILER_FEATURE,
        CONF_AC_MODE,
        CONF_AUTO_REGULATION_MODE,
        CONF_AUTO_REGULATION_DTEMP,
        CONF_AUTO_REGULATION_PERIOD_MIN,
        CONF_AUTO_REGULATION_USE_DEVICE_TEMP,
        CONF_INVERSE_SWITCH,
        CONF_AUTO_FAN_MODE,
        CONF_USE_MAIN_CENTRAL_CONFIG,
        CONF_USE_TPI_CENTRAL_CONFIG,
        CONF_USE_PRESETS_CENTRAL_CONFIG,
        CONF_USE_WINDOW_CENTRAL_CONFIG,
        CONF_USE_MOTION_CENTRAL_CONFIG,
        CONF_USE_POWER_CENTRAL_CONFIG,
        CONF_USE_PRESENCE_CENTRAL_CONFIG,
        CONF_USE_ADVANCED_CENTRAL_CONFIG,
        CONF_USE_CENTRAL_MODE,
        CONF_USED_BY_CENTRAL_BOILER,
        CONF_CENTRAL_BOILER_ACTIVATION_SRV,
        CONF_CENTRAL_BOILER_DEACTIVATION_SRV,
        CONF_WINDOW_ACTION,
        CONF_STEP_TEMPERATURE,
    ]
    + CONF_PRESETS_VALUES
    + CONF_PRESETS_AWAY_VALUES
    + CONF_PRESETS_WITH_AC_VALUES
    + CONF_PRESETS_AWAY_WITH_AC_VALUES,
)

CONF_FUNCTIONS = [
    PROPORTIONAL_FUNCTION_TPI,
]

CONF_AUTO_REGULATION_MODES = [
    CONF_AUTO_REGULATION_NONE,
    CONF_AUTO_REGULATION_VALVE,
    CONF_AUTO_REGULATION_LIGHT,
    CONF_AUTO_REGULATION_MEDIUM,
    CONF_AUTO_REGULATION_STRONG,
    CONF_AUTO_REGULATION_SLOW,
    CONF_AUTO_REGULATION_EXPERT,
]

CONF_THERMOSTAT_TYPES = [
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_THERMOSTAT_SWITCH,
    CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_VALVE,
]

CONF_AUTO_FAN_MODES = [
    CONF_AUTO_FAN_NONE,
    CONF_AUTO_FAN_LOW,
    CONF_AUTO_FAN_MEDIUM,
    CONF_AUTO_FAN_HIGH,
    CONF_AUTO_FAN_TURBO,
]

CONF_WINDOW_TURN_OFF = "window_turn_off"
CONF_WINDOW_FAN_ONLY = "window_fan_only"
CONF_WINDOW_FROST_TEMP = "window_frost_temp"
CONF_WINDOW_ECO_TEMP = "window_eco_temp"

CONF_WINDOW_ACTIONS = [
    CONF_WINDOW_TURN_OFF,
    CONF_WINDOW_FAN_ONLY,
    CONF_WINDOW_FROST_TEMP,
    CONF_WINDOW_ECO_TEMP,
]

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)

SERVICE_SET_PRESENCE = "set_presence"
SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
SERVICE_SET_SAFETY = "set_safety"
SERVICE_SET_WINDOW_BYPASS = "set_window_bypass"
SERVICE_SET_AUTO_REGULATION_MODE = "set_auto_regulation_mode"
SERVICE_SET_AUTO_FAN_MODE = "set_auto_fan_mode"

DEFAULT_SAFETY_MIN_ON_PERCENT = 0.5
DEFAULT_SAFETY_DEFAULT_ON_PERCENT = 0.1

ATTR_TOTAL_ENERGY = "total_energy"
ATTR_MEAN_POWER_CYCLE = "mean_cycle_power"

AUTO_FAN_DTEMP_THRESHOLD = 2
AUTO_FAN_DEACTIVATED_MODES = ["mute", "auto", "low"]

CENTRAL_CONFIG_NAME = "Central configuration"

CENTRAL_MODE_AUTO = "Auto"
CENTRAL_MODE_STOPPED = "Stopped"
CENTRAL_MODE_HEAT_ONLY = "Heat only"
CENTRAL_MODE_COOL_ONLY = "Cool only"
CENTRAL_MODE_FROST_PROTECTION = "Frost protection"
CENTRAL_MODES = [
    CENTRAL_MODE_AUTO,
    CENTRAL_MODE_STOPPED,
    CENTRAL_MODE_HEAT_ONLY,
    CENTRAL_MODE_COOL_ONLY,
    CENTRAL_MODE_FROST_PROTECTION,
]


#  A special regulation parameter suggested by @Maia here: https://github.com/jmcollin78/versatile_thermostat/discussions/154
class RegulationParamSlow:
    """Light parameters for slow latency regulation"""

    kp: float = (
        0.2  # 20% of the current internal regulation offset are caused by the current difference of target temperature and room temperature
    )
    ki: float = (
        0.8 / 288.0
    )  # 80% of the current internal regulation offset are caused by the average offset of the past 24 hours
    k_ext: float = (
        1.0 / 25.0
    )  # this will add 1°C to the offset when it's 25°C colder outdoor than indoor
    offset_max: float = 2.0  # limit to a final offset of -2°C to +2°C
    stabilization_threshold: float = (
        0.0  # this needs to be disabled as otherwise the long term accumulated error will always be reset when the temp briefly crosses from/to below/above the target
    )
    accumulated_error_threshold: float = (
        2.0 * 288
    )  # this allows up to 2°C long term offset in both directions


class RegulationParamLight:
    """Light parameters for regulation"""

    kp: float = 0.2
    ki: float = 0.05
    k_ext: float = 0.05
    offset_max: float = 1.5
    stabilization_threshold: float = 0.1
    accumulated_error_threshold: float = 10


class RegulationParamMedium:
    """Light parameters for regulation"""

    kp: float = 0.3
    ki: float = 0.05
    k_ext: float = 0.1
    offset_max: float = 2
    stabilization_threshold: float = 0.1
    accumulated_error_threshold: float = 20


class RegulationParamStrong:
    """Strong parameters for regulation
    A set of parameters which doesn't take into account the external temp
    and concentrate to internal temp error + accumulated error.
    This should work for cold external conditions which else generates
    high external_offset"""

    kp: float = 0.4
    ki: float = 0.08
    k_ext: float = 0.0
    offset_max: float = 5
    stabilization_threshold: float = 0.1
    accumulated_error_threshold: float = 50


# Not used now
class RegulationParamVeryStrong:
    """Strong parameters for regulation"""

    kp: float = 0.6
    ki: float = 0.1
    k_ext: float = 0.2
    offset_max: float = 8
    stabilization_threshold: float = 0.1
    accumulated_error_threshold: float = 80


class EventType(Enum):
    """The event type that can be sent"""

    SECURITY_EVENT: str = "versatile_thermostat_security_event"
    POWER_EVENT: str = "versatile_thermostat_power_event"
    TEMPERATURE_EVENT: str = "versatile_thermostat_temperature_event"
    HVAC_MODE_EVENT: str = "versatile_thermostat_hvac_mode_event"
    CENTRAL_BOILER_EVENT: str = "versatile_thermostat_central_boiler_event"
    PRESET_EVENT: str = "versatile_thermostat_preset_event"
    WINDOW_AUTO_EVENT: str = "versatile_thermostat_window_auto_event"
    AUTO_START_STOP_EVENT: str = "versatile_thermostat_auto_start_stop_event"


def send_vtherm_event(hass, event_type: EventType, entity, data: dict):
    """Send an event"""
    _LOGGER.info("%s - Sending event %s with data: %s", entity, event_type, data)
    data["entity_id"] = entity.entity_id
    data["name"] = entity.name
    data["state_attributes"] = entity.state_attributes
    hass.bus.fire(event_type.value, data)


def get_safe_float(hass, entity_id: str):
    """Get a safe float state value for an entity.
    Return None if entity is not available"""
    if (
        entity_id is None
        or not (state := hass.states.get(entity_id))
        or state.state is None
        or state.state == "None"
        or state.state == "unknown"
        or state.state == "unavailable"
    ):
        return None
    float_val = float(state.state)
    return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


class NowClass:
    """For testing purpose only"""

    @staticmethod
    def get_now(hass: HomeAssistant) -> datetime:
        """A test function to get the now.
        For testing purpose this method can be overriden to get a specific
        timestamp.
        """
        return datetime.now(get_tz(hass))


class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""


class WindowOpenDetectionMethod(HomeAssistantError):
    """Error to indicate there is an error in the window open detection method given."""


class NoCentralConfig(HomeAssistantError):
    """Error to indicate that we try to use a central configuration but no VTherm of type CENTRAL CONFIGURATION has been found"""


class ServiceConfigurationError(HomeAssistantError):
    """Error in the service configuration to control the central boiler"""


class ConfigurationNotCompleteError(HomeAssistantError):
    """Error the configuration is not complete"""


class ValveRegulationNbEntitiesIncorrect(HomeAssistantError):
    """Error to indicate there is an error in the configuration of the TRV with valve regulation.
    The number of specific entities is incorrect."""


class ValveRegulationMinOpeningDegreesIncorrect(HomeAssistantError):
    """Error to indicate that the minimal opening degrees is not a list of int separated by coma"""


class VirtualSwitchConfigurationIncorrect(HomeAssistantError):
    """Error when a virtual switch is not configured correctly"""


class overrides:  # pylint: disable=invalid-name
    """An annotation to inform overrides"""

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"Method {self.func.__name__} should have been overridden")
