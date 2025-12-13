"""Auto TPI Manager implementing TPI algorithm."""

import logging
import json
import os
import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, asdict, field

import asyncio
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store

from .const import (
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_AUTO_TPI_HEATING_POWER,
    CONF_AUTO_TPI_COOLING_POWER,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 8
STORAGE_KEY_PREFIX = "versatile_thermostat.auto_tpi"


@dataclass
class AutoTpiState:
    """Persistent state for Auto TPI algorithm."""
    # Learning coefficients (heat)
    coeff_indoor_heat: float = 0.1
    coeff_outdoor_heat: float = 0.01
    coeff_indoor_autolearn: int = 1  # Counter
    coeff_outdoor_autolearn: int = 0

    # Learning coefficients for Cool
    coeff_indoor_cool: float = 0.1
    coeff_outdoor_cool: float = 0.01
    coeff_indoor_cool_autolearn: int = 1
    coeff_outdoor_cool_autolearn: int = 0

    # Max Capacity (physical power of the system)
    max_capacity_heat: float = 0.0
    max_capacity_cool: float = 0.0

    # Offsets.
    offset: float = 0.0
    
    # Previous cycle state (Snapshot for learning)
    last_power: float = 0.0
    last_order: float = 0.0
    last_temp_in: float = 0.0
    last_temp_out: float = 0.0
    last_state: str = 'stop'  # 'heat', 'cool', 'stop'
    previous_state: str = 'stop' # State of the previous cycle
    last_on_temp_in: float = 0.0 # Temp at the end of ON time
    last_update_date: Optional[datetime] = None
    last_heater_stop_time: Optional[datetime] = None # When heater stopped
    
    # Cycle management
    cycle_start_date: Optional[datetime] = None  # Start of current cycle
    cycle_active: bool = False
    current_cycle_cold_factor: float = 0.0 # 1.0 = cold, 0.0 = hot
    
    # Management
    consecutive_failures: int = 0
    autolearn_enabled: bool = False
    last_learning_status: str = "startup"
    total_cycles: int = 0  # Total number of TPI cycles
    consecutive_boosts: int = 0  # Track consecutive boost attempts
    recent_errors: list = field(default_factory=list) # Store last N errors for regime change detection
    regime_change_detected: bool = False # Flag for temporary alpha boost
    learning_start_date: Optional[datetime] = None # Date when learning started

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        d = data.copy()
        # Date conversion from ISO format
        for date_field in ["last_update_date", "cycle_start_date", "last_heater_stop_time", "learning_start_date"]:
            if d.get(date_field):
                try:
                    d[date_field] = datetime.fromisoformat(d[date_field])
                except (ValueError, TypeError):
                    d[date_field] = None
        
        # Create instance with defaults first
        instance = cls()
        
        # Filter unknown fields and update only valid ones
        valid_fields = {k for k in cls.__annotations__}
        for key, value in d.items():
            if key in valid_fields:
                setattr(instance, key, value)
        
        return instance


class AutoTpiManager:
    """Auto TPI Manager implementing TPI algorithm."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, unique_id: str, name: str, cycle_min: int,
                 tpi_threshold_low: float = 0.0, tpi_threshold_high: float = 0.0,
                 minimal_deactivation_delay: int = 0,
                 coef_int: float = 0.6, coef_ext: float = 0.04,
                 heater_heating_time: int = 0, heater_cooling_time: int = 0,
                 calculation_method: str = "ema", ema_alpha: float = 0.2,
                 avg_initial_weight: int = 1, max_coef_int: float = 0.6,
                 heating_rate: float = 1.0, cooling_rate: float = 1.0,
                 ema_decay_rate: float = 0.1,
                 continuous_learning: bool = False,
                 keep_ext_learning: bool = False,
                 enable_update_config: bool = False,
                 enable_notification: bool = False):
        self._hass = hass
        self._config_entry = config_entry
        self._enable_update_config = enable_update_config
        self._enable_notification = enable_notification
        self._unique_id = unique_id
        self._name = name
        self._cycle_min = cycle_min
        self._tpi_threshold_low = tpi_threshold_low
        self._tpi_threshold_high = tpi_threshold_high
        self._minimal_deactivation_delay_sec = minimal_deactivation_delay
        self._heater_heating_time = heater_heating_time
        self._heater_cooling_time = heater_cooling_time

        self._calculation_method = calculation_method
        self._ema_alpha = ema_alpha
        self._avg_initial_weight = avg_initial_weight
        self._max_coef_int = max_coef_int
        self._heating_rate = heating_rate
        self._cooling_rate = cooling_rate
        self._ema_decay_rate = ema_decay_rate
        self._continuous_learning = continuous_learning
        self._keep_ext_learning = keep_ext_learning
        
        # Notification management
        self._last_notified_coef_int: Optional[float] = None
        self._last_notified_coef_ext: Optional[float] = None
        
        storage_key = f"{STORAGE_KEY_PREFIX}.{unique_id.replace('.', '_')}"
        self._store = Store(hass, STORAGE_VERSION, storage_key)
        self._default_coef_int = coef_int if coef_int is not None else 0.6
        self._default_coef_ext = coef_ext if coef_ext is not None else 0.04

        self.state = AutoTpiState(
            coeff_indoor_heat=self._default_coef_int,
            coeff_outdoor_heat=self._default_coef_ext,
            coeff_indoor_cool=self._default_coef_int,
            coeff_outdoor_cool=self._default_coef_ext
        )
        self._calculated_params = {}

        # Transient state
        self._current_temp_in: float = 0.0
        self._current_temp_out: float = 0.0
        self._current_target_temp: float = 0.0
        self._current_hvac_mode: str = 'heat' # 'heat' or 'cool' (or 'off' etc)
        self._last_cycle_power_efficiency: float = 1.0
        self._current_cycle_params: dict = None
        self._save_lock = asyncio.Lock()

        self._timer_remove_callback: Callable[[], None] | None = None
        self._timer_capture_remove_callback: Callable[[], None] | None = None
        self._learning_just_completed: bool = False  # Transient flag to suppress 'cycle interrupted' log after learning
        # data_provider: async function that returns a dict with:
        # on_time_sec, off_time_sec, on_percent, hvac_mode
        self._data_provider: Callable[[], dict] | None = None
        # event_sender: async function that sends events to thermostat
        self._event_sender: Callable[[dict], None] | None = None
        
        # Interruption management
        self._current_cycle_interrupted: bool = False

    async def async_update_coefficients_config(self, coef_int: float, coef_ext: float):
        """Update CONF_TPI_COEF_INT and CONF_TPI_COEF_EXT in the HA config entry."""

        if not self._enable_update_config:
            _LOGGER.debug(
                "%s - Auto TPI: Skipping config update for coefficients as enable_update_config is False",
                self._name
            )
            return

        new_data = {
            **self._config_entry.data,
            CONF_TPI_COEF_INT: round(coef_int, 3),
            CONF_TPI_COEF_EXT: round(coef_ext, 3),
        }

        self._hass.config_entries.async_update_entry(
            self._config_entry, data=new_data
        )
        _LOGGER.info(
            "%s - Auto TPI: Updated config coefficients: Kint=%.3f, Kext=%.3f",
            self._name, coef_int, coef_ext
        )

    async def async_update_capacity_config(self, capacity: float, is_heat_mode: bool):
        """Update capacity parameters in the HA config entry."""

        if capacity <= 0.0:
            _LOGGER.warning(
                "%s - Auto TPI: Skipping capacity config update, capacity is not positive (%.3f)",
                self._name, capacity
            )
            return

        rate_key = (
            CONF_AUTO_TPI_HEATING_POWER
            if is_heat_mode
            else CONF_AUTO_TPI_COOLING_POWER
        )

        new_data = {
            **self._config_entry.data,
            rate_key: round(capacity, 3),
        }

        self._hass.config_entries.async_update_entry(
            self._config_entry, data=new_data
        )

        # Also update the local state for immediate use in future cycles
        if is_heat_mode:
            self.state.max_capacity_heat = capacity
            self._heating_rate = capacity
        else:
            self.state.max_capacity_cool = capacity
            self._cooling_rate = capacity

        await self.async_save_data()

        _LOGGER.info(
            "%s - Auto TPI: Updated config capacity for %s mode: Capacity=%.3f",
            self._name, "heat" if is_heat_mode else "cool", capacity
        )

    async def process_learning_completion(self, current_params: dict) -> Optional[dict]:
        """
        Processes the learned coefficients after a cycle to:
        1. Check if learning is finished/stabilized.
        2. Apply continuous learning if enabled.
        3. Persist coefficients to HA config if enabled.
        4. Send persistent notifications if enabled.

        Returns a dict of finalized coefficients if persisted, or None.
        """

        is_cool_mode = self._current_hvac_mode == 'cool'

        if is_cool_mode:
            k_int = current_params.get("coeff_indoor_cool", self._default_coef_int)
            k_ext = current_params.get("coeff_outdoor_cool", self._default_coef_ext)
            int_cycles_count = self.state.coeff_indoor_cool_autolearn
            ext_cycles_count = self.state.coeff_outdoor_cool_autolearn
        else:
            k_int = current_params.get("coeff_indoor_heat", self._default_coef_int)
            k_ext = current_params.get("coeff_outdoor_heat", self._default_coef_ext)
            int_cycles_count = self.state.coeff_indoor_autolearn
            ext_cycles_count = self.state.coeff_outdoor_autolearn

        # 1. Check if learning is finished/stabilized (for non-continuous learning)
        # We check if the *raw* counter has reached the threshold, which accounts for _avg_initial_weight.
        INT_CYCLES_THRESHOLD = 50 + self._avg_initial_weight
        EXT_CYCLES_THRESHOLD = 50
        
        is_int_finished = (int_cycles_count >= INT_CYCLES_THRESHOLD)
        is_kext_standard_finished = (ext_cycles_count >= EXT_CYCLES_THRESHOLD)
        
        is_ext_finished = (
            is_kext_standard_finished and
            (not self._keep_ext_learning or is_int_finished)
        )

        
        if self._continuous_learning:
            # For continuous learning, we persist if the base threshold is met (stabilized).
            if is_int_finished:
                _LOGGER.debug("%s - Auto TPI: Continuous learning stabilized (Kint > %d cycles). Persisting values.", self._name, INT_CYCLES_THRESHOLD - self._avg_initial_weight)
            else:
                _LOGGER.debug("%s - Auto TPI: Continuous learning in progress (Kint cycles: %d). Skipping persistence.", self._name, int_cycles_count - self._avg_initial_weight)
                return None
        else:
            # Standard learning: stop if both finished.
            if not (is_int_finished and is_ext_finished):
                _LOGGER.debug(
                    "%s - Auto TPI: Learning in progress (Kint cycles: %d/%d, Kext cycles: %d/%d). Skipping persistence.",
                    self._name, int_cycles_count - self._avg_initial_weight, INT_CYCLES_THRESHOLD - self._avg_initial_weight, ext_cycles_count, EXT_CYCLES_THRESHOLD
                )
                return None
            else:
                _LOGGER.info("%s - Auto TPI: Learning completed. Persisting final coefficients.", self._name)


        # 3. Persist coefficients to HA config if enabled
        await self.async_update_coefficients_config(k_int, k_ext)

        # 4. Send persistent notifications if enabled
        if self._enable_notification:
            # Implement "notify once" logic
            # Check for a significant change (> 0.005) or if it's the first time
            if (self._last_notified_coef_int is None or abs(self._last_notified_coef_int - k_int) > 0.005) or \
               (self._last_notified_coef_ext is None or abs(self._last_notified_coef_ext - k_ext) > 0.005):

                # Get translated message. Since I cannot read translations, I will use a simple English message.
                title = f"Versatile Thermostat: Auto TPI Learned Coefficients for {self._name}"
                message = f"Auto TPI has learned new coefficients: Indoor={round(k_int, 3)}, Outdoor={round(k_ext, 3)} (Cycles: Int={int_cycles_count - self._avg_initial_weight}, Ext={ext_cycles_count}). These values have been saved to the configuration."

                try:
                    await self._hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": title,
                            "message": message,
                            "notification_id": f"autotpi_learning_completed_{self._unique_id}",
                        },
                        blocking=False,
                    )
                    self._last_notified_coef_int = k_int
                    self._last_notified_coef_ext = k_ext
                    _LOGGER.info(
                        "%s - Auto TPI: Persistent notification sent for final coefficients.",
                        self._name
                    )
                except Exception as e:
                    _LOGGER.error(
                        "%s - Auto TPI: Error sending persistent notification: %s",
                        self._name, e
                    )

        return {CONF_TPI_COEF_INT: k_int, CONF_TPI_COEF_EXT: k_ext}

    async def async_save_data(self):
        """Save data."""
        await self._store.async_save(self.state.to_dict())

    async def async_load_data(self):
        """Load data."""
        data = await self._store.async_load()

        if not data:
            # Try to migrate from old JSON file
            old_storage_key = f"versatile_thermostat_{self._unique_id}_auto_tpi_v2.json"
            old_path = self._hass.config.path(f".storage/{old_storage_key}")
            if os.path.exists(old_path):
                _LOGGER.debug("%s - Auto TPI: Migrating from old storage %s", self._name, old_path)
                try:
                    with open(old_path, "r") as f:
                        old_json = json.load(f)
                    # Extract state from old format
                    data = old_json.get("state", old_json)
                    await self._store.async_save(data)  # Save to new format
                    os.remove(old_path)  # Clean up old file
                except Exception as e:
                     _LOGGER.error("%s - Auto TPI: Migration error: %s", self._name, e)

        if data:
            self.state = AutoTpiState.from_dict(data)
            
            # Clamping: Apply new max_coef_int to loaded coefficients immediately,
            # in case the user lowered the limit via config flow.
            self.state.coeff_indoor_heat = min(self.state.coeff_indoor_heat, self._max_coef_int)
            self.state.coeff_indoor_cool = min(self.state.coeff_indoor_cool, self._max_coef_int)
            
            # Capacity update logic on load (to fix startup issue after config change)
            # We prioritize the capacity from the latest config flow over the persisted state
            # if they are different and the config value is valid. This handles both an initial
            # state with 0 capacity and a configuration change on restart.
            
            is_capacity_heat_outdated = (self.state.max_capacity_heat != self._heating_rate)
            is_capacity_cool_outdated = (self.state.max_capacity_cool != self._cooling_rate)
            
            if is_capacity_heat_outdated and self._heating_rate > 0.0:
                 _LOGGER.info("%s - Auto TPI: Overwriting persisted max_capacity_heat (%.3f) with new configured value (%.3f) on load.",
                             self._name, self.state.max_capacity_heat, self._heating_rate)
                 self.state.max_capacity_heat = self._heating_rate
                 
            if is_capacity_cool_outdated and self._cooling_rate > 0.0:
                 _LOGGER.info("%s - Auto TPI: Overwriting persisted max_capacity_cool (%.3f) with new configured value (%.3f) on load.",
                             self._name, self.state.max_capacity_cool, self._cooling_rate)
                 self.state.max_capacity_cool = self._cooling_rate
                 
            if is_capacity_heat_outdated or is_capacity_cool_outdated:
                 await self.async_save_data() # Save the new correct config value

            # If no learning has been done yet, force the configured defaults
            if self.state.total_cycles == 0:
                 _LOGGER.info("%s - Auto TPI: No learning cycles yet. Enforcing configured coefficients.", self._name)
                 self.state.coeff_indoor_heat = self._default_coef_int
                 self.state.coeff_outdoor_heat = self._default_coef_ext
                 self.state.coeff_indoor_cool = self._default_coef_int
                 self.state.coeff_outdoor_cool = self._default_coef_ext
                 # Initialize counters with the configured weight
                 self.state.coeff_indoor_autolearn = self._avg_initial_weight
                 self.state.coeff_indoor_cool_autolearn = self._avg_initial_weight
                 self.state.coeff_outdoor_autolearn = 0
                 self.state.coeff_outdoor_cool_autolearn = 0

            _LOGGER.info("%s - Auto TPI: State loaded. Cycles: %d, Indoor learn count: %d",
                        self._name, self.state.total_cycles, self.state.coeff_indoor_autolearn)
        else:
            self.state = AutoTpiState(
                coeff_indoor_heat=self._default_coef_int,
                coeff_outdoor_heat=self._default_coef_ext,
                coeff_indoor_cool=self._default_coef_int,
                coeff_outdoor_cool=self._default_coef_ext
            )

        await self.calculate()

    async def update(self, room_temp: float, ext_temp: float,
                    hvac_mode: str, target_temp: float,
                    is_overpowering_detected: bool = False) -> float:
        """Update state with new data.

        This method is called at each control_heating cycle.
        It updates the transient state used for power calculation and future learning.

        Returns the calculated power for validation/indication.
        """

        # Check for Overpowering Interruption
        # If overpowering is detected, the heating/cooling is artificially stopped/limited.
        # We must mark this cycle as interrupted so we don't learn from it (false data).
        if is_overpowering_detected:
            if not self._current_cycle_interrupted:
                _LOGGER.info("%s - Auto TPI: Cycle interrupted by Overpowering/Power Shedding. Learning will be skipped for this cycle.", self._name)
                self._current_cycle_interrupted = True

        # Store current values for later use in cycle callbacks
        self._current_temp_in = room_temp if room_temp is not None else 0.0
        self._current_temp_out = ext_temp if ext_temp is not None else 0.0
        self._current_target_temp = target_temp if target_temp is not None else 0.0
        self._current_hvac_mode = hvac_mode
        
        # Calculate and return power
        # Use hvac_mode to force direction
        calc_state_str = 'stop'
        if hvac_mode == 'cool':
            calc_state_str = 'cool'
        elif hvac_mode == 'heat':
            calc_state_str = 'heat'

        return self.calculate_power(target_temp, room_temp, ext_temp, calc_state_str)

    async def calculate(self) -> Optional[dict]:
        """Return the current calculated TPI parameters."""
        # Return current coefficients for the thermostat to use
        params = {}
        
        # Use hvac_mode to determine which coefficients to return
        # This prevents flapping when switching between heating/cooling actions while in the same mode (e.g. idle)
        # Note: hvac_mode usually comes from VThermHvacMode (heat, cool, off, auto...)
        
        is_cool_mode = self._current_hvac_mode == 'cool'
        
        if is_cool_mode:
            params[CONF_TPI_COEF_INT] = self.state.coeff_indoor_cool
            params[CONF_TPI_COEF_EXT] = self.state.coeff_outdoor_cool
        else:
            params[CONF_TPI_COEF_INT] = self.state.coeff_indoor_heat
            params[CONF_TPI_COEF_EXT] = self.state.coeff_outdoor_heat
            
        self._calculated_params = params
        return params

    def _get_adaptive_alpha(self, cycle_count: int) -> float:
        """Calculate adaptive alpha for EMA, with temporary boost on regime change."""
        
        # Standard calculation
        base_alpha = self._ema_alpha / (1 + self._ema_decay_rate * cycle_count)
        
        # If continuous learning is enabled and regime change detected, temporary boost
        if self._continuous_learning and self.state.regime_change_detected:
            # Max boost alpha is min(base_alpha * 3.0, 0.15)
            # We want to ensure the base alpha is not too small before boosting.
            # If base_alpha is very small (after many cycles), boost will still be limited.
            boost_alpha = min(base_alpha * 3.0, 0.15)
            
            _LOGGER.info(f"%s - Auto TPI: Regime change detected, boosting alpha: {base_alpha:.3f} -> {boost_alpha:.3f}", self._name)
            
            # The flag will be reset in _learn_indoor after consumption
            return boost_alpha
        
        return base_alpha

    def _detect_regime_change(self, recent_errors: list) -> bool:
        """
        Detects a thermal regime change (systematic bias).
        If detected, we can temporarily increase alpha for faster adaptation.
        """
        N = 10
        if not self._continuous_learning or len(recent_errors) < N:
            return False
        
        # We only look at the last N errors
        errors_to_check = recent_errors[-N:]
        
        # Simple statistical test:
        # Do the last N errors have a systematic bias?
        # mean_error is the average 'correction needed' in °C
        mean_error = sum(errors_to_check) / N
        
        # Calculate standard deviation
        # Avoid zero division
        std_error = (sum((e - mean_error)**2 for e in errors_to_check) / N)**0.5
        if std_error == 0:
            return False
            
        # Student's t-test: significant systematic error?
        t_stat = abs(mean_error) / (std_error / math.sqrt(N))
        
        # 95% confidence threshold (t > 2.0 for n=10)
        return t_stat > 2.0

    def _should_learn(self) -> bool:
        """Check if learning should be performed."""
        if not self.state.autolearn_enabled:
            return False

        # Power conditions: 0 < last_power < saturation_threshold
        # If power is >= saturation_threshold, the cycle is saturated and we skip learning.
        saturation_threshold = self.saturation_threshold
        if not (0 < self.state.last_power < saturation_threshold):
            _LOGGER.debug("%s - Auto TPI: Not learning - Power out of range (%.3f not in 0 < power < %.3f)",
                         self._name, self.state.last_power, saturation_threshold)
            return False

        if self._current_cycle_interrupted:
             _LOGGER.debug("%s - Auto TPI: Not learning - Cycle was interrupted (e.g. Power Shedding)", self._name)
             return False

        # Failures check
        if self.state.consecutive_failures >= 3:
            return False
        
        # 1. First Cycle Exclusion
        if self.state.previous_state == 'stop':
            _LOGGER.debug("%s - Auto TPI: Not learning - First cycle (previous state was stop)", self._name)
            return False
        if self.state.last_order == 0:
            _LOGGER.debug("%s - Auto TPI: Not learning - Last order is 0", self._name)
            return False
            
        # 2. Mild Weather Exclusion (Safe Ratio)
        # Avoid division by small numbers or learning when delta is too small to be significant
        delta_out = self.state.last_order - self._current_temp_out
        if abs(delta_out) < 1.0: 
             _LOGGER.debug("%s - Auto TPI: Not learning - Delta out too small (< 1.0)", self._name)
             return False

        # Natural drift exclusion - check temperature at CYCLE START
        # If temp was already past setpoint at cycle START, this is passive drift, not active regulation
        # is_heat = self.state.last_state == 'heat'
        # is_cool = self.state.last_state == 'cool'

        # if is_heat and self.state.last_temp_in > self.state.last_order + 0.05:
        #     _LOGGER.debug("%s - Auto TPI: Not learning - Passive cooling at cycle start (T_in %.2f > Target %.2f + 0.05)",
        #                 self._name, self.state.last_temp_in, self.state.last_order)
        #     return False

        # if is_cool and self.state.last_temp_in < self.state.last_order - 0.05:
        #     _LOGGER.debug("%s - Auto TPI: Not learning - Passive heating at cycle start (T_in %.2f < Target %.2f - 0.05)",
        #                 self._name, self.state.last_temp_in, self.state.last_order)
        #     return False

        return True

    def _get_no_learn_reason(self) -> str:
        """Get reason why learning is not happening."""
        if not self.state.autolearn_enabled:
            return "learning_disabled"
        saturation_threshold = self.saturation_threshold  # pylint: disable=no-member
        if not (0 < self.state.last_power < saturation_threshold):
            return f"power_out_of_range({self.state.last_power * 100:.1f}% vs Saturation {saturation_threshold * 100:.1f}%)"
        if self.state.consecutive_failures >= 3:
            return f"too_many_failures({self.state.consecutive_failures})"
        
        # Check passive drift conditions
        # is_heat = self.state.last_state == 'heat'
        # is_cool = self.state.last_state == 'cool'
        # if is_heat and self.state.last_temp_in > self.state.last_order:
        #     return f"passive_cooling(T_in={self.state.last_temp_in:.1f}>Target={self.state.last_order:.1f})"
        # if is_cool and self.state.last_temp_in < self.state.last_order:
        #     return f"passive_heating(T_in={self.state.last_temp_in:.1f}<Target={self.state.last_order:.1f})"
                    
        return "unknown"

    async def _perform_learning(self, current_temp_in: float, current_temp_out: float):
        """Execute the learning logic based on previous state and current observations."""
        
        is_heat = self.state.last_state == 'heat'
        is_cool = self.state.last_state == 'cool'
        
        if not (is_heat or is_cool):
            self.state.last_learning_status = "not_heating_or_cooling"
            _LOGGER.debug("%s - Auto TPI: Not learning - system was in %s mode",
                         self._name, self.state.last_state)
            return

        target_temp = self.state.last_order

        # Calculate deltas based on direction
        if is_heat:
            temp_progress = current_temp_in - self.state.last_temp_in
            target_diff = self.state.last_order - self.state.last_temp_in
            outdoor_condition = current_temp_out < self.state.last_order
        else:  # Cool
            temp_progress = self.state.last_temp_in - current_temp_in
            target_diff = self.state.last_temp_in - self.state.last_order
            outdoor_condition = current_temp_out > self.state.last_order
        
        # CASE 1: Indoor Learning
        # ---------------------------
        # Strict conditions to avoid false positives:
        # - Significant temperature progress (> 0.05°C)
        # - Significant gap to cover (> 0.1°C)
        # - Power not saturated (0 < power < 0.99)
        
        if 0 < self.state.last_power < 0.99:
            if temp_progress > 0.05 and target_diff > 0.01:
                # Indoor learning attempt
                error = self._learn_indoor(target_diff, temp_progress, self._last_cycle_power_efficiency, is_cool)
                if error is not None:
                    # Learning was successful
                    self.state.last_learning_status = f"learned_indoor_{'cool' if is_cool else 'heat'}"
                    _LOGGER.info("%s - Auto TPI: Indoor coefficient learned successfully (Error: %.3f)", self._name, error)
                    self._learning_just_completed = True

                    # Continuous Learning: Track error and detect regime change
                    if self._continuous_learning:
                        self.state.recent_errors.append(error)
                        # Keep only the last 20 errors (N=10 for detection + buffer)
                        if len(self.state.recent_errors) > 20:
                            self.state.recent_errors = self.state.recent_errors[-20:]
                            
                        is_regime_change = self._detect_regime_change(self.state.recent_errors)
                        if is_regime_change and not self.state.regime_change_detected:
                            self.state.regime_change_detected = True
                            _LOGGER.warning("%s - Auto TPI: SYSTEMIC REGIME CHANGE DETECTED. Alpha boost activated.", self._name)

                    return  # Indoor success, we exit
                else:
                    # Indoor failed, reason already logged in _learn_indoor
                    _LOGGER.debug("%s - Auto TPI: Indoor learning failed, will try outdoor", self._name)
            else:
                _LOGGER.debug("%s - Auto TPI: Indoor conditions not met (progress=%.3f, target_diff=%.3f)",
                             self._name, temp_progress, target_diff)
        else:
            _LOGGER.debug("%s - Auto TPI: Skipping indoor coeff learning because power is saturated (%.1f%%)",
                          self._name, self.state.last_power * 100)
        
        # CASE 2: Outdoor Learning
        # ----------------------------
        # Executed when:
        # - Indoor was not applicable (conditions not met)
        # - OR indoor failed (_learn_indoor returned False)
        # Conditions:
        # - Relevant outdoor temperature (outdoor_condition)
        # - Significant remaining gap
        
        gap_in = target_temp - current_temp_in
        
        if outdoor_condition and abs(gap_in) > 0.05:
            if self._learn_outdoor(current_temp_in, current_temp_out, is_cool):
                self.state.last_learning_status = f"learned_outdoor_{'cool' if is_cool else 'heat'}"
                _LOGGER.info("%s - Auto TPI: Outdoor coefficient learned successfully", self._name)
                self._learning_just_completed = True
                return  # Outdoor success
            else:
                _LOGGER.debug("%s - Auto TPI: Outdoor learning failed", self._name)
        else:
            _LOGGER.debug("%s - Auto TPI: Outdoor conditions not met (outdoor_condition=%s, gap_in=%.3f)",
                         self._name, outdoor_condition, gap_in)
        
        # No learning was possible
        self.state.last_learning_status = f"no_learning_possible(progress={temp_progress:.2f},target_diff={target_diff:.2f},gap_in={gap_in:.2f})"
        _LOGGER.debug("%s - Auto TPI: No learning possible - %s", self._name, self.state.last_learning_status)

    def _learn_indoor(self, delta_theoretical: float, delta_real: float, efficiency: float = 1.0, is_cool: bool = False) -> Optional[float]:
        """Learn indoor coefficient and return the learning error (expected_rise - actual_rise) if successful."""
        
        real_rise = delta_real
        # We use full cycle delta (passed as delta_real), not ON-time delta.

        if real_rise <= 0.01: # Minimal rise required (0.01 to account for float precision/small sensors)
            _LOGGER.debug("%s - Auto TPI: Cannot learn indoor - real_rise %.3f <= 0.01. Will try outdoor learning.", self._name, real_rise)
            self.state.last_learning_status = "real_rise_too_small"
            return None # Return None on failure

        # Capacity-Based Learning Logic
        # We aim to close the full temperature gap (delta_theoretical),
        # but capped by the physical capacity of the system (state.max_capacity_*)
        
        # 1. Define Reference Capacity (in °C/h)
        ref_capacity_h = self.state.max_capacity_cool if is_cool else self.state.max_capacity_heat

        # Fallback if capacity is 0 (i.e. not calibrated yet)
        if ref_capacity_h <= 0:
            ref_capacity_h = 1.0
            _LOGGER.debug("%s - Auto TPI: Using fallback ref_capacity_h=1.0 (not calibrated yet)", self._name)

        # If no capacity defined, skip learning for this cycle
        if ref_capacity_h <= 0:
            _LOGGER.debug("%s - Auto TPI: Cannot learn indoor - no capacity defined (ref_capacity_h=%.2f)",
                          self._name, ref_capacity_h)
            self.state.last_learning_status = "no_capacity_defined"
            return False

        # 2. Calculate Effective Capacity with thermal losses
        if is_cool:
            k_ext = self.state.coeff_outdoor_cool
            delta_t = self._current_temp_out - self._current_temp_in
        else:
            k_ext = self.state.coeff_outdoor_heat
            delta_t = self._current_temp_in - self._current_temp_out

        loss_factor = k_ext * max(0.0, delta_t)
        loss_factor = min(loss_factor, 0.95)  # Prevent going negative

        effective_capacity_h = ref_capacity_h * (1.0 - loss_factor)
        
        # 3. Calculate Max Achievable Rise in this cycle (°C)
        cycle_duration_h = self._cycle_min / 60.0
        max_achievable_rise = effective_capacity_h * cycle_duration_h * efficiency
        
        _LOGGER.debug("%s - Auto TPI: Capacity calc: ref=%.3f °C/h, loss=%.2f, eff=%.3f °C/h, max_rise=%.3f °C (cycle=%.1f min, eff=%.2f)",
                      self._name, ref_capacity_h, loss_factor, effective_capacity_h, max_achievable_rise, self._cycle_min, efficiency)

        # 4. Calculate adjusted_theoretical: aim for full gap, capped by capacity
        adjusted_theoretical = min(delta_theoretical, max_achievable_rise)
        
        if max_achievable_rise < delta_theoretical:
            mode_str = "cooling" if is_cool else "heating"
            _LOGGER.debug("%s - Auto TPI: Target rise clamped from %.3f to %.3f (Max %s Capacity)",
                          self._name, delta_theoretical, max_achievable_rise, mode_str)

        if adjusted_theoretical <= 0:
             _LOGGER.warning("%s - Auto TPI: Cannot learn indoor - adjusted_theoretical <= 0 (max_rise=%.3f, target_diff=%.3f)",
                             self._name, max_achievable_rise, delta_theoretical)
             self.state.last_learning_status = "adjusted_theoretical_lte_0"
             return False

        ratio = adjusted_theoretical / real_rise
        
        # Check for deboost before calculating new coefficient
        is_heat = not is_cool
        self._check_deboost(is_heat, real_rise, adjusted_theoretical)
        
        current_coeff = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        coeff_new = current_coeff * ratio
        
        # Validate coefficient - reject only truly invalid values (non-finite or <= 0)
        if not math.isfinite(coeff_new) or coeff_new <= 0:
            _LOGGER.warning("%s - Auto TPI: Invalid new indoor coeff: %.3f (non-finite or <= 0), skipping",
                           self._name, coeff_new)
            self.state.last_learning_status = "invalid_indoor_coeff"
            return False
        
        # 4. Cap Coefficient
        MAX_COEFF = self._max_coef_int
        if coeff_new > MAX_COEFF:
            _LOGGER.info("%s - Auto TPI: Calculated indoor coeff %.3f > %.1f, capping to %.1f before averaging",
                        self._name, coeff_new, MAX_COEFF, MAX_COEFF)
            coeff_new = MAX_COEFF
            
        old_coeff = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        count = self.state.coeff_indoor_cool_autolearn if is_cool else self.state.coeff_indoor_autolearn
        
        # 5. Calculation Method
        if self._calculation_method == "average":
            # Weighted average
            # avg_coeff = ((old_coeff * count + coeff_new) / (count + 1))
            # We must use the current count (not incremented) as weight for old_coeff
            
            # If count is 0 (should not happen for valid state), treat as 1
            weight_old = max(count, 1)
            
            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Weighted Average: old=%.3f (weight=%d), new=%.3f, result=%.3f",
                          self._name, old_coeff, weight_old, coeff_new, avg_coeff)

        else: # EMA
            # EMA Smoothing (20% weight by default)
            # new_avg = (old_avg * (1 - alpha)) + (new_sample * alpha)
            alpha = self._get_adaptive_alpha(count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: EMA: old=%.3f, new=%.3f, alpha=%.2f (count=%d), result=%.3f",
                          self._name, old_coeff, coeff_new, alpha, count, avg_coeff)

        # Update counters
        new_count = count + 1
        
        if is_cool:
            self.state.coeff_indoor_cool = avg_coeff
            self.state.coeff_indoor_cool_autolearn = new_count
        else:
            self.state.coeff_indoor_heat = avg_coeff
            self.state.coeff_indoor_autolearn = new_count
        
        _LOGGER.info(
            "%s - Auto TPI: Learn indoor (%s). Old: %.3f, New calculated: %.3f (rise=%.3f), Averaged: %.3f (count: %d)",
            self._name, 'cool' if is_cool else 'heat', old_coeff, coeff_new, real_rise, avg_coeff, new_count
        )
        
        # Reset boost counter after successful learning
        if hasattr(self.state, 'consecutive_boosts'):
            self.state.consecutive_boosts = 0
        
        # Reset regime change flag after consuming the boost
        if self._continuous_learning and self.state.regime_change_detected:
            _LOGGER.debug("%s - Auto TPI: Regime change alpha consumed, resetting flag", self._name)
            self.state.regime_change_detected = False
            
        return adjusted_theoretical - real_rise # Return the error: Expected Rise - Actual Rise

    def _learn_outdoor(self, current_temp_in: float, current_temp_out: float, is_cool: bool = False) -> bool:
        """Learn outdoor coefficient."""
        gap_in = self.state.last_order - current_temp_in
        gap_out = self.state.last_order - current_temp_out
        
        # Validation delta_out (moved here)
        if abs(gap_out) < 0.05:
            _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - gap_out too small (%.3f)",
                        self._name, abs(gap_out))
            self.state.last_learning_status = "gap_out_too_small"
            return False
        
        if gap_out == 0:
            _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - gap_out is 0", self._name)
            self.state.last_learning_status = "gap_out_is_zero"
            return False

        # =============================================================================
        # INTELLIGENT VALIDATION : Overshoot
        # =============================================================================
        # An overshoot indicates that the model OVERESTIMATED the necessary power.
        # This is VALUABLE information to correct Kext.
        #
        # BUT: We must filter external anomalies (open door, sun, etc.)
        # → Overshoot without significant power = anomaly, not model error

        # CASE 1: Check that the setpoint did not change during the cycle
        consigne_changed = abs(self._current_target_temp - self.state.last_order) > 0.1

        if consigne_changed:
            _LOGGER.debug(
                "%s - Auto TPI: Cannot learn outdoor - consigne changed during cycle (%.1f → %.1f)",
                self._name, self.state.last_order, self._current_target_temp
            )
            self.state.last_learning_status = "consigne_changed"
            return False

        # CASE 2: Overshoot without significant power = external anomaly
        # If we have an overshoot but we barely heated/cooled (power < 20%),
        # it is an external anomaly (open door, sun), not a model error
        if is_cool:
            # In cool mode: overcooled if gap_in > 0 (temp < target)
            # Acceptable only if we really cooled (power > 1% instead of 20%)
            # If power is > 1% and we are overcooling, it means Kext is too high and should be reduced.
            if gap_in > 0 and self.state.last_power < 0.01:
                _LOGGER.debug(
                    "%s - Auto TPI: Cannot learn outdoor - Anomalous overcooling (gap_in=%.2f, power=%.1f%%)",
                    self._name, gap_in, self.state.last_power * 100
                )
                self.state.last_learning_status = "anomalous_overcooling"
                return False
        else:
            # In heat mode: overheated if gap_in < 0 (temp > target)
            # Acceptable only if we really heated (power > 1% instead of 20%)
            # If power is > 1% and we are overheating, it means Kext is too high and should be reduced.
            if gap_in < 0 and self.state.last_power < 0.01:
                _LOGGER.debug(
                    "%s - Auto TPI: Cannot learn outdoor - Anomalous overheating (gap_in=%.2f, power=%.1f%%)",
                    self._name, gap_in, self.state.last_power * 100
                )
                self.state.last_learning_status = "anomalous_overheating"
                return False

        # If we get here with an overshoot AND significant power:
        # → It is a real model error, we MUST learn from it
        # → The Kext correction will help correct the underestimated external influence
        _LOGGER.debug(
            "%s - Auto TPI: Overshoot validation passed (gap_in=%.2f, power=%.1f%%) - proceeding with learning",
            self._name, gap_in, self.state.last_power * 100
        )

        # ratio_influence = gap_in / gap_out
        current_indoor = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        current_outdoor = self.state.coeff_outdoor_cool if is_cool else self.state.coeff_outdoor_heat
        
        # Calculate corrective term based on indoor error (Missing power = Gap_In * Kint)
        # Shift this missing power to Outdoor term (Equivalent Kext = Missing Power / Gap_Out)
        # correction = (Gap_In / Gap_Out) * Kint
        # Target = Current_Kext + Correction
        
        correction = current_indoor * (gap_in / gap_out)
        target_outdoor = current_outdoor + correction
        
        # Use target_outdoor as the new sample
        coeff_new = target_outdoor

        # Validate coefficient
        if not math.isfinite(coeff_new) or coeff_new <= 0:
            _LOGGER.warning("%s - Auto TPI: Invalid new outdoor coeff: %.3f (non-finite or <= 0), skipping",
                           self._name, coeff_new)
            self.state.last_learning_status = "invalid_outdoor_coeff"
            return False
        
        # Cap at 1.2 (Slightly relaxed to allow logic to work in extreme cases, but bounded)
        MAX_KEXT = 1.2
        if coeff_new > MAX_KEXT:
            _LOGGER.info("%s - Auto TPI: Calculated outdoor coeff %.3f > %.1f, capping to %.1f before averaging",
                        self._name, coeff_new, MAX_KEXT, MAX_KEXT)
            coeff_new = MAX_KEXT

        count = self.state.coeff_outdoor_cool_autolearn if is_cool else self.state.coeff_outdoor_autolearn
        old_coeff = current_outdoor
        
        # Apply EMA or average
        if self._calculation_method == "average":
            weight_old = max(count, 1)  # Same as _learn_indoor
            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Outdoor Weighted Average: old=%.3f (weight=%d), new=%.3f, result=%.3f",
                          self._name, old_coeff, count, coeff_new, avg_coeff)
        else:  # EMA
            alpha = self._get_adaptive_alpha(count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: Outdoor EMA: old=%.3f, new=%.3f, alpha=%.2f (count=%d), result=%.3f",
                          self._name, old_coeff, coeff_new, alpha, count, avg_coeff)
        
        new_count = count + 1
        
        # We only cap if continuous learning is OFF, and we want to stop learning
        if not self._continuous_learning:
            # The standard threshold is 50 + initial weight
            INT_CYCLES_THRESHOLD = 50 + self._avg_initial_weight
            
            indoor_autolearn_count = self.state.coeff_indoor_cool_autolearn if is_cool else self.state.coeff_indoor_autolearn
            is_indoor_finished = (indoor_autolearn_count >= INT_CYCLES_THRESHOLD)
            
            #  Kext learning stops (capped at 50) ONLY if:
            # (kext_cycles >= 50) AND (not keep_ext_learning OR kint_cycles >= 50 + initial_weight).
            # This ensures Kext always learns a minimum of 50 cycles (Standard minimum).
            
            EXT_CYCLES_THRESHOLD = 50
            is_kext_standard_finished = (count >= EXT_CYCLES_THRESHOLD)
            
            # stop_learning_now is not used here, only for final persistence check
            
            # new_count is NOT capped anymore to reflect the real number of cycles
            pass # No cap
        
        if is_cool:
            self.state.coeff_outdoor_cool = avg_coeff
            self.state.coeff_outdoor_cool_autolearn = new_count
        else:
            self.state.coeff_outdoor_heat = avg_coeff
            self.state.coeff_outdoor_autolearn = new_count
        
        _LOGGER.info(
            "%s - Auto TPI: Learn outdoor (%s). Old: %.3f, Correction: %.3f, Target: %.3f, Averaged: %.3f (count: %d)",
            self._name, 'cool' if is_cool else 'heat', old_coeff, correction, coeff_new, avg_coeff, new_count
        )
        return True

    def _boost_indoor_coeff(self, is_heat: bool):
        """Boost indoor coefficient when system is underpowered."""
        BOOST_FACTOR = 1.15  # increaase by 15%
        MAX_CONSECUTIVE_BOOSTS = 5  # limit consecutive boosts
        
        # Check if we've already boosted too many times
        if not hasattr(self.state, 'consecutive_boosts'):
            self.state.consecutive_boosts = 0
        
        if self.state.consecutive_boosts >= MAX_CONSECUTIVE_BOOSTS:
            _LOGGER.info("%s - Auto TPI: Boost skipped - max consecutive boosts (%d) reached",
                        self._name, MAX_CONSECUTIVE_BOOSTS)
            return
        
        if is_heat:
            old = self.state.coeff_indoor_heat
            self.state.coeff_indoor_heat = min(old * BOOST_FACTOR, self._max_coef_int)
            _LOGGER.info("%s - Boosting Kint heat: %.3f → %.3f (boost #%d)",
                        self._name, old, self.state.coeff_indoor_heat, self.state.consecutive_boosts + 1)
        else:
            old = self.state.coeff_indoor_cool
            self.state.coeff_indoor_cool = min(old * BOOST_FACTOR, self._max_coef_int)
            _LOGGER.info("%s - Boosting Kint cool: %.3f → %.3f (boost #%d)",
                        self._name, old, self.state.coeff_indoor_cool, self.state.consecutive_boosts + 1)
        
        self.state.consecutive_boosts += 1

    def _check_deboost(self, is_heat: bool, real_rise: float, adjusted_theoretical: float):
        """Check if we should reduce indoor coefficient after good performance."""
        # If we achieved more than expected, consider reducing coefficient
        if real_rise > adjusted_theoretical * 1.2:  # 20% overshoot
            DEBOOST_FACTOR = 0.95  # Reduce by 5%
            
            if is_heat:
                old = self.state.coeff_indoor_heat
                # Only deboost if we're above the default
                if old > self._default_coef_int:
                    self.state.coeff_indoor_heat = max(old * DEBOOST_FACTOR, self._default_coef_int)
                    _LOGGER.info("%s - Deboosting Kint heat: %.3f → %.3f",
                                self._name, old, self.state.coeff_indoor_heat)
            else:
                old = self.state.coeff_indoor_cool
                if old > self._default_coef_int:
                    self.state.coeff_indoor_cool = max(old * DEBOOST_FACTOR, self._default_coef_int)
                    _LOGGER.info("%s - Deboosting Kint cool: %.3f → %.3f",
                                self._name, old, self.state.coeff_indoor_cool)
            
            # Reset boost counter
            if hasattr(self.state, 'consecutive_boosts'):
                self.state.consecutive_boosts = 0

    def _detect_failures(self, current_temp_in: float):
        """Detect system failures."""
        OFFSET_FAILURE = 1.0
        MIN_LEARN_FOR_DETECTION = 25
        
        failure_detected = False
        
        if (self.state.last_state == 'heat' and
            current_temp_in < self.state.last_order - OFFSET_FAILURE and
            current_temp_in < self.state.last_temp_in and
            self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION):
            failure_detected = True
            _LOGGER.warning("%s - Auto TPI: Failure detected in HEAT mode", self._name)
            
        elif (self.state.last_state == 'cool' and
              current_temp_in > self.state.last_order + OFFSET_FAILURE and
              current_temp_in > self.state.last_temp_in and
              self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION):
            failure_detected = True
            _LOGGER.warning("%s - Auto TPI: Failure detected in COOL mode", self._name)
            
        if failure_detected:
            self.state.consecutive_failures += 1
            if self.state.consecutive_failures >= 3:
                self.state.autolearn_enabled = False
                self.state.learning_start_date = None
                _LOGGER.error("%s - Auto TPI: Learning disabled due to %d consecutive failures.",
                             self._name, self.state.consecutive_failures)
        else:
            self.state.consecutive_failures = 0


    @property
    def saturation_threshold(self) -> float:
        """The saturation power threshold (default 1.0, 100%)."""
        # This property is expected to be overridden by the mixing/main component.
        # Defaulting to 1.0 for self-contained use if not overridden.
        return 1.0
        
    def calculate_power(self, setpoint: float, temp_in: float, temp_out: float, state_str: str) -> float:
        """Calculate power using TPI formula."""
        if setpoint is None or temp_in is None or temp_out is None:
            return 0.0

        direction = 1 if state_str == 'heat' else -1
        delta_in = setpoint - temp_in
        delta_out = setpoint - temp_out
        
        if state_str == 'cool':
            coeff_int = self.state.coeff_indoor_cool
            coeff_ext = self.state.coeff_outdoor_cool
        else:
            coeff_int = self.state.coeff_indoor_heat
            coeff_ext = self.state.coeff_outdoor_heat
            
        offset = self.state.offset
        # Jeedom has an offset you can dynamically feed to the thermostat.
        # We keep it here for future addition if needed, it's not used yet.
        power = (direction * delta_in * coeff_int) + (direction * delta_out * coeff_ext) + offset
        return max(0.0, min(100.0, power))

    @staticmethod
    def _linear_regression(x_values: list[float], y_values: list[float]) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Calculates linear regression y = a*x + b
        Returns (a, b, r_squared, se_intercept)
        a: slope, b: intercept, r_squared: quality of fit, se_intercept: standard error of intercept
        """
        n = len(x_values)
        if n < 2:
            return None, None, None, None
        
        # Averages
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        # Calculate slope and intercept
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if abs(denominator) < 1e-9:
            return None, None, None, None
        
        a = numerator / denominator  # slope
        b = y_mean - a * x_mean      # intercept
        
        # Calculate R² (coefficient of determination)
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))
        
        if abs(ss_tot) < 1e-9:
            # All y-values are the same, R² is undefined or 1 if slope is 0.
            # We return 0 as not significant
            return a, b, 0.0, 0.0

        ss_res = sum((y_values[i] - (a * x_values[i] + b)) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot)
        
        # Standard Error of Intercept calculation
        if n > 2:
            mse = ss_res / (n - 2)
            # var(b) = MSE * (1/n + x_mean^2 / Sxx) where Sxx is denominator
            var_b = mse * (1.0/n + (x_mean ** 2) / denominator)
            se_intercept = math.sqrt(var_b)
        else:
            se_intercept = 0.0
            
        return a, b, r_squared, se_intercept
        
    def _get_power_percent(self, state) -> Optional[float]:
        """Extract power_percent from a VTherm state history object (State or dict)."""
        
        # Handle State object vs dict
        if hasattr(state, "attributes"):
            attrs = state.attributes or {}
        else:
            attrs = state.get("attributes", {}) or {}
            
        # First check directly in attributes
        if "power_percent" in attrs:
            try:
                return float(attrs["power_percent"]) / 100.0
            except (ValueError, TypeError):
                return None

        # Over switch (fallback)
        v_over_sw = attrs.get("vtherm_over_switch", {})
        if isinstance(v_over_sw, dict) and "power_percent" in v_over_sw:
            try:
                return float(v_over_sw["power_percent"]) / 100.0
            except (ValueError, TypeError):
                return None

        # Over climate (fallback)
        v_over_cl = attrs.get("vtherm_over_climate", {})
        if isinstance(v_over_cl, dict) and "valve_regulation" in v_over_cl:
            try:
                return float(v_over_cl["valve_regulation"]) / 100.0
            except (ValueError, TypeError):
                return None

        return None

    def _get_indoor_temp(self, state) -> Optional[float]:
        """Extract current_temperature from a VTherm state history object (State or dict)."""
        
        # Handle State object vs dict for attributes
        if hasattr(state, "attributes"):
            attrs = state.attributes or {}
        else:
            attrs = state.get("attributes", {}) or {}

        temp = attrs.get("current_temperature")
        if temp is not None:
            try:
                return float(temp)
            except (ValueError, TypeError):
                pass
        
        # Fallback to state itself if entity is a temperature sensor
        # Handle State object vs dict for state value
        if hasattr(state, "state"):
            temp = state.state
        else:
            temp = state.get("state")
            
        try:
            if temp not in ["unknown", "unavailable", None]:
                return float(temp)
        except (ValueError, TypeError):
            pass
        return None

    def _get_outdoor_temp(self, outdoor_states, target_dt: datetime) -> Optional[float]:
        """
        Interpolates linearly the outdoor temperature at a given time.
        """
        if not outdoor_states:
            return None

        # Fix 1: Use attribute access for last_changed (already a datetime) and simplify key
        try:
            outdoor_states_sorted = sorted(outdoor_states, key=lambda x: x.last_changed)
        except (AttributeError, TypeError):
            _LOGGER.error("%s - Auto TPI Calibration: Cannot sort outdoor history. Check state format.", self._name)
            return None
        
        before = None
        after = None
        
        for state in outdoor_states_sorted:
            try:
                # Fix 2: Use getattr for state value to handle State/LazyState objects
                temp_str = getattr(state, "state", None)
                if temp_str in ["unknown", "unavailable", None]:
                    continue
                temp = float(temp_str)
                
                # Fix 3: Use attribute access for last_changed (already a datetime)
                state_dt = state.last_changed
                
                if state_dt <= target_dt:
                    if before is None:
                        before = (state_dt, temp)
                    elif state_dt > before[0]: # Compare datetimes
                        before = (state_dt, temp)
                if state_dt >= target_dt:
                    if after is None:
                        after = (state_dt, temp)
                    elif state_dt < after[0]: # Compare datetimes
                        after = (state_dt, temp)
            except (ValueError, AttributeError, TypeError):
                # Catch float conversion or missing attribute
                continue
        
        if before is None and after is None:
            return None
        if before is None:
            if after is not None:
                return after[1] # Return temperature
            return None # Should not happen, but for Pylance
        if after is None:
            if before is not None:
                return before[1] # Return temperature
            return None # Should not happen, but for Pylance
        if before[0] == after[0]:
            return before[1] # Return temperature
        
        # Linear interpolation
        total_seconds = (after[0] - before[0]).total_seconds() # Use datetimes for diff
        target_seconds = (target_dt - before[0]).total_seconds() # Use datetimes for diff
        
        if abs(total_seconds) < 1e-9: # Should be caught by before == after but for robustness
            return before[1]
            
        ratio = target_seconds / total_seconds
        
        interpolated = before[1] + (after[1] - before[1]) * ratio # Use temperatures for math
        return interpolated

    def _get_avg_outdoor_temp(self, outdoor_states, start_dt: datetime, end_dt: datetime) -> Optional[float]:
        """
        Calculates the average outdoor temperature between two instants
        by sampling every 5 minutes and interpolating.
        """
        if not outdoor_states:
            return None
        
        samples = []
        current = start_dt
        interval = timedelta(minutes=5)
        
        while current <= end_dt:
            temp = self._get_outdoor_temp(outdoor_states, current)
            if temp is not None:
                samples.append(temp)
            current += interval
        
        if not samples:
            return None
        
        return sum(samples) / len(samples)

    def _extract_cycles(self, vtherm_history: list, outdoor_history: list, hvac_mode: str) -> list[dict]:
        """
        Extracts valid heating/cooling cycles from raw VTherm and outdoor sensor history.
        
        A cycle is a continuous period where power is >= self.saturation_threshold.
        It must be longer than self._cycle_min * 0.9 (adaptation from tests) and
        not be the first cycle after a 'stop' (cold start exclusion).
        """
        
        mode_str = 'heat' if hvac_mode == 'heat' else 'cool'
        
        # The true calculated power (as reported in history) at which the cycle is forced to 100% ON
        # by the minimal_deactivation_delay constraint (PropAlgorithm lines 214-224 in base_thermostat).
        # P_min = 1 - (min_deactivation_delay_sec / cycle_duration_sec)
        cycle_duration_sec = self._cycle_min * 60
        min_deact_delay_sec = self._minimal_deactivation_delay_sec
        
        if cycle_duration_sec > 0 and min_deact_delay_sec > 0:
            # P_min is the power calculated by TPI that will result in a fully ON relay due to the minimal deactivation delay constraint.
            physical_saturation_threshold = 1.0 - (min_deact_delay_sec / cycle_duration_sec)
        else:
            physical_saturation_threshold = 1.0 # Default if no delay or cycle set

        # Match the script's behavior: use 95% power threshold
        # The script uses --min-power 95 by default, which means power_percent >= 95
        min_power_threshold = 0.95  # 95% - same as script default
        
        _LOGGER.debug("%s - Auto TPI Calibration: Physical saturation at %.3f (min_deact=%.0fs), filtering threshold: %.3f",
                      self._name, physical_saturation_threshold, min_deact_delay_sec, min_power_threshold)


        if not vtherm_history:
            return []

        # vtherm_history and outdoor_history are already lists of states
        states = vtherm_history
        outdoor_states = outdoor_history
        
        # Sort by date
        try:
            states_sorted = sorted(states, key=lambda x: x.last_changed)
        except (ValueError, AttributeError, TypeError):
            _LOGGER.error("%s - Auto TPI Calibration: Cannot sort VTherm history. Check state format.", self._name)
            return []

        cycles = []
        current_cycle: Optional[dict] = None
        last_cycle_end_ts = None  # Track end timestamp to prevent same-timestamp cycles
        
        for s in states_sorted:
            hvac = s.state
            power = self._get_power_percent(s)
            temp = self._get_indoor_temp(s)
            
            # Skip states with invalid temperature or power data
            if temp is None or power is None:
                continue

            current_hvac_mode = 'stop'
            if hvac == "heat":
                current_hvac_mode = 'heat'
            elif hvac == "cool":
                current_hvac_mode = 'cool'
            
            is_correct_mode = current_hvac_mode == mode_str
            is_saturated = power >= min_power_threshold
            
            # First check HVAC mode - if not correct mode, ABANDON any active cycle
            if not is_correct_mode:
                if current_cycle is not None:
                    # Script behavior: abandon cycle when mode changes (don't save)
                    current_cycle = None
                continue
            
            # Now we're in correct mode, check saturation
            if is_saturated:
                # Continuous saturated cycle
                if current_cycle is None:
                    # Debounce: don't start a new cycle if this state has same timestamp as last cycle end
                    # This prevents 0-duration cycles when HA records multiple states with same timestamp
                    state_ts = s.last_changed
                    if last_cycle_end_ts is not None and state_ts == last_cycle_end_ts:
                        continue
                    
                    # Start of a new saturated cycle
                    current_cycle = {
                        "start": s,
                        "end": None,
                        "hvac_mode_str": mode_str
                    }
            else:
                # Power dropped below threshold while still in correct mode - SAVE cycle
                if current_cycle is not None:
                    start_ts = current_cycle["start"].last_changed
                    end_ts = s.last_changed
                    
                    # Skip 0-duration cycles (same timestamp for start and end)
                    # Keep the cycle open to find the real end state
                    if start_ts == end_ts:
                        _LOGGER.debug("%s - Skipping false end at %s (same timestamp as start)", self._name, start_ts)
                        # DON'T reset current_cycle - keep looking for the real end
                        continue
                    
                    current_cycle["end"] = s
                    last_cycle_end_ts = end_ts  # Track end timestamp for debounce
                    _LOGGER.debug("%s - Raw cycle saved: start=%s, end=%s, power_at_end=%.1f%%",
                                  self._name, start_ts, end_ts, power * 100)
                    cycles.append(current_cycle)
                    current_cycle = None
        
        # Capture last cycle if it was still active at the end of history
        if current_cycle and current_cycle["start"] and current_cycle["end"] is None:
            # Use the last state as the end, but this might lead to inaccurate duration
            # Better to discard partial last cycle.
            pass


        # Validation and Data Preparation
        validated = []
        prev_was_complete = False # For cold-start filtering
        cycle_index = 0

        for c in cycles:
            cycle_index += 1
            s = c["start"]
            e = c["end"]

            if not e:
                _LOGGER.debug("%s - Cycle %d rejected: no end state", self._name, cycle_index)
                prev_was_complete = False
                continue

            try:
                t0 = s.last_changed
                t1 = e.last_changed
            except Exception:
                _LOGGER.debug("%s - Cycle %d rejected: datetime error", self._name, cycle_index)
                prev_was_complete = False
                continue

            duration_h = (t1 - t0).total_seconds() / 3600.0

            # Minimum duration filter: 90% of TPI cycle time (matches script behavior)
            min_duration_h = 0.9 * (self._cycle_min / 60.0)
            if duration_h < min_duration_h:
                _LOGGER.debug("%s - Cycle %d rejected: too short (%.3fh < %.3fh)", 
                              self._name, cycle_index, duration_h, min_duration_h)
                prev_was_complete = False
                continue

            if not prev_was_complete:
                # Cold-start exclusion: ignore the first cycle after a stop/short-cycle
                _LOGGER.debug("%s - Cycle %d rejected: cold-start (duration=%.3fh)", 
                              self._name, cycle_index, duration_h)
                prev_was_complete = True
                continue

            # Cycle valid duration and not cold-start
            t_indoor_start = self._get_indoor_temp(s)
            t_indoor_end = self._get_indoor_temp(e)
            
            if t_indoor_start is None or t_indoor_end is None:
                _LOGGER.debug("%s - Cycle %d rejected: missing indoor temp (start=%s, end=%s)", 
                              self._name, cycle_index, t_indoor_start, t_indoor_end)
                prev_was_complete = True
                continue
            
            # Calculate average outdoor temperature over the cycle
            t_outdoor_avg = self._get_avg_outdoor_temp(outdoor_states, t0, t1)

            if t_outdoor_avg is None:
                _LOGGER.debug("%s - Cycle %d rejected: missing outdoor temp", self._name, cycle_index)
                prev_was_complete = True
                continue
            
            # Data Preparation for Linear Regression
            t_in_avg = (t_indoor_start + t_indoor_end) / 2.0
            
            # Y value: Slope (°C/h)
            slope = (t_indoor_end - t_indoor_start) / duration_h
            
            # X value: Delta_T (T_indoor_avg - T_outdoor_avg)
            delta_t = t_in_avg - t_outdoor_avg
            
            _LOGGER.debug("%s - Cycle %d VALIDATED: duration=%.3fh, T_start=%.1f, T_end=%.1f, T_out=%.1f",
                          self._name, cycle_index, duration_h, t_indoor_start, t_indoor_end, t_outdoor_avg)
            
            validated.append({
                "duration_h": duration_h,
                "slope": slope,
                "delta_t": delta_t
            })

            prev_was_complete = True

        _LOGGER.debug("%s - Auto TPI Calibration: Extracted %d cycles (filtered from %d raw cycles)",
                      self._name, len(validated), len(cycles))
        
        return validated

    async def calculate_capacity_from_history(self, vtherm_history: list, outdoor_history: list, hvac_mode: str) -> dict:
        """
        Processes historical data to determine the maximum heating/cooling capacity (Capacity)
        using linear regression on saturated cycles.

        Args:
            vtherm_history: A list of raw Home Assistant state history data for the thermostat entity.
            outdoor_history: A list of raw Home Assistant state history data for the outdoor sensor.
            hvac_mode: The mode for which to calculate ('heat' or 'cool').

        Returns:
            A dictionary with the calculated capacity and fit quality.
        """

        # vtherm_history and outdoor_history are directly passed
        
        # 1. Cycle Extraction and Data Preparation
        validated_cycles = self._extract_cycles(vtherm_history, outdoor_history, hvac_mode)
        
        if len(validated_cycles) < 2:
            error_msg = f"Not enough valid cycles ({len(validated_cycles)} found). Cannot perform linear regression."
            _LOGGER.warning("%s - Auto TPI Calibration: %s",
                            self._name, error_msg)
            return {
                "success": False, "error": error_msg, "cycles_used": 0
            }
            
        x_values = [c["delta_t"] for c in validated_cycles]  # X: T_indoor_avg - T_outdoor_avg
        y_values = [c["slope"] for c in validated_cycles]    # Y: Capacity observed (°C/h)

        # Debug: Show regression data points
        _LOGGER.debug("%s - Auto TPI Calibration: Regression data points:", self._name)
        for i, c in enumerate(validated_cycles):
            _LOGGER.debug("  Cycle %d: delta_t=%.2f°C, slope=%.4f°C/h, duration=%.1fmin",
                          i + 1, c["delta_t"], c["slope"], c["duration_h"] * 60)

        # 2. Linear Regression (Y = a*X + b)
        # Equation: slope = Capacity - (Kext * delta_t)
        # We only care about the Intercept (b) = Capacity
        
        slope_reg, intercept_reg, r_squared, se_intercept = self._linear_regression(x_values, y_values)
        
        if intercept_reg is None:
            error_msg = "Linear regression failed (e.g., all X-values are the same)."
            _LOGGER.error("%s - Auto TPI Calibration: %s", self._name, error_msg)
            return {
                "success": False, "error": error_msg, "cycles_used": len(validated_cycles)
            }
            
        # 3. Interpret Results
        capacity_effective = float(intercept_reg)

        # 4. Correction for Thermal Inertia (Heater Warm-up Time)
        # The calculated intercept is the effective capacity over the cycle duration,
        # discounted by the heater warm-up time. Correct the value to find the true capacity.
        
        # Calculate average cycle duration
        avg_duration_h = sum(c["duration_h"] for c in validated_cycles) / len(validated_cycles)
        
        # Warmup time in hours (from configuration)
        warmup_h = self._heater_heating_time / 60.0
        
        # Effective Power (assumed average across saturated cycles)
        if avg_duration_h > 0.0 and warmup_h < avg_duration_h:
            effective_power = (avg_duration_h - warmup_h) / avg_duration_h
        else:
            effective_power = 1.0
            
        capacity = capacity_effective
        if effective_power < 1.0:
            capacity = capacity_effective / effective_power
            _LOGGER.info(
                "%s - Auto TPI Calibration: Effective Capacity corrected: %.3f / %.3f = %.3f (Warmup=%.1f min, AvgCycle=%.1f min)",
                self._name, capacity_effective, effective_power, capacity, self._heater_heating_time, avg_duration_h * 60
            )

        # Ensure capacity is positive (physical constraint)
        if capacity <= 0.0:
            warning_msg = f"Calculated capacity ({capacity:.3f}) is not positive. Forcing capacity=0.01."
            _LOGGER.warning("%s - Auto TPI Calibration: %s", self._name, warning_msg)
            capacity = 0.01

        # Calculate additional metrics
        k_ext = -slope_reg if slope_reg is not None else 0.0
        
        # Reliability Calculation
        # Reliability = max(0, 100 * (1 - (2 * SE_b / Capacity)))
        # SE_b is se_intercept
        if se_intercept is not None and capacity > 0:
            reliability = max(0.0, 100.0 * (1.0 - (2.0 * se_intercept / capacity)))
        else:
            reliability = 0.0

        # Penalty for small samples (< 5 cycles)
        # We want to avoid 100% reliability with only 2 cycles (even if perfect fit)
        n_cycles = len(validated_cycles)
        if n_cycles < 5:
            factor = n_cycles / 5.0
            old_reliability = reliability
            reliability = reliability * factor
            _LOGGER.debug(
                "%s - Auto TPI Calibration: Small sample penalty (n=%d, factor=%.2f): %.1f%% -> %.1f%%",
                self._name, n_cycles, factor, old_reliability, reliability
            )
            
        # Period calculation (in days)
        period_days = 0.0
        if vtherm_history:
             timestamps = [s.last_changed for s in vtherm_history]
             if timestamps:
                 start_date = min(timestamps)
                 end_date = max(timestamps)
                 period_days = (end_date - start_date).total_seconds() / 86400.0
                 
        min_power_threshold = 0.95 # Hardcoded in _extract_cycles

        _LOGGER.info(
            "%s - Auto TPI Calibration: Capacity=%.3f °C/h (R²=%.3f, Reliability=%.1f%%, Cycles=%d)",
            self._name, capacity, r_squared if r_squared is not None else 0.0, reliability, len(validated_cycles)
        )
            
        return {
            "success": True,
            "capacity": capacity,
            "cycles_used": len(validated_cycles),
            "reliability": round(reliability, 1),
            "k_ext": round(k_ext, 4),
            "min_power_threshold": min_power_threshold,
            "period": round(period_days, 1)
        }
    
    async def on_cycle_started(self, on_time_sec: float, off_time_sec: float,
                             on_percent: float, hvac_mode: str):
        """Called when a TPI cycle starts."""
        # Detect if previous cycle was interrupted
        is_expected_interruption = self._learning_just_completed
        self._learning_just_completed = False  # Reset the flag after check

        if self.state.cycle_active and not is_expected_interruption:
            _LOGGER.info("%s - Auto TPI: Previous cycle was interrupted (not completed). Discarding it.", self._name)
            # You could add specific logic here if needed (stats, etc)
        
        # Cancel any pending capture timer
        if self._timer_capture_remove_callback:
            self._timer_capture_remove_callback()
            self._timer_capture_remove_callback = None

        self.state.cycle_active = True
        
        _LOGGER.debug("%s - Auto TPI: Cycle started. On: %.0fs, Off: %.0fs (%.1f%%), Mode: %s",
                     self._name, on_time_sec, off_time_sec, on_percent * 100, hvac_mode)
        
        now = datetime.now()
        
        # Snapshot current state for learning at the end of the cycle
        self.state.last_temp_in = self._current_temp_in
        self.state.last_temp_out = self._current_temp_out
        self.state.last_order = self._current_target_temp
        self.state.last_power = on_percent if on_percent is not None else 0.0
        self.state.last_on_temp_in = 0.0 # Reset
        
        # Save previous state before updating last_state (for first cycle detection)
        self.state.previous_state = self.state.last_state

        # Map VThermHvacMode/HVACMode to internal state string
        # hvac_mode is expected to be VThermHvacMode or string representation
        mode_str = str(hvac_mode)
        if mode_str == 'heat' or mode_str == 'heating':
            self.state.last_state = 'heat'
        elif mode_str == 'cool' or mode_str == 'cooling':
            self.state.last_state = 'cool'
        else:
            self.state.last_state = 'stop'
            
        self.state.cycle_start_date = now
        self.state.last_update_date = now
        
        # Schedule capture of temperature at the end of the ON pulse
        if on_time_sec > 0:
            self._timer_capture_remove_callback = async_call_later(
                self._hass,
                on_time_sec,
                self._capture_end_of_on_temp
            )

        # Calculate cold factor for this cycle
        self.state.current_cycle_cold_factor = 0.0
        if self._heater_cooling_time > 0 and self.state.last_heater_stop_time:
            elapsed_off = (now - self.state.last_heater_stop_time).total_seconds() / 60.0
            if elapsed_off >= 0:
                self.state.current_cycle_cold_factor = min(1.0, max(0.0, elapsed_off / self._heater_cooling_time))
                _LOGGER.debug("%s - Auto TPI: Cold factor calc: elapsed_off=%.1f min, cooling_time=%.1f min, factor=%.2f",
                              self._name, elapsed_off, self._heater_cooling_time, self.state.current_cycle_cold_factor)
        
        await self.async_save_data()

    async def on_cycle_completed(self, on_time_sec: float, off_time_sec: float, hvac_mode: str):
        """Called when a TPI cycle completes."""
        if not self.state.cycle_active:
            _LOGGER.debug("%s - Auto TPI: Cycle completed but no cycle active. Ignoring.", self._name)
            return

        self.state.cycle_active = False

        elapsed_minutes = (on_time_sec + off_time_sec) / 60
        on_time_minutes = on_time_sec / 60.0
        self.state.total_cycles += 1
        
        # Update last_heater_stop_time if we were heating
        if self.state.last_state == 'heat':
            self.state.last_heater_stop_time = datetime.now()

        # Calculate Power Efficiency based on Heater Warm-up Time and Cold Factor
        # heater_heating_time is the time for the heater to warm up when fully cold.
        # effective_warm_up_time is the actual warm-up time in this cycle, adjusted by the cold_factor.
        # This part of the ON time is considered 'ineffective' for room temperature rise.
        self._last_cycle_power_efficiency = 1.0
        # effective_warm_up_time is the portion of the ON time used to heat up the radiator itself
        effective_warm_up_time = self._heater_heating_time * self.state.current_cycle_cold_factor
        
        if effective_warm_up_time > 0 and on_time_minutes > 0:
            # effective_time is the time remaining after the radiator is warmed up
            effective_time = max(0.0, on_time_minutes - effective_warm_up_time)
            self._last_cycle_power_efficiency = effective_time / on_time_minutes
            
            _LOGGER.debug("%s - Auto TPI: Power Efficiency calc: on_time=%.1f min, warm_up_time=%.1f, cold_factor=%.2f, eff_warm_up_time=%.1f, eff=%.2f",
                          self._name, on_time_minutes, self._heater_heating_time, self.state.current_cycle_cold_factor, effective_warm_up_time, self._last_cycle_power_efficiency)
        
        if self.learning_active:
            _LOGGER.info("%s - Auto TPI: Cycle #%d completed after %.1f minutes (efficiency: %.2f)",
                        self._name, self.state.total_cycles, elapsed_minutes, self._last_cycle_power_efficiency)
        else:
            _LOGGER.debug("%s - Auto TPI: Cycle #%d completed after %.1f minutes (efficiency: %.2f)",
                        self._name, self.state.total_cycles, elapsed_minutes, self._last_cycle_power_efficiency)
        
        # Attempt learning
        # We check if the cycle was significant enough for learning.
        # The ON pulse must be longer than the estimated time used to warm up the radiator itself.
        is_significant_cycle = True
        if effective_warm_up_time > 0 and on_time_minutes <= effective_warm_up_time:
            is_significant_cycle = False
            _LOGGER.debug("%s - Auto TPI: Cycle ignored for learning - ON time (%.1f) <= Est. Warm-up Time (%.1f)",
                          self._name, on_time_minutes, effective_warm_up_time)

        if self._should_learn() and is_significant_cycle:
            _LOGGER.info("%s - Auto TPI: Attempting to learn from cycle data", self._name)
            await self._perform_learning(self._current_temp_in, self._current_temp_out)
        else:
            reason = self._get_no_learn_reason()
            if not is_significant_cycle and reason == "unknown":
                reason = "on_time_too_short_vs_heating_time"
                
            _LOGGER.debug("%s - Auto TPI: Not learning this cycle: %s", self._name, reason)
            self.state.last_learning_status = reason
            
        # Check for failures
        self._detect_failures(self._current_temp_in)

        # The Max Capacity detection logic has been removed as capacity is now set by service.
        await self.async_save_data()

    def get_calculated_params(self) -> dict:
        return self._calculated_params
    
    @property
    def learning_active(self) -> bool:
        return self.state.autolearn_enabled
    
    @property
    def int_cycles(self) -> int:
        """Number of ACTUAL learning cycles completed for internal coefficient"""
        is_cool_mode = self._current_hvac_mode == 'cool'
        if is_cool_mode:
            return max(0, self.state.coeff_indoor_cool_autolearn - self._avg_initial_weight)
        return max(0, self.state.coeff_indoor_autolearn - self._avg_initial_weight)

    @property
    def ext_cycles(self) -> int:
        """Number of learning cycles completed for external coefficient"""
        is_cool_mode = self._current_hvac_mode == 'cool'
        if is_cool_mode:
            return self.state.coeff_outdoor_cool_autolearn
        return self.state.coeff_outdoor_autolearn
    
    @property
    def heating_cycles_count(self) -> int:
        """Number of total TPI cycles"""
        return self.state.total_cycles
    
    @property
    def time_constant(self) -> float:
        """Thermal time constant in hours"""
        if self.state.coeff_indoor_heat > 0:
            return round(1.0 / self.state.coeff_indoor_heat, 2)
        return 0.0
    
    @property
    def confidence(self) -> float:
        """Confidence level in the learned model (0.0 to 1.0)"""
        # We consider stability reached when both coefficients have 50 cycles
        int_cycles = self.int_cycles
        ext_cycles = self.ext_cycles
        
        if int_cycles == 0 and ext_cycles == 0:
            return 0.0
            
        # Average of progress for both
        confidence_int = min(int_cycles / 50.0, 1.0)
        confidence_ext = min(ext_cycles / 50.0, 1.0)
        
        cycle_confidence = (confidence_int + confidence_ext) / 2.0
        
        if self.state.consecutive_failures > 0:
            failure_penalty = min(self.state.consecutive_failures * 0.15, 0.6)
            cycle_confidence = max(0.2, cycle_confidence - failure_penalty)
        
        return round(cycle_confidence, 2)

    async def start_learning(self, coef_int: float = None, coef_ext: float = None):
        """Start learning, optionally resetting coefficients to configured values."""
        # Use provided values, or fallback to default (configured) values
        # This allows resetting to the original configuration when starting a new learning session
        target_int = coef_int if coef_int is not None else self._default_coef_int
        target_ext = coef_ext if coef_ext is not None else self._default_coef_ext

        _LOGGER.info("%s - Auto TPI: Starting learning with coef_int=%.3f, coef_ext=%.3f",
                    self._name, target_int, target_ext)
        
        self.state.coeff_indoor_heat = target_int
        self.state.coeff_indoor_cool = target_int
        self.state.coeff_outdoor_heat = target_ext
        self.state.coeff_outdoor_cool = target_ext
        
        # ALWAYS reset ALL counters (moved outside the if blocks)
        self.state.coeff_indoor_autolearn = self._avg_initial_weight
        self.state.coeff_outdoor_autolearn = 0
        self.state.coeff_indoor_cool_autolearn = self._avg_initial_weight
        self.state.coeff_outdoor_cool_autolearn = 0
        
        # Reset all learning data for fresh start
        self.state.last_power = 0.0
        self.state.last_order = 0.0
        self.state.last_temp_in = 0.0
        self.state.last_temp_out = 0.0
        self.state.last_state = 'stop'
        self.state.last_update_date = None
        self.state.last_heater_stop_time = None
        self.state.total_cycles = 0
        self.state.consecutive_failures = 0
        self.state.last_learning_status = "learning_started"
        self.state.autolearn_enabled = True
        self.state.learning_start_date = datetime.now()
        self.state.cycle_start_date = datetime.now()
        self.state.cycle_active = False
        
        # The capacity startup logic is removed as capacity is now set manually by service/initial config.
        # We assume the capacity is already known or set to a safe default (1.0) when learning starts.
        
        # Ensure max_capacity is not 0, if it is, force default 1.0 (to allow proper indoor learning calc)
        if self.state.max_capacity_heat == 0.0:
            self.state.max_capacity_heat = 1.0
        if self.state.max_capacity_cool == 0.0:
            self.state.max_capacity_cool = 1.0

        await self.async_save_data()

    async def stop_learning(self):
        _LOGGER.info("%s - Auto TPI: Stopping learning", self._name)
        self.state.autolearn_enabled = False
        self.state.learning_start_date = None
        self.state.last_learning_status = "learning_stopped"
        await self.async_save_data()
        
    async def reset_learning_data(self):
        _LOGGER.info("%s - Auto TPI: Resetting all learning data", self._name)
        self.state = AutoTpiState()
        self.state.cycle_active = False
        await self.async_save_data()

    async def reset_capacities(self):
        """Reset max heat/cool capacities to default (1.0)."""
        _LOGGER.info("%s - Auto TPI: Resetting max heat/cool capacities to default (1.0)", self._name)
        self.state.max_capacity_heat = 1.0
        self.state.max_capacity_cool = 1.0
        await self.async_save_data()
        
    async def start_cycle_loop(self, data_provider: Callable[[], dict], event_sender: Callable[[dict], None]):
        """Start the TPI cycle loop."""
        _LOGGER.debug("%s - Auto TPI: Starting cycle loop", self._name)
        self._data_provider = data_provider
        self._event_sender = event_sender

        # Stop existing timer if any
        if self._timer_remove_callback:
            self._timer_remove_callback()
            self._timer_remove_callback = None

        self._current_cycle_interrupted = False

        # Execute immediately
        await self._tick()

    async def _capture_end_of_on_temp(self, _):
        """Called when the ON period ends (heater turns off)."""
        self.state.last_on_temp_in = self._current_temp_in
        _LOGGER.debug("%s - Auto TPI: Captured last_on_temp_in: %.3f", self._name, self.state.last_on_temp_in)
        self._timer_capture_remove_callback = None

    def stop_cycle_loop(self):
        """Stop the TPI cycle loop."""
        _LOGGER.debug("%s - Auto TPI: Stopping cycle loop", self._name)
        if self._timer_remove_callback:
            self._timer_remove_callback()
            self._timer_remove_callback = None
        if self._timer_capture_remove_callback:
            self._timer_capture_remove_callback()
            self._timer_capture_remove_callback = None

        self._data_provider = None
        self._event_sender = None

    def _schedule_next_timer(self):
        """Schedule the next timer."""
        # Ensure we don't have multiple timers
        if self._timer_remove_callback:
            self._timer_remove_callback()
            
        self._timer_remove_callback = async_call_later(
            self._hass, self._cycle_min * 60, self._on_timer_fired
        )

    async def _on_timer_fired(self, _):
        """Called when timer fires."""
        await self._tick()

    async def _tick(self):
        """Perform a tick of the cycle loop."""
        if not self._data_provider:
            return

        now = datetime.now()
        
        # 1. Handle previous cycle completion
        if self.state.cycle_start_date is not None and self._current_cycle_params is not None:
            elapsed_minutes = (now - self.state.cycle_start_date).total_seconds() / 60
            expected_duration = self._cycle_min
            tolerance = max(expected_duration * 0.1, 1.0)

            if abs(elapsed_minutes - expected_duration) <= tolerance:
                _LOGGER.debug(
                    "%s - Cycle validation success: duration=%.1fmin (expected=%.1fmin). Triggering learning.",
                    self._name, elapsed_minutes, expected_duration
                )
                # Use stored parameters from the PREVIOUS cycle
                prev_params = self._current_cycle_params
                await self.on_cycle_completed(
                    on_time_sec=prev_params.get("on_time_sec", 0),
                    off_time_sec=prev_params.get("off_time_sec", 0),
                    hvac_mode=prev_params.get("hvac_mode", "stop")
                )
            else:
                _LOGGER.debug(
                    "%s - Cycle validation failed: duration=%.1fmin (expected=%.1fmin, tolerance=%.1fmin). Skipping learning.",
                    self._name, elapsed_minutes, expected_duration, tolerance
                )
            
            # Reset previous cycle tracking
            self._current_cycle_params = None

        # 2. Get fresh data from thermostat
        try:
            if asyncio.iscoroutinefunction(self._data_provider):
                params = await self._data_provider()
            else:
                params = self._data_provider()
        except Exception as e:
            _LOGGER.error("%s - Auto TPI: Error getting data from thermostat: %s", self._name, e)
            # Retry later ?
            self._schedule_next_timer()
            return

        if not params:
            _LOGGER.warning("%s - Auto TPI: No data received from thermostat", self._name)
            self._schedule_next_timer()
            return
            
        self._current_cycle_params = params
        on_time = params.get("on_time_sec", 0)
        off_time = params.get("off_time_sec", 0)
        on_percent = params.get("on_percent", 0)
        hvac_mode = params.get("hvac_mode", "stop")

        # 3. Notify start of cycle
        await self.on_cycle_started(on_time, off_time, on_percent, hvac_mode)
        
        # 4. Notify thermostat to apply changes
        if self._event_sender:
            try:
                if asyncio.iscoroutinefunction(self._event_sender):
                    await self._event_sender(params)
                else:
                    self._event_sender(params)
            except Exception as e:
                _LOGGER.error("%s - Auto TPI: Error sending event to thermostat: %s", self._name, e)

        # 5. Schedule next tick
        self._schedule_next_timer()

