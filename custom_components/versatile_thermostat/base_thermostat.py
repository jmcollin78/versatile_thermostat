# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=invalid-name
""" Implements the VersatileThermostat climate component """
import math
import logging

from datetime import timedelta, datetime
from types import MappingProxyType
from typing import Any, TypeVar, Generic

from homeassistant.util import dt as dt_util
from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    State,

)

from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_call_later,
    EventStateChangedData,
)

from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition

from homeassistant.components.climate import (
    ATTR_PRESET_MODE,
    # ATTR_FAN_MODE,
    HVACMode,
    HVACAction,
    # HVAC_MODE_COOL,
    # HVAC_MODE_HEAT,
    # HVAC_MODE_OFF,
    PRESET_ACTIVITY,
    # PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    # PRESET_HOME,
    PRESET_NONE,
    # PRESET_SLEEP,
    ClimateEntityFeature,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_OFF,
    STATE_ON,
    STATE_HOME,
    STATE_NOT_HOME,
)

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_POWER_SENSOR,
    CONF_TEMP_SENSOR,
    CONF_LAST_SEEN_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_WINDOW_DELAY,
    CONF_WINDOW_AUTO_CLOSE_THRESHOLD,
    CONF_WINDOW_AUTO_OPEN_THRESHOLD,
    CONF_WINDOW_AUTO_MAX_DURATION,
    CONF_MOTION_SENSOR,
    CONF_MOTION_DELAY,
    CONF_MOTION_OFF_DELAY,
    CONF_MOTION_PRESET,
    CONF_NO_MOTION_PRESET,
    CONF_DEVICE_POWER,
    CONF_PRESETS,
    # CONF_PRESETS_AWAY,
    # CONF_PRESETS_WITH_AC,
    # CONF_PRESETS_AWAY_WITH_AC,
    CONF_CYCLE_MIN,
    CONF_PROP_FUNCTION,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_PRESENCE_SENSOR,
    CONF_PRESET_POWER,
    SUPPORT_FLAGS,
    PRESET_FROST_PROTECTION,
    PRESET_POWER,
    PRESET_SECURITY,
    PROPORTIONAL_FUNCTION_TPI,
    PRESET_AWAY_SUFFIX,
    CONF_SECURITY_DELAY_MIN,
    CONF_SECURITY_MIN_ON_PERCENT,
    CONF_SECURITY_DEFAULT_ON_PERCENT,
    DEFAULT_SECURITY_MIN_ON_PERCENT,
    DEFAULT_SECURITY_DEFAULT_ON_PERCENT,
    CONF_MINIMAL_ACTIVATION_DELAY,
    CONF_USE_MAIN_CENTRAL_CONFIG,
    CONF_USE_TPI_CENTRAL_CONFIG,
    CONF_USE_PRESETS_CENTRAL_CONFIG,
    CONF_USE_WINDOW_CENTRAL_CONFIG,
    CONF_USE_MOTION_CENTRAL_CONFIG,
    CONF_USE_POWER_CENTRAL_CONFIG,
    CONF_USE_PRESENCE_CENTRAL_CONFIG,
    CONF_USE_ADVANCED_CENTRAL_CONFIG,
    CONF_USE_PRESENCE_FEATURE,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    HIDDEN_PRESETS,
    CONF_AC_MODE,
    EventType,
    ATTR_MEAN_POWER_CYCLE,
    ATTR_TOTAL_ENERGY,
    PRESET_AC_SUFFIX,
    DEFAULT_SHORT_EMA_PARAMS,
    CENTRAL_MODE_AUTO,
    CENTRAL_MODE_STOPPED,
    CENTRAL_MODE_HEAT_ONLY,
    CENTRAL_MODE_COOL_ONLY,
    CENTRAL_MODE_FROST_PROTECTION,
    send_vtherm_event,
)

from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingEntity

from .prop_algorithm import PropAlgorithm
from .open_window_algorithm import WindowOpenDetectionAlgorithm
from .ema import ExponentialMovingAverage

_LOGGER = logging.getLogger(__name__)
ConfigData = MappingProxyType[str, Any]
T = TypeVar("T", bound=UnderlyingEntity)


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


