# pylint: disable=line-too-long
"""Constants for the Versatile Thermostat integration."""

from enum import Enum
from homeassistant.const import CONF_NAME, Platform

from homeassistant.components.climate import (
    # PRESET_ACTIVITY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntityFeature,
)

from homeassistant.exceptions import HomeAssistantError

from .prop_algorithm import (
    PROPORTIONAL_FUNCTION_TPI,
)

PRESET_AC_SUFFIX = "_ac"
PRESET_ECO_AC = PRESET_ECO + PRESET_AC_SUFFIX
PRESET_COMFORT_AC = PRESET_COMFORT + PRESET_AC_SUFFIX
PRESET_BOOST_AC = PRESET_BOOST + PRESET_AC_SUFFIX


DEVICE_MANUFACTURER = "JMCOLLIN"
DEVICE_MODEL = "Versatile Thermostat"

PRESET_POWER = "power"
PRESET_SECURITY = "security"
PRESET_FROST_PROTECTION = "frost"

HIDDEN_PRESETS = [PRESET_POWER, PRESET_SECURITY]

DOMAIN = "versatile_thermostat"

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SELECT,
]

CONF_HEATER = "heater_entity_id"
CONF_HEATER_2 = "heater_entity2_id"
CONF_HEATER_3 = "heater_entity3_id"
CONF_HEATER_4 = "heater_entity4_id"
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
CONF_MOTION_OFF_DELAY = "motion_off_delay"
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
CONF_THERMOSTAT_CENTRAL_CONFIG = "thermostat_central_config"
CONF_THERMOSTAT_SWITCH = "thermostat_over_switch"
CONF_THERMOSTAT_CLIMATE = "thermostat_over_climate"
CONF_THERMOSTAT_VALVE = "thermostat_over_valve"
CONF_CLIMATE = "climate_entity_id"
CONF_CLIMATE_2 = "climate_entity2_id"
CONF_CLIMATE_3 = "climate_entity3_id"
CONF_CLIMATE_4 = "climate_entity4_id"
CONF_USE_WINDOW_FEATURE = "use_window_feature"
CONF_USE_MOTION_FEATURE = "use_motion_feature"
CONF_USE_PRESENCE_FEATURE = "use_presence_feature"
CONF_USE_POWER_FEATURE = "use_power_feature"
CONF_AC_MODE = "ac_mode"
CONF_WINDOW_AUTO_OPEN_THRESHOLD = "window_auto_open_threshold"
CONF_WINDOW_AUTO_CLOSE_THRESHOLD = "window_auto_close_threshold"
CONF_WINDOW_AUTO_MAX_DURATION = "window_auto_max_duration"
CONF_VALVE = "valve_entity_id"
CONF_VALVE_2 = "valve_entity2_id"
CONF_VALVE_3 = "valve_entity3_id"
CONF_VALVE_4 = "valve_entity4_id"
CONF_AUTO_REGULATION_MODE = "auto_regulation_mode"
CONF_AUTO_REGULATION_NONE = "auto_regulation_none"
CONF_AUTO_REGULATION_SLOW = "auto_regulation_slow"
CONF_AUTO_REGULATION_LIGHT = "auto_regulation_light"
CONF_AUTO_REGULATION_MEDIUM = "auto_regulation_medium"
CONF_AUTO_REGULATION_STRONG = "auto_regulation_strong"
CONF_AUTO_REGULATION_EXPERT = "auto_regulation_expert"
CONF_AUTO_REGULATION_DTEMP = "auto_regulation_dtemp"
CONF_AUTO_REGULATION_PERIOD_MIN = "auto_regulation_periode_min"
CONF_INVERSE_SWITCH = "inverse_switch_command"
CONF_SHORT_EMA_PARAMS = "short_ema_params"
CONF_AUTO_FAN_MODE = "auto_fan_mode"
CONF_AUTO_FAN_NONE = "auto_fan_none"
CONF_AUTO_FAN_LOW = "auto_fan_low"
CONF_AUTO_FAN_MEDIUM = "auto_fan_medium"
CONF_AUTO_FAN_HIGH = "auto_fan_high"
CONF_AUTO_FAN_TURBO = "auto_fan_turbo"

CONF_USE_MAIN_CENTRAL_CONFIG = "use_main_central_config"
CONF_USE_TPI_CENTRAL_CONFIG = "use_tpi_central_config"
CONF_USE_WINDOW_CENTRAL_CONFIG = "use_window_central_config"
CONF_USE_MOTION_CENTRAL_CONFIG = "use_motion_central_config"
CONF_USE_POWER_CENTRAL_CONFIG = "use_power_central_config"
CONF_USE_PRESENCE_CENTRAL_CONFIG = "use_presence_central_config"
CONF_USE_PRESETS_CENTRAL_CONFIG = "use_presets_central_config"
CONF_USE_ADVANCED_CENTRAL_CONFIG = "use_advanced_central_config"

CONF_USE_CENTRAL_MODE = "use_central_mode"

CONF_ADD_CENTRAL_BOILER_CONTROL = "add_central_boiler_control"
CONF_CENTRAL_BOILER_ACTIVATION_SRV = "central_boiler_activation_service"
CONF_CENTRAL_BOILER_DEACTIVATION_SRV = "central_boiler_deactivation_service"

