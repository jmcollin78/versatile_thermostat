# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=invalid-name
""" Implements the VersatileThermostat climate component """
import math
import logging
from typing import Any, Generic

from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    State,
)

from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.restore_state import (
    RestoreEntity,
    async_get as restore_async_get,
)
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from homeassistant.helpers.event import (
    async_track_state_change_event,
)


from homeassistant.components.climate.const import (
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
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData, T

from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingEntity

from .prop_algorithm import PropAlgorithm
from .ema import ExponentialMovingAverage

from .base_manager import BaseFeatureManager
from .feature_presence_manager import FeaturePresenceManager
from .feature_power_manager import FeaturePowerManager
from .feature_motion_manager import FeatureMotionManager
from .feature_window_manager import FeatureWindowManager
from .feature_safety_manager import FeatureSafetyManager

_LOGGER = logging.getLogger(__name__)


class BaseThermostat(ClimateEntity, RestoreEntity, Generic[T]):
    """Representation of a base class for all Versatile Thermostat device."""

    # breaking change with 2024.12 climate workaround
    _attr_swing_horizontal_modes = []
    _attr_swing_horizontal_mode = ""

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
                    "saved_preset_mode",
                    "saved_target_temp",
                    "saved_hvac_mode",
                    "saved_preset_mode_central_mode",
                    "saved_hvac_mode_central_mode",
                    "last_temperature_datetime",
                    "last_ext_temperature_datetime",
                    "minimal_activation_delay_sec",
                    "minimal_deactivation_delay_sec",
                    "last_update_datetime",
                    "timezone",
                    "temperature_unit",
                    "is_device_active",
                    "device_actives",
                    "target_temperature_step",
                    "is_used_by_central_boiler",
                    "temperature_slope",
                    "max_on_percent",
                    "have_valve_regulation",
                    "last_change_time_from_vtherm",
                }
            )
        )
        .union(FeaturePresenceManager.unrecorded_attributes)
        .union(FeaturePowerManager.unrecorded_attributes)
        .union(FeatureMotionManager.unrecorded_attributes)
        .union(FeatureWindowManager.unrecorded_attributes)
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

        self._saved_hvac_mode = None

        self._cur_temp = None
        self._ac_mode = None
        self._temp_sensor_entity_id = None
        self._last_seen_temp_sensor_entity_id = None
        self._ext_temp_sensor_entity_id = None
        self._last_ext_temperature_measure = None
        self._last_temperature_measure = None
        self._cur_ext_temp = None
        self._should_relaunch_control_heating = None

        self._thermostat_type = None

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

        self._use_central_config_temperature = False

        self._hvac_off_reason: str | None = None

        # Store the last havac_mode before central mode changes
        # has been introduce to avoid conflict with window
        self._saved_hvac_mode_central_mode = None
        self._saved_preset_mode_central_mode = None

        # Instantiate all features manager
        self._managers: list[BaseFeatureManager] = []

        self._presence_manager: FeaturePresenceManager = FeaturePresenceManager(
            self, hass
        )
        self._power_manager: FeaturePowerManager = FeaturePowerManager(self, hass)
        self._motion_manager: FeatureMotionManager = FeatureMotionManager(self, hass)
        self._window_manager: FeatureWindowManager = FeatureWindowManager(self, hass)
        self._safety_manager: FeatureSafetyManager = FeatureSafetyManager(self, hass)

        self.register_manager(self._presence_manager)
        self.register_manager(self._power_manager)
        self.register_manager(self._motion_manager)
        self.register_manager(self._window_manager)
        self.register_manager(self._safety_manager)

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
        self._attr_max_temp = entry_infos.get(CONF_TEMP_MAX)
        self._attr_min_temp = entry_infos.get(CONF_TEMP_MIN)
        if (step := entry_infos.get(CONF_STEP_TEMPERATURE)) is not None:
            self._attr_target_temperature_step = step

        self._attr_preset_modes = []

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

        # stop listening for all managers
        for manager in self._managers:
            manager.stop_listening()

        for under in self._underlyings:
            under.remove_entity()

    async def async_startup(self, central_configuration):
        """Triggered on startup, used to get old state and set internal states
         accordingly. This is triggered by VTherm API"""
        _LOGGER.debug("%s - Calling async_startup", self)

        _LOGGER.debug("%s - Calling async_startup_internal", self)
        need_write_state = False

        # start listening for all managers
        for manager in self._managers:
            await manager.start_listening()

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

        # refresh states for all managers
        for manager in self._managers:
            if await manager.refresh_state():
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
            # If we have no initial temperature, restore
            if self._target_temp is None:
                # If we have a previously saved temperature
                if old_state.attributes.get(ATTR_TEMPERATURE) is None:
                    if self._ac_mode:
                        await self.change_target_temperature(self.max_temp)
                    else:
                        await self.change_target_temperature(self.min_temp)
                    _LOGGER.warning(
                        "%s - Undefined target temperature, falling back to %s",
                        self,
                        self._target_temp,
                    )
                else:
                    await self.change_target_temperature(
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

            # Restore old hvac_off_reason
            self._hvac_off_reason = old_state.attributes.get(HVAC_OFF_REASON_NAME, None)

            if old_state.state in [
                HVACMode.OFF,
                HVACMode.HEAT,
                HVACMode.COOL,
            ]:
                self._hvac_mode = old_state.state

            # restore also saved info so that window detection will work
            self._saved_hvac_mode = old_state.attributes.get("saved_hvac_mode", None)
            self._saved_preset_mode = old_state.attributes.get(
                "saved_preset_mode", None
            )
            self._saved_hvac_mode_central_mode = old_state.attributes.get("saved_hvac_mode_central_mode", None)
            self._saved_preset_mode_central_mode = old_state.attributes.get("saved_preset_mode_central_mode", None)

            old_total_energy = old_state.attributes.get(ATTR_TOTAL_ENERGY)
            self._total_energy = old_total_energy if old_total_energy is not None else 0
            _LOGGER.debug(
                "%s - get_my_previous_state restored energy is %s",
                self,
                self._total_energy,
            )

            self.restore_specific_previous_state(old_state)
        else:
            # No previous state, try and restore defaults
            if self._target_temp is None:
                if self._ac_mode:
                    await self.change_target_temperature(self.max_temp)
                else:
                    await self.change_target_temperature(self.min_temp)
            _LOGGER.warning(
                "No previously saved temperature, setting to %s", self._target_temp
            )
            self._total_energy = 0
            _LOGGER.debug(
                "%s - get_my_previous_state  no previous state energy is %s",
                self,
                self._total_energy,
            )

        if not self._hvac_mode:
            self._hvac_mode = HVACMode.OFF

        if not self.is_on and self.hvac_off_reason is None:
            self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)

        self.save_target_temp()

        self.send_event(EventType.PRESET_EVENT, {"preset": self._attr_preset_mode})
        self.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": self._hvac_mode})

        _LOGGER.info(
            "%s - restored state is target_temp=%s, preset_mode=%s, hvac_mode=%s",
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

    @property
    def hvac_off_reason(self) -> str | None:
        """Returns the reason of the last switch to HVAC_OFF
        This is useful for features that turns off the VTherm like
        window detection or auto-start-stop"""
        return self._hvac_off_reason

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

        def save_state():
            self.reset_last_change_time_from_vtherm()
            self.update_custom_attributes()
            self.async_write_ha_state()
            self.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": self._hvac_mode})

        # If we already are in OFF, the manual OFF should just
        # overwrite the reason and saved_hvac_mode
        if self._hvac_mode == HVACMode.OFF and hvac_mode == HVACMode.OFF:
            _LOGGER.info(
                "%s - already in OFF. Change the reason to MANUAL "
                "and erase the saved_havc_mode"
            )
            self._hvac_off_reason = HVAC_OFF_REASON_MANUAL
            self._saved_hvac_mode = HVACMode.OFF

            save_state()

            return

        # Remove eventual overpoering if we want to turn-off
        if hvac_mode == HVACMode.OFF and self.power_manager.is_overpowering_detected:
            await self.power_manager.set_overpowering(False)

        self._hvac_mode = hvac_mode

        # Delegate to all underlying
        sub_need_control_heating = False
        for under in self._underlyings:
            sub_need_control_heating = (
                await under.set_hvac_mode(hvac_mode) or need_control_heating
            )

        # If AC is on maybe we have to change the temperature in force mode,
        # but not in frost mode (there is no Frost protection possible in AC mode)
        if (
            self._hvac_mode in [HVACMode.COOL, HVACMode.HEAT, HVACMode.HEAT_COOL]
            and self.preset_mode != PRESET_NONE
        ):
            if self.preset_mode != PRESET_FROST_PROTECTION or self._hvac_mode in [HVACMode.HEAT, HVACMode.HEAT_COOL]:
                await self.async_set_preset_mode_internal(self.preset_mode, True)
            else:
                await self.async_set_preset_mode_internal(PRESET_ECO, True, False)

        if need_control_heating and sub_need_control_heating:
            await self.async_control_heating(force=True)

        # Ensure we update the current operation after changing the mode
        self.reset_last_temperature_time()

        if self._hvac_mode != HVACMode.OFF:
            self.set_hvac_off_reason(None)

        save_state()

    @overrides
    async def async_set_preset_mode(self, preset_mode: str, overwrite_saved_preset=True):
        """Set new preset mode."""

        # We accept a new preset when:
        # 1. last_central_mode is not set,
        # 2. or last_central_mode is AUTO,
        # 3. or last_central_mode is CENTRAL_MODE_FROST_PROTECTION and preset_mode is
        #    PRESET_FROST_PROTECTION (to be abel to re-set the preset_mode)
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

        await self.async_set_preset_mode_internal(preset_mode, force=False, overwrite_saved_preset=overwrite_saved_preset)
        await self.async_control_heating(force=True)

    async def async_set_preset_mode_internal(self, preset_mode: str, force=False, overwrite_saved_preset=True):
        """Set new preset mode."""
        _LOGGER.info("%s - Set preset_mode: %s force=%s", self, preset_mode, force)
        if (
            preset_mode not in (self._attr_preset_modes or [])
            and preset_mode not in HIDDEN_PRESETS
        ):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {
                    self._attr_preset_modes}"  # pylint: disable=line-too-long
            )

        old_preset_mode = self._attr_preset_mode
        if preset_mode == old_preset_mode and not force:
            # I don't think we need to call async_write_ha_state
            # if we didn't change the state
            return

        # In safety mode don't change preset but memorise
        # the new expected preset when safety will be off
        if preset_mode != PRESET_SAFETY and self._safety_manager.is_safety_detected:
            _LOGGER.debug(
                "%s - is in safety mode. Just memorise the new expected ", self
            )
            if preset_mode not in HIDDEN_PRESETS:
                self._saved_preset_mode = preset_mode
            return

        # Remove this old_preset_mode = self._attr_preset_mode
        recalculate = True
        if preset_mode == PRESET_NONE:
            self._attr_preset_mode = PRESET_NONE
            if self._saved_target_temp:
                await self.restore_target_temp()
        elif preset_mode == PRESET_ACTIVITY:
            self._attr_preset_mode = PRESET_ACTIVITY
            await self._motion_manager.update_motion_state(None, False)
        else:
            if self._attr_preset_mode == PRESET_NONE:
                self.save_target_temp()
            self._attr_preset_mode = preset_mode
            # Switch the temperature if window is not 'on'
            if not self._window_manager.is_window_detected or self._window_manager.window_action in [CONF_WINDOW_TURN_OFF, CONF_WINDOW_FAN_ONLY]:
                await self.change_target_temperature(self.find_preset_temp(preset_mode))
            else:
                # Window is on, so we just save the new expected temp
                # so that closing the window will restore it
                recalculate = False
                self._saved_target_temp = self.find_preset_temp(preset_mode)

        if recalculate:
            self.reset_last_temperature_time(old_preset_mode)

            if overwrite_saved_preset:
                self.save_preset_mode()
                self._saved_preset_mode_central_mode = preset_mode

            self.recalculate()
        # Notify only if there was a real change
        if self._attr_preset_mode != old_preset_mode:
            self.send_event(EventType.PRESET_EVENT, {"preset": self._attr_preset_mode})

    def reset_last_change_time_from_vtherm(
        self, old_preset_mode: str | None = None
    ):  # pylint: disable=unused-argument
        """Reset to now the last change time"""
        self._last_change_time_from_vtherm = self.now
        _LOGGER.debug(
            "%s - last_change_time is now %s", self, self._last_change_time_from_vtherm
        )

    def reset_last_temperature_time(self, old_preset_mode: str | None = None):
        """Reset to now the last temperature time if conditions are satisfied"""
        if (
            self._attr_preset_mode not in HIDDEN_PRESETS
            and old_preset_mode not in HIDDEN_PRESETS
        ):
            self._last_temperature_measure = self._last_ext_temperature_measure = (
                self.now
            )

    def find_preset_temp(self, preset_mode: str):
        """Find the right temperature of a preset considering
         the presence if configured"""
        if preset_mode is None or preset_mode == "none":
            return (
                self._attr_max_temp
                if self._ac_mode and self._hvac_mode == HVACMode.COOL
                else self._attr_min_temp
            )

        if preset_mode == PRESET_SAFETY:
            return (
                self._target_temp
            )
            # In safety just keep the current target temperature,
            # the thermostat should be off
        if preset_mode == PRESET_POWER:
            return self._power_manager.power_temperature
        if preset_mode == PRESET_ACTIVITY:
            motion_preset = self._motion_manager.get_current_motion_preset()
            if self._ac_mode and self._hvac_mode == HVACMode.COOL:
                motion_preset = motion_preset + PRESET_AC_SUFFIX

            if motion_preset in self._presets:
                if self._presence_manager.is_absence_detected:
                    return self._presets_away[motion_preset + PRESET_AWAY_SUFFIX]
                else:
                    return self._presets[motion_preset]
            else:
                return None
        else:
            # Select _ac presets if in COOL Mode (or over_switch with _ac_mode)
            if self._ac_mode and self._hvac_mode == HVACMode.COOL:
                preset_mode = preset_mode + PRESET_AC_SUFFIX

            _LOGGER.info("%s - find preset temp: %s", self, preset_mode)

            temp_val = self._presets.get(preset_mode, 0)
            # if not self._presence_on or self._presence_state in [
            #     None,
            #     STATE_ON,
            #     STATE_HOME,
            # ]:
            if self._presence_manager.is_absence_detected:
                # We should return the preset_away temp val but if
                # preset temp is 0, that means the user don't want to use
                # the preset so we return 0, even if there is a value is preset_away
                return (
                    self._presets_away.get(self.get_preset_away_name(preset_mode), 0)
                    if temp_val > 0
                    else temp_val
                )
            else:
                return temp_val

    def get_preset_away_name(self, preset_mode: str) -> str:
        """Get the preset name in away mode (when presence is off)"""
        return preset_mode + PRESET_AWAY_SUFFIX

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        _LOGGER.info("%s - Set fan mode: %s", self, fan_mode)
        return

    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set humidity: %s", self, humidity)
        return

    async def async_set_swing_mode(self, swing_mode: str):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set swing mode: %s", self, swing_mode)
        return

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.info("%s - Set target temp: %s", self, temperature)
        if temperature is None:
            return

        self._attr_preset_mode = PRESET_NONE
        if not self._window_manager.is_window_detected or self._window_manager.window_action in [CONF_WINDOW_TURN_OFF, CONF_WINDOW_FAN_ONLY]:
            await self.change_target_temperature(temperature, force=True)
        else:
            self._saved_target_temp = temperature

    async def change_target_temperature(self, temperature: float, force=False):
        """Set the target temperature and the target temperature
         of underlying climate if any"""
        if temperature:
            self._target_temp = temperature
            if force:
                self.recalculate()
                self.reset_last_change_time_from_vtherm()
                await self.async_control_heating(force=True)

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

    @callback
    async def entry_update_listener(
        self, _, config_entry: ConfigEntry  # hass: HomeAssistant,
    ) -> None:
        """Called when the entry have changed in ConfigFlow"""
        _LOGGER.info("%s - Change entry with the values: %s", self, config_entry.data)

    @callback
    async def _async_temperature_changed(self, event: Event) -> callable:
        """Handle temperature of the temperature sensor changes.
        Return the function to dearm (clear) the window auto check"""
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
            # Convert ISO 8601 string to datetime object
            self._last_temperature_measure = self.get_last_updated_date_or_now(
                new_state
            )
            # issue 690 - don't reset the last change time on lastSeen
            # self.reset_last_change_time_from_vtherm()
            _LOGGER.debug(
                "%s - new last_temperature_measure is now: %s",
                self,
                self._last_temperature_measure,
            )

            # try to restart if we were in safety mode
            if self._safety_manager.is_safety_detected:
                await self._safety_manager.refresh_state()

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
    async def _check_initial_state(self):
        """Prevent the device from keep running if HVAC_MODE_OFF."""
        _LOGGER.debug("%s - Calling _check_initial_state", self)
        for under in self._underlyings:
            await under.check_initial_state(self._hvac_mode)

        # Prevent from starting a VTherm if window is open
        if self.is_on:
            _LOGGER.info("%s - the heater wants to heat. Check to prevent starting the VTherm is window is open", self)
            await self._window_manager.refresh_state()

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
                "%s - After setting _last_temperature_measure %s, "
                "state.last_changed.replace=%s",
                self,
                self._last_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            if self._safety_manager.is_safety_detected:
                await self._safety_manager.refresh_state()

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
                "%s - After setting _last_ext_temperature_measure %s, "
                "state.last_changed.replace=%s",
                self,
                self._last_ext_temperature_measure,
                state.last_changed.astimezone(self._current_tz),
            )

            # try to restart if we were in safety mode
            if self._safety_manager.is_safety_detected:
                await self._safety_manager.refresh_state()
        except ValueError as ex:
            _LOGGER.error("Unable to update external temperature from sensor: %s", ex)

    async def async_underlying_entity_turn_off(self):
        """Turn heater toggleable device off. Used by Window, overpowering,
         control_heating to turn all off"""

        for under in self._underlyings:
            await under.turn_off_and_cancel_cycle()

    def save_preset_mode(self):
        """Save the current preset mode to be restored later
        We never save a hidden preset mode
        """
        if (
            self._attr_preset_mode not in HIDDEN_PRESETS
            and self._attr_preset_mode is not None
        ):
            self._saved_preset_mode = self._attr_preset_mode

    async def restore_preset_mode(self, force=False):
        """Restore a previous preset mode
        We never restore a hidden preset mode. Normally that is not possible
        """
        if (
            self._saved_preset_mode not in HIDDEN_PRESETS
            and self._saved_preset_mode is not None
        ):
            await self.async_set_preset_mode_internal(self._saved_preset_mode, force=force)

    def save_hvac_mode(self):
        """Save the current hvac-mode to be restored later"""
        self._saved_hvac_mode = self._hvac_mode
        _LOGGER.debug(
            "%s - Saved hvac mode - saved_hvac_mode is %s, hvac_mode is %s",
            self,
            self._saved_hvac_mode,
            self._hvac_mode,
        )

    def set_hvac_off_reason(self, hvac_off_reason: str):
        """Set the reason of hvac_off"""
        self._hvac_off_reason = hvac_off_reason

    async def restore_hvac_mode(self, need_control_heating=False):
        """Restore a previous hvac_mod"""
        await self.async_set_hvac_mode(self._saved_hvac_mode, need_control_heating)
        _LOGGER.debug(
            "%s - Restored hvac_mode - saved_hvac_mode is %s, hvac_mode is %s",
            self,
            self._saved_hvac_mode,
            self._hvac_mode,
        )

    def save_target_temp(self):
        """Save the target temperature"""
        self._saved_target_temp = self._target_temp

    async def restore_target_temp(self, force=False):
        """Restore the saved target temp"""
        await self.change_target_temperature(self._saved_target_temp, force=force)

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
            if not is_window_detected:
                self._saved_hvac_mode_central_mode = self._hvac_mode
                self._saved_preset_mode_central_mode = self._attr_preset_mode
            else:
                self._saved_hvac_mode_central_mode = self._saved_hvac_mode
                self._saved_preset_mode_central_mode = self._saved_preset_mode

        async def restore_all():
            """restore preset and hvac_mode"""
            await self.async_set_preset_mode_internal(self._saved_preset_mode_central_mode, force=False)
            await self.async_set_hvac_mode(self._saved_hvac_mode_central_mode, need_control_heating=True)

        is_window_detected = self._window_manager.is_window_detected
        if new_central_mode == CENTRAL_MODE_AUTO:
            if not is_window_detected and not first_init:
                await restore_all()
            elif is_window_detected and self.hvac_mode == HVACMode.OFF:
                # do not restore but mark the reason of off with window detection
                self.set_hvac_off_reason(HVAC_OFF_REASON_WINDOW_DETECTION)
            return

        if old_central_mode == CENTRAL_MODE_AUTO:
            save_all()

        if new_central_mode == CENTRAL_MODE_STOPPED:
            if self.hvac_mode != HVACMode.OFF:
                self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_COOL_ONLY:
            if HVACMode.COOL in self.hvac_modes:
                await self.async_set_hvac_mode(HVACMode.COOL)
            else:
                self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_HEAT_ONLY:
            if HVACMode.HEAT in self.hvac_modes:
                await self.async_set_hvac_mode(HVACMode.HEAT)
            # if not already off
            elif self.hvac_mode != HVACMode.OFF:
                self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

        if new_central_mode == CENTRAL_MODE_FROST_PROTECTION:
            if (
                PRESET_FROST_PROTECTION in self.preset_modes
                and HVACMode.HEAT in self.hvac_modes
            ):
                await self.async_set_hvac_mode(HVACMode.HEAT)
                await self.async_set_preset_mode(PRESET_FROST_PROTECTION, overwrite_saved_preset=False)
            else:
                self.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL)
                await self.async_set_hvac_mode(HVACMode.OFF)
            return

    @property
    def is_initialized(self) -> bool:
        """Check if all underlyings are initialized
        This is useful only for over_climate in which we
        should have found the underlying climate to be operational"""
        return True

    async def async_control_heating(self, force=False, _=None) -> bool:
        """The main function used to run the calculation at each cycle"""

        _LOGGER.debug(
            "%s - Checking new cycle. hvac_mode=%s, safety_state=%s, preset_mode=%s",
            self,
            self._hvac_mode,
            self._safety_manager.safety_state,
            self._attr_preset_mode,
        )

        # check auto_window conditions
        await self._window_manager.manage_window_auto(in_cycle=True)

        # In over_climate mode, if the underlying climate is not initialized,
        # try to initialize it
        if not self.is_initialized:
            if not self.init_underlyings():
                # still not found, we an stop here
                return False

        # Check overpowering condition
        # Not usefull. Will be done at the next power refresh
        # await VersatileThermostatAPI.get_vtherm_api().central_power_manager.refresh_state()

        safety: bool = await self._safety_manager.refresh_state()
        if safety and self.is_over_climate:
            _LOGGER.debug("%s - End of cycle (safety and over climate)", self)
            return True

        # Stop here if we are off
        if self._hvac_mode == HVACMode.OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF)", self)
            # A security to force stop heater if still active
            if self.is_device_active:
                await self.async_underlying_entity_turn_off()
        else:
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
        Should be overridden by super class
        """
        raise NotImplementedError()

    def incremente_energy(self):
        """increment the energy counter if device is active
        Should be overridden by super class
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
            "frost_away_temp": self._presets_away.get(self.get_preset_away_name(PRESET_FROST_PROTECTION), 0),
            "eco_away_temp": self._presets_away.get(self.get_preset_away_name(PRESET_ECO), 0),
            "boost_away_temp": self._presets_away.get(self.get_preset_away_name(PRESET_BOOST), 0),
            "comfort_away_temp": self._presets_away.get(self.get_preset_away_name(PRESET_COMFORT), 0),
            "target_temperature_step": self.target_temperature_step,
            "ext_current_temperature": self._cur_ext_temp,
            "ac_mode": self._ac_mode,
            "saved_target_temp": self._saved_target_temp,
            "saved_preset_mode": self._saved_preset_mode,
            "saved_hvac_mode": self._saved_hvac_mode,
            "saved_preset_mod_central_modee": self._saved_preset_mode_central_mode,
            "saved_hvac_mode_central_mode": self._saved_hvac_mode_central_mode,
            "last_temperature_datetime": self._last_temperature_measure.astimezone(self._current_tz).isoformat(),
            "last_ext_temperature_datetime": self._last_ext_temperature_measure.astimezone(self._current_tz).isoformat(),
            "minimal_activation_delay_sec": self._minimal_activation_delay,
            "minimal_deactivation_delay_sec": self._minimal_deactivation_delay,
            ATTR_TOTAL_ENERGY: self.total_energy,
            "last_update_datetime": self.now.isoformat(),
            "timezone": str(self._current_tz),
            "temperature_unit": self.temperature_unit,
            "is_device_active": self.is_device_active,
            "device_actives": self.device_actives,
            "nb_device_actives": self.nb_device_actives,
            "ema_temp": self._ema_temp,
            "is_used_by_central_boiler": self.is_used_by_central_boiler,
            "temperature_slope": round(self.last_temperature_slope or 0, 3),
            "hvac_off_reason": self.hvac_off_reason,
            "max_on_percent": self._max_on_percent,
            "have_valve_regulation": self.have_valve_regulation,
            "last_change_time_from_vtherm": (
                self._last_change_time_from_vtherm.astimezone(self._current_tz).isoformat() if self._last_change_time_from_vtherm is not None else None
            ),
        }

        for manager in self._managers:
            manager.add_custom_attributes(self._attr_extra_state_attributes)

    @overrides
    def async_write_ha_state(self):
        """overrides to have log"""
        return super().async_write_ha_state()

    @property
    def have_valve_regulation(self) -> bool:
        """True if the Thermostat is regulated by valve"""
        return False

    @property
    def saved_target_temp(self) -> float:
        """Returns the saved_target_temp"""
        return self._saved_target_temp

    @property
    def saved_hvac_mode(self) -> float:
        """Returns the saved_hvac_mode"""
        return self._saved_hvac_mode

    @property
    def saved_preset_mode(self) -> float:
        """Returns the saved_preset_mode"""
        return self._saved_preset_mode

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
        await self._presence_manager.update_presence(presence)
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
            "%s - Calling service_set_preset_temperature, preset: %s, "
            "temperature: %s, temperature_away: %s",
            self,
            preset,
            temperature,
            temperature_away,
        )
        if preset in self._presets:
            if temperature is not None:
                self._presets[preset] = temperature
            if self._presence_manager.is_configured and temperature_away is not None:
                self._presets_away[self.get_preset_away_name(preset)] = temperature_away
        else:
            _LOGGER.warning(
                "%s - No preset %s configured for this thermostat. "
                "Ignoring set_preset_temperature call",
                self,
                preset,
            )

        # If the changed preset is active, change the current temperature
        # Issue #119 - reload new preset temperature also in ac mode
        if preset.startswith(self._attr_preset_mode):
            await self.async_set_preset_mode_internal(preset.rstrip(PRESET_AC_SUFFIX), force=True)
            await self.async_control_heating(force=True)

    async def SERVICE_SET_SAFETY(
        self,
        delay_min: int | None,
        min_on_percent: float | None,
        default_on_percent: float | None,
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
        _LOGGER.info(
            "%s - Calling SERVICE_SET_SAFETY, delay_min: %s, "
            "min_on_percent: %s %%, default_on_percent: %s %%",
            self,
            delay_min,
            min_on_percent * 100,
            default_on_percent * 100,
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
        if await self._window_manager.set_window_bypass(window_bypass):
            self.update_custom_attributes()

    def send_event(self, event_type: EventType, data: dict):
        """Send an event"""
        send_vtherm_event(self._hass, event_type=event_type, entity=self, data=data)

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
        self._attr_preset_modes = [PRESET_NONE]
        if len(self._presets):
            self._support_flags = SUPPORT_FLAGS | ClimateEntityFeature.PRESET_MODE

            for key, _ in CONF_PRESETS.items():
                preset_value = self.find_preset_temp(key)
                if preset_value is not None and preset_value > 0:
                    self._attr_preset_modes.append(key)

            _LOGGER.debug(
                "After adding presets, preset_modes to %s", self._attr_preset_modes
            )
        else:
            _LOGGER.debug("No preset_modes")

        if self._motion_manager.is_configured:
            self._attr_preset_modes.append(PRESET_ACTIVITY)

        # Re-applicate the last preset if any to take change into account
        if self._attr_preset_mode:
            await self.async_set_preset_mode_internal(self._attr_preset_mode, True)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        if self._ac_mode:
            await self.async_set_hvac_mode(HVACMode.COOL)
        else:
            await self.async_set_hvac_mode(HVACMode.HEAT)

    def is_preset_configured(self, preset) -> bool:
        """Returns True if the preset in argument is configured"""
        return self._presets.get(preset, None) is not None

    # For testing purpose
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
