# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=invalid-name
""" Implements the VersatileThermostat climate component """
import math
import logging
import asyncio
from datetime import datetime, timedelta
from functools import partial

from homeassistant.components.recorder import history, get_instance
from homeassistant.util import dt as dt_util
from typing import Any, Generic
from collections.abc import Callable

from homeassistant.exceptions import ServiceValidationError
from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    State,
)
from homeassistant.exceptions import HomeAssistantError

from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.restore_state import (
    RestoreEntity,
    async_get as restore_async_get,
)
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.helpers.event import (
    async_track_state_change_event,
)


from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    # ATTR_FAN_MODE,
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log
from .commons_type import ConfigData

from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingEntity, T

from .prop_algorithm import PropAlgorithm
from .ema import ExponentialMovingAverage

from .base_manager import BaseFeatureManager
from .feature_presence_manager import FeaturePresenceManager
from .feature_power_manager import FeaturePowerManager
from .feature_motion_manager import FeatureMotionManager
from .feature_window_manager import FeatureWindowManager
from .feature_safety_manager import FeatureSafetyManager
from .feature_auto_start_stop_manager import FeatureAutoStartStopManager
from .feature_lock_manager import FeatureLockManager
from .state_manager import StateManager
from .vtherm_state import VThermState
from .vtherm_preset import VThermPreset, HIDDEN_PRESETS, PRESET_AC_SUFFIX
from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF, to_legacy_ha_hvac_mode
from .auto_tpi_manager import AutoTpiManager

_LOGGER = logging.getLogger(__name__)