CONF_USED_BY_CENTRAL_BOILER = "used_by_controls_central_boiler"

DEFAULT_SHORT_EMA_PARAMS = {
    "max_alpha": 0.5,
    # In sec
    "halflife_sec": 300,
    "precision": 2,
}

CONF_PRESETS = {
    p: f"{p}_temp"
    for p in (
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    )
}

CONF_PRESETS_WITH_AC = {
    p: f"{p}_temp"
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
    p: f"{p}_temp"
    for p in (
        PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX,
        PRESET_ECO + PRESET_AWAY_SUFFIX,
        PRESET_COMFORT + PRESET_AWAY_SUFFIX,
        PRESET_BOOST + PRESET_AWAY_SUFFIX,
    )
}

CONF_PRESETS_AWAY_WITH_AC = {
    p: f"{p}_temp"
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
        CONF_HEATER,
        CONF_HEATER_2,
        CONF_HEATER_3,
        CONF_HEATER_4,
        CONF_TEMP_SENSOR,
        CONF_EXTERNAL_TEMP_SENSOR,
        CONF_POWER_SENSOR,
        CONF_MAX_POWER_SENSOR,
        CONF_WINDOW_SENSOR,
        CONF_WINDOW_DELAY,
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
        CONF_TEMP_MIN,
        CONF_TEMP_MAX,
        CONF_SECURITY_DELAY_MIN,
        CONF_SECURITY_MIN_ON_PERCENT,
        CONF_SECURITY_DEFAULT_ON_PERCENT,
        CONF_THERMOSTAT_TYPE,
        CONF_THERMOSTAT_SWITCH,
        CONF_THERMOSTAT_CLIMATE,
        CONF_CLIMATE,
        CONF_CLIMATE_2,
        CONF_CLIMATE_3,
        CONF_CLIMATE_4,
        CONF_USE_WINDOW_FEATURE,
        CONF_USE_MOTION_FEATURE,
        CONF_USE_PRESENCE_FEATURE,
        CONF_USE_POWER_FEATURE,
        CONF_AC_MODE,
        CONF_VALVE,
        CONF_VALVE_2,
        CONF_VALVE_3,
        CONF_VALVE_4,
        CONF_AUTO_REGULATION_MODE,
        CONF_AUTO_REGULATION_DTEMP,
        CONF_AUTO_REGULATION_PERIOD_MIN,
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
        CONF_ADD_CENTRAL_BOILER_CONTROL,
        CONF_USED_BY_CENTRAL_BOILER,
        CONF_CENTRAL_BOILER_ACTIVATION_SRV,
        CONF_CENTRAL_BOILER_DEACTIVATION_SRV,
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

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE

SERVICE_SET_PRESENCE = "set_presence"
SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"
SERVICE_SET_SECURITY = "set_security"
SERVICE_SET_WINDOW_BYPASS = "set_window_bypass"
SERVICE_SET_AUTO_REGULATION_MODE = "set_auto_regulation_mode"
SERVICE_SET_AUTO_FAN_MODE = "set_auto_fan_mode"

DEFAULT_SECURITY_MIN_ON_PERCENT = 0.5
DEFAULT_SECURITY_DEFAULT_ON_PERCENT = 0.1

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

    kp: float = 0.2  # 20% of the current internal regulation offset are caused by the current difference of target temperature and room temperature
    ki: float = (
        0.8 / 288.0
    )  # 80% of the current internal regulation offset are caused by the average offset of the past 24 hours
    k_ext: float = (
        1.0 / 25.0
    )  # this will add 1°C to the offset when it's 25°C colder outdoor than indoor
    offset_max: float = 2.0  # limit to a final offset of -2°C to +2°C
    stabilization_threshold: float = 0.0  # this needs to be disabled as otherwise the long term accumulated error will always be reset when the temp briefly crosses from/to below/above the target
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
    offset_max: float = 4
    stabilization_threshold: float = 0.1
    accumulated_error_threshold: float = 30


class EventType(Enum):
    """The event type that can be sent"""

    SECURITY_EVENT: str = "versatile_thermostat_security_event"
    POWER_EVENT: str = "versatile_thermostat_power_event"
    TEMPERATURE_EVENT: str = "versatile_thermostat_temperature_event"
    HVAC_MODE_EVENT: str = "versatile_thermostat_hvac_mode_event"
    HVAC_ACTION_EVENT: str = "versatile_thermostat_hvac_action_event"
    PRESET_EVENT: str = "versatile_thermostat_preset_event"
    WINDOW_AUTO_EVENT: str = "versatile_thermostat_window_auto_event"


class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""


class WindowOpenDetectionMethod(HomeAssistantError):
    """Error to indicate there is an error in the window open detection method given."""


class NoCentralConfig(HomeAssistantError):
    """Error to indicate that we try to use a central configuration but no VTherm of type CENTRAL CONFIGURATION has been found"""


class overrides:  # pylint: disable=invalid-name
    """An annotation to inform overrides"""

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"Method {self.func.__name__} should have been overridden")
