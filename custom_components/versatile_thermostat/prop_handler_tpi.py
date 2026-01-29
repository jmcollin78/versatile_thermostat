# pylint: disable=line-too-long, abstract-method
"""TPI algorithm handler for ThermostatProp."""

import logging
from typing import Any, TYPE_CHECKING
from datetime import datetime

from homeassistant.exceptions import ServiceValidationError

from .prop_algo_tpi import TpiAlgorithm
from .auto_tpi_manager import AutoTpiManager
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL
from .vtherm_api import VersatileThermostatAPI
from .commons import write_event_log
from .const import EventType
from .timing_utils import calculate_cycle_times

if TYPE_CHECKING:
    from .thermostat_prop import ThermostatProp

_LOGGER = logging.getLogger(__name__)


class TPIHandler:
    """Handler for TPI-specific logic.
    
    This class encapsulates all TPI-specific behavior and is used
    via composition by ThermostatProp. It updates thermostat attributes
    directly for backward compatibility with child classes.
    """

    def __init__(self, thermostat: "ThermostatProp"):
        """Initialize handler with parent thermostat reference."""
        self._thermostat = thermostat
        self._auto_tpi_manager: AutoTpiManager | None = None
        # Save default values for Auto TPI reset
        self._default_coef_int: float = 0
        self._default_coef_ext: float = 0

    @property
    def tpi_coef_int(self) -> float:
        """Return TPI internal coefficient from thermostat."""
        return self._thermostat.tpi_coef_int

    @property
    def tpi_coef_ext(self) -> float:
        """Return TPI external coefficient from thermostat."""
        return self._thermostat.tpi_coef_ext

    @property
    def tpi_threshold_low(self) -> float:
        """Return TPI low threshold from thermostat."""
        return self._thermostat.tpi_threshold_low

    @property
    def tpi_threshold_high(self) -> float:
        """Return TPI high threshold from thermostat."""
        return self._thermostat.tpi_threshold_high

    @property
    def minimal_activation_delay(self) -> int:
        """Return minimal activation delay from thermostat."""
        return self._thermostat.minimal_activation_delay

    @property
    def minimal_deactivation_delay(self) -> int:
        """Return minimal deactivation delay from thermostat."""
        return self._thermostat.minimal_deactivation_delay

    @property
    def proportional_function(self) -> str | None:
        """Return proportional function from thermostat."""
        return self._thermostat.proportional_function

    @property
    def auto_tpi_manager(self) -> AutoTpiManager | None:
        """Return the Auto TPI manager."""
        return self._auto_tpi_manager

    def init_algorithm(self):
        """Initialize PropAlgorithm and AutoTpiManager.
        
        Updates thermostat attributes directly for backward compatibility.
        """
        t = self._thermostat
        entry = t.entry_infos

        # Read and set TPI-specific config on thermostat using public setters
        t.tpi_coef_int = entry.get(CONF_TPI_COEF_INT)
        t.tpi_coef_ext = entry.get(CONF_TPI_COEF_EXT)
        t.tpi_threshold_low = entry.get(CONF_TPI_THRESHOLD_LOW, 0.0)
        t.tpi_threshold_high = entry.get(CONF_TPI_THRESHOLD_HIGH, 0.0)
        t.minimal_activation_delay = entry.get(CONF_MINIMAL_ACTIVATION_DELAY, 0)
        t.minimal_deactivation_delay = entry.get(CONF_MINIMAL_DEACTIVATION_DELAY, 0)

        # Save default values for Auto TPI reset
        self._default_coef_int = t.tpi_coef_int
        self._default_coef_ext = t.tpi_coef_ext

        # Validation: thresholds - if one is 0 then both are 0
        if t.tpi_threshold_low == 0.0 or t.tpi_threshold_high == 0.0:
            t.tpi_threshold_low = 0.0
            t.tpi_threshold_high = 0.0

        # Validation: delays
        if (t.minimal_activation_delay + t.minimal_deactivation_delay) / 60 > t.cycle_min:
            _LOGGER.warning(
                "%s - The sum of minimal_activation_delay (%s sec) and "
                "minimal_deactivation_delay (%s sec) is greater than cycle_min (%s). "
                "This can create some unexpected behavior. Please review your configuration",
                t,
                t.minimal_activation_delay,
                t.minimal_deactivation_delay,
                t.cycle_min,
            )

        # Validation: external temp sensor for TPI
        if (
            t.proportional_function == PROPORTIONAL_FUNCTION_TPI
            and t.ext_temp_sensor_entity_id is None
        ):
            _LOGGER.warning(
                "Using TPI function but not external temperature sensor is set. "
                "Removing the delta temp ext factor. "
                "Thermostat will not be fully operational."
            )
            t.tpi_coef_ext = 0

        # Create TpiAlgorithm on thermostat
        t.prop_algorithm = TpiAlgorithm(
            t.tpi_coef_int,
            t.tpi_coef_ext,
            t.name,
            max_on_percent=t.max_on_percent,
            tpi_threshold_low=t.tpi_threshold_low,
            tpi_threshold_high=t.tpi_threshold_high,
        )

        # Initialize Auto TPI Manager from config
        heater_heating_time = entry.get(CONF_AUTO_TPI_HEATER_HEATING_TIME, 5)
        heater_cooling_time = entry.get(CONF_AUTO_TPI_HEATER_COOLING_TIME, 5)
        calculation_method = entry.get(CONF_AUTO_TPI_CALCULATION_METHOD, AUTO_TPI_METHOD_EMA)
        ema_alpha = entry.get(CONF_AUTO_TPI_EMA_ALPHA, 0.2)
        avg_initial_weight = entry.get(CONF_AUTO_TPI_AVG_INITIAL_WEIGHT, 1)

        heating_rate = entry.get(CONF_AUTO_TPI_HEATING_POWER, 1.0)
        cooling_rate = entry.get(CONF_AUTO_TPI_COOLING_POWER, 1.0)
        aggressiveness = entry.get(CONF_AUTO_TPI_AGGRESSIVENESS, 1.0)

        _LOGGER.info("%s - DEBUG: TPI coefficients from entry_infos: int=%.3f, ext=%.3f",
                     t, t.tpi_coef_int, t.tpi_coef_ext)

        self._auto_tpi_manager = AutoTpiManager(
            t.hass,
            t.config_entry,
            t.unique_id,
            t.name,
            t.cycle_min,
            t.tpi_threshold_low,
            t.tpi_threshold_high,
            t.minimal_deactivation_delay,
            coef_int=t.tpi_coef_int,
            coef_ext=t.tpi_coef_ext,
            heater_heating_time=heater_heating_time,
            heater_cooling_time=heater_cooling_time,
            calculation_method=calculation_method,
            ema_alpha=ema_alpha,
            avg_initial_weight=avg_initial_weight,
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            aggressiveness=aggressiveness,
        )
        self._auto_tpi_manager.set_is_vtherm_stopping_callback(lambda: t.is_removed)
        _LOGGER.info("%s - DEBUG: AutoTpiManager initialized with defaults: int=%.3f, ext=%.3f",
                     t, self._auto_tpi_manager._default_coef_int, self._auto_tpi_manager._default_coef_ext)

    async def async_added_to_hass(self):
        """Load Auto TPI data."""
        t = self._thermostat
        if self._auto_tpi_manager:
            # Set entity_id for pre-bootstrap calibration sensor lookup
            self._auto_tpi_manager._entity_id = t.entity_id
            _LOGGER.info("%s - DEBUG: Before load_data - int=%.3f, ext=%.3f", t, t.tpi_coef_int, t.tpi_coef_ext)
            await self._auto_tpi_manager.async_load_data()
            
            # If we have learned parameters, apply them
            learned_params = self._auto_tpi_manager.get_calculated_params()
            if learned_params:
                _LOGGER.info("%s - DEBUG: Learned params found: %s, learning_active=%s",
                             t, learned_params, self._auto_tpi_manager.learning_active)
                if self._auto_tpi_manager.learning_active:
                    t.tpi_coef_int = learned_params.get(CONF_TPI_COEF_INT, t.tpi_coef_int)
                    t.tpi_coef_ext = learned_params.get(CONF_TPI_COEF_EXT, t.tpi_coef_ext)
                    _LOGGER.info("%s - Restored Auto TPI parameters: %s", t, learned_params)
                else:
                    _LOGGER.info("%s - Auto TPI parameters found but not applied because learning is disabled", t)

            _LOGGER.info("%s - DEBUG: After load_data - int=%.3f, ext=%.3f",
                         t, t.tpi_coef_int, t.tpi_coef_ext)

            if self._auto_tpi_manager.learning_active:
                # Security: if the feature is disabled in config, we must stop learning
                if not t.entry_infos.get(CONF_AUTO_TPI_MODE, False):
                    _LOGGER.info("%s - Auto TPI learning was active but feature is disabled in config. Stopping learning.", t)
                    await self._auto_tpi_manager.stop_learning()
                else:
                    _LOGGER.info("%s - Auto TPI learning is active (restored from storage)", t)

    async def async_startup(self):
        """Startup actions."""
        # No more active cycle loop to start, it's now handled passively in control_heating
        pass

    def remove(self):
        """Cleanup on removal."""
        t = self._thermostat
        if self._auto_tpi_manager:
            t.hass.async_create_task(self._auto_tpi_manager.async_save_data())

    def _is_central_boiler_off(self) -> bool:
        """Check if the central boiler is configured but currently off."""
        t = self._thermostat
        if not t.is_used_by_central_boiler:
            return False
        api = VersatileThermostatAPI.get_vtherm_api()
        if api and api.central_boiler_manager:
            return not api.central_boiler_manager.is_on
        return False

    async def _get_tpi_data(self) -> dict[str, Any]:
        """Calculate and return TPI cycle parameters."""
        t = self._thermostat
        
        # Feed current temperatures to AutoTpiManager BEFORE getting params
        if self._auto_tpi_manager:
            await self._auto_tpi_manager.update(
                room_temp=t.current_temperature,
                ext_temp=t.current_outdoor_temperature,
                target_temp=t.target_temperature,
                hvac_mode=str(t.vtherm_hvac_mode),
                is_overpowering_detected=t.power_manager.is_overpowering_detected,
                is_central_boiler_off=self._is_central_boiler_off(),
                is_heating_failure=t.heating_failure_detection_manager.is_failure_detected,
            )

        # Sync coefficients from AutoTpiManager before calculating
        if self._auto_tpi_manager and self._auto_tpi_manager.learning_active:
            new_params = await self._auto_tpi_manager.calculate()
            if new_params:
                new_coef_int = new_params.get(CONF_TPI_COEF_INT)
                new_coef_ext = new_params.get(CONF_TPI_COEF_EXT)
                if new_coef_int != t.prop_algorithm.tpi_coef_int or \
                   new_coef_ext != t.prop_algorithm.tpi_coef_ext:
                    t.prop_algorithm.update_parameters(tpi_coef_int=new_coef_int, tpi_coef_ext=new_coef_ext)
                    _LOGGER.debug("%s - Synced TPI coeffs before cycle: int=%.3f, ext=%.3f",
                                  t, new_coef_int, new_coef_ext)

        # Force recalculation with potentially updated coefficients
        t.recalculate()

        # Calculate time (in seconds)
        if t.prop_algorithm:
            # temporary ignore the forced_by_timing prop
            # todo: implement handle of forced_by_timing to auto_tpi loop
            on_time_sec, off_time_sec, forced_by_timing = calculate_cycle_times(
                t.on_percent,
                t.cycle_min,
                t.minimal_activation_delay,
                t.minimal_deactivation_delay,
            )

            # if forced_by_timing, update the realized power
            if forced_by_timing:
                realized_percent = on_time_sec / (t.cycle_min * 60)
                if t.prop_algorithm and hasattr(t.prop_algorithm, "update_realized_power"):
                    t.prop_algorithm.update_realized_power(realized_percent)
        else:
            on_time_sec = 0
            off_time_sec = 0

        return {
            "on_time_sec": on_time_sec,
            "off_time_sec": off_time_sec,
            "on_percent": t.safe_on_percent,
            "hvac_mode": str(t.vtherm_hvac_mode),
        }

    async def control_heating(self, force=False):
        """TPI-specific control heating logic."""
        t = self._thermostat

        # Feed the Auto TPI manager
        if self._auto_tpi_manager:
            # 1. Update manager's transient state
            await self._auto_tpi_manager.update(
                room_temp=t.current_temperature,
                ext_temp=t.current_outdoor_temperature,
                target_temp=t.target_temperature,
                hvac_mode=str(t.vtherm_hvac_mode),
                is_overpowering_detected=t.power_manager.is_overpowering_detected,
                is_central_boiler_off=self._is_central_boiler_off(),
                is_heating_failure=t.heating_failure_detection_manager.is_failure_detected,
            )

            # 2. Drive the cycle processing passively
            if self._auto_tpi_manager.learning_active:
                await self._auto_tpi_manager.process_cycle(
                    # Use provided timestamp or current time if missing
                    timestamp=dt_util.now(),
                    data_provider=self._get_tpi_data,
                    event_sender=t._on_prop_cycle_start,
                    force=force
                )

            # 3. Synchronize parameters if learning is active
            new_params = await self._auto_tpi_manager.calculate()
            if self._auto_tpi_manager.learning_active and new_params:
                new_coef_int = new_params.get(CONF_TPI_COEF_INT)
                new_coef_ext = new_params.get(CONF_TPI_COEF_EXT)
                if new_coef_int is not None and new_coef_ext is not None:
                    if t.prop_algorithm:
                        # Update effective algo parameters
                        t.prop_algorithm.update_parameters(tpi_coef_int=new_coef_int, tpi_coef_ext=new_coef_ext)
                        # Keep thermostat attributes in sync
                        t.tpi_coef_int = new_coef_int
                        t.tpi_coef_ext = new_coef_ext
                        _LOGGER.debug("%s - Synced PropAlgorithm with current Auto TPI coeffs: int=%.3f, ext=%.3f",
                                      t, new_coef_int, new_coef_ext)

        # Stop here if we are off
        if t.vtherm_hvac_mode == VThermHvacMode_OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF)", t)
            if t.is_device_active:
                await t.async_underlying_entity_turn_off()
        else:
            on_time_sec = 0
            off_time_sec = 0
            on_percent = 0
            if t.prop_algorithm:
                on_percent = t.on_percent
                on_time_sec, off_time_sec, forced_by_timing = calculate_cycle_times(
                    on_percent,
                    t.cycle_min,
                    t.minimal_activation_delay,
                    t.minimal_deactivation_delay,
                )
                if forced_by_timing:
                    realized_percent = on_time_sec / (t.cycle_min * 60)
                    if t.prop_algorithm and hasattr(t.prop_algorithm, "update_realized_power"):
                        t.prop_algorithm.update_realized_power(realized_percent)

            for under in t.underlyings:
                await under.start_cycle(
                    t.vtherm_hvac_mode,
                    on_time_sec,
                    off_time_sec,
                    on_percent,
                    force,
                )

    async def on_state_changed(self):
        """Handle state changes."""
        # Cycle management is now passive, no need to start/stop loop
        pass

    def update_attributes(self):
        """Add TPI-specific attributes to thermostat."""
        t = self._thermostat
        t._attr_extra_state_attributes["specific_states"].update({
            "auto_tpi_state": "on" if self._auto_tpi_manager and self._auto_tpi_manager.learning_active else "off",
            "auto_tpi_learning": (
                self._auto_tpi_manager.get_filtered_state()
                if self._auto_tpi_manager and self._auto_tpi_manager.learning_active
                else {}
            ),
        })

        t._attr_extra_state_attributes["configuration"].update({
            "minimal_activation_delay_sec": t.minimal_activation_delay,
            "minimal_deactivation_delay_sec": t.minimal_deactivation_delay,
        })



    async def _async_update_tpi_config_entry(self):
        """Update the config entry with current TPI parameters."""
        t = self._thermostat
        entry = t.hass.config_entries.async_get_entry(t.unique_id)
        if entry:
            new_data = entry.data.copy()
            new_data[CONF_TPI_COEF_INT] = t.tpi_coef_int
            new_data[CONF_TPI_COEF_EXT] = t.tpi_coef_ext
            new_data[CONF_TPI_THRESHOLD_LOW] = t.tpi_threshold_low
            new_data[CONF_TPI_THRESHOLD_HIGH] = t.tpi_threshold_high
            new_data[CONF_MINIMAL_ACTIVATION_DELAY] = t.minimal_activation_delay
            new_data[CONF_MINIMAL_DEACTIVATION_DELAY] = t.minimal_deactivation_delay

            result = t.hass.config_entries.async_update_entry(entry, data=new_data)
            _LOGGER.debug("%s - Config entry updated with new TPI params: %s", t, result)

    async def service_set_tpi_parameters(
        self,
        tpi_coef_int: float | None = None,
        tpi_coef_ext: float | None = None,
        minimal_activation_delay: int | None = None,
        minimal_deactivation_delay: int | None = None,
        tpi_threshold_low: float | None = None,
        tpi_threshold_high: float | None = None,
    ):
        """Service handler for set_tpi_parameters."""
        t = self._thermostat

        if t.lock_manager.check_is_locked("service_set_tpi_parameters"):
            return

        write_event_log(
            _LOGGER,
            t,
            f"Calling SERVICE_SET_TPI_PARAMETERS, tpi_coef_int: {tpi_coef_int}, "
            f"tpi_coef_ext: {tpi_coef_ext}"
            f"minimal_activation_delay: {minimal_activation_delay}, "
            f"minimal_deactivation_delay: {minimal_deactivation_delay}, "
            f"tpi_threshold_low: {tpi_threshold_low}, "
            f"tpi_threshold_high: {tpi_threshold_high}",
        )

        if t.prop_algorithm is None:
            raise ServiceValidationError(f"{t} - No TPI algorithm configured for this thermostat.")

        entry = t.hass.config_entries.async_get_entry(t.unique_id)
        if not entry:
            raise ServiceValidationError(f"{t} - No config entry has been found for this thermostat.")

        if entry.data.get(CONF_USE_TPI_CENTRAL_CONFIG, False):
            raise ServiceValidationError(f"{t} - Impossible to set TPI parameters when using central TPI configuration.")

        # Update the algorithm with coefficients and thresholds
        t.prop_algorithm.update_parameters(
            tpi_coef_int,
            tpi_coef_ext,
            tpi_threshold_low,
            tpi_threshold_high,
        )

        # Update thermostat attributes directly (handler updates them via setters)
        t.tpi_coef_int = t.prop_algorithm.tpi_coef_int
        t.tpi_coef_ext = t.prop_algorithm.tpi_coef_ext
        t.tpi_threshold_low = t.prop_algorithm.tpi_threshold_low
        t.tpi_threshold_high = t.prop_algorithm.tpi_threshold_high

        # Update delays directly on thermostat (not in algo anymore)
        if minimal_activation_delay is not None:
            t.minimal_activation_delay = minimal_activation_delay
        if minimal_deactivation_delay is not None:
            t.minimal_deactivation_delay = minimal_deactivation_delay

        await self._async_update_tpi_config_entry()

        if t.is_removed:
            _LOGGER.debug("%s - Entity is removed, stop service_set_tpi_parameters", t)
            return

        t.recalculate()
        await t.async_control_heating(force=True)

    async def service_set_auto_tpi_mode(
        self,
        auto_tpi_mode: bool,
        reinitialise: bool = True,
        allow_kint_boost_on_stagnation: bool = False,
        allow_kext_compensation_on_overshoot: bool = False,
    ):
        """Service handler for set_auto_tpi_mode."""
        t = self._thermostat

        if t.proportional_function != PROPORTIONAL_FUNCTION_TPI:
            raise ServiceValidationError(f"{t} - This service is only available for TPI algorithm.")
        if not t.entry_infos.get(CONF_AUTO_TPI_MODE, False):
            raise ServiceValidationError(f"{t} - Auto TPI is not enabled in configuration.")

        write_event_log(
            _LOGGER,
            t,
            f"Calling SERVICE_SET_AUTO_TPI_MODE, auto_tpi_mode: {auto_tpi_mode}, "
            f"reinitialise: {reinitialise}, "
            f"allow_kint_boost: {allow_kint_boost_on_stagnation}, "
            f"allow_kext_overshoot: {allow_kext_compensation_on_overshoot}",
        )
        await self.async_set_auto_tpi_mode(
            auto_tpi_mode,
            reinitialise,
            allow_kint_boost_on_stagnation,
            allow_kext_compensation_on_overshoot,
        )

    async def service_auto_tpi_calibrate_capacity(
        self,
        save_to_config: bool,
        min_power_threshold: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        """Service handler for auto_tpi_calibrate_capacity."""
        t = self._thermostat

        if t.proportional_function != PROPORTIONAL_FUNCTION_TPI:
            raise ServiceValidationError(f"{t} - This service is only available for TPI algorithm.")
        if not t.entry_infos.get(CONF_AUTO_TPI_MODE, False):
            raise ServiceValidationError(f"{t} - Auto TPI is not enabled in configuration.")

        write_event_log(_LOGGER, t, f"Calling SERVICE_AUTO_TPI_CALIBRATE_CAPACITY, save_to_config: {save_to_config}, start_date: {start_date}, end_date: {end_date}, min_power_threshold: {min_power_threshold}")

        if not self._auto_tpi_manager:
            raise ServiceValidationError(f"{t} - Auto TPI Manager not initialized, cannot calibrate capacity.")

        result = await self._auto_tpi_manager.service_calibrate_capacity(
            thermostat_entity_id=t.entity_id,
            ext_temp_entity_id=t.ext_temp_sensor_entity_id,
            save_to_config=save_to_config,
            start_date=start_date,
            end_date=end_date,
            min_power_threshold=min_power_threshold / 100.0,
        )

        if result and result.get("success") and result.get("max_capacity"):
            t.recalculate()

        t.update_custom_attributes()
        t.async_write_ha_state()

        return result

    async def async_set_auto_tpi_mode(
        self,
        auto_tpi_mode: bool,
        reinitialise: bool = True,
        allow_kint_boost: bool = False,
        allow_kext_overshoot: bool = False,
    ):
        """Set the auto TPI mode."""
        t = self._thermostat
        
        _LOGGER.debug(
            "%s - async_set_auto_tpi_mode called with auto_tpi_mode=%s, reinitialise=%s, kint_boost=%s, kext_overshoot=%s",
            t,
            auto_tpi_mode,
            reinitialise,
            allow_kint_boost,
            allow_kext_overshoot,
        )
        if not self._auto_tpi_manager:
            _LOGGER.warning("%s - Auto TPI Manager not initialized", t)
            return

        # Safety check: Prevent enabling learning if the feature is disabled in config
        if auto_tpi_mode and not t.entry_infos.get(CONF_AUTO_TPI_MODE, False):
            _LOGGER.warning("%s - Cannot start Auto TPI Learning: feature is disabled in configuration", t)
            await self._auto_tpi_manager.stop_learning()
            return

        if auto_tpi_mode:
            # Use the original configured default values
            await self._auto_tpi_manager.start_learning(
                coef_int=self._auto_tpi_manager._default_coef_int,
                coef_ext=self._auto_tpi_manager._default_coef_ext,
                reset_data=reinitialise,
                allow_kint_boost=allow_kint_boost,
                allow_kext_overshoot=allow_kext_overshoot,
            )

            # Sync PropAlgorithm with the configured coefficients
            if t.prop_algorithm:
                t.prop_algorithm.update_parameters(tpi_coef_int=t.tpi_coef_int, tpi_coef_ext=t.tpi_coef_ext)
                _LOGGER.info("%s - PropAlgorithm synced with config: Kint=%.3f, Kext=%.3f",
                             t, t.tpi_coef_int, t.tpi_coef_ext)

            # If we enable auto_tpi, we must disable central config for TPI
            # Note: _entry_infos is a dict, we can update it directly
            if t._entry_infos:
                t._entry_infos[CONF_USE_TPI_CENTRAL_CONFIG] = False

            # Persist the change to the config entry
            entry = t.hass.config_entries.async_get_entry(t.unique_id)
            if entry and entry.data.get(CONF_USE_TPI_CENTRAL_CONFIG, True):
                new_data = entry.data.copy()
                new_data[CONF_USE_TPI_CENTRAL_CONFIG] = False
                t.hass.config_entries.async_update_entry(entry, data=new_data)

            if t.is_removed:
                _LOGGER.debug("%s - Entity is removed, stop async_set_auto_tpi_mode", t)
                return

            # Starting learning is sufficient, cycle processing is passive
            pass
        else:
            await self._auto_tpi_manager.stop_learning()

            # Apply configured coefficients to PropAlgorithm
            if t.prop_algorithm:
                t.prop_algorithm.update_parameters(tpi_coef_int=t.tpi_coef_int, tpi_coef_ext=t.tpi_coef_ext)
                _LOGGER.info(
                    "%s - PropAlgorithm reset to config values: Kint=%.3f, Kext=%.3f",
                    t, t.tpi_coef_int, t.tpi_coef_ext
                )

        # Fire event to notify listeners
        t.hass.bus.async_fire(
            EventType.AUTO_TPI_EVENT.value,
            {
                "entity_id": t.entity_id,
                "auto_tpi_mode": self._auto_tpi_manager.learning_active,
            },
        )

        # Force update of state attributes
        t.update_custom_attributes()
        t.async_write_ha_state()