class BaseThermostat(ClimateEntity, RestoreEntity, Generic[T]):
    """Representation of a base class for all Versatile Thermostat device."""

    _entity_component_unrecorded_attributes = (
        ClimateEntity._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "is_on",
                    "is_controlled_by_central_mode",
                    "last_central_mode",
                    "type",
                    "frost_temp",
                    "eco_temp",
                    "boost_temp",
                    "comfort_temp",
                    "frost_away_temp",
                    "eco_away_temp",
                    "boost_away_temp",
                    "comfort_away_temp",
                    "power_temp",
                    "ac_mode",
                    "current_power_max",
                    "saved_preset_mode",
                    "saved_target_temp",
                    "saved_hvac_mode",
                    "security_delay_min",
                    "security_min_on_percent",
                    "security_default_on_percent",
                    "last_temperature_datetime",
                    "last_ext_temperature_datetime",
                    "minimal_activation_delay_sec",
                    "device_power",
                    "mean_cycle_power",
                    "last_update_datetime",
                    "timezone",
                    "window_sensor_entity_id",
                    "window_delay_sec",
                    "window_auto_enabled",
                    "window_auto_open_threshold",
                    "window_auto_close_threshold",
                    "window_auto_max_duration",
                    "window_action",
                    "motion_sensor_entity_id",
                    "presence_sensor_entity_id",
                    "power_sensor_entity_id",
                    "max_power_sensor_entity_id",
                    "temperature_unit",
                    "is_device_active",
                    "target_temperature_step",
                    "is_used_by_central_boiler",
                }
            )
        )
    )

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        entry_infos: ConfigData,
    ):
        """Initialize the thermostat."""

        super().__init__()

        # To remove some silly warning event if code is fixed
        self._enable_turn_on_off_backwards_compatibility = False

        self._hass = hass
        self._entry_infos = None
        self._attr_extra_state_attributes = {}

        self._unique_id = unique_id
        self._name = name
        self._prop_algorithm = None
        self._async_cancel_cycle = None
        self._hvac_mode = None
        self._target_temp = None
        self._saved_target_temp = None
        self._saved_preset_mode = None
        self._fan_mode = None
        self._humidity = None
        self._swing_mode = None
        self._current_power = None
        self._current_power_max = None
        self._window_state = None
        self._motion_state = None
        self._saved_hvac_mode = None
        self._window_call_cancel = None
        self._motion_call_cancel = None
        self._cur_temp = None
        self._ac_mode = None
        self._temp_sensor_entity_id = None
        self._last_seen_temp_sensor_entity_id = None
        self._ext_temp_sensor_entity_id = None
        self._last_ext_temperature_measure = None
        self._last_temperature_measure = None
        self._cur_ext_temp = None
        self._presence_state = None
        self._overpowering_state = None
        self._should_relaunch_control_heating = None

        self._security_delay_min = None
        self._security_min_on_percent = None
        self._security_default_on_percent = None
        self._security_state = None

        self._thermostat_type = None

        self._attr_translation_key = "versatile_thermostat"

        self._total_energy = None

        # because energy of climate is calculated in the thermostat we have to keep that here and not in underlying entity
        self._underlying_climate_start_hvac_action_date = None
        self._underlying_climate_delta_t = 0

        self._window_sensor_entity_id = None
        self._window_delay_sec = None
        self._window_auto_open_threshold = 0
        self._window_auto_close_threshold = 0
        self._window_auto_max_duration = 0
        self._window_auto_state = False
        self._window_auto_on = False
        self._window_auto_algo = None
        self._window_bypass_state = False
        self._window_action = None

        self._current_tz = dt_util.get_time_zone(self._hass.config.time_zone)

        self._last_change_time = None

        self._underlyings: list[T] = []

        self._ema_temp = None
        self._ema_algo = None
        self._now = None

        self._attr_fan_mode = None

        self._is_central_mode = None
        self._last_central_mode = None
        self._is_used_by_central_boiler = False

        self._support_flags = None
        # Preset will be initialized from Number entities
        self._presets: dict[str, Any] = {}  # presets
        self._presets_away: dict[str, Any] = {}  # presets_away

        self._attr_preset_modes: list[str] = []

        self._use_central_config_temperature = False

        self.post_init(entry_infos)

    def clean_central_config_doublon(
        self, config_entry: ConfigData, central_config: ConfigEntry | None
    ) -> dict[str, Any]:
        """Removes all values from config with are concerned by central_config"""

        def clean_one(cfg, schema: vol.Schema):
            """Clean one schema"""
            for key, _ in schema.schema.items():
                if key in cfg:
                    del cfg[key]

        cfg = config_entry.copy()
        if central_config and central_config.data:
            # Removes config if central is used
            if cfg.get(CONF_USE_MAIN_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_MAIN_DATA_SCHEMA)

            if cfg.get(CONF_USE_TPI_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_TPI_DATA_SCHEMA)

            if cfg.get(CONF_USE_WINDOW_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_WINDOW_DATA_SCHEMA)

            if cfg.get(CONF_USE_MOTION_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_MOTION_DATA_SCHEMA)

            if cfg.get(CONF_USE_POWER_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_POWER_DATA_SCHEMA)

            if cfg.get(CONF_USE_PRESENCE_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_PRESENCE_DATA_SCHEMA)

            if cfg.get(CONF_USE_ADVANCED_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_ADVANCED_DATA_SCHEMA)

            # take all central config
            entry_infos = central_config.data.copy()
            # and merge with cleaned config_entry
            entry_infos.update(cfg)
        else:
            entry_infos = cfg

        return entry_infos

    def post_init(self, config_entry: ConfigData):
        """Finish the initialization of the thermostast"""

        _LOGGER.info(
            "%s - Updating VersatileThermostat with infos %s",
            self,
            config_entry,
        )

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        central_config = api.find_central_configuration()

        entry_infos = self.clean_central_config_doublon(config_entry, central_config)

        _LOGGER.info("%s - The merged configuration is %s", self, entry_infos)

        self._entry_infos = entry_infos

        self._use_central_config_temperature = entry_infos.get(
            CONF_USE_PRESETS_CENTRAL_CONFIG
        ) or (
            entry_infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG)
            and entry_infos.get(CONF_USE_PRESENCE_FEATURE)
        )

        self._ac_mode = entry_infos.get(CONF_AC_MODE) is True
        self._attr_max_temp = entry_infos.get(CONF_TEMP_MAX)
        self._attr_min_temp = entry_infos.get(CONF_TEMP_MIN)
        if (step := entry_infos.get(CONF_STEP_TEMPERATURE)) is not None:
            self._attr_target_temperature_step = step

        self._attr_preset_modes: list[str] | None

        if self._window_call_cancel is not None:
            self._window_call_cancel()
            self._window_call_cancel = None
        if self._motion_call_cancel is not None:
            self._motion_call_cancel()
            self._motion_call_cancel = None

        self._cycle_min = entry_infos.get(CONF_CYCLE_MIN)

        # Initialize underlying entities (will be done in subclasses)
        self._underlyings = []

        self._proportional_function = entry_infos.get(CONF_PROP_FUNCTION)
        self._temp_sensor_entity_id = entry_infos.get(CONF_TEMP_SENSOR)
        self._last_seen_temp_sensor_entity_id = entry_infos.get(
            CONF_LAST_SEEN_TEMP_SENSOR
        )
        self._ext_temp_sensor_entity_id = entry_infos.get(CONF_EXTERNAL_TEMP_SENSOR)
        self._power_sensor_entity_id = entry_infos.get(CONF_POWER_SENSOR)
        self._max_power_sensor_entity_id = entry_infos.get(CONF_MAX_POWER_SENSOR)
        self._window_sensor_entity_id = entry_infos.get(CONF_WINDOW_SENSOR)
        self._window_delay_sec = entry_infos.get(CONF_WINDOW_DELAY)

        self._window_auto_open_threshold = entry_infos.get(
            CONF_WINDOW_AUTO_OPEN_THRESHOLD
        )
        self._window_auto_close_threshold = entry_infos.get(
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD
        )
        self._window_auto_max_duration = entry_infos.get(CONF_WINDOW_AUTO_MAX_DURATION)
        self._window_auto_on = (
            self._window_sensor_entity_id is None
            and self._window_auto_open_threshold is not None
            and self._window_auto_open_threshold > 0.0
            and self._window_auto_close_threshold is not None
            and self._window_auto_max_duration is not None
            and self._window_auto_max_duration > 0
        )
        self._window_auto_state = False
        self._window_auto_algo = WindowOpenDetectionAlgorithm(
            alert_threshold=self._window_auto_open_threshold,
            end_alert_threshold=self._window_auto_close_threshold,
        )

        self._motion_sensor_entity_id = entry_infos.get(CONF_MOTION_SENSOR)
        self._motion_delay_sec = entry_infos.get(CONF_MOTION_DELAY)
        self._motion_off_delay_sec = entry_infos.get(CONF_MOTION_OFF_DELAY)
        if not self._motion_off_delay_sec:
            self._motion_off_delay_sec = self._motion_delay_sec

        self._motion_preset = entry_infos.get(CONF_MOTION_PRESET)
        self._no_motion_preset = entry_infos.get(CONF_NO_MOTION_PRESET)
        self._motion_on = (
            self._motion_sensor_entity_id is not None
            and self._motion_preset is not None
            and self._no_motion_preset is not None
        )

        self._tpi_coef_int = entry_infos.get(CONF_TPI_COEF_INT)
        self._tpi_coef_ext = entry_infos.get(CONF_TPI_COEF_EXT)
        self._presence_sensor_entity_id = entry_infos.get(CONF_PRESENCE_SENSOR)
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._presence_on = (
            entry_infos.get(CONF_USE_PRESENCE_FEATURE, False)
            and self._presence_sensor_entity_id is not None
        )

        if self._ac_mode:
            # Added by https://github.com/jmcollin78/versatile_thermostat/pull/144
            # Some over_switch can do both heating and cooling
            self._hvac_list = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        else:
            self._hvac_list = [HVACMode.HEAT, HVACMode.OFF]

        self._unit = self._hass.config.units.temperature_unit
        # Will be restored if possible
        self._hvac_mode = None  # HVAC_MODE_OFF
        self._saved_hvac_mode = self._hvac_mode

        self._support_flags = SUPPORT_FLAGS

        # Preset will be initialized from Number entities
        self._presets: dict[str, Any] = {}  # presets
        self._presets_away: dict[str, Any] = {}  # presets_away

        # Will be restored if possible
        self._attr_preset_mode = PRESET_NONE
        self._saved_preset_mode = PRESET_NONE

        # Power management
        self._device_power = entry_infos.get(CONF_DEVICE_POWER) or 0
        self._pmax_on = False
        self._current_power = None
        self._current_power_max = None
        if (
            self._max_power_sensor_entity_id
            and self._power_sensor_entity_id
            and self._device_power
        ):
            self._pmax_on = True
        else:
            _LOGGER.info("%s - Power management is not fully configured", self)

        # will be restored if possible
        self._target_temp = None
        self._saved_target_temp = PRESET_NONE
        self._humidity = None
        self._fan_mode = None
        self._swing_mode = None
        self._cur_temp = None
        self._cur_ext_temp = None

        # Fix parameters for TPI
        if (
            self._proportional_function == PROPORTIONAL_FUNCTION_TPI
            and self._ext_temp_sensor_entity_id is None
        ):
            _LOGGER.warning(
                "Using TPI function but not external temperature sensor is set. Removing the delta temp ext factor. Thermostat will not be fully operationnal"  # pylint: disable=line-too-long
            )
            self._tpi_coef_ext = 0

        self._security_delay_min = entry_infos.get(CONF_SECURITY_DELAY_MIN)
        self._security_min_on_percent = (
            entry_infos.get(CONF_SECURITY_MIN_ON_PERCENT)
            if entry_infos.get(CONF_SECURITY_MIN_ON_PERCENT) is not None
            else DEFAULT_SECURITY_MIN_ON_PERCENT
        )
        self._security_default_on_percent = (
            entry_infos.get(CONF_SECURITY_DEFAULT_ON_PERCENT)
            if entry_infos.get(CONF_SECURITY_DEFAULT_ON_PERCENT) is not None
            else DEFAULT_SECURITY_DEFAULT_ON_PERCENT
        )
        self._minimal_activation_delay = entry_infos.get(CONF_MINIMAL_ACTIVATION_DELAY)
        self._last_temperature_measure = datetime.now(tz=self._current_tz)
        self._last_ext_temperature_measure = datetime.now(tz=self._current_tz)
        self._security_state = False

        # Initiate the ProportionalAlgorithm
        if self._prop_algorithm is not None:
            del self._prop_algorithm

        # Memory synthesis state
        self._motion_state = None
        self._window_state = None
        self._overpowering_state = None
        self._presence_state = None

        self._total_energy = None

        # Read the parameter from configuration.yaml if it exists
        short_ema_params = DEFAULT_SHORT_EMA_PARAMS
        if api is not None and api.short_ema_params:
            short_ema_params = api.short_ema_params

        self._ema_algo = ExponentialMovingAverage(
            self.name,
            short_ema_params.get("halflife_sec"),
            # Needed for time calculation
            get_tz(self._hass),
            # two digits after the coma for temperature slope calculation
            short_ema_params.get("precision"),
            short_ema_params.get("max_alpha"),
        )

        self._is_central_mode = not (
            entry_infos.get(CONF_USE_CENTRAL_MODE) is False
        )  # Default value (None) is True

        self._is_used_by_central_boiler = (
            entry_infos.get(CONF_USED_BY_CENTRAL_BOILER) is True
        )

        self._window_action = (
            entry_infos.get(CONF_WINDOW_ACTION) or CONF_WINDOW_TURN_OFF
        )

        _LOGGER.debug(
            "%s - Creation of a new VersatileThermostat entity: unique_id=%s",
            self,
            self.unique_id,
        )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._temp_sensor_entity_id],
                self._async_temperature_changed,
            )
        )

        if self._last_seen_temp_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._last_seen_temp_sensor_entity_id],
                    self._async_last_seen_temperature_changed,
                )
            )

        if self._ext_temp_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._ext_temp_sensor_entity_id],
                    self._async_ext_temperature_changed,
                )
            )

        if self._window_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._window_sensor_entity_id],
                    self._async_windows_changed,
                )
            )
        if self._motion_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._motion_sensor_entity_id],
                    self._async_motion_changed,
                )
            )

        if self._power_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._power_sensor_entity_id],
                    self._async_power_changed,
                )
            )

        if self._max_power_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._max_power_sensor_entity_id],
                    self._async_max_power_changed,
                )
            )

        if self._presence_on:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._presence_sensor_entity_id],
                    self._async_presence_changed,
                )
            )

        self.async_on_remove(self.remove_thermostat)

        # issue 428. Link to others entities will start at link
        # await self.async_startup()

    def remove_thermostat(self):
        """Called when the thermostat will be removed"""
        _LOGGER.info("%s - Removing thermostat", self)
        for under in self._underlyings:
            under.remove_entity()

    async def async_startup(self, central_configuration):
        """Triggered on startup, used to get old state and set internal states accordingly"""
        _LOGGER.debug("%s - Calling async_startup", self)

        _LOGGER.debug("%s - Calling async_startup_internal", self)
        need_write_state = False

        await self.get_my_previous_state()

        await self.init_presets(central_configuration)

        # Initialize all UnderlyingEntities
        self.init_underlyings()

        temperature_state = self.hass.states.get(self._temp_sensor_entity_id)
        if temperature_state and temperature_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            _LOGGER.debug(
                "%s - temperature sensor have been retrieved: %.1f",
                self,
                float(temperature_state.state),
            )
            await self._async_update_temp(temperature_state)
            need_write_state = True

        if self._ext_temp_sensor_entity_id:
            ext_temperature_state = self.hass.states.get(
                self._ext_temp_sensor_entity_id
            )
            if ext_temperature_state and ext_temperature_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug(
                    "%s - external temperature sensor have been retrieved: %.1f",
                    self,
                    float(ext_temperature_state.state),
                )
                await self._async_update_ext_temp(ext_temperature_state)
            else:
                _LOGGER.debug(
                    "%s - external temperature sensor have NOT been retrieved cause unknown or unavailable",
                    self,
                )
        else:
            _LOGGER.debug(
                "%s - external temperature sensor have NOT been retrieved cause no external sensor",
                self,
            )

        if self._pmax_on:
            # try to acquire current power and power max
            current_power_state = self.hass.states.get(self._power_sensor_entity_id)
            if current_power_state and current_power_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._current_power = float(current_power_state.state)
                _LOGGER.debug(
                    "%s - Current power have been retrieved: %.3f",
                    self,
                    self._current_power,
                )
                need_write_state = True

            # Try to acquire power max
            current_power_max_state = self.hass.states.get(
                self._max_power_sensor_entity_id
            )
            if current_power_max_state and current_power_max_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._current_power_max = float(current_power_max_state.state)
                _LOGGER.debug(
                    "%s - Current power max have been retrieved: %.3f",
                    self,
                    self._current_power_max,
                )
                need_write_state = True

        # try to acquire window entity state
        if self._window_sensor_entity_id:
            window_state = self.hass.states.get(self._window_sensor_entity_id)
            if window_state and window_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._window_state = window_state.state == STATE_ON
                _LOGGER.debug(
                    "%s - Window state have been retrieved: %s",
                    self,
                    self._window_state,
                )
                need_write_state = True

        # try to acquire motion entity state
        if self._motion_sensor_entity_id:
            motion_state = self.hass.states.get(self._motion_sensor_entity_id)
            if motion_state and motion_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._motion_state = motion_state.state
                _LOGGER.debug(
                    "%s - Motion state have been retrieved: %s",
                    self,
                    self._motion_state,
                )
                # recalculate the right target_temp in activity mode
                await self._async_update_motion_temp()
                need_write_state = True

        if self._presence_on:
            # try to acquire presence entity state
            presence_state = self.hass.states.get(self._presence_sensor_entity_id)
            if presence_state and presence_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                await self._async_update_presence(presence_state.state)
                _LOGGER.debug(
                    "%s - Presence have been retrieved: %s",
                    self,
                    presence_state.state,
                )
                need_write_state = True

        if need_write_state:
            self.async_write_ha_state()
            if self._prop_algorithm:
                self._prop_algorithm.calculate(
                    self._target_temp,
                    self._cur_temp,
                    self._cur_ext_temp,
                    self._hvac_mode or HVACMode.OFF,
                )

        self.hass.create_task(self._check_initial_state())

        self.reset_last_change_time()

        # if self.hass.state == CoreState.running:
        #     await _async_startup_internal()
        # else:
        #     self.hass.bus.async_listen_once(
        #         EVENT_HOMEASSISTANT_START, _async_startup_internal
        #     )

    def init_underlyings(self):
        """Initialize all underlyings. Should be overriden if necessary"""

    def restore_specific_previous_state(self, old_state: State):
        """Should be overriden in each specific thermostat
        if a specific previous state or attribute should be
        restored
        """

    async def get_my_previous_state(self):
        """Try to get my previou state"""
        # Check If we have an old state
        old_state = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling get_my_previous_state old_state is %s", self, old_state
        )
        if old_state is not None:
            # If we have no initial temperature, restore
            if self._target_temp is None:
                # If we have a previously saved temperature
                if old_state.attributes.get(ATTR_TEMPERATURE) is None:
                    if self._ac_mode:
                        await self._async_internal_set_temperature(self.max_temp)
                    else:
                        await self._async_internal_set_temperature(self.min_temp)
                    _LOGGER.warning(
                        "%s - Undefined target temperature, falling back to %s",
                        self,
                        self._target_temp,
                    )
                else:
                    await self._async_internal_set_temperature(
                        float(old_state.attributes[ATTR_TEMPERATURE])
                    )

            old_preset_mode = old_state.attributes.get(ATTR_PRESET_MODE)
            # Never restore a Power or Security preset
            if old_preset_mode is not None and old_preset_mode not in HIDDEN_PRESETS:
                # old_preset_mode in self._attr_preset_modes
                self._attr_preset_mode = old_preset_mode
                self.save_preset_mode()
            else:
                self._attr_preset_mode = PRESET_NONE

            if old_state.state in [
                HVACMode.OFF,
                HVACMode.HEAT,
                HVACMode.COOL,
            ]:
                self._hvac_mode = old_state.state
            else:
                if not self._hvac_mode:
                    self._hvac_mode = HVACMode.OFF

            old_total_energy = old_state.attributes.get(ATTR_TOTAL_ENERGY)
            self._total_energy = old_total_energy if old_total_energy else 0

            self.restore_specific_previous_state(old_state)
        else:
            # No previous state, try and restore defaults
            if self._target_temp is None:
                if self._ac_mode:
                    await self._async_internal_set_temperature(self.max_temp)
                else:
                    await self._async_internal_set_temperature(self.min_temp)
            _LOGGER.warning(
                "No previously saved temperature, setting to %s", self._target_temp
            )
            self._total_energy = 0

        self._saved_target_temp = self._target_temp

        # Set default state to off
        if not self._hvac_mode:
            self._hvac_mode = HVACMode.OFF

        self.send_event(EventType.PRESET_EVENT, {"preset": self._attr_preset_mode})
        self.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": self._hvac_mode})

        _LOGGER.info(
            "%s - restored state is target_temp=%.1f, preset_mode=%s, hvac_mode=%s",
            self,
            self._target_temp,
            self._attr_preset_mode,
            self._hvac_mode,
        )

    def __str__(self) -> str:
        return f"VersatileThermostat-{self.name}"

    @property
    def is_over_climate(self) -> bool:
        """True if the Thermostat is over_climate"""
        return False

    @property
    def is_over_switch(self) -> bool:
        """True if the Thermostat is over_switch"""
        return False

    @property
    def is_over_valve(self) -> bool:
        """True if the Thermostat is over_valve"""
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._unique_id)},
            name=self._name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return self._name

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """List of available operation modes."""
        return self._hvac_list

    @property
    def ac_mode(self) -> bool:
        """Get the ac_mode of the Themostat"""
        return self._ac_mode

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting.

        Requires ClimateEntityFeature.FAN_MODE.
        """
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes.

        Requires ClimateEntityFeature.FAN_MODE.
        """
        return []

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        return None

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        return None

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self._unit

    @property
    def ema_temperature(self) -> str:
        """Return the EMA temperature."""
        return self._ema_temp

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current operation."""
        # Issue #114 - returns my current hvac_mode and not the underlying hvac_mode which could be different
        # delta will be managed by climate_state_change event.
        # if self.is_over_climate:
        # if one not OFF -> return it
        # else OFF
        #    for under in self._underlyings:
        #        if (mode := under.hvac_mode) not in [HVACMode.OFF]
        #            return mode
        #    return HVACMode.OFF

        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported.
        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVACMode.OFF:
            action = HVACAction.OFF
        elif not self.is_device_active:
            action = HVACAction.IDLE
        elif self._hvac_mode == HVACMode.COOL:
            action = HVACAction.COOLING
        else:
            action = HVACAction.HEATING
        return action

    @property
    def is_used_by_central_boiler(self) -> HVACAction | None:
        """Return true is the VTherm is configured to be used by
        central boiler"""
        return self._is_used_by_central_boiler

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return self._support_flags

    @property
    def is_device_active(self) -> bool:
        """Returns true if one underlying is active"""
        for under in self._underlyings:
            if under.is_device_active:
                return True
        return False

    @property
    def current_temperature(self) -> float | None:
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def is_aux_heat(self) -> bool | None:
        """Return true if aux heater.

        Requires ClimateEntityFeature.AUX_HEAT.
        """
        return None

    @property
    def mean_cycle_power(self) -> float | None:
        """Returns the mean power consumption during the cycle"""
        if not self._device_power:
            return None

        return float(self._device_power * self._prop_algorithm.on_percent)

    @property
    def total_energy(self) -> float | None:
        """Returns the total energy calculated for this thermostast"""
        if self._total_energy is not None:
            return round(self._total_energy, 2)
        else:
            return None

    @property
    def device_power(self) -> float | None:
        """Returns the device_power for this thermostast"""
        return self._device_power

    @property
    def overpowering_state(self) -> bool | None:
        """Get the overpowering_state"""
        return self._overpowering_state

    @property
    def window_state(self) -> str | None:
        """Get the window_state"""
        return STATE_ON if self._window_state else STATE_OFF

    @property
    def window_auto_state(self) -> str | None:
        """Get the window_auto_state"""
        return STATE_ON if self._window_auto_state else STATE_OFF

    @property
    def window_bypass_state(self) -> bool | None:
        """Get the Window Bypass"""
        return self._window_bypass_state

    @property
    def window_action(self) -> bool | None:
        """Get the Window Action"""
        return self._window_action

    @property
    def security_state(self) -> bool | None:
        """Get the security_state"""
        return self._security_state

    @property
    def motion_state(self) -> bool | None:
        """Get the motion_state"""
        return self._motion_state

    @property
    def presence_state(self) -> bool | None:
        """Get the presence_state"""
        return self._presence_state

    @property
    def proportional_algorithm(self) -> PropAlgorithm | None:
        """Get the eventual ProportionalAlgorithm"""
        return self._prop_algorithm

    @property
    def last_temperature_measure(self) -> datetime | None:
        """Get the last temperature datetime"""
        return self._last_temperature_measure

    @property
    def last_ext_temperature_measure(self) -> datetime | None:
        """Get the last external temperature datetime"""
        return self._last_ext_temperature_measure

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp.

        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._attr_preset_mode

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes.
        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._attr_preset_modes

    @property
    def last_temperature_slope(self) -> float | None:
        """Return the last temperature slope curve if any"""
        if not self._window_auto_algo:
            return None
        else:
            return self._window_auto_algo.last_slope

    @property
    def is_window_auto_enabled(self) -> bool:
        """True if the Window auto feature is enabled"""
        return self._window_auto_on

    @property
    def nb_underlying_entities(self) -> int:
        """Returns the number of underlying entities"""
        return len(self._underlyings)

    @property
    def underlying_entities(self) -> list | None:
        """Returns the underlying entities"""
        return self._underlyings

    def find_underlying_by_entity_id(self, entity_id: str) -> Entity | None:
        """Get the underlying entity by a entity_id"""
        for under in self._underlyings:
            if under.entity_id == entity_id:
                return under
        return None

    @property
    def is_on(self) -> bool:
        """True if the VTherm is on (! HVAC_OFF)"""
        return self.hvac_mode and self.hvac_mode != HVACMode.OFF

    @property
    def is_controlled_by_central_mode(self) -> bool:
        """Returns True if this VTherm can be controlled by the central_mode"""
        return self._is_central_mode

    @property
    def last_central_mode(self) -> str | None:
        """Returns the last central_mode taken into account.
        Is None if the VTherm is not controlled by central_mode"""
        return self._last_central_mode

    @property
    def use_central_config_temperature(self):
        """True if this VTHerm uses the central configuration temperature"""
        return self._use_central_config_temperature

    def underlying_entity_id(self, index=0) -> str | None:
        """The climate_entity_id. Added for retrocompatibility reason"""
        if index < self.nb_underlying_entities:
            return self.underlying_entity(index).entity_id
        else:
            return None

    def underlying_entity(self, index=0) -> UnderlyingEntity | None:
        """Get the underlying entity at specified index"""
        if index < self.nb_underlying_entities:
            return self._underlyings[index]
        else:
            return None

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        raise NotImplementedError()

    @overrides
    async def async_turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        raise NotImplementedError()

    @overrides
    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        raise NotImplementedError()

    @overrides
    async def async_turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        raise NotImplementedError()

    @overrides
    async def async_set_hvac_mode(self, hvac_mode: HVACMode, need_control_heating=True):
        """Set new target hvac mode."""
        _LOGGER.info("%s - Set hvac mode: %s", self, hvac_mode)

        if hvac_mode is None:
            return

        self._hvac_mode = hvac_mode

        # Delegate to all underlying
        sub_need_control_heating = False
        for under in self._underlyings:
            sub_need_control_heating = (
                await under.set_hvac_mode(hvac_mode) or need_control_heating
            )

        # If AC is on maybe we have to change the temperature in force mode, but not in frost mode (there is no Frost protection possible in AC mode)
        if self._hvac_mode in [HVACMode.COOL, HVACMode.HEAT, HVACMode.HEAT_COOL] and self.preset_mode != PRESET_NONE:
            if self.preset_mode != PRESET_FROST_PROTECTION:
                await self._async_set_preset_mode_internal(self.preset_mode, True)
            else:
                await self._async_set_preset_mode_internal(PRESET_ECO, True, False)

        if need_control_heating and sub_need_control_heating:
            await self.async_control_heating(force=True)

        # Ensure we update the current operation after changing the mode
        self.reset_last_temperature_time()

        self.reset_last_change_time()

        self.update_custom_attributes()
        self.async_write_ha_state()
        self.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": self._hvac_mode})

    @overrides
    async def async_set_preset_mode(
        self, preset_mode: str, overwrite_saved_preset=True
    ):
        """Set new preset mode."""

        # Wer accept a new preset when:
        # 1. last_central_mode is not set,
        # 2. or last_central_mode is AUTO,
        # 3. or last_central_mode is CENTRAL_MODE_FROST_PROTECTION and preset_mode is PRESET_FROST_PROTECTION (to be abel to re-set the preset_mode)
        accept = self._last_central_mode in [
            None,
            CENTRAL_MODE_AUTO,
            CENTRAL_MODE_COOL_ONLY,
            CENTRAL_MODE_HEAT_ONLY,
            CENTRAL_MODE_STOPPED,
        ] or (
            self._last_central_mode == CENTRAL_MODE_FROST_PROTECTION
            and preset_mode == PRESET_FROST_PROTECTION
        )
        if not accept:
            _LOGGER.info(
                "%s - Impossible to change the preset to %s because central mode is %s",
                self,
                preset_mode,
                self._last_central_mode,
            )

            return

        await self._async_set_preset_mode_internal(
            preset_mode, force=False, overwrite_saved_preset=overwrite_saved_preset
        )
        await self.async_control_heating(force=True)

    async def _async_set_preset_mode_internal(
        self, preset_mode: str, force=False, overwrite_saved_preset=True
    ):
        """Set new preset mode."""
        _LOGGER.info("%s - Set preset_mode: %s force=%s", self, preset_mode, force)
        if (
            preset_mode not in (self._attr_preset_modes or [])
            and preset_mode not in HIDDEN_PRESETS
        ):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self._attr_preset_modes}"  # pylint: disable=line-too-long
            )

        old_preset_mode = self._attr_preset_mode
        if preset_mode == old_preset_mode and not force:
            # I don't think we need to call async_write_ha_state if we didn't change the state
            return

        # In safety mode don't change preset but memorise the new expected preset when security will be off
        if preset_mode != PRESET_SECURITY and self._security_state:
            _LOGGER.debug(
                "%s - is in safety mode. Just memorise the new expected ", self
            )
            if preset_mode not in HIDDEN_PRESETS:
                self._saved_preset_mode = preset_mode
            return

        old_preset_mode = self._attr_preset_mode
        if preset_mode == PRESET_NONE:
            self._attr_preset_mode = PRESET_NONE
            if self._saved_target_temp:
                await self._async_internal_set_temperature(self._saved_target_temp)
        elif preset_mode == PRESET_ACTIVITY:
            self._attr_preset_mode = PRESET_ACTIVITY
            await self._async_update_motion_temp()
        else:
            if self._attr_preset_mode == PRESET_NONE:
                self._saved_target_temp = self._target_temp
            self._attr_preset_mode = preset_mode
            await self._async_internal_set_temperature(
                self.find_preset_temp(preset_mode)
            )

        self.reset_last_temperature_time(old_preset_mode)

        if overwrite_saved_preset:
            self.save_preset_mode()

        self.recalculate()
        # Notify only if there was a real change
        if self._attr_preset_mode != old_preset_mode:
            self.send_event(EventType.PRESET_EVENT, {"preset": self._attr_preset_mode})

    def reset_last_change_time(
        self, old_preset_mode: str | None = None
    ):  # pylint: disable=unused-argument
        """Reset to now the last change time"""
        self._last_change_time = datetime.now(tz=self._current_tz)
        _LOGGER.debug("%s - last_change_time is now %s", self, self._last_change_time)

    def reset_last_temperature_time(self, old_preset_mode: str | None = None):
        """Reset to now the last temperature time if conditions are satisfied"""
        if (
            self._attr_preset_mode not in HIDDEN_PRESETS
            and old_preset_mode not in HIDDEN_PRESETS
        ):
            self._last_temperature_measure = self._last_ext_temperature_measure = (
                datetime.now(tz=self._current_tz)
            )

    def find_preset_temp(self, preset_mode: str):
        """Find the right temperature of a preset considering the presence if configured"""
        if preset_mode is None or preset_mode == "none":
            return (
                self._attr_max_temp
                if self._ac_mode and self._hvac_mode == HVACMode.COOL
                else self._attr_min_temp
            )

        if preset_mode == PRESET_SECURITY:
            return (
                self._target_temp
            )  # in security just keep the current target temperature, the thermostat should be off
        if preset_mode == PRESET_POWER:
            return self._power_temp
        if preset_mode == PRESET_ACTIVITY:
            if self._ac_mode and self._hvac_mode == HVACMode.COOL:
                motion_preset = (
                    self._motion_preset + PRESET_AC_SUFFIX
                    if self._motion_state == STATE_ON
                    else self._no_motion_preset + PRESET_AC_SUFFIX
                )
            else:
                motion_preset = (
                    self._motion_preset
                    if self._motion_state == STATE_ON
                    else self._no_motion_preset
                )

            if motion_preset in self._presets:
                return self._presets[motion_preset]
            else:
                return None
        else:
            # Select _ac presets if in COOL Mode (or over_switch with _ac_mode)
            if self._ac_mode and self._hvac_mode == HVACMode.COOL:
                preset_mode = preset_mode + PRESET_AC_SUFFIX

            _LOGGER.info("%s - find preset temp: %s", self, preset_mode)

            temp_val = self._presets.get(preset_mode, 0)
            if not self._presence_on or self._presence_state in [
                None,
                STATE_ON,
                STATE_HOME,
            ]:
                return temp_val
            else:
                # We should return the preset_away temp val but if
                # preset temp is 0, that means the user don't want to use
                # the preset so we return 0, even if there is a value is preset_away
                return (
                    self._presets_away.get(self.get_preset_away_name(preset_mode), 0)
                    if temp_val > 0
                    else temp_val
                )

    def get_preset_away_name(self, preset_mode: str) -> str:
        """Get the preset name in away mode (when presence is off)"""
        return preset_mode + PRESET_AWAY_SUFFIX

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        _LOGGER.info("%s - Set fan mode: %s", self, fan_mode)
        return

    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set fan mode: %s", self, humidity)
        return

    async def async_set_swing_mode(self, swing_mode: str):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set fan mode: %s", self, swing_mode)
        return

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.info("%s - Set target temp: %s", self, temperature)
        if temperature is None:
            return
        await self._async_internal_set_temperature(temperature)
        self._attr_preset_mode = PRESET_NONE
        self.recalculate()
        self.reset_last_change_time()
        await self.async_control_heating(force=True)

    async def _async_internal_set_temperature(self, temperature: float):
        """Set the target temperature and the target temperature of underlying climate if any
        For testing purpose you can pass an event_timestamp.
        """
        if temperature:
            self._target_temp = temperature
        return

    def get_state_date_or_now(self, state: State) -> datetime:
        """Extract the last_changed state from State or return now if not available"""
        return (
            state.last_changed.astimezone(self._current_tz)
            if state.last_changed is not None
            else datetime.now(tz=self._current_tz)
        )

    def get_last_updated_date_or_now(self, state: State) -> datetime:
        """Extract the last_changed state from State or return now if not available"""
        return (
            state.last_updated.astimezone(self._current_tz)
            if state.last_updated is not None
            else datetime.now(tz=self._current_tz)
        )

    @callback
    async def entry_update_listener(
        self, _, config_entry: ConfigEntry  # hass: HomeAssistant,
    ) -> None:
        """Called when the entry have changed in ConfigFlow"""
        _LOGGER.info("%s - Change entry with the values: %s", self, config_entry.data)

    @callback
    async def _async_temperature_changed(self, event: Event):
        """Handle temperature of the temperature sensor changes."""
        new_state: State = event.data.get("new_state")
        _LOGGER.debug(
            "%s - Temperature changed. Event.new_state is %s",
            self,
            new_state,
        )
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        dearm_window_auto = await self._async_update_temp(new_state)
        self.recalculate()
        await self.async_control_heating(force=False)
        return dearm_window_auto

    @callback
    async def _async_last_seen_temperature_changed(self, event: Event):
        """Handle last seen temperature sensor changes."""
        new_state: State = event.data.get("new_state")
        _LOGGER.debug(
            "%s - Last seen temperature changed. Event.new_state is %s",
            self,
            new_state,
        )
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        # try to extract the datetime (from state)
        try:
            # Convertir la chaîne au format ISO 8601 en objet datetime
            self._last_temperature_measure = self.get_last_updated_date_or_now(
                new_state
            )
            self.reset_last_change_time()
            _LOGGER.debug(
                "%s - new last_temperature_measure is now: %s",
                self,
                self._last_temperature_measure,
            )

            # try to restart if we were in safety mode
            if self._security_state:
                await self.check_safety()

        except ValueError as err:
            # La conversion a échoué, la chaîne n'est pas au format ISO 8601
            _LOGGER.warning(
                "%s - impossible to convert last seen datetime %s. Error is: %s",
                self,
                new_state.state,
                err,
            )

    async def _async_ext_temperature_changed(self, event: Event):
        """Handle external temperature opf the sensor changes."""
        new_state: State = event.data.get("new_state")
        _LOGGER.debug(
            "%s - external Temperature changed. Event.new_state is %s",
            self,
            new_state,
        )
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        await self._async_update_ext_temp(new_state)
        self.recalculate()
        await self.async_control_heating(force=False)

    @callback
    async def _async_windows_changed(self, event):
        """Handle window changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        _LOGGER.info(
            "%s - Window changed. Event.new_state is %s, _hvac_mode=%s, _saved_hvac_mode=%s",
            self,
            new_state,
            self._hvac_mode,
            self._saved_hvac_mode,
        )

        # Check delay condition
        async def try_window_condition(_):
            try:
                long_enough = condition.state(
                    self.hass,
                    self._window_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=self._window_delay_sec),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Window delay condition is not satisfied. Ignore window event"
                )
                self._window_state = old_state.state == STATE_ON
                return

            _LOGGER.debug("%s - Window delay condition is satisfied", self)
            # if not self._saved_hvac_mode:
            #    self._saved_hvac_mode = self._hvac_mode

            if self._window_state == (new_state.state == STATE_ON):
                _LOGGER.debug("%s - no change in window state. Forget the event")
                return

            self._window_state = new_state.state == STATE_ON

            _LOGGER.debug("%s - Window ByPass is : %s", self, self._window_bypass_state)
            if self._window_bypass_state:
                _LOGGER.info(
                    "%s - Window ByPass is activated. Ignore window event", self
                )
            else:
                await self.change_window_detection_state(self._window_state)

            self.update_custom_attributes()

        if new_state is None or old_state is None or new_state.state == old_state.state:
            return try_window_condition

        if self._window_call_cancel:
            self._window_call_cancel()
            self._window_call_cancel = None
        self._window_call_cancel = async_call_later(
            self.hass, timedelta(seconds=self._window_delay_sec), try_window_condition
        )
        # For testing purpose we need to access the inner function
        return try_window_condition

    @callback
    async def _async_motion_changed(self, event):
        """Handle motion changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Motion changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._attr_preset_mode,
            PRESET_ACTIVITY,
        )

        if new_state is None or new_state.state not in (STATE_OFF, STATE_ON):
            return

        # Check delay condition
        async def try_motion_condition(_):
            try:
                delay = (
                    self._motion_delay_sec
                    if new_state.state == STATE_ON
                    else self._motion_off_delay_sec
                )
                long_enough = condition.state(
                    self.hass,
                    self._motion_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=delay),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Motion delay condition is not satisfied. Ignore motion event"
                )
            else:
                _LOGGER.debug("%s - Motion delay condition is satisfied", self)
                self._motion_state = new_state.state
                if self._attr_preset_mode == PRESET_ACTIVITY:

                    new_preset = (
                        self._motion_preset
                        if self._motion_state == STATE_ON
                        else self._no_motion_preset
                    )
                    _LOGGER.info(
                        "%s - Motion condition have changes. New preset temp will be %s",
                        self,
                        new_preset,
                    )
                    # We do not change the preset which is kept to ACTIVITY but only the target_temperature
                    # We take the presence into account

                    await self._async_internal_set_temperature(
                        self.find_preset_temp(new_preset)
                    )
                self.recalculate()
                await self.async_control_heating(force=True)
            self._motion_call_cancel = None

        im_on = self._motion_state == STATE_ON
        delay_running = self._motion_call_cancel is not None
        event_on = new_state.state == STATE_ON

        def arm():
            """Arm the timer"""
            delay = (
                self._motion_delay_sec
                if new_state.state == STATE_ON
                else self._motion_off_delay_sec
            )
            self._motion_call_cancel = async_call_later(
                self.hass, timedelta(seconds=delay), try_motion_condition
            )

        def desarm():
            # restart the timer
            self._motion_call_cancel()
            self._motion_call_cancel = None

        # if I'm off
        if not im_on:
            if event_on and not delay_running:
                _LOGGER.debug(
                    "%s - Arm delay cause i'm off and event is on and no delay is running",
                    self,
                )
                arm()
                return try_motion_condition
            # Ignore the event
            _LOGGER.debug("%s - Event ignored cause i'm already off", self)
            return None
        else:  # I'm On
            if not event_on and not delay_running:
                _LOGGER.info("%s - Arm delay cause i'm on and event is off", self)
                arm()
                return try_motion_condition
            if event_on and delay_running:
                _LOGGER.debug(
                    "%s - Desarm off delay cause i'm on and event is on and a delay is running",
                    self,
                )
                desarm()
                return None
            # Ignore the event
            _LOGGER.debug("%s - Event ignored cause i'm already on", self)
            return None

    @callback
    async def _check_initial_state(self):
        """Prevent the device from keep running if HVAC_MODE_OFF."""
        _LOGGER.debug("%s - Calling _check_initial_state", self)
        for under in self._underlyings:
            await under.check_initial_state(self._hvac_mode)

        # Starts the initial control loop (don't wait for an update of temperature)
        await self.async_control_heating(force=True)

    @callback
    async def _async_update_temp(self, state: State):
        """Update thermostat with latest state from sensor."""
        try:
            cur_temp = float(state.state)
            if math.isnan(cur_temp) or math.isinf(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_temp = cur_temp

            self._last_temperature_measure = self.get_state_date_or_now(state)

            # calculate the smooth_temperature with EMA calculation
            self._ema_temp = self._ema_algo.calculate_ema(
                self._cur_temp, self._last_temperature_measure
            )

            _LOGGER.debug(
                "%s - After setting _last_temperature_measure %s , state.last_changed.replace=%s",
                self,
                self._last_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            if self._security_state:
                await self.check_safety()

            # check window_auto
            return await self._async_manage_window_auto()

        except ValueError as ex:
            _LOGGER.error("Unable to update temperature from sensor: %s", ex)

    @callback
    async def _async_update_ext_temp(self, state: State):
        """Update thermostat with latest state from sensor."""
        try:
            cur_ext_temp = float(state.state)
            if math.isnan(cur_ext_temp) or math.isinf(cur_ext_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_ext_temp = cur_ext_temp
            self._last_ext_temperature_measure = self.get_state_date_or_now(state)

            _LOGGER.debug(
                "%s - After setting _last_ext_temperature_measure %s , state.last_changed.replace=%s",
                self,
                self._last_ext_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            if self._security_state:
                await self.check_safety()
        except ValueError as ex:
            _LOGGER.error("Unable to update external temperature from sensor: %s", ex)

    @callback
    async def _async_power_changed(self, event: Event[EventStateChangedData]):
        """Handle power changes."""
        _LOGGER.debug("Thermostat %s - Receive new Power event", self.name)
        _LOGGER.debug(event)
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if (
            new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            or (old_state is not None and new_state.state == old_state.state)
        ):
            return

        try:
            current_power = float(new_state.state)
            if math.isnan(current_power) or math.isinf(current_power):
                raise ValueError(f"Sensor has illegal state {new_state.state}")
            self._current_power = current_power

            if self._attr_preset_mode == PRESET_POWER:
                await self.async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    @callback
    async def _async_max_power_changed(self, event: Event[EventStateChangedData]):
        """Handle power max changes."""
        _LOGGER.debug("Thermostat %s - Receive new Power Max event", self.name)
        _LOGGER.debug(event)
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if (
            new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            or (old_state is not None and new_state.state == old_state.state)
        ):
            return

        try:
            current_power_max = float(new_state.state)
            if math.isnan(current_power_max) or math.isinf(current_power_max):
                raise ValueError(f"Sensor has illegal state {new_state.state}")
            self._current_power_max = current_power_max
            if self._attr_preset_mode == PRESET_POWER:
                await self.async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    @callback
    async def _async_presence_changed(self, event: Event[EventStateChangedData]):
        """Handle presence changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Presence changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._attr_preset_mode,
            PRESET_ACTIVITY,
        )
        if new_state is None:
            return

        await self._async_update_presence(new_state.state)
        await self.async_control_heating(force=True)

    async def _async_update_presence(self, new_state: str):
        _LOGGER.info("%s - Updating presence. New state is %s", self, new_state)
        self._presence_state = (
            STATE_ON if new_state in (STATE_ON, STATE_HOME) else STATE_OFF
        )
        if self._attr_preset_mode in HIDDEN_PRESETS or self._presence_on is False:
            _LOGGER.info(
                "%s - Ignoring presence change cause in Power or Security preset or presence not configured",
                self,
            )
            return
        if new_state is None or new_state not in (
            STATE_OFF,
            STATE_ON,
            STATE_HOME,
            STATE_NOT_HOME,
        ):
            return
        if self._attr_preset_mode not in [PRESET_BOOST, PRESET_COMFORT, PRESET_ECO]:
            return

        new_temp = self.find_preset_temp(self.preset_mode)
        if new_temp is not None:
            _LOGGER.debug(
                "%s - presence change in temperature mode new_temp will be: %.2f",
                self,
                new_temp,
            )
            await self._async_internal_set_temperature(new_temp)
            self.recalculate()

    async def _async_update_motion_temp(self):
        """Update the temperature considering the ACTIVITY preset and current motion state"""
        _LOGGER.debug(
            "%s - Calling _update_motion_temp preset_mode=%s, motion_state=%s",
            self,
            self._attr_preset_mode,
            self._motion_state,
        )
        if (
            self._motion_sensor_entity_id is None
            or self._attr_preset_mode != PRESET_ACTIVITY
        ):
            return

        new_preset = (
                        self._motion_preset
                        if self._motion_state == STATE_ON
                        else self._no_motion_preset
                    )
        _LOGGER.info(
                    "%s - Motion condition have changes. New preset temp will be %s",
                        self,
                        new_preset,
                    )
        # We do not change the preset which is kept to ACTIVITY but only the target_temperature
        # We take the presence into account

        await self._async_internal_set_temperature(
            self.find_preset_temp(new_preset)
        )

        _LOGGER.debug(
            "%s - regarding motion, target_temp have been set to %.2f",
            self,
            self._target_temp,
        )

    async def _async_underlying_entity_turn_off(self):
        """Turn heater toggleable device off. Used by Window, overpowering, control_heating to turn all off"""

        for under in self._underlyings:
            await under.turn_off()

    async def _async_manage_window_auto(self, in_cycle=False):
        """The management of the window auto feature"""

        async def dearm_window_auto(_):
            """Callback that will be called after end of WINDOW_AUTO_MAX_DURATION"""
            _LOGGER.info("Unset window auto because MAX_DURATION is exceeded")
            await deactivate_window_auto(auto=True)

        async def deactivate_window_auto(auto=False):
            """Deactivation of the Window auto state"""
            _LOGGER.warning(
                "%s - End auto detection of open window slope=%.3f", self, slope
            )
            # Send an event
            cause = "max duration expiration" if auto else "end of slope alert"
            self.send_event(
                EventType.WINDOW_AUTO_EVENT,
                {"type": "end", "cause": cause, "curve_slope": slope},
            )
            # Set attributes
            self._window_auto_state = False
            await self.change_window_detection_state(self._window_auto_state)
            # await self.restore_hvac_mode(True)

            if self._window_call_cancel:
                self._window_call_cancel()
            self._window_call_cancel = None

        if not self._window_auto_algo:
            return

        if in_cycle:
            slope = self._window_auto_algo.check_age_last_measurement(
                temperature=self._ema_temp,
                datetime_now=datetime.now(get_tz(self._hass)),
            )
        else:
            slope = self._window_auto_algo.add_temp_measurement(
                temperature=self._ema_temp,
                datetime_measure=self._last_temperature_measure,
            )

        _LOGGER.debug(
            "%s - Window auto is on, check the alert. last slope is %.3f",
            self,
            slope if slope is not None else 0.0,
        )

        if self.window_bypass_state or not self.is_window_auto_enabled:
            _LOGGER.debug(
                "%s - Window auto event is ignored because bypass is ON or window auto detection is disabled",
                self,
            )
            return

        if (
            self._window_auto_algo.is_window_open_detected()
            and self._window_auto_state is False
            and self.hvac_mode != HVACMode.OFF
        ):
            if (
                self.proportional_algorithm
                and self.proportional_algorithm.on_percent <= 0.0
            ):
                _LOGGER.info(
                    "%s - Start auto detection of open window slope=%.3f but no heating detected (on_percent<=0). Forget the event",
                    self,
                    slope,
                )
                return dearm_window_auto

            _LOGGER.warning(
                "%s - Start auto detection of open window slope=%.3f", self, slope
            )

            # Send an event
            self.send_event(
                EventType.WINDOW_AUTO_EVENT,
                {"type": "start", "cause": "slope alert", "curve_slope": slope},
            )
            # Set attributes
            self._window_auto_state = True
            await self.change_window_detection_state(self._window_auto_state)
            # self.save_hvac_mode()
            # await self.async_set_hvac_mode(HVACMode.OFF)

            # Arm the end trigger
            if self._window_call_cancel:
                self._window_call_cancel()
                self._window_call_cancel = None
            self._window_call_cancel = async_call_later(
                self.hass,
                timedelta(minutes=self._window_auto_max_duration),
                dearm_window_auto,
            )

        elif (
            self._window_auto_algo.is_window_close_detected()
            and self._window_auto_state is True
        ):
            await deactivate_window_auto(False)

        # For testing purpose we need to return the inner function
        return dearm_window_auto

    def save_preset_mode(self):
        """Save the current preset mode to be restored later
        We never save a hidden preset mode
        """
        if (
            self._attr_preset_mode not in HIDDEN_PRESETS
            and self._attr_preset_mode is not None
        ):
            self._saved_preset_mode = self._attr_preset_mode

    async def restore_preset_mode(self):
        """Restore a previous preset mode
        We never restore a hidden preset mode. Normally that is not possible
        """
        if (
            self._saved_preset_mode not in HIDDEN_PRESETS
            and self._saved_preset_mode is not None
        ):
            await self._async_set_preset_mode_internal(self._saved_preset_mode)

    def save_hvac_mode(self):
        """Save the current hvac-mode to be restored later"""
        self._saved_hvac_mode = self._hvac_mode
        _LOGGER.debug(
            "%s - Saved hvac mode - saved_hvac_mode is %s, hvac_mode is %s",
            self,
            self._saved_hvac_mode,
            self._hvac_mode,
        )

    async def restore_hvac_mode(self, need_control_heating=False):
        """Restore a previous hvac_mod"""
        await self.async_set_hvac_mode(self._saved_hvac_mode, need_control_heating)
        _LOGGER.debug(
            "%s - Restored hvac_mode - saved_hvac_mode is %s, hvac_mode is %s",
            self,
            self._saved_hvac_mode,
            self._hvac_mode,
        )

    async def check_overpowering(self) -> bool:
        """Check the overpowering condition
        Turn the preset_mode of the heater to 'power' if power conditions are exceeded
        """

        if not self._pmax_on:
            _LOGGER.debug(
                "%s - power not configured. check_overpowering not available", self
            )
            return False

        if (
            self._current_power is None
            or self._device_power is None
            or self._current_power_max is None
        ):
            _LOGGER.warning(
                "%s - power not valued. check_overpowering not available", self
            )
            return False

        _LOGGER.debug(
            "%s - overpowering check: power=%.3f, max_power=%.3f heater power=%.3f",
            self,
            self._current_power,
            self._current_power_max,
            self._device_power,
        )

        # issue 407 - power_consumption_max is power we need to add. If already active we don't need to add more power
        if self.is_device_active:
            power_consumption_max = 0
        else:
            if self.is_over_climate:
                power_consumption_max = self._device_power
            else:
                power_consumption_max = max(
                    self._device_power / self.nb_underlying_entities,
                    self._device_power * self._prop_algorithm.on_percent,
                )

        ret = (self._current_power + power_consumption_max) >= self._current_power_max
        if not self._overpowering_state and ret and self._hvac_mode != HVACMode.OFF:
            _LOGGER.warning(
                "%s - overpowering is detected. Heater preset will be set to 'power'",
                self,
            )
            if self.is_over_climate:
                self.save_hvac_mode()
            self.save_preset_mode()
            await self._async_underlying_entity_turn_off()
            await self._async_set_preset_mode_internal(PRESET_POWER)
            self.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "start",
                    "current_power": self._current_power,
                    "device_power": self._device_power,
                    "current_power_max": self._current_power_max,
                    "current_power_consumption": power_consumption_max,
                },
            )

        # Check if we need to remove the POWER preset
        if (
            self._overpowering_state
            and not ret
            and self._attr_preset_mode == PRESET_POWER
        ):
            _LOGGER.warning(
                "%s - end of overpowering is detected. Heater preset will be restored to '%s'",
                self,
                self._saved_preset_mode,
            )
            if self.is_over_climate:
                await self.restore_hvac_mode(False)
            await self.restore_preset_mode()
            self.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "end",
                    "current_power": self._current_power,
                    "device_power": self._device_power,
                    "current_power_max": self._current_power_max,
                },
            )

        if self._overpowering_state != ret:
            self._overpowering_state = ret
            self.update_custom_attributes()

        return self._overpowering_state

    async def check_central_mode(
        self, new_central_mode: str | None, old_central_mode: str | None
    ):
        """Take into account a central mode change"""
        if not self.is_controlled_by_central_mode:
            self._last_central_mode = None
            return

        _LOGGER.info(
            "%s - Central mode have change from %s to %s",
            self,
            old_central_mode,
            new_central_mode,
        )

        first_init = self._last_central_mode is None

        self._last_central_mode = new_central_mode

        def save_all():
            """save preset and hvac_mode"""
            self.save_preset_mode()
            self.save_hvac_mode()

        if new_central_mode == CENTRAL_MODE_AUTO:
            if self.window_state is not STATE_ON and not first_init:
                await self.restore_hvac_mode()
                await self.restore_preset_mode()

            return

        if old_central_mode == CENTRAL_MODE_AUTO and self.window_state is not STATE_ON:
            save_all()

        if new_central_mode == CENTRAL_MODE_STOPPED:
            await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_COOL_ONLY:
            if HVACMode.COOL in self.hvac_modes:
                await self.async_set_hvac_mode(HVACMode.COOL)
            else:
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_HEAT_ONLY:
            if HVACMode.HEAT in self.hvac_modes:
                await self.async_set_hvac_mode(HVACMode.HEAT)
            else:
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_FROST_PROTECTION:
            if (
                PRESET_FROST_PROTECTION in self.preset_modes
                and HVACMode.HEAT in self.hvac_modes
            ):
                await self.async_set_hvac_mode(HVACMode.HEAT)
                await self.async_set_preset_mode(
                    PRESET_FROST_PROTECTION, overwrite_saved_preset=False
                )
            else:
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

    def _set_now(self, now: datetime):
        """Set the now timestamp. This is only for tests purpose"""
        self._now = now

    @property
    def now(self) -> datetime:
        """Get now. The local datetime or the overloaded _set_now date"""
        return self._now if self._now is not None else datetime.now(self._current_tz)

    async def check_safety(self) -> bool:
        """Check if last temperature date is too long"""
        now = self.now
        delta_temp = (
            now - self._last_temperature_measure.replace(tzinfo=self._current_tz)
        ).total_seconds() / 60.0
        delta_ext_temp = (
            now - self._last_ext_temperature_measure.replace(tzinfo=self._current_tz)
        ).total_seconds() / 60.0

        mode_cond = self._hvac_mode != HVACMode.OFF

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()
        is_outdoor_checked = (
            not api.safety_mode
            or api.safety_mode.get("check_outdoor_sensor") is not False
        )

        temp_cond: bool = delta_temp > self._security_delay_min or (
            is_outdoor_checked and delta_ext_temp > self._security_delay_min
        )
        climate_cond: bool = self.is_over_climate and self.hvac_action not in [
            HVACAction.COOLING,
            HVACAction.IDLE,
        ]
        switch_cond: bool = (
            not self.is_over_climate
            and self._prop_algorithm is not None
            and self._prop_algorithm.calculated_on_percent
            >= self._security_min_on_percent
        )

        _LOGGER.debug(
            "%s - checking security delta_temp=%.1f delta_ext_temp=%.1f mod_cond=%s temp_cond=%s climate_cond=%s switch_cond=%s",
            self,
            delta_temp,
            delta_ext_temp,
            mode_cond,
            temp_cond,
            climate_cond,
            switch_cond,
        )

        # Issue 99 - a climate is regulated by the device itself and not by VTherm. So a VTherm should never be in security !
        shouldClimateBeInSecurity = False  # temp_cond and climate_cond
        shouldSwitchBeInSecurity = temp_cond and switch_cond
        shouldBeInSecurity = shouldClimateBeInSecurity or shouldSwitchBeInSecurity

        shouldStartSecurity = (
            mode_cond and not self._security_state and shouldBeInSecurity
        )
        # attr_preset_mode is not necessary normaly. It is just here to be sure
        shouldStopSecurity = (
            self._security_state
            and not shouldBeInSecurity
            and self._attr_preset_mode == PRESET_SECURITY
        )

        # Logging and event
        if shouldStartSecurity:
            if shouldClimateBeInSecurity:
                _LOGGER.warning(
                    "%s - No temperature received for more than %.1f minutes (dt=%.1f, dext=%.1f) and underlying climate is %s. Setting it into safety mode",
                    self,
                    self._security_delay_min,
                    delta_temp,
                    delta_ext_temp,
                    self.hvac_action,
                )
            elif shouldSwitchBeInSecurity:
                _LOGGER.warning(
                    "%s - No temperature received for more than %.1f minutes (dt=%.1f, dext=%.1f) and on_percent (%.2f %%) is over defined value (%.2f %%). Set it into safety mode",
                    self,
                    self._security_delay_min,
                    delta_temp,
                    delta_ext_temp,
                    self._prop_algorithm.on_percent * 100,
                    self._security_min_on_percent * 100,
                )

            self.send_event(
                EventType.TEMPERATURE_EVENT,
                {
                    "last_temperature_measure": self._last_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._last_ext_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "current_temp": self._cur_temp,
                    "current_ext_temp": self._cur_ext_temp,
                    "target_temp": self.target_temperature,
                },
            )

        # Start safety mode
        if shouldStartSecurity:
            self._security_state = True
            self.save_hvac_mode()
            self.save_preset_mode()
            if self._prop_algorithm:
                self._prop_algorithm.set_security(self._security_default_on_percent)
            await self._async_set_preset_mode_internal(PRESET_SECURITY)
            # Turn off the underlying climate or heater if security default on_percent is 0
            if self.is_over_climate or self._security_default_on_percent <= 0.0:
                await self.async_set_hvac_mode(HVACMode.OFF, False)

            self.send_event(
                EventType.SECURITY_EVENT,
                {
                    "type": "start",
                    "last_temperature_measure": self._last_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._last_ext_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "current_temp": self._cur_temp,
                    "current_ext_temp": self._cur_ext_temp,
                    "target_temp": self.target_temperature,
                },
            )

        # Stop safety mode
        if shouldStopSecurity:
            _LOGGER.warning(
                "%s - End of safety mode. restoring hvac_mode to %s and preset_mode to %s",
                self,
                self._saved_hvac_mode,
                self._saved_preset_mode,
            )
            self._security_state = False
            if self._prop_algorithm:
                self._prop_algorithm.unset_security()
            # Restore hvac_mode if previously saved
            if self.is_over_climate or self._security_default_on_percent <= 0.0:
                await self.restore_hvac_mode(False)
            await self.restore_preset_mode()
            self.send_event(
                EventType.SECURITY_EVENT,
                {
                    "type": "end",
                    "last_temperature_measure": self._last_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._last_ext_temperature_measure.replace(
                        tzinfo=self._current_tz
                    ).isoformat(),
                    "current_temp": self._cur_temp,
                    "current_ext_temp": self._cur_ext_temp,
                    "target_temp": self.target_temperature,
                },
            )

        return shouldBeInSecurity

    @property
    def is_initialized(self) -> bool:
        """Check if all underlyings are initialized
        This is usefull only for over_climate in which we
        should have found the underlying climate to be operational"""
        return True

    async def change_window_detection_state(self, new_state):
        """Change the window detection state.
        new_state is on if an open window have been detected or off else
        """
        if not new_state:
            _LOGGER.info(
                "%s - Window is closed. Restoring hvac_mode '%s' if central_mode is not STOPPED",
                self,
                self._saved_hvac_mode,
            )
            if self._window_action in [CONF_WINDOW_FROST_TEMP, CONF_WINDOW_ECO_TEMP]:
                await self._async_internal_set_temperature(self._saved_target_temp)
            # default to TURN_OFF
            elif self._window_action in [CONF_WINDOW_TURN_OFF, CONF_WINDOW_FAN_ONLY]:
                if self.last_central_mode != CENTRAL_MODE_STOPPED:
                    await self.restore_hvac_mode(True)
            else:
                _LOGGER.error(
                    "%s - undefined window_action %s. Please open a bug in the github of this project with this log",
                    self,
                    self._window_action,
                )
        else:
            _LOGGER.info(
                "%s - Window is open. Set hvac_mode to '%s'", self, HVACMode.OFF
            )
            if self.last_central_mode in [CENTRAL_MODE_AUTO, None]:
                if self._window_action in [CONF_WINDOW_TURN_OFF, CONF_WINDOW_FAN_ONLY]:
                    self.save_hvac_mode()
                elif self._window_action in [
                    CONF_WINDOW_FROST_TEMP,
                    CONF_WINDOW_ECO_TEMP,
                ]:
                    self._saved_target_temp = self._target_temp

            if (
                self._window_action == CONF_WINDOW_FAN_ONLY
                and HVACMode.FAN_ONLY in self.hvac_modes
            ):
                await self.async_set_hvac_mode(HVACMode.FAN_ONLY)
            elif (
                self._window_action == CONF_WINDOW_FROST_TEMP
                and self._presets.get(PRESET_FROST_PROTECTION) is not None
            ):
                await self._async_internal_set_temperature(
                    self.find_preset_temp(PRESET_FROST_PROTECTION)
                )
            elif (
                self._window_action == CONF_WINDOW_ECO_TEMP
                and self._presets.get(PRESET_ECO) is not None
            ):
                await self._async_internal_set_temperature(
                    self.find_preset_temp(PRESET_ECO)
                )
            else:  # default is to turn_off
                await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_control_heating(self, force=False, _=None) -> bool:
        """The main function used to run the calculation at each cycle"""

        _LOGGER.debug(
            "%s - Checking new cycle. hvac_mode=%s, security_state=%s, preset_mode=%s",
            self,
            self._hvac_mode,
            self._security_state,
            self._attr_preset_mode,
        )

        # check auto_window conditions
        await self._async_manage_window_auto(in_cycle=True)

        # Issue 56 in over_climate mode, if the underlying climate is not initialized, try to initialize it
        if not self.is_initialized:
            if not self.init_underlyings():
                # still not found, we an stop here
                return False

        # Check overpowering condition
        # Not necessary for switch because each switch is checking at startup
        overpowering: bool = await self.check_overpowering()
        if overpowering:
            _LOGGER.debug("%s - End of cycle (overpowering)", self)
            return True

        security: bool = await self.check_safety()
        if security and self.is_over_climate:
            _LOGGER.debug("%s - End of cycle (security and over climate)", self)
            return True

        # Stop here if we are off
        if self._hvac_mode == HVACMode.OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF)", self)
            # A security to force stop heater if still active
            if self.is_device_active:
                await self._async_underlying_entity_turn_off()
            return True

        for under in self._underlyings:
            await under.start_cycle(
                self._hvac_mode,
                self._prop_algorithm.on_time_sec if self._prop_algorithm else None,
                self._prop_algorithm.off_time_sec if self._prop_algorithm else None,
                self._prop_algorithm.on_percent if self._prop_algorithm else None,
                force,
            )

        self.update_custom_attributes()
        return True

    def recalculate(self):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state.
        Should be overriden by super class
        """
        raise NotImplementedError()

    def incremente_energy(self):
        """increment the energy counter if device is active
        Should be overriden by super class
        """
        raise NotImplementedError()

    def update_custom_attributes(self):
        """Update the custom extra attributes for the entity"""

        self._attr_extra_state_attributes: dict[str, Any] = {
            "is_on": self.is_on,
            "hvac_action": self.hvac_action,
            "hvac_mode": self.hvac_mode,
            "preset_mode": self.preset_mode,
            "type": self._thermostat_type,
            "is_controlled_by_central_mode": self.is_controlled_by_central_mode,
            "last_central_mode": self.last_central_mode,
            "frost_temp": self._presets.get(PRESET_FROST_PROTECTION, 0),
            "eco_temp": self._presets.get(PRESET_ECO, 0),
            "boost_temp": self._presets.get(PRESET_BOOST, 0),
            "comfort_temp": self._presets.get(PRESET_COMFORT, 0),
            "frost_away_temp": self._presets_away.get(
                self.get_preset_away_name(PRESET_FROST_PROTECTION), 0
            ),
            "eco_away_temp": self._presets_away.get(
                self.get_preset_away_name(PRESET_ECO), 0
            ),
            "boost_away_temp": self._presets_away.get(
                self.get_preset_away_name(PRESET_BOOST), 0
            ),
            "comfort_away_temp": self._presets_away.get(
                self.get_preset_away_name(PRESET_COMFORT), 0
            ),
            "power_temp": self._power_temp,
            "target_temperature_step": self.target_temperature_step,
            "ext_current_temperature": self._cur_ext_temp,
            "ac_mode": self._ac_mode,
            "current_power": self._current_power,
            "current_power_max": self._current_power_max,
            "saved_preset_mode": self._saved_preset_mode,
            "saved_target_temp": self._saved_target_temp,
            "saved_hvac_mode": self._saved_hvac_mode,
            "motion_sensor_entity_id": self._motion_sensor_entity_id,
            "motion_state": self._motion_state,
            "power_sensor_entity_id": self._power_sensor_entity_id,
            "max_power_sensor_entity_id": self._max_power_sensor_entity_id,
            "overpowering_state": self.overpowering_state,
            "presence_sensor_entity_id": self._presence_sensor_entity_id,
            "presence_state": self._presence_state,
            "window_state": self.window_state,
            "window_auto_state": self.window_auto_state,
            "window_bypass_state": self._window_bypass_state,
            "window_sensor_entity_id": self._window_sensor_entity_id,
            "window_delay_sec": self._window_delay_sec,
            "window_auto_enabled": self.is_window_auto_enabled,
            "window_auto_open_threshold": self._window_auto_open_threshold,
            "window_auto_close_threshold": self._window_auto_close_threshold,
            "window_auto_max_duration": self._window_auto_max_duration,
            "window_action": self.window_action,
            "security_delay_min": self._security_delay_min,
            "security_min_on_percent": self._security_min_on_percent,
            "security_default_on_percent": self._security_default_on_percent,
            "last_temperature_datetime": self._last_temperature_measure.astimezone(
                self._current_tz
            ).isoformat(),
            "last_ext_temperature_datetime": self._last_ext_temperature_measure.astimezone(
                self._current_tz
            ).isoformat(),
            "security_state": self._security_state,
            "minimal_activation_delay_sec": self._minimal_activation_delay,
            "device_power": self._device_power,
            ATTR_MEAN_POWER_CYCLE: self.mean_cycle_power,
            ATTR_TOTAL_ENERGY: self.total_energy,
            "last_update_datetime": datetime.now()
            .astimezone(self._current_tz)
            .isoformat(),
            "timezone": str(self._current_tz),
            "temperature_unit": self.temperature_unit,
            "is_device_active": self.is_device_active,
            "ema_temp": self._ema_temp,
            "is_used_by_central_boiler": self.is_used_by_central_boiler,
        }

    @callback
    def async_registry_entry_updated(self):
        """update the entity if the config entry have been updated
        Note: this don't work either
        """
        _LOGGER.info("%s - The config entry have been updated", self)

    async def service_set_presence(self, presence: str):
        """Called by a service call:
        service: versatile_thermostat.set_presence
        data:
            presence: "off"
        target:
            entity_id: climate.thermostat_1
        """
        _LOGGER.info("%s - Calling service_set_presence, presence: %s", self, presence)
        await self._async_update_presence(presence)
        await self.async_control_heating(force=True)

    async def service_set_preset_temperature(
        self,
        preset: str,
        temperature: float | None = None,
        temperature_away: float | None = None,
    ):
        """Called by a service call:
        service: versatile_thermostat.set_preset_temperature
        data:
            preset: boost
            temperature: 17.8
            temperature_away: 15
        target:
            entity_id: climate.thermostat_2
        """
        _LOGGER.info(
            "%s - Calling service_set_preset_temperature, preset: %s, temperature: %s, temperature_away: %s",
            self,
            preset,
            temperature,
            temperature_away,
        )
        if preset in self._presets:
            if temperature is not None:
                self._presets[preset] = temperature
            if self._presence_on and temperature_away is not None:
                self._presets_away[self.get_preset_away_name(preset)] = temperature_away
        else:
            _LOGGER.warning(
                "%s - No preset %s configured for this thermostat. Ignoring set_preset_temperature call",
                self,
                preset,
            )

        # If the changed preset is active, change the current temperature
        # Issue #119 - reload new preset temperature also in ac mode
        if preset.startswith(self._attr_preset_mode):
            await self._async_set_preset_mode_internal(
                preset.rstrip(PRESET_AC_SUFFIX), force=True
            )
            await self.async_control_heating(force=True)

    async def service_set_security(
        self,
        delay_min: int | None,
        min_on_percent: float | None,
        default_on_percent: float | None,
    ):
        """Called by a service call:
        service: versatile_thermostat.set_security
        data:
            delay_min: 15
            min_on_percent: 0.5
            default_on_percent: 0.2
        target:
            entity_id: climate.thermostat_2
        """
        _LOGGER.info(
            "%s - Calling service_set_security, delay_min: %s, min_on_percent: %s %%, default_on_percent: %s %%",
            self,
            delay_min,
            min_on_percent * 100,
            default_on_percent * 100,
        )
        if delay_min:
            self._security_delay_min = delay_min
        if min_on_percent:
            self._security_min_on_percent = min_on_percent
        if default_on_percent:
            self._security_default_on_percent = default_on_percent

        if self._prop_algorithm and self._security_state:
            self._prop_algorithm.set_security(self._security_default_on_percent)

        await self.async_control_heating()
        self.update_custom_attributes()

    async def service_set_window_bypass_state(self, window_bypass: bool):
        """Called by a service call:
        service: versatile_thermostat.set_window_bypass
        data:
            window_bypass: True
        target:
            entity_id: climate.thermostat_1
        """
        _LOGGER.info(
            "%s - Calling service_set_window_bypass, window_bypass: %s",
            self,
            window_bypass,
        )
        self._window_bypass_state = window_bypass
        if not self._window_bypass_state and self._window_state:
            _LOGGER.info(
                "%s - Last window state was open & ByPass is now off. Set hvac_mode to '%s'",
                self,
                HVACMode.OFF,
            )
            self.save_hvac_mode()
            await self.async_set_hvac_mode(HVACMode.OFF)
        if self._window_bypass_state and self._window_state:
            _LOGGER.info(
                "%s - Last window state was open & ByPass is now on. Set hvac_mode to last available mode",
                self,
            )
            await self.restore_hvac_mode(True)
        self.update_custom_attributes()

    def send_event(self, event_type: EventType, data: dict):
        """Send an event"""
        send_vtherm_event(self._hass, event_type=event_type, entity=self, data=data)

    async def init_presets(self, central_config):
        """Init all presets of the VTherm"""
        # If preset central config is used and central config is set , take the presets from central config
        vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()

        presets: dict[str, Any] = {}
        presets_away: dict[str, Any] = {}

        def calculate_presets(items, use_central_conf_key):
            presets: dict[str, Any] = {}
            config_id = self._unique_id
            if (
                central_config
                and self._entry_infos.get(use_central_conf_key, False) is True
            ):
                config_id = central_config.entry_id

            for key, preset_name in items:
                _LOGGER.debug("looking for key=%s, preset_name=%s", key, preset_name)
                value = vtherm_api.get_temperature_number_value(
                    config_id=config_id, preset_name=preset_name
                )
                if value is not None:
                    presets[key] = value
                else:
                    _LOGGER.debug("preset_name %s not found in VTherm API", preset_name)
                    presets[key] = (
                        self._attr_max_temp if self._ac_mode else self._attr_min_temp
                    )
            return presets

        # Calculate all presets
        presets = calculate_presets(
            CONF_PRESETS_WITH_AC.items() if self._ac_mode else CONF_PRESETS.items(),
            CONF_USE_PRESETS_CENTRAL_CONFIG,
        )

        if self._entry_infos.get(CONF_USE_PRESENCE_FEATURE) is True:
            presets_away = calculate_presets(
                (
                    CONF_PRESETS_AWAY_WITH_AC.items()
                    if self._ac_mode
                    else CONF_PRESETS_AWAY.items()
                ),
                CONF_USE_PRESENCE_CENTRAL_CONFIG,
            )

        # aggregate all available presets now
        self._presets: dict[str, Any] = presets
        self._presets_away: dict[str, Any] = presets_away

        # Calculate all possible presets
        self._attr_preset_modes = [PRESET_NONE]
        if len(self._presets):
            self._support_flags = SUPPORT_FLAGS | ClimateEntityFeature.PRESET_MODE

            for key, _ in CONF_PRESETS.items():
                if self.find_preset_temp(key) > 0:
                    self._attr_preset_modes.append(key)

            _LOGGER.debug(
                "After adding presets, preset_modes to %s", self._attr_preset_modes
            )
        else:
            _LOGGER.debug("No preset_modes")

        if self._motion_on:
            self._attr_preset_modes.append(PRESET_ACTIVITY)

        # Re-applicate the last preset if any to take change into account
        if self._attr_preset_mode:
            await self._async_set_preset_mode_internal(self._attr_preset_mode, True)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        if self._ac_mode:
            await self.async_set_hvac_mode(HVACMode.COOL)
        else:
            await self.async_set_hvac_mode(HVACMode.HEAT)
