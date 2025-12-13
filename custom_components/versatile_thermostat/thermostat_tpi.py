# pylint: disable=line-too-long, abstract-method
""" A base class for TPI based thermostats """
import logging
import asyncio

from datetime import datetime, timedelta
from functools import partial

from homeassistant.core import HomeAssistant, callback
from homeassistant.components.climate import HVACMode
from homeassistant.components.recorder import history, get_instance
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ServiceValidationError

from .base_thermostat import BaseThermostat, ConfigData
from .prop_algorithm import PropAlgorithm
from .auto_tpi_manager import AutoTpiManager
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL
from .commons import write_event_log

_LOGGER = logging.getLogger(__name__)

from typing import Any, Generic
from .underlyings import T

class ThermostatTPI(BaseThermostat[T], Generic[T]):
    """Representation of a base class for Versatile Thermostat with TPI."""

    def __init__(self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData):
        """Initialize the thermostat."""
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
        self._prop_algorithm = None
        self._auto_tpi_manager: AutoTpiManager | None = None

        super().__init__(hass, unique_id, name, entry_infos)

    def post_init(self, config_entry: ConfigData):
        """Finish the initialization of the thermostat"""
        super().post_init(config_entry)

        self._proportional_function = config_entry.get(CONF_PROP_FUNCTION)

        # Initialize TPI parameters
        self._tpi_coef_int = config_entry.get(CONF_TPI_COEF_INT)
        self._tpi_coef_ext = config_entry.get(CONF_TPI_COEF_EXT)
        self._tpi_threshold_low = config_entry.get(CONF_TPI_THRESHOLD_LOW, 0.0)
        self._tpi_threshold_high = config_entry.get(CONF_TPI_THRESHOLD_HIGH, 0.0)
        # If one is 0 then both are 0
        if self._tpi_threshold_low == 0.0 or self._tpi_threshold_high == 0.0:
            self._tpi_threshold_low = 0.0
            self._tpi_threshold_high = 0.0

        self._minimal_activation_delay = config_entry.get(CONF_MINIMAL_ACTIVATION_DELAY, 0)
        self._minimal_deactivation_delay = config_entry.get(CONF_MINIMAL_DEACTIVATION_DELAY, 0)

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

        # Initialize PropAlgorithm
        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
            self._minimal_deactivation_delay,
            self.name,
            max_on_percent=self._max_on_percent,
            tpi_threshold_low=self._tpi_threshold_low,
            tpi_threshold_high=self._tpi_threshold_high,
        )

        # Initialize Auto TPI Manager
        heater_heating_time = config_entry.get(CONF_HEATER_HEATING_TIME, 0)
        heater_cooling_time = config_entry.get(CONF_HEATER_COOLING_TIME, 0)
        calculation_method = config_entry.get(CONF_AUTO_TPI_CALCULATION_METHOD, AUTO_TPI_METHOD_EMA)
        ema_alpha = config_entry.get(CONF_AUTO_TPI_EMA_ALPHA, 0.2)
        avg_initial_weight = config_entry.get(CONF_AUTO_TPI_AVG_INITIAL_WEIGHT, 1)
        max_coef_int = config_entry.get(CONF_AUTO_TPI_MAX_COEF_INT, 1.5)
        heating_rate = config_entry.get(CONF_AUTO_TPI_HEATING_POWER, 1.0)
        cooling_rate = config_entry.get(CONF_AUTO_TPI_COOLING_POWER, 1.0)
        self._auto_tpi_enable_update_config = config_entry.get(CONF_AUTO_TPI_ENABLE_UPDATE_CONFIG, False)
        self._auto_tpi_enable_notification = config_entry.get(CONF_AUTO_TPI_ENABLE_NOTIFICATION, False)
        self._auto_tpi_continuous_learning = False # Default TODO check if configurable
        self._auto_tpi_keep_ext_learning = False # Default TODO check if configurable

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

    def remove_thermostat(self):
        """Called when the thermostat will be removed"""
        if self._auto_tpi_manager:
            self._auto_tpi_manager.stop_cycle_loop()
            self.hass.async_create_task(self._auto_tpi_manager.async_save_data())
        super().remove_thermostat()

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
                    self._prop_algorithm.update_parameters(tpi_coef_int=new_coef_int, tpi_coef_ext=new_coef_ext)
                    _LOGGER.debug("%s - Synced TPI coeffs before cycle: int=%.3f, ext=%.3f",
                                  self, new_coef_int, new_coef_ext)

        # Force recalculation with potentially updated coefficients
        self.recalculate()

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

    async def _control_heating_specific(self, force=False):
        """Implement the specific control heating logic for TPI"""
        
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
                        self._prop_algorithm.update_parameters(tpi_coef_int=self._tpi_coef_int, tpi_coef_ext=self._tpi_coef_ext)
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
        
    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        Should be overridden by super class
        """
        self._prop_algorithm.calculate(
            self.target_temperature,
            self._cur_temp,
            self._cur_ext_temp,
            self.last_temperature_slope,
            self.vtherm_hvac_mode or VThermHvacMode_OFF,
        )

    async def update_states(self, force=False):
        """Update states and eventually start cycle loop"""
        changed = await super().update_states(force)
        
        # If we have a change, we may need to start/stop the cycle loop
        if changed:
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
        return changed

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
                self._prop_algorithm.update_parameters(tpi_coef_int=self._tpi_coef_int, tpi_coef_ext=self._tpi_coef_ext)
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
                self._prop_algorithm.update_parameters(tpi_coef_int=self._tpi_coef_int, tpi_coef_ext=self._tpi_coef_ext)
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

    def update_custom_attributes(self):
        """Update custom attributes"""
        super().update_custom_attributes()
        
        self._attr_extra_state_attributes["specific_states"].update({
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
        })

        self._attr_extra_state_attributes["configuration"].update({
            "minimal_activation_delay_sec": self._minimal_activation_delay,
            "minimal_deactivation_delay_sec": self._minimal_deactivation_delay,
        })