class BaseThermostat(ClimateEntity, RestoreEntity, Generic[T]):
    """Representation of a base class for all Versatile Thermostat device."""

    # breaking change with 2024.12 climate workaround
    _attr_swing_horizontal_modes = []
    _attr_swing_horizontal_mode = ""

    _entity_component_unrecorded_attributes = (
        ClimateEntity._entity_component_unrecorded_attributes.union(frozenset({"configuration", "preset_temperatures"}))
        .union(FeaturePresenceManager.unrecorded_attributes)
        .union(FeaturePowerManager.unrecorded_attributes)
        .union(FeatureMotionManager.unrecorded_attributes)
        .union(FeatureWindowManager.unrecorded_attributes)
    )

    ##
    ## Startup functions
    ##

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

        # Callbacks for TPI cycle events
        self._on_cycle_start_callbacks: list[Callable] = []

        self._state_manager = StateManager()
        # self._hvac_mode = None
        # self._target_temp = None
        # self._saved_target_temp = None
        # self._saved_preset_mode = None
        # self._saved_hvac_mode = None

        self._fan_mode = None
        self._humidity = None
        self._swing_mode = None
        self._swing_horizontal_mode = None
        self._ac_mode = None

        self._cur_temp = None

        self._temp_sensor_entity_id = None
        self._last_seen_temp_sensor_entity_id = None
        self._ext_temp_sensor_entity_id = None
        self._last_ext_temperature_measure = None
        self._last_temperature_measure = None
        self._cur_ext_temp = None

        self._should_relaunch_control_heating = None

        self._attr_translation_key = "versatile_thermostat"

        self._total_energy = None
        _LOGGER.debug("%s - _init_ resetting energy to None", self)

        # Because energy of climate is calculated in the thermostat we have to keep
        # that here and not in underlying entity
        self._underlying_climate_start_hvac_action_date = None
        self._underlying_climate_delta_t = 0

        self._current_tz = dt_util.get_time_zone(self._hass.config.time_zone)

        # Last change time is the datetime of the last change sent by
        # VTherm to the device it is used in `over_climate` when a
        # state changes from underlying to avoid loops
        self._last_change_time_from_vtherm = None

        self._underlyings: list[T] = []

        self._ema_temp = None
        self._ema_algo = None

        self._attr_fan_mode = None

        self._is_central_mode = None
        self._last_central_mode = None
        self._is_used_by_central_boiler = False

        self._support_flags = None
        # Preset will be initialized from Number entities
        self._presets: dict[str, Any] = {}  # presets
        self._presets_away: dict[str, Any] = {}  # presets_away

        self._attr_preset_modes: list[str] = []
        self._vtherm_preset_modes: list[VThermPreset] = []

        self._use_central_config_temperature = False

        self._hvac_off_reason: str | None = None
        self._hvac_list: list[VThermHvacMode] = []
        self._str_hvac_list: list[str] = []
        self._temperature_reason: str | None = None

        # Instantiate all features manager
        self._managers: list[BaseFeatureManager] = []

        self._presence_manager: FeaturePresenceManager = FeaturePresenceManager(
            self, hass
        )
        self._power_manager: FeaturePowerManager = FeaturePowerManager(self, hass)
        self._motion_manager: FeatureMotionManager = FeatureMotionManager(self, hass)
        self._window_manager: FeatureWindowManager = FeatureWindowManager(self, hass)
        self._safety_manager: FeatureSafetyManager = FeatureSafetyManager(self, hass)
        # Auto start/stop is only for over_climate
        self._auto_start_stop_manager: FeatureAutoStartStopManager | None = None
        self._lock_manager: FeatureLockManager = FeatureLockManager(self, hass)

        self.register_manager(self._presence_manager)
        self.register_manager(self._power_manager)
        self.register_manager(self._motion_manager)
        self.register_manager(self._window_manager)
        self.register_manager(self._safety_manager)
        self.register_manager(self._safety_manager)
        self.register_manager(self._lock_manager)

        self._cancel_recalculate_later: Callable[[], None] | None = None

        self._tpi_coef_int: float = 0
        self._tpi_coef_ext: float = 0
        self._minimal_activation_delay: int = 0
        self._minimal_deactivation_delay: int = 0
        self._tpi_threshold_low: float = 0
        self._tpi_threshold_high: float = 0
        self._auto_tpi_keep_ext_learning: bool = False
        self._auto_tpi_continuous_learning: bool = False
        self._auto_tpi_enable_update_config: bool = False
        self._auto_tpi_enable_notification: bool = False

        self.post_init(entry_infos)

    def register_manager(self, manager: BaseFeatureManager):
        """Register a manager"""
        self._managers.append(manager)

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

            if cfg.get(CONF_USE_LOCK_CENTRAL_CONFIG) is True:
                clean_one(cfg, STEP_CENTRAL_LOCK_DATA_SCHEMA)

            # take all central config
            entry_infos = central_config.data.copy()
            # and merge with cleaned config_entry
            entry_infos.update(cfg)
        else:
            entry_infos = cfg

        return entry_infos

    def post_init(self, config_entry: ConfigData):
        """Finish the initialization of the thermostat"""

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

        # Post init all managers
        for manager in self._managers:
            manager.post_init(entry_infos)

        self._use_central_config_temperature = entry_infos.get(
            CONF_USE_PRESETS_CENTRAL_CONFIG
        ) or (
            entry_infos.get(CONF_USE_PRESENCE_CENTRAL_CONFIG)
            and entry_infos.get(CONF_USE_PRESENCE_FEATURE)
        )

        self._ac_mode = entry_infos.get(CONF_AC_MODE) is True
        self._attr_max_temp = float(entry_infos.get(CONF_TEMP_MAX, 0.0))
        self._attr_min_temp = float(entry_infos.get(CONF_TEMP_MIN, 0.0))
        if (step := entry_infos.get(CONF_STEP_TEMPERATURE)) is not None:
            self._attr_target_temperature_step = step

        self._attr_preset_modes = []
        self._vtherm_preset_modes = []

        self._cycle_min = max(1, entry_infos.get(CONF_CYCLE_MIN, 1))

        # Initialize underlying entities (will be done in subclasses)
        self._underlyings = []

        self._proportional_function = entry_infos.get(CONF_PROP_FUNCTION)
        self._temp_sensor_entity_id = entry_infos.get(CONF_TEMP_SENSOR)
        self._last_seen_temp_sensor_entity_id = entry_infos.get(
            CONF_LAST_SEEN_TEMP_SENSOR
        )
        self._ext_temp_sensor_entity_id = entry_infos.get(CONF_EXTERNAL_TEMP_SENSOR)

        self._tpi_coef_int = entry_infos.get(CONF_TPI_COEF_INT)
        self._tpi_coef_ext = entry_infos.get(CONF_TPI_COEF_EXT)
        self._tpi_threshold_low = entry_infos.get(CONF_TPI_THRESHOLD_LOW, 0.0)
        self._tpi_threshold_high = entry_infos.get(CONF_TPI_THRESHOLD_HIGH, 0.0)
        # If one is 0 then both are 0
        if self._tpi_threshold_low == 0.0 or self._tpi_threshold_high == 0.0:
            self._tpi_threshold_low = 0.0
            self._tpi_threshold_high = 0.0

        self.set_hvac_list()

        self._unit = self._hass.config.units.temperature_unit

        # Will be restored if possible
        self._state_manager = StateManager()

        self._support_flags = SUPPORT_FLAGS

        # Preset will be initialized from Number entities
        self._presets: dict[str, Any] = {}  # presets
        self._presets_away: dict[str, Any] = {}  # presets_away

        self._humidity = None
        self._fan_mode = None
        self._swing_mode = None
        self._swing_horizontal_mode = None
        self._cur_temp = None
        self._cur_ext_temp = None

        # Fix parameters for TPI
        if (
            self._proportional_function == PROPORTIONAL_FUNCTION_TPI
            and self._ext_temp_sensor_entity_id is None
        ):
            _LOGGER.warning(
                "Using TPI function but not external temperature sensor is set. "
                "Removing the delta temp ext factor. "
                "Thermostat will not be fully operational."
            )
            self._tpi_coef_ext = 0

        self._minimal_activation_delay = entry_infos.get(CONF_MINIMAL_ACTIVATION_DELAY, 0)
        self._minimal_deactivation_delay = entry_infos.get(CONF_MINIMAL_DEACTIVATION_DELAY, 0)
        self._last_temperature_measure = self.now
        self._last_ext_temperature_measure = self.now

        # Initiate the ProportionalAlgorithm
        if self._prop_algorithm is not None:
            del self._prop_algorithm

        self._total_energy = None
        _LOGGER.debug("%s - post_init_ resetting energy to None", self)

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

        self._max_on_percent = api.max_on_percent

        # Add a warning if minimal_deactivation_delay or minimal_activation_delay os greater than cycle_min
        if (self._minimal_activation_delay + self._minimal_deactivation_delay) / 60 > self._cycle_min:
            _LOGGER.warning(
                "%s - The sum of minimal_activation_delay (%s sec) and "
                "minimal_deactivation_delay (%s sec) is greater than cycle_min (%s). "
                "This can create some unexpected behavior. Please review your configuration",
                self,
                self._minimal_activation_delay,
                self._minimal_deactivation_delay,
                self._cycle_min,
            )

        _LOGGER.debug(
            "%s - Creation of a new VersatileThermostat entity: unique_id=%s",
            self,
            self.unique_id,
        )

        # Initialize Auto TPI Manager here because we need self._cycle_min which is initialized in post_init
        heater_heating_time = entry_infos.get(CONF_HEATER_HEATING_TIME, 0)
        heater_cooling_time = entry_infos.get(CONF_HEATER_COOLING_TIME, 0)
        calculation_method = entry_infos.get(CONF_AUTO_TPI_CALCULATION_METHOD, AUTO_TPI_METHOD_EMA)
        ema_alpha = entry_infos.get(CONF_AUTO_TPI_EMA_ALPHA, 0.2)
        avg_initial_weight = entry_infos.get(CONF_AUTO_TPI_AVG_INITIAL_WEIGHT, 1)
        max_coef_int = entry_infos.get(CONF_AUTO_TPI_MAX_COEF_INT, 1.5)
        heating_rate = entry_infos.get(CONF_AUTO_TPI_HEATING_POWER, 1.0)
        cooling_rate = entry_infos.get(CONF_AUTO_TPI_COOLING_POWER, 1.0)
        self._auto_tpi_enable_update_config = entry_infos.get(CONF_AUTO_TPI_ENABLE_UPDATE_CONFIG, False)
        self._auto_tpi_enable_notification = entry_infos.get(CONF_AUTO_TPI_ENABLE_NOTIFICATION, False)

        _LOGGER.info("%s - DEBUG: TPI coefficients from entry_infos: int=%.3f, ext=%.3f",
                     self, self._tpi_coef_int, self._tpi_coef_ext)
        self._auto_tpi_manager = AutoTpiManager(
            self._hass,
            self.config_entry,
            self.unique_id,
            self.name,
            self._cycle_min,
            self._tpi_threshold_low,
            self._tpi_threshold_high,
            self._minimal_deactivation_delay,
            coef_int=self._tpi_coef_int,
            coef_ext=self._tpi_coef_ext,
            heater_heating_time=heater_heating_time,
            heater_cooling_time=heater_cooling_time,
            calculation_method=calculation_method,
            ema_alpha=ema_alpha,
            avg_initial_weight=avg_initial_weight,
            max_coef_int=max_coef_int,
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            continuous_learning=self._auto_tpi_continuous_learning,
            keep_ext_learning=self._auto_tpi_keep_ext_learning,
            enable_update_config=self._auto_tpi_enable_update_config, # Pass the config flags
            enable_notification=self._auto_tpi_enable_notification, # Pass the config flags
        )
        _LOGGER.info("%s - DEBUG: AutoTpiManager initialized with defaults: int=%.3f, ext=%.3f",
                     self, self._auto_tpi_manager._default_coef_int, self._auto_tpi_manager._default_coef_ext)


    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        # Load data from Auto TPI Manager
        if self._auto_tpi_manager:
            _LOGGER.info("%s - DEBUG: Before load_data - int=%.3f, ext=%.3f", 
                         self, self._tpi_coef_int, self._tpi_coef_ext)
            await self._auto_tpi_manager.async_load_data()
            # If we have learned parameters, apply them
            learned_params = self._auto_tpi_manager.get_calculated_params()
            if learned_params:
                _LOGGER.info("%s - DEBUG: Learned params found: %s, learning_active=%s, update_config=%s",
                             self, learned_params, self._auto_tpi_manager.learning_active, self._auto_tpi_enable_update_config)
                if self._auto_tpi_enable_update_config:
                    if self._auto_tpi_manager.learning_active:
                        self._tpi_coef_int = learned_params.get(CONF_TPI_COEF_INT, self._tpi_coef_int)
                        self._tpi_coef_ext = learned_params.get(CONF_TPI_COEF_EXT, self._tpi_coef_ext)
                        _LOGGER.info("%s - Restored Auto TPI parameters: %s", self, learned_params)
                    else:
                        _LOGGER.info("%s - Auto TPI parameters found but not applied because learning is disabled", self)
                else:
                    _LOGGER.info("%s - Auto TPI parameters found but not applied because auto_tpi_enable_update_config is False", self)
            
            _LOGGER.info("%s - DEBUG: After load_data - int=%.3f, ext=%.3f",
                         self, self._tpi_coef_int, self._tpi_coef_ext)
            
            if self._auto_tpi_manager.learning_active:
                # Security: if the feature is disabled in config, we must stop learning
                if not self._entry_infos.get(CONF_AUTO_TPI_MODE, False):
                    _LOGGER.info("%s - Auto TPI learning was active but feature is disabled in config. Stopping learning.", self)
                    await self._auto_tpi_manager.stop_learning()
                else:
                    _LOGGER.info("%s - Auto TPI learning is active (restored from storage)", self)

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

        self.async_on_remove(self.remove_thermostat)

        # issue 428. Link to others entities will start at link
        # await self.async_startup()

    async def async_will_remove_from_hass(self):
        """Try to force backup of entity"""
        _LOGGER.debug(
            "%s - force write before remove. Energy is %s", self, self.total_energy
        )
        # Force dump in background
        await restore_async_get(self.hass).async_dump_states()

    def remove_thermostat(self):
        """Called when the thermostat will be removed"""
        _LOGGER.info("%s - Removing thermostat", self)

        self.stop_recalculate_later()

        if self._auto_tpi_manager:
            self._auto_tpi_manager.stop_cycle_loop()

        # stop listening for all managers
        for manager in self._managers:
            manager.stop_listening()

        for under in self._underlyings:
            under.remove_entity()

        if self._auto_tpi_manager:
            self.hass.async_create_task(self._auto_tpi_manager.async_save_data())

    def register_cycle_callback(
        self,
        on_start: Callable | None = None,
    ):
        """Register callbacks for TPI cycle events.

        Args:
            on_start: Callback called at the start of each TPI cycle
                      Signature: async def callback(on_time_sec, off_time_sec, on_percent, hvac_mode)
        """
        if on_start:
            self._on_cycle_start_callbacks.append(on_start)
            _LOGGER.debug("%s - Registered cycle start callback: %s", self, on_start)
            # Register to existing underlyings
            if self._underlyings:
                for under in self._underlyings:
                    under.register_cycle_callback(on_start)

    async def _fire_cycle_start_callbacks(self, on_time_sec, off_time_sec, on_percent, hvac_mode):
        """Fire cycle start callbacks."""
        for callback in self._on_cycle_start_callbacks:
            try:
                if is_async := (
                    asyncio.iscoroutinefunction(callback)
                    or (hasattr(callback, "__call__") and asyncio.iscoroutinefunction(callback.__call__))
                ):
                    await callback(on_time_sec, off_time_sec, on_percent, hvac_mode)
                else:
                    await self.hass.async_add_executor_job(
                        callback, on_time_sec, off_time_sec, on_percent, hvac_mode
                    )
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("%s - Error calling cycle start callback: %s", self, ex)


    def stop_recalculate_later(self):
        """Stop any scheduled call later tasks if any."""
        if self._cancel_recalculate_later:
            self._cancel_recalculate_later()  # pylint: disable=not-callable
            self._cancel_recalculate_later = None

    async def async_startup(self, central_configuration):
        """Triggered on startup, used to get old state and set internal states
         accordingly. This is triggered by VTherm API"""
        write_event_log(_LOGGER, self, "Start up VTherm")

        _LOGGER.debug("%s - Calling async_startup_internal", self)
        # need_write_state = False

        # start listening for all managers
        for manager in self._managers:
            await manager.start_listening()

        await self.get_my_previous_state()

        # Initialize all UnderlyingEntities
        self.init_underlyings()

        # Register callbacks to new underlyings
        for under in self._underlyings:
            for callback in self._on_cycle_start_callbacks:
                under.register_cycle_callback(callback)

        # init presets. Should be after underlyings init because for over_climate it uses the hvac_modes
        await self.init_presets(central_configuration)

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
                    "%s - external temperature sensor have NOT been retrieved "
                    "cause unknown or unavailable",
                    self,
                )
        else:
            _LOGGER.debug(
                "%s - external temperature sensor have NOT been retrieved "
                "cause no external sensor",
                self,
            )

        # Then we:
        # - refresh all managers states,
        # - calculate the current state of the VTherm (it depends on the managers states and the requested state)
        # - check if the initial conditions are met
        # - force the first cycle if changes has been detected

        # refresh states for all managers
        for manager in self._managers:
            await manager.refresh_state()
            #    need_write_state = True

        await self.update_states(force=True)
        # self.async_write_ha_state()
        if self._prop_algorithm:
            self._prop_algorithm.calculate(
                self.target_temperature,
                self._cur_temp,
                self._cur_ext_temp,
                self.last_temperature_slope,
                self.vtherm_hvac_mode or VThermHvacMode_OFF,
            )

        # check initial state should be done after the current state has been calculated and so after the manager has been updated
        await self._check_initial_state()
        self.reset_last_change_time_from_vtherm()

    def init_underlyings(self):
        """Initialize all underlyings. Should be overridden if necessary"""

    def restore_specific_previous_state(self, old_state: State):
        """Should be overridden in each specific thermostat
        if a specific previous state or attribute should be
        restored
        """

    async def get_my_previous_state(self):
        """Try to get my previous state"""
        # Check If we have an old state
        old_state = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling get_my_previous_state old_state is %s", self, old_state
        )
        if old_state is not None:
            # Restore current_state
            if current_state_attr := old_state.attributes.get(ATTR_CURRENT_STATE, None):
                current_state = VThermState.from_dict(current_state_attr)
                self._state_manager.current_state.set_state(
                    hvac_mode=current_state.hvac_mode,
                    target_temperature=current_state.target_temperature,
                    preset=current_state.preset,
                )
            else:
                # Try to init current_state with old temperature, preset and mode
                self._state_manager.current_state.set_state(
                    target_temperature=old_state.attributes.get(ATTR_TEMPERATURE, None),
                    preset=VThermPreset(old_state.attributes.get(ATTR_PRESET_MODE, None) or VThermPreset.NONE),
                    hvac_mode=old_state.state if isinstance(old_state.state, VThermHvacMode) else from_ha_hvac_mode(old_state.state),
                )
            # If we have no initial temperature set with min (or max depending on ac_mode)
            if self._state_manager.current_state.target_temperature is None:
                self._state_manager.current_state.set_target_temperature(self.max_temp if self._ac_mode else self.min_temp)
                _LOGGER.warning(
                    "%s - Undefined target temperature, falling back to %s",
                    self,
                    self._state_manager.current_state.target_temperature,
                )

            # Restore requested_state or default with current_state
            if requested_state_attr := old_state.attributes.get(ATTR_REQUESTED_STATE, None):
                requested_state = VThermState.from_dict(requested_state_attr)
                self._state_manager.requested_state.set_state(
                    hvac_mode=requested_state.hvac_mode,
                    target_temperature=requested_state.target_temperature,
                    preset=requested_state.preset,
                )
            else:
                # Try to init requested_state with old temperature, preset and mode
                self._state_manager.requested_state.set_state(
                    target_temperature=old_state.attributes.get(ATTR_TEMPERATURE, None),
                    preset=VThermPreset(old_state.attributes.get(ATTR_PRESET_MODE, None) or VThermPreset.NONE),
                    hvac_mode=old_state.state if isinstance(old_state.state, VThermHvacMode) else from_ha_hvac_mode(old_state.state),
                )

            self._hvac_off_reason = old_state.attributes.get(HVAC_OFF_REASON_NAME, None)

            old_total_energy = old_state.attributes.get(ATTR_TOTAL_ENERGY)
            self._total_energy = old_total_energy if old_total_energy is not None else 0
            _LOGGER.debug(
                "%s - get_my_previous_state restored energy is %s",
                self,
                self._total_energy,
            )

            self.restore_specific_previous_state(old_state)

            # Restore all managers states from previous state
            for manager in self._managers:
                manager.restore_state(old_state)
        else:
            # No previous state, try and restore defaults
            if self._state_manager.current_state.target_temperature is None:
                self._state_manager.current_state.set_target_temperature(self.max_temp if self._ac_mode else self.min_temp)
            _LOGGER.warning("No previously saved temperature, setting to %s", self._state_manager.current_state.target_temperature)
            self._total_energy = 0
            _LOGGER.debug(
                "%s - get_my_previous_state  no previous state energy is %s",
                self,
                self._total_energy,
            )

        if not self.is_on and self.hvac_off_reason is None:
            self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)

        _LOGGER.info(
            "%s - restored current state is %s, requested state is %s",
            self,
            self._state_manager.current_state,
            self._state_manager.requested_state,
        )

    def __str__(self) -> str:
        return f"VersatileThermostat-{self.name}"

    def set_hvac_list(self):
        """Set the hvac list depending on ac_mode"""
        self._hvac_list = self.build_hvac_list()
        self._str_hvac_list = [to_ha_hvac_mode(mode) for mode in self._hvac_list if to_ha_hvac_mode(mode) is not None]

    @callback
    def async_registry_entry_updated(self):
        """update the entity if the config entry have been updated
        Note: this don't work either
        """
        write_event_log(_LOGGER, self, "The config entry have been updated")

    @callback
    async def entry_update_listener(self, _, config_entry: ConfigEntry) -> None:  # hass: HomeAssistant,
        """Called when the entry have changed in ConfigFlow"""
        _LOGGER.info("%s - Change entry with the values: %s", self, config_entry.data)

    @callback
    async def _check_initial_state(self):
        """Prevent the device from keep running if HVAC_MODE_OFF."""
        _LOGGER.debug("%s - Calling _check_initial_state", self)
        for under in self._underlyings:
            await under.check_initial_state(self.vtherm_hvac_mode)

    async def init_presets(self, central_config):
        """Init all presets of the VTherm"""
        # If preset central config is used and central config is set,
        # take the presets from central config
        vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()

        presets: dict[str, Any] = {}
        presets_away: dict[str, Any] = {}

        def calculate_presets(items, use_central_conf_key):
            presets: dict[str, Any] = {}
            config_id = self._unique_id
            if central_config and self._entry_infos.get(use_central_conf_key, False) is True:
                config_id = central_config.entry_id

            for key, preset_name in items:
                _LOGGER.debug("looking for key=%s, preset_name=%s", key, preset_name)
                # removes preset_name frost if heat is not in hvac_modes
                if key == VThermPreset.FROST and VThermHvacMode_HEAT not in self.vtherm_hvac_modes:
                    _LOGGER.debug("removing preset_name %s which reserved for HEAT devices", preset_name)
                    continue
                value = vtherm_api.get_temperature_number_value(config_id=config_id, preset_name=preset_name)
                if value is not None:
                    presets[key] = value
                else:
                    _LOGGER.debug("preset_name %s not found in VTherm API", preset_name)
                    presets[key] = self._attr_max_temp if self._ac_mode else self._attr_min_temp
            return presets

        # Calculate all presets
        presets = calculate_presets(
            CONF_PRESETS_WITH_AC.items() if self._ac_mode else CONF_PRESETS.items(),
            CONF_USE_PRESETS_CENTRAL_CONFIG,
        )

        # refacto
        # if self._entry_infos.get(CONF_USE_PRESENCE_FEATURE) is True:
        if self._presence_manager.is_configured:
            presets_away = calculate_presets(
                (CONF_PRESETS_AWAY_WITH_AC.items() if self._ac_mode else CONF_PRESETS_AWAY.items()),
                CONF_USE_PRESETS_CENTRAL_CONFIG,
            )

        # aggregate all available presets now
        self._presets: dict[str, Any] = presets
        self._presets_away: dict[str, Any] = presets_away

        # Calculate all possible presets
        self._attr_preset_modes = [VThermPreset.NONE]
        if len(self._presets):
            self._support_flags = SUPPORT_FLAGS | ClimateEntityFeature.PRESET_MODE

            for key, _ in CONF_PRESETS.items():
                preset_value = self.find_preset_temp(key)
                if preset_value is not None and preset_value > 0:
                    self._attr_preset_modes.append(key)

            _LOGGER.debug("After adding presets, preset_modes to %s", self._attr_preset_modes)
        else:
            _LOGGER.debug("No preset_modes")

        if self._motion_manager.is_configured:
            self._attr_preset_modes.append(VThermPreset.ACTIVITY)

        # transform _attr_preset_modes into _vtherm_preset_modes
        self._vtherm_preset_modes = [VThermPreset(mode) for mode in self._attr_preset_modes]

        # Re-applicate the last preset if any to take change into account
        if self._state_manager.current_state.preset and self._state_manager.current_state.preset != VThermPreset.NONE:
            await self.async_set_preset_mode_internal(self._state_manager.current_state.preset)

    ##
    ## Properties overriden from ClimateEntity (or not)
    ##

    @property
    def is_initialized(self) -> bool:
        """Check if all underlyings are initialized
        This is useful only for over_climate in which we
        should have found the underlying climate to be operational"""
        return True

    @property
    def vtherm_hvac_modes(self) -> list[VThermHvacMode]:
        """List of available VTherm operation modes."""
        return self._hvac_list

    @property
    def hvac_modes(self) -> list[str]:
        """List of available VTherm operation modes."""
        return self._str_hvac_list

    def build_hvac_list(self) -> list[VThermHvacMode]:
        """Build the hvac list depending on ac_mode"""
        if self._ac_mode:
            return [VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF]
        else:
            return [VThermHvacMode_HEAT, VThermHvacMode_OFF]

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
            entry_type=None,
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
    def ac_mode(self) -> bool | None:
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
    def ema_temperature(self) -> float | None:
        """Return the EMA temperature."""
        return self._ema_temp

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current operation."""
        return to_legacy_ha_hvac_mode(self._state_manager.current_state.hvac_mode)

    @property
    def vtherm_hvac_mode(self) -> VThermHvacMode | None:
        """Return current operation."""
        return self._state_manager.current_state.hvac_mode

    @property
    def is_recalculate_scheduled(self) -> bool:
        """Return true if a recalculation is scheduled."""
        return self._cancel_recalculate_later is not None

    @property
    def is_used_by_central_boiler(self) -> HVACAction | None:
        """Return true is the VTherm is configured to be used by
        central boiler"""
        return self._is_used_by_central_boiler

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._state_manager.current_state.target_temperature

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
    def device_actives(self) -> int:
        """Calculate the active devices"""
        ret = []
        for under in self._underlyings:
            if under.is_device_active:
                ret.append(under.entity_id)
        return ret

    @property
    def nb_device_actives(self) -> int:
        """Calculate the number of active devices"""
        return len(self.device_actives)

    @property
    def current_temperature(self) -> float | None:
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def current_outdoor_temperature(self) -> float | None:
        """Return the outdoor sensor temperature."""
        return self._cur_ext_temp

    @property
    def is_aux_heat(self) -> bool | None:
        """Return true if aux heater.

        Requires ClimateEntityFeature.AUX_HEAT.
        """
        return None

    @property
    def total_energy(self) -> float | None:
        """Returns the total energy calculated for this thermostat"""
        if self._total_energy is not None:
            return round(self._total_energy, 2)
        else:
            return None

    @property
    def overpowering_state(self) -> bool | None:
        """Get the overpowering_state"""
        return self._power_manager.overpowering_state

    @property
    def power_manager(self) -> FeaturePowerManager | None:
        """Get the power manager"""
        return self._power_manager

    @property
    def presence_manager(self) -> FeaturePresenceManager | None:
        """Get the presence manager"""
        return self._presence_manager

    @property
    def motion_manager(self) -> FeatureMotionManager | None:
        """Get the motion manager"""
        return self._motion_manager

    @property
    def window_manager(self) -> FeatureWindowManager | None:
        """Get the window manager"""
        return self._window_manager

    @property
    def safety_manager(self) -> FeatureSafetyManager | None:
        """Get the safety manager"""
        return self._safety_manager

    @property
    def auto_start_stop_manager(self) -> FeatureAutoStartStopManager | None:
        """Get the auto start/stop manager (only implemented in over_climate)"""
        return self._auto_start_stop_manager

    @property
    def lock_manager(self) -> FeatureLockManager | None:
        """Get the lock manager"""
        return self._lock_manager

    @property
    def current_state(self) -> VThermState | None:
        """Get the current state"""
        return self._state_manager.current_state

    @property
    def requested_state(self) -> VThermState | None:
        """Get the requested state"""
        return self._state_manager.requested_state

    @property
    def window_state(self) -> str | None:
        """Get the window_state"""
        return self._window_manager.window_state

    @property
    def window_auto_state(self) -> str | None:
        """Get the window_auto_state"""
        return self._window_manager.window_auto_state

    @property
    def is_window_bypass(self) -> bool | None:
        """Get the Window Bypass"""
        return self._window_manager.is_window_bypass

    @property
    def safety_state(self) -> str | None:
        """Get the safety_state"""
        return self._safety_manager.safety_state

    @property
    def motion_state(self) -> str | None:
        """Get the motion_state"""
        return self._motion_manager.motion_state

    @property
    def presence_state(self) -> str | None:
        """Get the presence_state"""
        return self._presence_manager.presence_state

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
        """Return the current preset mode comfort, eco, boost,...,"""
        return str(self._state_manager.current_state.preset)

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes.
        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._attr_preset_modes

    @property
    def vtherm_preset_mode(self) -> VThermPreset | None:
        """Return the current preset mode comfort, eco, boost,...,"""
        return self._state_manager.current_state.preset

    @property
    def vtherm_preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes.
        Requires ClimateEntityFeature.PRESET_MODE.
        """
        return self._vtherm_preset_modes

    @property
    def last_temperature_slope(self) -> float | None:
        """Return the last temperature slope curve if any"""
        return self._window_manager.last_slope

    @property
    def nb_underlying_entities(self) -> int:
        """Returns the number of underlying entities"""
        return len(self._underlyings)

    @property
    def underlying_entities(self) -> list | None:
        """Returns the underlying entities"""
        return self._underlyings

    @property
    def activable_underlying_entities(self) -> list | None:
        """Returns the activable underlying entities for controlling
         the central boiler"""
        return self.underlying_entities

    def find_underlying_by_entity_id(self, entity_id: str) -> Entity | None:
        """Get the underlying entity by a entity_id"""
        for under in self._underlyings:
            if under.entity_id == entity_id:
                return under
        return None

    @property
    def is_on(self) -> bool:
        """True if the VTherm is on (! HVAC_OFF)"""
        return self.vtherm_hvac_mode and self.vtherm_hvac_mode != VThermHvacMode_OFF

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

    @property
    def hvac_off_reason(self) -> str | None:
        """Returns the reason of the last switch to HVAC_OFF
        This is useful for features that turns off the VTherm like
        window detection or auto-start-stop"""
        return self._hvac_off_reason

    @property
    def temperature_reason(self) -> str | None:
        """Returns the reason of the target temperature
        This is useful for features that changes the VTherm like window detection or power management"""
        return self._temperature_reason

    @property
    def is_sleeping(self) -> bool:
        """True if the thermostat is in sleep mode. Only for over_climate with valve regulation"""
        return False

    @property
    def have_valve_regulation(self) -> bool:
        """True if the Thermostat is regulated by valve"""
        return False

    @property
    def power_percent(self) -> float | None:
        """Get the current on_percent as a percentage value. valid only for Vtherm with a TPI algo
        Get the current on_percent value"""
        if self._prop_algorithm and self._prop_algorithm.on_percent is not None:
            return round(self._prop_algorithm.on_percent * 100, 0)
        else:
            return None

    @property
    def on_percent(self) -> float | None:
        """Get the current on_percent value. valid only for Vtherm with a TPI algo"""
        if self._prop_algorithm and self._prop_algorithm.on_percent is not None:
            return self._prop_algorithm.on_percent
        else:
            return None

    @property
    def vtherm_type(self) -> str | None:
        """Return the type of thermostat"""
        return None

    @property
    def config_entry(self) -> ConfigEntry | None:
        """Return the config entry associated with the thermostat."""
        return self._hass.config_entries.async_get_entry(self.unique_id)

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

    ##
    ## Entry events (from linked devices or users)
    ##

    @staticmethod
    def check_lock(func):
        """Decorator to check if the thermostat is locked."""
        async def wrapper(self, *args, **kwargs):
            if self.lock_manager.check_is_locked(func.__name__):
                return
            return await func(self, *args, **kwargs)
        return wrapper

    @overrides
    @check_lock
    async def async_set_hvac_mode(self, hvac_mode: VThermHvacMode):  # , need_control_heating=True):
        """Set new target hvac mode. Uses the HA VThermHvacMode enum to respect the original type."""
        write_event_log(_LOGGER, self, f"Set hvac mode: {hvac_mode}")

        if hvac_mode is None:
            return

        # Change the requested state
        self._state_manager.requested_state.set_hvac_mode(hvac_mode)
        await self.update_states(force=False)

    @overrides
    @check_lock
    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        # We accept a new preset when:
        # 1. last_central_mode is not set,
        # 2. or last_central_mode is AUTO,
        # 3. or last_central_mode is CENTRAL_MODE_FROST_PROTECTION and preset_mode is
        #    VThermPreset.FROST (to be abel to re-set the preset_mode)

        write_event_log(_LOGGER, self, f"Set preset mode: {preset_mode}")

        vtherm_preset_mode = VThermPreset(preset_mode)
        accept = self._last_central_mode in [
            None,
            CENTRAL_MODE_AUTO,
            CENTRAL_MODE_COOL_ONLY,
            CENTRAL_MODE_HEAT_ONLY,
            CENTRAL_MODE_STOPPED,
        ] or (self._last_central_mode == CENTRAL_MODE_FROST_PROTECTION and preset_mode == VThermPreset.FROST)
        if not accept:
            _LOGGER.info(
                "%s - Impossible to change the preset to %s because central mode is %s",
                self,
                preset_mode,
                self._last_central_mode,
            )

            return

        await self.async_set_preset_mode_internal(vtherm_preset_mode)  # overwrite_saved_preset=overwrite_saved_preset)
        await self.update_states(force=True)

    async def async_set_preset_mode_internal(self, preset_mode: VThermPreset):  # , overwrite_saved_preset=True):
        """Set new preset mode."""
        _LOGGER.info("%s - Set requested preset_mode: %s", self, preset_mode)

        if preset_mode not in (self._vtherm_preset_modes or []) and preset_mode not in HIDDEN_PRESETS:
            raise ValueError(f"Got unsupported preset_mode {preset_mode}. Must be one of {self._vtherm_preset_modes}")

        self._state_manager.requested_state.set_preset(preset_mode)

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        _LOGGER.info("%s - Set fan mode: %s", self, fan_mode)
        return

    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        write_event_log(_LOGGER, self, f"Set humidity: {humidity}")
        return

    async def async_set_swing_mode(self, swing_mode: str):
        """Set new target swing operation."""
        write_event_log(_LOGGER, self, f"Set swing mode: {swing_mode}")
        return

    @check_lock
    async def async_set_temperature(self, **kwargs):
        """Set new requested target temperature and turn off any active presets."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        write_event_log(_LOGGER, self, f"Set target temp: {temperature}")
        if temperature is None:
            return

        self._state_manager.requested_state.set_target_temperature(temperature)
        self._state_manager.requested_state.set_preset(VThermPreset.NONE)
        await self.update_states(force=True)

    async def set_preset_temperature(
        self,
        preset: str,
        temperature: float | None = None,
        temperature_away: float | None = None,
    ):
        """Called by a to change the temperature of a preset
        data:
            preset: boost
            temperature: 17.8
            temperature_away: 15
        target:
            entity_id: climate.thermostat_2
        """
        write_event_log(_LOGGER, self, f"Calling SERVICE_SET_PRESET_TEMPERATURE, preset: {preset}, temperature: {temperature}, temperature_away: {temperature_away}")

        if preset in self._presets:
            if temperature is not None:
                self._presets[preset] = temperature
            if self._presence_manager.is_configured and temperature_away is not None:
                self._presets_away[self.get_preset_away_name(preset)] = temperature_away
        else:
            _LOGGER.warning("%s - No preset %s configured for this thermostat. ", self, preset)

        if preset in self._presets:
            if temperature is not None:
                self._presets[preset] = temperature
            if self._presence_manager.is_configured and temperature_away is not None:
                self._presets_away[self.get_preset_away_name(preset)] = temperature_away
        else:
            _LOGGER.warning(
                "%s - No preset %s configured for this thermostat. Ignoring set_preset_temperature call",
                self,
                preset,
            )

        # If the changed preset is active, change the current temperature
        # Issue #119 - reload new preset temperature also in ac mode
        if preset.startswith(self.preset_mode):
            self.requested_state.force_changed()
            await self.update_states(force=True)

    ##
    ## Calculation and utility functions
    ##
    async def _get_tpi_data(self) -> dict[str, Any]:
        """Calculate and return TPI cycle parameters.
        Called by AutoTpiManager at the start of each cycle.
        """
        # Sync coefficients from AutoTpiManager before calculating
        if self._auto_tpi_manager and self._auto_tpi_manager.learning_active:
            new_params = await self._auto_tpi_manager.calculate()
            if new_params:
                new_coef_int = new_params.get(CONF_TPI_COEF_INT)
                new_coef_ext = new_params.get(CONF_TPI_COEF_EXT)
                if new_coef_int != self._prop_algorithm.tpi_coef_int or \
                   new_coef_ext != self._prop_algorithm.tpi_coef_ext:
                    self._prop_algorithm.update_tpi_coef(new_coef_int, new_coef_ext)
                    _LOGGER.debug("%s - Synced TPI coeffs before cycle: int=%.3f, ext=%.3f",
                                  self, new_coef_int, new_coef_ext)

        # Force recalculation with potentially updated coefficients
        self._prop_algorithm.calculate(
            self.target_temperature,
            self._cur_temp,
            self._cur_ext_temp,
            self.last_temperature_slope,
            self.vtherm_hvac_mode or VThermHvacMode_OFF,
        )

        return {
            "on_time_sec": self._prop_algorithm.on_time_sec if self._prop_algorithm else 0,
            "off_time_sec": self._prop_algorithm.off_time_sec if self._prop_algorithm else 0,
            "on_percent": self._prop_algorithm.on_percent if self._prop_algorithm else 0,
            "hvac_mode": str(self.vtherm_hvac_mode),
        }

    async def _on_tpi_cycle_start(self, params: dict[str, Any]):
        """Called by AutoTpiManager when a new cycle starts."""
        await self._fire_cycle_start_callbacks(
            params.get("on_time_sec", 0),
            params.get("off_time_sec", 0),
            params.get("on_percent", 0),
            params.get("hvac_mode", "stop")
        )

    async def update_states(self, force=False):
        """Update the states of the thermostat considering the requested state and the current state"""
        changed = False
        if self._state_manager.requested_state.is_changed:
            if changed := await self._state_manager.calculate_current_state(self):
                _LOGGER.info("%s - current state changed to %s", self, self._state_manager.current_state)
                sub_need_control_heating = False
                # Apply preset
                if self._state_manager.current_state.is_preset_changed:
                    _LOGGER.info("%s - Applying new preset: %s", self, self.vtherm_preset_mode)
                    self.send_event(EventType.PRESET_EVENT, {"preset": self.preset_mode})
                    if self.preset_mode not in HIDDEN_PRESETS:
                        self._attr_preset_mode = self.preset_mode

                # Apply temperature
                if self._state_manager.current_state.is_target_temperature_changed:
                    _LOGGER.info("%s - Applying new target temperature: %s", self, self.target_temperature)
                    self._attr_target_temperature = self.target_temperature

                # Apply hvac_mode
                if self._state_manager.current_state.is_hvac_mode_changed:
                    _LOGGER.info("%s - Applying new hvac mode: %s", self, self.vtherm_hvac_mode)
                    # Delegate to all underlying
                    for under in self._underlyings:
                        sub_need_control_heating = await under.set_hvac_mode(self.vtherm_hvac_mode) or sub_need_control_heating
                    self._attr_hvac_mode = to_legacy_ha_hvac_mode(self.vtherm_hvac_mode)
                    self.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": str(self.vtherm_hvac_mode)})
                    # Remove eventual overpowering if we want to turn-off
                    if self.hvac_mode in [VThermHvacMode_OFF, VThermHvacMode_SLEEP] and self.power_manager.is_overpowering_detected:
                        await self.power_manager.set_overpowering(False)

                if changed:
                    self.recalculate(force=force)
                    self.reset_last_change_time_from_vtherm()
                    await self.async_control_heating(force=force or sub_need_control_heating)

                    if self._state_manager.current_state.is_hvac_mode_changed:
                        if self._auto_tpi_manager:
                            # Start cycle loop for HEAT or COOL modes, regardless of learning_active
                            if self.vtherm_hvac_mode in [VThermHvacMode_HEAT, VThermHvacMode_COOL]:
                                await self._auto_tpi_manager.start_cycle_loop(
                                    self._get_tpi_data,
                                    self._on_tpi_cycle_start
                                )
                            else:
                                self._auto_tpi_manager.stop_cycle_loop()

            self.calculate_hvac_action()
            self.update_custom_attributes()
            self.async_write_ha_state()
        else:
            _LOGGER.debug("%s - current state did not change. Still %s", self, self._state_manager.current_state)

        self._state_manager.requested_state.reset_changed()
        self._state_manager.current_state.reset_changed()

        return changed

    async def async_control_heating(self, timestamp=None, force=False) -> bool:
        """The main function used to run the calculation at each cycle
        Returns True if the cycle was successfully calculated, False otherwise."""

        if timestamp:
            # Timestamp is set only on periodical calls
            write_event_log(_LOGGER, self, "Periodical control cycle started")

        _LOGGER.debug(
            "%s - Checking new cycle. hvac_mode=%s, safety_state=%s, preset_mode=%s, force=%s",
            self,
            self.vtherm_hvac_mode,
            self._safety_manager.safety_state,
            self.vtherm_preset_mode,
            force,
        )

        # check auto_window conditions
        await self._window_manager.manage_window_auto(in_cycle=True)

        # In over_climate mode, if the underlying climate is not initialized,
        # try to initialize it
        if not self.is_initialized:
            if not self.init_underlyings():
                # still not found, we an stop here
                return False

        if await self._safety_manager.refresh_and_update_if_changed():
            return False

        if self._safety_manager.is_safety_detected and self.is_over_climate:
            _LOGGER.debug("%s - End of cycle (safety and over climate)", self)

            return True

        # Feed the Auto TPI manager (Before starting the cycle to apply new coeffs if any)
        if self._auto_tpi_manager:
            await self._auto_tpi_manager.update(
                room_temp=self._cur_temp,
                ext_temp=self._cur_ext_temp,
                target_temp=self.target_temperature,
                hvac_mode=str(self.vtherm_hvac_mode),
                is_overpowering_detected=self.power_manager.is_overpowering_detected,
            )

            # Check if we have new learned parameters
            new_params = await self._auto_tpi_manager.calculate()
            if self._auto_tpi_manager.learning_active and new_params:
                finalized_values = await self._auto_tpi_manager.process_learning_completion(new_params)
                
                if finalized_values:
                    # Update local configured values to match persisted ones
                    self._tpi_coef_int = finalized_values.get(CONF_TPI_COEF_INT, self._tpi_coef_int)
                    self._tpi_coef_ext = finalized_values.get(CONF_TPI_COEF_EXT, self._tpi_coef_ext)
                    
                    # Update PropAlgorithm with the newly persisted values for the current cycle
                    if self._prop_algorithm:
                        self._prop_algorithm.update_tpi_coef(self._tpi_coef_int, self._tpi_coef_ext)
                        _LOGGER.info("%s - Synced PropAlgorithm with final persisted Auto TPI coeffs: int=%.3f, ext=%.3f",
                                      self, self._tpi_coef_int, self._tpi_coef_ext)
        
        # Stop here if we are off
        if self.vtherm_hvac_mode == VThermHvacMode_OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF)", self)
            # A security to force stop heater if still active
            if self.is_device_active:
                await self.async_underlying_entity_turn_off()
        else:
            for under in self._underlyings:
                await under.start_cycle(
                    self.vtherm_hvac_mode,
                    self._prop_algorithm.on_time_sec if self._prop_algorithm else None,
                    self._prop_algorithm.off_time_sec if self._prop_algorithm else None,
                    self._prop_algorithm.on_percent if self._prop_algorithm else None,
                    force,
                )

        self.calculate_hvac_action()
        self.update_custom_attributes()
        self.async_write_ha_state()
        return True

    def reset_last_change_time_from_vtherm(self, old_preset_mode: VThermPreset | None = None):  # pylint: disable=unused-argument
        """Reset to now the last change time"""
        self._last_change_time_from_vtherm = self.now
        _LOGGER.debug(
            "%s - last_change_time is now %s", self, self._last_change_time_from_vtherm
        )

    def reset_last_temperature_time(self, old_preset_mode: VThermPreset | str | None = None):
        """Reset to now the last temperature time if conditions are satisfied"""
        if self._state_manager.current_state.preset not in HIDDEN_PRESETS and old_preset_mode not in HIDDEN_PRESETS:
            self._last_temperature_measure = self._last_ext_temperature_measure = (
                self.now
            )

    def find_preset_temp(self, preset_mode: VThermPreset):
        """Find the right temperature of a preset considering
         the presence if configured"""
        if preset_mode is None or preset_mode == VThermPreset.NONE:
            return self._attr_max_temp if self._ac_mode and self.vtherm_hvac_mode == VThermHvacMode_COOL else self._attr_min_temp

        if preset_mode == VThermPreset.SAFETY:
            return self._state_manager.current_state.target_temperature
            # In safety just keep the current target temperature,
            # the thermostat should be off

        if preset_mode == VThermPreset.POWER:
            return self._power_manager.power_temperature
        if preset_mode == VThermPreset.ACTIVITY:
            motion_preset = self._motion_manager.get_current_motion_preset()
            if self._ac_mode and self.vtherm_hvac_mode == VThermHvacMode_COOL:
                motion_preset = motion_preset + PRESET_AC_SUFFIX

            if motion_preset in self._presets:
                if self._presence_manager.is_absence_detected:
                    return self._presets_away[motion_preset + PRESET_AWAY_SUFFIX]
                else:
                    return self._presets[motion_preset]
            else:
                return None
        else:
            # Select _ac presets if in COOL Mode (or over_switch with _ac_mode) or OFF but requested is cool
            preset_name = preset_mode
            if (
                (self._ac_mode and self.vtherm_hvac_mode == VThermHvacMode_COOL)
                or (self.vtherm_hvac_mode == VThermHvacMode_OFF and self.requested_state.hvac_mode == VThermHvacMode_COOL)
                #                (self.is_over_switch and self._ac_mode)
                #                or self.vtherm_hvac_mode == VThermHvacMode_COOL
                #                or (self.vtherm_hvac_mode == VThermHvacMode_OFF and self.requested_state.hvac_mode == VThermHvacMode_COOL)
            ):
                # if self._ac_mode and self.vtherm_hvac_mode == VThermHvacMode_COOL:
                preset_name += PRESET_AC_SUFFIX

            _LOGGER.info("%s - find preset temp: %s", self, preset_mode)

            temp_val = self._presets.get(preset_name, 0)
            # if not self._presence_on or self._presence_state in [
            #     None,
            #     STATE_ON,
            #     STATE_HOME,
            # ]:
            if self._presence_manager.is_absence_detected:
                # We should return the preset_away temp val but if
                # preset temp is 0, that means the user don't want to use
                # the preset so we return 0, even if there is a value is preset_away
                return self._presets_away.get(self.get_preset_away_name(preset_name), 0) if temp_val > 0 else temp_val
            else:
                return temp_val

    def get_preset_away_name(self, preset_mode: str) -> str:
        """Get the preset name in away mode (when presence is off)"""
        return preset_mode + PRESET_AWAY_SUFFIX

    def get_state_date_or_now(self, state: State) -> datetime:
        """Extract the last_changed state from State or return now if not available"""
        return (
            state.last_changed.astimezone(self._current_tz)
            if isinstance(state.last_changed, datetime)
            else self.now
        )

    def get_last_updated_date_or_now(self, state: State) -> datetime:
        """Extract the last_changed state from State or return now if not available"""
        return (
            state.last_updated.astimezone(self._current_tz)
            if isinstance(state.last_updated, datetime)
            else self.now
        )

    async def async_underlying_entity_turn_off(self):
        """Turn heater toggleable device off. Used by Window, overpowering,
        control_heating to turn all off"""

        for under in self._underlyings:
            await under.turn_off_and_cancel_cycle()

    def set_hvac_off_reason(self, hvac_off_reason: str | None):
        """Set the reason of hvac_off"""
        self._hvac_off_reason = hvac_off_reason

    def set_temperature_reason(self, temperature_reason: str | None):
        """Set the reason of temperature"""
        self._temperature_reason = temperature_reason

    async def check_central_mode(self, new_central_mode: str | None, old_central_mode: str | None):
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

        self._last_central_mode = new_central_mode

        self.requested_state.force_changed()
        await self.update_states()
        return

    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state.
        Should be overridden by super class
        """
        raise NotImplementedError()

    def incremente_energy(self):
        """increment the energy counter if device is active
        Should be overridden by super class
        """
        raise NotImplementedError()

    def calculate_hvac_action(self, _: list = None) -> HVACAction | None:
        """Calculate the HVAC action based on the current state and underlying devices"""
        if self.vtherm_hvac_mode == VThermHvacMode_OFF:
            action = HVACAction.OFF
        elif not self.is_device_active:
            action = HVACAction.IDLE
        elif self.vtherm_hvac_mode == VThermHvacMode_COOL:
            action = HVACAction.COOLING
        else:
            action = HVACAction.HEATING
        self._attr_hvac_action = action

    def update_custom_attributes(self):
        """Update the custom extra attributes for the entity"""

        messages: list[str] = []
        if self.safety_manager.is_safety_detected:
            messages.append(MSG_SAFETY_DETECTED)
        if self.power_manager.is_overpowering_detected:
            messages.append(MSG_OVERPOWERING_DETECTED)
        if self.hvac_off_reason:
            messages.append(self.hvac_off_reason)
        if self.temperature_reason:
            messages.append(self.temperature_reason)

        self._attr_extra_state_attributes: dict[str, Any] = {
            "hvac_action": self.hvac_action,
            "hvac_mode": self.hvac_mode,
            "preset_mode": self.preset_mode,
            "ema_temp": self._ema_temp,
            "specific_states": {
                "is_on": self.is_on,
                "last_central_mode": self.last_central_mode,
                "last_update_datetime": self.now.isoformat(),
                "ext_current_temperature": self._cur_ext_temp,
                "last_temperature_datetime": self._last_temperature_measure.astimezone(self._current_tz).isoformat(),
                "last_ext_temperature_datetime": self._last_ext_temperature_measure.astimezone(self._current_tz).isoformat(),
                "is_device_active": self.is_device_active,
                "device_actives": self.device_actives,
                "nb_device_actives": self.nb_device_actives,
                "ema_temp": self._ema_temp,
                "temperature_slope": round(self.last_temperature_slope or 0, 3),
                "hvac_off_reason": self.hvac_off_reason,
                ATTR_TOTAL_ENERGY: self.total_energy,
                "last_change_time_from_vtherm": (
                    self._last_change_time_from_vtherm.astimezone(self._current_tz).isoformat() if self._last_change_time_from_vtherm is not None else None
                ),
                "messages": messages,
                "is_sleeping": self.is_sleeping,
                "is_locked": self.lock_manager.is_locked,
                "is_recalculate_scheduled": self.is_recalculate_scheduled,
                "auto_tpi_state": (
                    "on"
                    if self._auto_tpi_manager and self._auto_tpi_manager.learning_active
                    else "off"
                ),
                "auto_tpi_learning": (
                    self._auto_tpi_manager.state.to_dict()
                    if self._auto_tpi_manager
                    else None
                ),
            },
            "configuration": {
                "ac_mode": self._ac_mode,
                "type": self.vtherm_type,
                "is_controlled_by_central_mode": self.is_controlled_by_central_mode,
                "target_temperature_step": self.target_temperature_step,
                "minimal_activation_delay_sec": self._minimal_activation_delay,
                "minimal_deactivation_delay_sec": self._minimal_deactivation_delay,
                "timezone": str(self._current_tz),
                "temperature_unit": self.temperature_unit,
                "is_used_by_central_boiler": self.is_used_by_central_boiler,
                "max_on_percent": self._max_on_percent,
                "have_valve_regulation": self.have_valve_regulation,
                "cycle_min": self._cycle_min,
            },
            "preset_temperatures": {
                "frost_temp": self._presets.get(VThermPreset.FROST, 0),
                "eco_temp": self._presets.get(VThermPreset.ECO, 0),
                "boost_temp": self._presets.get(VThermPreset.BOOST, 0),
                "comfort_temp": self._presets.get(VThermPreset.COMFORT, 0),
                "frost_away_temp": self._presets_away.get(self.get_preset_away_name(VThermPreset.FROST), 0),
                "eco_away_temp": self._presets_away.get(self.get_preset_away_name(VThermPreset.ECO), 0),
                "boost_away_temp": self._presets_away.get(self.get_preset_away_name(VThermPreset.BOOST), 0),
                "comfort_away_temp": self._presets_away.get(self.get_preset_away_name(VThermPreset.COMFORT), 0),
            },
        }

        self._state_manager.add_custom_attributes(self._attr_extra_state_attributes)

        for manager in self._managers:
            manager.add_custom_attributes(self._attr_extra_state_attributes)

    def send_event(self, event_type: EventType, data: dict):
        """Send an event"""
        send_vtherm_event(self._hass, event_type=event_type, entity=self, data=data)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(VThermHvacMode_OFF)

    async def async_turn_on(self) -> None:
        if self._ac_mode:
            await self.async_set_hvac_mode(VThermHvacMode_COOL)
        else:
            await self.async_set_hvac_mode(VThermHvacMode_HEAT)

    def is_preset_configured(self, preset) -> bool:
        """Returns True if the preset in argument is configured"""
        return self._presets.get(preset, None) is not None

    ##
    ## Device changes events
    ##

    @callback
    async def _async_temperature_changed(self, event: Event) -> callable:
        """Handle temperature of the temperature sensor changes.
        Return the function to dearm (clear) the window auto check"""
        new_state: State = event.data.get("new_state")
        write_event_log(_LOGGER, self, f"Temperature changed to state {new_state.state if new_state else None}")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        dearm_window_auto = await self._async_update_temp(new_state)
        self.recalculate()

        # Potentially it generates a safety event
        if await self._safety_manager.refresh_and_update_if_changed() or (self.auto_start_stop_manager and await self.auto_start_stop_manager.refresh_and_update_if_changed()):
            _LOGGER.info("%s - Change in safety alert or auto_start_stopis detected. Force update states", self)
            return dearm_window_auto

        await self.async_control_heating(force=False)

        return dearm_window_auto

    @callback
    async def _async_last_seen_temperature_changed(self, event: Event):
        """Handle last seen temperature sensor changes."""
        new_state: State = event.data.get("new_state")
        write_event_log(_LOGGER, self, f"Last seen temperature changed to state {new_state.state if new_state else None}")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        # try to extract the datetime (from state)
        try:
            old_safety: bool = self._safety_manager.is_safety_detected
            safety: bool = old_safety

            # Convert ISO 8601 string to datetime object
            self._last_temperature_measure = self.get_last_updated_date_or_now(new_state)
            # issue 690 - don't reset the last change time on lastSeen
            # self.reset_last_change_time_from_vtherm()
            _LOGGER.debug(
                "%s - new last_temperature_measure is now: %s",
                self,
                self._last_temperature_measure,
            )

            # try to restart if we were in safety mode
            if self._safety_manager.is_safety_detected:
                safety = await self._safety_manager.refresh_state()

            if safety != old_safety:
                _LOGGER.debug("%s - Change in safety alert is detected. Force update states", self)
                self.requested_state.force_changed()
                await self.update_states(force=True)

        except ValueError as err:
            # La conversion a échoué, la chaîne n'est pas au format ISO 8601
            _LOGGER.warning(
                "%s - impossible to convert last seen datetime %s. Error is: %s",
                self,
                new_state.state,
                err,
            )

    async def _async_ext_temperature_changed(self, event: Event):
        """Handle external temperature of the sensor changes."""
        new_state: State = event.data.get("new_state")
        write_event_log(_LOGGER, self, f"Outdoor temperature changed to state {new_state.state if new_state else None}")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        await self._async_update_ext_temp(new_state)
        self.recalculate()

        # Potentially it generates a safety event
        if await self._safety_manager.refresh_and_update_if_changed() or (self.auto_start_stop_manager and await self.auto_start_stop_manager.refresh_and_update_if_changed()):
            _LOGGER.info("%s - Change in safety alert or auto_start_stopis detected. Force update states", self)
            return

        await self.async_control_heating(force=False)

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
            self._ema_temp = self._ema_algo.calculate_ema(self._cur_temp, self._last_temperature_measure)

            _LOGGER.debug(
                "%s - After setting _last_temperature_measure %s, state.last_changed.replace=%s",
                self,
                self._last_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            # if self._safety_manager.is_safety_detected:
            #     await self._safety_manager.refresh_state()

            # check window_auto
            return await self._window_manager.manage_window_auto()

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
                "%s - After setting _last_ext_temperature_measure %s, state.last_changed.replace=%s",
                self,
                self._last_ext_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            # if self._safety_manager.is_safety_detected:
            #     await self._safety_manager.refresh_state()
        except ValueError as ex:
            _LOGGER.error("Unable to update external temperature from sensor: %s", ex)

    ##
    ## Services (actions)
    ##

    async def service_set_presence(self, presence: str):
        """Called by a service call:
        service: versatile_thermostat.set_presence
        data:
            presence: "off"
        target:
            entity_id: climate.thermostat_1
        """
        if self.lock_manager.check_is_locked("service_set_presence"):
            return
        write_event_log(_LOGGER, self, f"Calling SERVICE_SET_PRESENCE, presence: {presence}")
        await self._presence_manager.update_presence(presence)
        await self.async_control_heating(force=True)

    async def service_set_safety(
        self,
        delay_min: int,
        min_on_percent: float,
        default_on_percent: float,
    ):
        """Called by a service call:
        service: versatile_thermostat.set_safety
        data:
            delay_min: 15
            min_on_percent: 0.5
            default_on_percent: 0.2
        target:
            entity_id: climate.thermostat_2
        """
        if self.lock_manager.check_is_locked("service_set_safety"):
            return
        write_event_log(
            _LOGGER, self, f"Calling SERVICE_SET_SAFETY, delay_min: {delay_min}, " f"min_on_percent: {min_on_percent * 100} %, default_on_percent: {default_on_percent * 100} %"
        )
        if delay_min:
            self._safety_manager.set_safety_delay_min(delay_min)
        if min_on_percent:
            self._safety_manager.set_safety_min_on_percent(min_on_percent)
        if default_on_percent:
            self._safety_manager.set_safety_default_on_percent(default_on_percent)

        if self._prop_algorithm:
            self._prop_algorithm.set_safety(
                self._safety_manager.safety_default_on_percent
            )

        await self.async_control_heating()
        self.update_custom_attributes()
        self.async_write_ha_state()

    async def service_set_window_bypass_state(self, window_bypass: bool):
        """Called by a service call:
        service: versatile_thermostat.set_window_bypass
        data:
            window_bypass: True
        target:
            entity_id: climate.thermostat_1
        """
        if self.lock_manager.check_is_locked("service_set_window_bypass_state"):
            return
        write_event_log(_LOGGER, self, f"Calling SERVICE_SET_WINDOW_BYPASS, window_bypass: {window_bypass}")
        if await self._window_manager.set_window_bypass(window_bypass):
            self.requested_state.force_changed()
            await self.update_states(force=True)

    async def service_set_hvac_mode_sleep(self):
        """Set the hvac_mode to SLEEP mode (valid only for over_climate with valve regulation):
        service: versatile_thermostat.set_hvac_mode_sleep
        target:
            entity_id: climate.thermostat_1
        """
        if self.lock_manager.check_is_locked("service_set_hvac_mode_sleep"):
            return
        write_event_log(_LOGGER, self, "Calling SERVICE_SET_HVAC_MODE_SLEEP")
        raise NotImplementedError("service_set_hva_mode_sleep not implemented for this kind of thermostat. Only for over_climate with valve regulation is supported")

    async def _async_update_tpi_config_entry(self):
        """Update the config entry with current TPI parameters."""
        entry = self.hass.config_entries.async_get_entry(self._unique_id)
        if entry:
            new_data = entry.data.copy()
            new_data[CONF_TPI_COEF_INT] = self._tpi_coef_int
            new_data[CONF_TPI_COEF_EXT] = self._tpi_coef_ext
            new_data[CONF_TPI_THRESHOLD_LOW] = self._tpi_threshold_low
            new_data[CONF_TPI_THRESHOLD_HIGH] = self._tpi_threshold_high
            new_data[CONF_MINIMAL_ACTIVATION_DELAY] = self._minimal_activation_delay
            new_data[CONF_MINIMAL_DEACTIVATION_DELAY] = self._minimal_deactivation_delay

            result = self.hass.config_entries.async_update_entry(
                entry, data=new_data
            )
            _LOGGER.debug("%s - Config entry updated with new TPI params: %s", self, result)


    async def service_set_tpi_parameters(
        self,
        tpi_coef_int: float | None = None,
        tpi_coef_ext: float | None = None,
        minimal_activation_delay: int | None = None,
        minimal_deactivation_delay: int | None = None,
        tpi_threshold_low: float | None = None,
        tpi_threshold_high: float | None = None,
    ):
        """Called by a service call:
        service: versatile_thermostat.set_tpi_parameters
        data:
            tpi_coef_int: 0.6
            tpi_coef_ext: 0.01
            minimal_activation_delay: 30
            minimal_deactivation_delay: 30
            tpi_threshold_low: 0.1
            tpi_threshold_high: 0.9
        target:
            entity_id: climate.thermostat_1
        """

        if self.lock_manager.check_is_locked("service_set_tpi_parameters"):
            return

        write_event_log(
            _LOGGER,
            self,
            f"Calling SERVICE_SET_TPI_PARAMETERS, tpi_coef_int: {tpi_coef_int}, "
            f"tpi_coef_ext: {tpi_coef_ext}"
            f"minimal_activation_delay: {minimal_activation_delay}, "
            f"minimal_deactivation_delay: {minimal_deactivation_delay}, "
            f"tpi_threshold_low: {tpi_threshold_low}, "
            f"tpi_threshold_high: {tpi_threshold_high}",
        )

        if self._prop_algorithm is None:
            raise ServiceValidationError(f"{self} - No TPI algorithm configured for this thermostat.")

        entry = self.hass.config_entries.async_get_entry(self._unique_id)
        if not entry:
            raise ServiceValidationError(f"{self} - No config entry has been found for this thermostat.")

        if entry.data.get(CONF_USE_TPI_CENTRAL_CONFIG, False):
            raise ServiceValidationError(f"{self} - Impossible to set TPI parameters when using central TPI configuration.")

        self._prop_algorithm.update_parameters(
            tpi_coef_int,
            tpi_coef_ext,
            minimal_activation_delay,
            minimal_deactivation_delay,
            tpi_threshold_low,
            tpi_threshold_high,
        )
        self._tpi_coef_int = self._prop_algorithm.tpi_coef_int
        self._tpi_coef_ext = self._prop_algorithm.tpi_coef_ext
        self._minimal_activation_delay = self._prop_algorithm.minimal_activation_delay
        self._minimal_deactivation_delay = self._prop_algorithm.minimal_deactivation_delay
        self._tpi_threshold_low = self._prop_algorithm.tpi_threshold_low
        self._tpi_threshold_high = self._prop_algorithm.tpi_threshold_high

        # Update the configuration attributes
        await self._async_update_tpi_config_entry()

        self.recalculate()
        await self.async_control_heating(force=True)

    async def service_lock(self, code: str | None = None):
        """Handle the lock service call."""

        if not self.lock_manager.has_lock_settings_enabled:
            _LOGGER.error("%s - Cannot lock thermostat: no lock settings enabled (neither users nor automations)", self)
            raise HomeAssistantError("Cannot lock thermostat: no lock settings enabled. At least one of 'lock users' or 'lock automations' must be enabled.")

        if self.lock_manager.change_lock_state(True, code):
            self.update_custom_attributes()
            self.async_write_ha_state()

    async def service_unlock(self, code: str | None = None):
        """Handle the unlock service call."""
        if self.lock_manager.change_lock_state(False, code):
            self.update_custom_attributes()
            self.async_write_ha_state()

    async def service_set_auto_tpi_mode(self, auto_tpi_mode: bool):
        """Called by a service call:
        service: versatile_thermostat.set_auto_tpi_mode
        data:
            auto_tpi_mode: True
        target:
            entity_id: climate.thermostat_1
        """
        write_event_log(_LOGGER, self, f"Calling SERVICE_SET_AUTO_TPI_MODE, auto_tpi_mode: {auto_tpi_mode}")
        await self.async_set_auto_tpi_mode(auto_tpi_mode)

    async def service_calibrate_capacity(
        self,
        hvac_mode: str,
        save_to_config: bool,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        """Called by a service call:
        service: versatile_thermostat.calibrate_capacity
        data:
            start_date: 2023-11-01T00:00:00+00:00
            end_date: 2023-12-01T00:00:00+00:00
            hvac_mode: heat
            save_to_config: true
        target:
            entity_id: climate.thermostat_1
        """
        write_event_log(_LOGGER, self, f"Calling SERVICE_CALIBRATE_CAPACITY, hvac_mode: {hvac_mode}, save_to_config: {save_to_config}, start_date: {start_date}, end_date: {end_date}")

        if not self._auto_tpi_manager:
            raise ServiceValidationError(f"{self} - Auto TPI Manager not initialized, cannot calibrate capacity.")

        # 1. Convert start_date and end_date to datetime objects and adjust for date-only selection.
        # date selector returns 'YYYY-MM-DD' string. We convert it to a timezone-aware datetime.
        if isinstance(start_date, str):
            _date = dt_util.parse_date(start_date)
            start_date = dt_util.start_of_local_day(_date) if _date else None
            
        if isinstance(end_date, str):
            _date = dt_util.parse_date(end_date)
            # When selecting an end date, we want to include the whole day.
            # History API query is exclusive of end_time, so we set it to the start of the next day.
            _end_day_start = dt_util.start_of_local_day(_date) if _date else None
            end_date = _end_day_start + timedelta(days=1) if _end_day_start else None
            
        # 2. Determine History Time Range
        now = self.now
        
        # history.get_significant_states expects timezone-aware datetime (preferably UTC)
        # Note: start_date and end_date from above are already timezone-aware (local timezone).
        start_time = dt_util.as_utc(start_date) if start_date is not None else now - timedelta(days=30)
        end_time = dt_util.as_utc(end_date) if end_date is not None else now
        
        _LOGGER.info("%s - Calibrating capacity using history from %s to %s", self, start_time, end_time)
        
        entity_ids = [self.entity_id]
        if self._ext_temp_sensor_entity_id:
            entity_ids.append(self._ext_temp_sensor_entity_id)

        states = await get_instance(self.hass).async_add_executor_job(
            partial(
                history.get_significant_states,
                self.hass,
                start_time,
                end_time=end_time,
                entity_ids=entity_ids,
                significant_changes_only=False,
            )
        )

        thermostat_history = states.get(self.entity_id, [])
        outdoor_history = states.get(self._ext_temp_sensor_entity_id, []) if self._ext_temp_sensor_entity_id else []

        _LOGGER.debug("%s - Fetched %d thermostat states and %d outdoor states for capacity calibration.",
                      self, len(thermostat_history), len(outdoor_history))

        # 3. Call Calculation
        result = await self._auto_tpi_manager.calculate_capacity_from_history(
            thermostat_history,
            outdoor_history,
            hvac_mode,
        )

        _LOGGER.info("%s - Capacity calibration result: %s", self, result)

        # 4. Save (if save_to_config is True) - ONLY CAPACITY
        if save_to_config and result and isinstance(result, dict) and result.get("success"):
            
            capacity = result.get("capacity")
            is_heat_mode = hvac_mode == HVACMode.HEAT.value
            
            if capacity is not None:
                await self._auto_tpi_manager.async_update_capacity_config(
                    capacity=capacity, is_heat_mode=is_heat_mode
                )
                
                mode_str = "Heating" if is_heat_mode else "Cooling"
                _LOGGER.info("%s - %s capacity calibrated to %.3f °C/h and saved to AutoTpiManager's state and config.", self, mode_str, capacity)
                
                # Capacity changes don't automatically trigger a recalculate/control heating cycle,
                # as they only affect auto-TPI calculations, not the proportional algorithm directly.
                self.recalculate()

        # Return result (as the service has a response schema defined)
        
        self.update_custom_attributes()
        self.async_write_ha_state()

        return result


    async def async_set_auto_tpi_mode(self, auto_tpi_mode: bool):
        """Set the auto TPI mode"""
        _LOGGER.debug("%s - async_set_auto_tpi_mode called with %s", self, auto_tpi_mode)
        if not self._auto_tpi_manager:
            _LOGGER.warning("%s - Auto TPI Manager not initialized", self)
            return

        # Safety check: Prevent enabling learning if the feature is disabled in config
        if auto_tpi_mode and not self._entry_infos.get(CONF_AUTO_TPI_MODE, False):
            _LOGGER.warning("%s - Cannot start Auto TPI Learning: feature is disabled in configuration", self)
            # Ensure it is stopped
            await self._auto_tpi_manager.stop_learning()
            return

        if auto_tpi_mode:
            # Use the original configured default values, not current (potentially learned) values
            # This ensures a fresh start when restarting learning
            await self._auto_tpi_manager.start_learning(
                coef_int=self._auto_tpi_manager._default_coef_int,
                coef_ext=self._auto_tpi_manager._default_coef_ext
            )

            # Sync PropAlgorithm with the configured coefficients
            if self._prop_algorithm:
                self._prop_algorithm.update_tpi_coef(self._tpi_coef_int, self._tpi_coef_ext)
                _LOGGER.info("%s - PropAlgorithm synced with config: Kint=%.3f, Kext=%.3f",
                             self, self._tpi_coef_int, self._tpi_coef_ext)

            # If we enable auto_tpi, we must disable central config for TPI
            # to avoid overriding the calculated values
            if self._entry_infos:
                self._entry_infos[CONF_USE_TPI_CENTRAL_CONFIG] = False
            
            # Persist the change to the config entry
            entry = self.hass.config_entries.async_get_entry(self._unique_id)
            if entry and entry.data.get(CONF_USE_TPI_CENTRAL_CONFIG, True):
                new_data = entry.data.copy()
                new_data[CONF_USE_TPI_CENTRAL_CONFIG] = False
                self.hass.config_entries.async_update_entry(entry, data=new_data)

            # Start timer if we are in HEAT or COOL
            if self.vtherm_hvac_mode in [VThermHvacMode_HEAT, VThermHvacMode_COOL]:
                await self._auto_tpi_manager.start_cycle_loop(
                    self._get_tpi_data,
                    self._on_tpi_cycle_start
                )
        else:
            await self._auto_tpi_manager.stop_learning()
            self._auto_tpi_manager.stop_cycle_loop()
            
            # Apply configured coefficients to PropAlgorithm to ensure
            # learned values are not kept in the regulation loop
            if self._prop_algorithm:
                self._prop_algorithm.update_tpi_coef(self._tpi_coef_int, self._tpi_coef_ext)
                _LOGGER.info(
                    "%s - PropAlgorithm reset to config values: Kint=%.3f, Kext=%.3f",
                    self, self._tpi_coef_int, self._tpi_coef_ext
                )

        # Fire event to notify potential listeners (like the switch if it existed, or UI)
        self.hass.bus.async_fire(
            EventType.AUTO_TPI_EVENT.value,
            {
                "entity_id": self.entity_id,
                "auto_tpi_mode": self._auto_tpi_manager.learning_active,
            },
        )

        # Force update of state attributes
        self.update_custom_attributes()
        self.async_write_ha_state()

    ##
    ## For testing purpose
    ##
    # @deprecated
    def _set_now(self, now: datetime):
        """Set the now timestamp. This is only for tests purpose
        This method should be replaced by the vthermAPI equivalent"""
        VersatileThermostatAPI.get_vtherm_api(self._hass)._set_now(now)  # pylint: disable=protected-access

    # @deprecated
    @property
    def now(self) -> datetime:
        """Get now. The local datetime or the overloaded _set_now date
        This method should be replaced by the vthermAPI equivalent"""
        return VersatileThermostatAPI.get_vtherm_api(self._hass).now
