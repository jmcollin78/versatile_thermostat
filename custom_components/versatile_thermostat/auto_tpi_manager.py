"""Auto TPI Manager implementing TPI algorithm."""

import logging
import json
import os
import math
import statistics
from datetime import datetime, timedelta
from typing import Optional
from homeassistant.util.unit_conversion import TemperatureConverter
from homeassistant.const import UnitOfTemperature
from dataclasses import dataclass, asdict, field

import asyncio
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers import entity_platform, service, translation
from homeassistant.helpers.storage import Store
from homeassistant.components.recorder import history, get_instance
from homeassistant.util import dt as dt_util
from functools import partial

from .const import (
    DOMAIN,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_AUTO_TPI_HEATING_POWER,
    CONF_AUTO_TPI_COOLING_POWER,
)
_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 8
STORAGE_KEY_PREFIX = "versatile_thermostat.auto_tpi"

# Configurable constants for learning algorithm behavior
MIN_KINT = 0.05  # Minimum Kint threshold to maintain temperature responsiveness
OVERSHOOT_THRESHOLD = 0.2  # Temperature overshoot threshold (°C) to trigger aggressive Kext correction
OVERSHOOT_POWER_THRESHOLD = 0.05  # Minimum power (5%) to consider overshoot as Kext error
OVERSHOOT_CORRECTION_BOOST = 2.0  # Multiplier for alpha during overshoot correction
KEXT_LEARNING_MAX_GAP = 0.5  # Max gap (°C) to allow Kext learning (Near-Field vs Far-Field)
INSUFFICIENT_RISE_GAP_THRESHOLD = KEXT_LEARNING_MAX_GAP  # Min gap (°C) to trigger Kint correction when temp stagnates
INSUFFICIENT_RISE_BOOST_FACTOR = 1.08  # Kint increase factor (8%) per stagnating cycle
MAX_CONSECUTIVE_KINT_BOOSTS = 5  # Max consecutive Kint boosts before warning (undersized heating)


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
    last_state: str = "stop"  # 'heat', 'cool', 'stop'
    previous_state: str = "stop"  # State of the previous cycle
    last_on_temp_in: float = 0.0  # Temp at the end of ON time
    last_update_date: Optional[datetime] = None
    last_heater_stop_time: Optional[datetime] = None  # When heater stopped

    # Cycle management
    cycle_start_date: Optional[datetime] = None  # Start of current cycle
    cycle_active: bool = False
    current_cycle_cold_factor: float = 0.0  # 1.0 = cold, 0.0 = hot

    # Management
    consecutive_failures: int = 0
    autolearn_enabled: bool = False
    last_learning_status: str = "startup"
    total_cycles: int = 0  # Total number of TPI cycles
    consecutive_boosts: int = 0  # Track consecutive boost attempts
    recent_errors: list = field(default_factory=list)  # Store last N errors for regime change detection
    regime_change_detected: bool = False  # Flag for temporary alpha boost
    learning_start_date: Optional[datetime] = None  # Date when learning started
    
    # Capacity learning (Heat only)
    capacity_heat_learn_count: int = 0
    bootstrap_failure_count: int = 0 # Number of consecutive failures to learn capacity during bootstrap
    # Bootstrap is implied when capacity_heat_learn_count < 3
    
    # Optional features configuration
    allow_kint_boost: bool = False
    allow_kext_overshoot: bool = False

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

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        unique_id: str,
        name: str,
        cycle_min: int,
        tpi_threshold_low: float = 0.0,
        tpi_threshold_high: float = 0.0,
        minimal_deactivation_delay: int = 0,
        coef_int: float = 0.6,
        coef_ext: float = 0.04,
        heater_heating_time: int = 5,
        heater_cooling_time: int = 5,
        calculation_method: str = "ema",
        max_coef_int: float = 1.0,
        heating_rate: float = 1.0,
        cooling_rate: float = 1.0,
        avg_initial_weight: int = 1,
        ema_alpha: float = 0.15,
        ema_decay_rate: float = 0.08,
        continuous_learning: bool = False,
        keep_ext_learning: bool = False,
        enable_update_config: bool = False,
        enable_notification: bool = False,
    ):
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

        self._temp_unit = self._hass.config.units.temperature_unit
        self._unit_factor = 1.8 if self._temp_unit == UnitOfTemperature.FAHRENHEIT else 1.0

        self._calculation_method = calculation_method
        self._ema_alpha = ema_alpha
        self._avg_initial_weight = avg_initial_weight
        self._max_coef_int = max_coef_int
        # Convert rates to Celsius/h if needed
        self._heating_rate = heating_rate / self._unit_factor
        self._cooling_rate = cooling_rate / self._unit_factor
        self._ema_decay_rate = ema_decay_rate
        self._continuous_learning = continuous_learning
        self._keep_ext_learning = keep_ext_learning
        self._keep_ext_learning = keep_ext_learning

        # Notification management
        self._last_notified_coef_int: Optional[float] = None
        self._last_notified_coef_ext: Optional[float] = None

        storage_key = f"{STORAGE_KEY_PREFIX}.{unique_id.replace('.', '_')}"
        self._store = Store(hass, STORAGE_VERSION, storage_key)
        # Convert config coefficients (User Unit) to Internal (Celsius)
        # K_C = K_F * 1.8
        self._default_coef_int = (coef_int if coef_int is not None else 0.6) * self._unit_factor
        self._default_coef_ext = (coef_ext if coef_ext is not None else 0.04) * self._unit_factor

        self.state = AutoTpiState(
            coeff_indoor_heat=self._default_coef_int, coeff_outdoor_heat=self._default_coef_ext, coeff_indoor_cool=self._default_coef_int, coeff_outdoor_cool=self._default_coef_ext
        )
        self._calculated_params = {}

        # Transient state
        self._current_temp_in: float = 0.0
        self._current_temp_out: float = 0.0
        self._current_target_temp: float = 0.0
        self._current_hvac_mode: str = "heat"  # 'heat' or 'cool' (or 'off' etc)
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
        self._central_boiler_off: bool = False

    def _to_celsius(self, temp: float) -> float:
        """Convert temperature to Celsius if needed."""
        if temp is None:
            return 0.0
        if self._temp_unit == UnitOfTemperature.FAHRENHEIT:
            return TemperatureConverter.convert(temp, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)
        return temp

    async def async_update_coefficients_config(self, coef_int: float, coef_ext: float):
        """Update CONF_TPI_COEF_INT and CONF_TPI_COEF_EXT in the HA config entry."""

        if not self._enable_update_config:
            _LOGGER.debug("%s - Auto TPI: Skipping config update for coefficients as enable_update_config is False", self._name)
            return

        new_data = {
            **self._config_entry.data,
            CONF_TPI_COEF_INT: round(coef_int / self._unit_factor, 3),
            CONF_TPI_COEF_EXT: round(coef_ext / self._unit_factor, 3),
        }

        self._hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        _LOGGER.info("%s - Auto TPI: Updated config coefficients: Kint=%.3f, Kext=%.3f", self._name, coef_int, coef_ext)

    async def async_update_capacity_config(self, capacity: float, is_heat_mode: bool):
        """Update capacity parameters in the HA config entry."""

        if capacity <= 0.0:
            _LOGGER.warning("%s - Auto TPI: Skipping capacity config update, capacity is not positive (%.3f)", self._name, capacity)
            return

        rate_key = CONF_AUTO_TPI_HEATING_POWER if is_heat_mode else CONF_AUTO_TPI_COOLING_POWER

        new_data = {
            **self._config_entry.data,
            rate_key: round(capacity * self._unit_factor, 3),
        }

        self._hass.config_entries.async_update_entry(self._config_entry, data=new_data)

        # Also update the local state for immediate use in future cycles
        if is_heat_mode:
            self.state.max_capacity_heat = capacity
            self._heating_rate = capacity
        else:
            self.state.max_capacity_cool = capacity
            self._cooling_rate = capacity

        await self.async_save_data()

        _LOGGER.info("%s - Auto TPI: Updated config capacity for %s mode: Capacity=%.3f", self._name, "heat" if is_heat_mode else "cool", capacity)

    async def process_learning_completion(self, current_params: dict) -> Optional[dict]:
        """
        Processes the learned coefficients after a cycle to:
        1. Check if learning is finished/stabilized.
        2. Apply continuous learning if enabled.
        3. Persist coefficients to HA config if enabled.
        4. Send persistent notifications if enabled.

        Returns a dict of finalized coefficients if persisted, or None.
        """

        is_cool_mode = self._current_hvac_mode == "cool"

        if is_cool_mode:
            k_int = self.state.coeff_indoor_cool
            k_ext = self.state.coeff_outdoor_cool
            int_cycles_count = self.state.coeff_indoor_cool_autolearn
            ext_cycles_count = self.state.coeff_outdoor_cool_autolearn
        else:
            k_int = self.state.coeff_indoor_heat
            k_ext = self.state.coeff_outdoor_heat
            int_cycles_count = self.state.coeff_indoor_autolearn
            ext_cycles_count = self.state.coeff_outdoor_autolearn

        # 1. Check if learning is finished/stabilized (for non-continuous learning)
        # We check if the *raw* counter has reached the threshold, which accounts for _avg_initial_weight.
        INT_CYCLES_THRESHOLD = 50 + self._avg_initial_weight
        EXT_CYCLES_THRESHOLD = 50

        is_int_finished = int_cycles_count >= INT_CYCLES_THRESHOLD
        is_kext_standard_finished = ext_cycles_count >= EXT_CYCLES_THRESHOLD

        is_ext_finished = is_kext_standard_finished and (not self._keep_ext_learning or is_int_finished)

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
                    self._name,
                    int_cycles_count - self._avg_initial_weight,
                    INT_CYCLES_THRESHOLD - self._avg_initial_weight,
                    ext_cycles_count,
                    EXT_CYCLES_THRESHOLD,
                )
                return None
            else:
                _LOGGER.info("%s - Auto TPI: Learning completed. Persisting final coefficients and stopping learning.", self._name)
                await self.stop_learning()

        # 3. Persist coefficients to HA config if enabled
        await self.async_update_coefficients_config(k_int, k_ext)

        # 4. Send persistent notifications if enabled
        if self._enable_notification:
            # Implement "notify once" logic
            # Check for a significant change (> 0.005) or if it's the first time
            if (self._last_notified_coef_int is None or abs(self._last_notified_coef_int - k_int) > 0.005) or (
                self._last_notified_coef_ext is None or abs(self._last_notified_coef_ext - k_ext) > 0.005
            ):

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
                    _LOGGER.info("%s - Auto TPI: Persistent notification sent for final coefficients.", self._name)
                except Exception as e:
                    _LOGGER.error("%s - Auto TPI: Error sending persistent notification: %s", self._name, e)

        # Return learned coefficients converted back to User Unit
        # Internal: C. Output: F/C. If F, output = internal / 1.8 (internal * 0.55 ?)
        # K_F = K_C / 1.8.
        return {
            CONF_TPI_COEF_INT: k_int / self._unit_factor,
            CONF_TPI_COEF_EXT: k_ext / self._unit_factor
        }

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

            is_capacity_heat_outdated = self.state.max_capacity_heat != self._heating_rate
            is_capacity_cool_outdated = self.state.max_capacity_cool != self._cooling_rate

            if is_capacity_heat_outdated and self._heating_rate > 0.0:
                _LOGGER.info(
                    "%s - Auto TPI: Overwriting persisted max_capacity_heat (%.3f) with new configured value (%.3f) on load.",
                    self._name,
                    self.state.max_capacity_heat,
                    self._heating_rate,
                )
                self.state.max_capacity_heat = self._heating_rate

            if is_capacity_cool_outdated and self._cooling_rate > 0.0:
                _LOGGER.info(
                    "%s - Auto TPI: Overwriting persisted max_capacity_cool (%.3f) with new configured value (%.3f) on load.",
                    self._name,
                    self.state.max_capacity_cool,
                    self._cooling_rate,
                )
                self.state.max_capacity_cool = self._cooling_rate

            if is_capacity_heat_outdated or is_capacity_cool_outdated:
                await self.async_save_data()  # Save the new correct config value

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

            _LOGGER.info("%s - Auto TPI: State loaded. Cycles: %d, Indoor learn count: %d", self._name, self.state.total_cycles, self.state.coeff_indoor_autolearn)
        else:
            self.state = AutoTpiState(
                coeff_indoor_heat=self._default_coef_int,
                coeff_outdoor_heat=self._default_coef_ext,
                coeff_indoor_cool=self._default_coef_int,
                coeff_outdoor_cool=self._default_coef_ext,
            )

        # MIGRATION FIX: If capacity is already known (legacy or manual), mark as learned
        # This prevents re-triggering bootstrap (count=0) for existing users
        if self.state.max_capacity_heat > 0 and self.state.capacity_heat_learn_count == 0:
            _LOGGER.info("%s - Auto TPI: Existing capacity found (%.3f), marking as learned (count=3)", self._name, self.state.max_capacity_heat)
            self.state.capacity_heat_learn_count = 3
        
        await self.calculate()

    async def update(self, room_temp: float, ext_temp: float, hvac_mode: str, target_temp: float, is_overpowering_detected: bool = False, is_central_boiler_off: bool = False) -> float:
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
        # Convert inputs to Celsius for internal logic
        self._current_temp_in = self._to_celsius(room_temp) if room_temp is not None else 0.0
        self._current_temp_out = self._to_celsius(ext_temp) if ext_temp is not None else 0.0
        self._current_target_temp = self._to_celsius(target_temp) if target_temp is not None else 0.0
        self._current_hvac_mode = hvac_mode
        self._central_boiler_off = is_central_boiler_off

        # Calculate and return power
        # Use hvac_mode to force direction
        calc_state_str = "stop"
        if hvac_mode == "cool":
            calc_state_str = "cool"
        elif hvac_mode == "heat":
            calc_state_str = "heat"

        return self.calculate_power(self._current_target_temp, self._current_temp_in, self._current_temp_out, calc_state_str)

    async def calculate(self) -> Optional[dict]:
        """Calculate TPI parameters, using aggressive coefficients during bootstrap."""
        
        # Determine if in bootstrap (capacity not yet learned)
        in_bootstrap = (
            self.state.max_capacity_heat == 0 or 
            self.state.capacity_heat_learn_count < 3
        )

        # Temporarily override learned coefficients if in bootstrap
        saved_kint = self.state.coeff_indoor_heat
        saved_kext = self.state.coeff_outdoor_heat

        if in_bootstrap:
            # Use aggressive coefficients for bootstrap
            # User requested 1.0 / 0.1 as "normal" values (sufficiently aggressive vs 0.6 default)
            KINT_BOOTSTRAP = 1.0
            KEXT_BOOTSTRAP = 0.1
            
            self.state.coeff_indoor_heat = KINT_BOOTSTRAP
            self.state.coeff_outdoor_heat = KEXT_BOOTSTRAP
        
        try:
            # Return current coefficients for the thermostat to use
            params = {}

            # Use hvac_mode to determine which coefficients to return
            # This prevents flapping when switching between heating/cooling actions while in the same mode (e.g. idle)
            # Note: hvac_mode usually comes from VThermHvacMode (heat, cool, off, auto...)

            is_cool_mode = self._current_hvac_mode == "cool"

            if is_cool_mode:
                params[CONF_TPI_COEF_INT] = self.state.coeff_indoor_cool / self._unit_factor
                params[CONF_TPI_COEF_EXT] = self.state.coeff_outdoor_cool / self._unit_factor
            else:
                params[CONF_TPI_COEF_INT] = self.state.coeff_indoor_heat / self._unit_factor
                params[CONF_TPI_COEF_EXT] = self.state.coeff_outdoor_heat / self._unit_factor

            self._calculated_params = params
            return params
        finally:
            # Restore original values
            if in_bootstrap:
                self.state.coeff_indoor_heat = saved_kint
                self.state.coeff_outdoor_heat = saved_kext

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
        std_error = (sum((e - mean_error) ** 2 for e in errors_to_check) / N) ** 0.5
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
            _LOGGER.debug("%s - Auto TPI: Not learning - Power out of range (%.3f not in 0 < power < %.3f)", self._name, self.state.last_power, saturation_threshold)
            return False

        if self._current_cycle_interrupted:
            _LOGGER.debug("%s - Auto TPI: Not learning - Cycle was interrupted (e.g. Power Shedding)", self._name)
            return False

        if self._central_boiler_off:
            _LOGGER.debug("%s - Auto TPI: Not learning - Central boiler is OFF although VTherm is active (boiler below activation threshold)", self._name)
            return False

        # Failures check
        if self.state.consecutive_failures >= 3:
            return False

        # 1. First Cycle Exclusion
        if self.state.previous_state == "stop":
            _LOGGER.debug("%s - Auto TPI: Not learning - First cycle (previous state was stop)", self._name)
            return False
        if self.state.last_order == 0:
            _LOGGER.debug("%s - Auto TPI: Not learning - Last order is 0", self._name)
            return False

        # 2. Mild Weather Exclusion (Safe Ratio)
        # Avoid division by small numbers or learning when delta is too small to be significant
        delta_out = self.state.last_order - self._current_temp_out
        delta_out_threshold = 1.0  # Celsius
        if abs(delta_out) < delta_out_threshold:
            _LOGGER.debug("%s - Auto TPI: Not learning - Delta out too small (< %.1f)", self._name, delta_out_threshold)
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

        if self._current_cycle_interrupted:
            return "cycle_interrupted_by_overpowering"

        if self._central_boiler_off:
            return "central_boiler_off"

        if self.state.consecutive_failures >= 3:
            return f"too_many_failures({self.state.consecutive_failures})"

        if self.state.previous_state == "stop":
            return "startup_cycle"

        if self.state.last_order == 0:
            return "target_temp_is_zero"

        delta_out = self.state.last_order - self._current_temp_out
        if abs(delta_out) < 1.0:
            return f"outdoor_delta_too_small({delta_out:.1f})"

        return "unknown"

    async def _perform_learning(self, current_temp_in: float, current_temp_out: float):
        """Execute the learning logic based on previous state and current observations."""

        is_heat = self.state.last_state == "heat"
        is_cool = self.state.last_state == "cool"

        if not (is_heat or is_cool):
            self.state.last_learning_status = "not_heating_or_cooling"
            _LOGGER.debug("%s - Auto TPI: Not learning - system was in %s mode", self._name, self.state.last_state)
            return

        # Check if setpoint changed during the cycle - if so, skip ALL learning
        # This prevents incorrect coefficient updates when user adjusts temperature mid-cycle
        setpoint_changed = abs(self._current_target_temp - self.state.last_order) > 0.1
        if setpoint_changed:
            self.state.last_learning_status = "setpoint_changed_during_cycle"
            _LOGGER.debug(
                "%s - Auto TPI: Skipping learning - setpoint changed during cycle (%.1f → %.1f)",
                self._name, self.state.last_order, self._current_target_temp
            )
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

        # CASE 0: Overshoot Correction (BEFORE standard learning)
        # ----------------------------------------------------------
        # When room is overheating despite heat still being applied,
        # Kext is clearly too high. Correct it aggressively before
        # attempting normal learning.
        #
        # IMPORTANT: Only correct if temperature is NOT FALLING despite overshoot.
        # If temp is falling naturally (e.g., after setpoint was lowered), the
        # system is working correctly - no need to reduce Kext.
        # If temp stagnates or rises, Kext is too high (preventing natural cooling).
        # A small threshold (0.02°C) filters out sensor noise.
        temp_not_falling = current_temp_in >= self.state.last_temp_in - 0.02

        if is_heat:
            overshoot = current_temp_in - target_temp
            if overshoot > OVERSHOOT_THRESHOLD and self.state.last_power > OVERSHOOT_POWER_THRESHOLD and temp_not_falling:
                _LOGGER.info(
                    "%s - Auto TPI: Overshoot detected (%.2f°C > %.2f°C threshold, power=%.1f%%, temp not falling)",
                    self._name, overshoot, OVERSHOOT_THRESHOLD, self.state.last_power * 100
                )
                if self._correct_kext_overshoot(overshoot, is_cool=False):
                    return  # Skip other learning for this cycle
        elif is_cool:
            temp_not_rising = current_temp_in <= self.state.last_temp_in + 0.02
            overshoot = target_temp - current_temp_in
            if overshoot > OVERSHOOT_THRESHOLD and self.state.last_power > OVERSHOOT_POWER_THRESHOLD and temp_not_rising:
                _LOGGER.info(
                    "%s - Auto TPI: Overcooling detected (%.2f°C > %.2f°C threshold, power=%.1f%%, temp not rising)",
                    self._name, overshoot, OVERSHOOT_THRESHOLD, self.state.last_power * 100
                )
                if self._correct_kext_overshoot(overshoot, is_cool=True):
                    return  # Skip other learning for this cycle

        # CASE 0.5: Insufficient Rise Correction
        # ----------------------------------------
        # When temperature stagnates despite a significant gap (> 0.3°C)
        # and power is not saturated, Kint is likely too low.
        # Instead of incorrectly adjusting Kext, we boost Kint.
        #
        # This handles the scenario where:
        # - target_diff > 0.3°C (significant gap to setpoint)
        # - temp_progress < 0.02 (temperature is stagnating or dropping)
        # - power < 0.99 (not saturated, so we CAN increase power)
        #
        # In this case, standard indoor learning fails (requires temp_progress > 0.05)
        # and the system incorrectly falls through to outdoor learning, increasing Kext.

        temp_stagnating = temp_progress < 0.02

        if target_diff > INSUFFICIENT_RISE_GAP_THRESHOLD and temp_stagnating and self.state.last_power < 0.99:
            if self._correct_kint_insufficient_rise(target_diff, temp_progress, is_cool):
                return  # Kint corrected, skip other learning for this cycle

        # CASE 0.8: Capacity Learning (Independent of Kint saturation)
        # ------------------------------------------------------------
        # We want to learn capacity even (and especially) when power is saturated (100%)
        if self._should_learn_capacity():
             k_ext = self.state.coeff_outdoor_heat if not is_cool else self.state.coeff_outdoor_cool
             # Delta T for capacity: Tin - Tout (Heat) or Tout - Tin (Cool)
             delta_t_cap = self._current_temp_in - self._current_temp_out if not is_cool else self._current_temp_out - self._current_temp_in
             
             if self._learn_capacity(self.state.last_power, delta_t_cap, temp_progress, self._last_cycle_power_efficiency, k_ext):
                 # Capacity learned. We do NOT return here, because we might still want to try indoor learning
                 # (if not saturated) or outdoor learning.
                 pass

        # CASE 1: Indoor Learning
        # ---------------------------
        # Strict conditions to avoid false positives:
        # - Significant temperature progress (> 0.05°C)
        # - Significant gap to cover (> 0.1°C)
        # - Power not saturated (0 < power < 0.99)

        if 0 < self.state.last_power < 0.99:
            temp_progress_threshold = 0.05
            target_diff_threshold = 0.01
            if temp_progress > temp_progress_threshold and target_diff > target_diff_threshold:
                # Indoor learning attempt
                error = self._learn_indoor(target_diff, temp_progress, self._last_cycle_power_efficiency, is_cool)
                if error is not None:
                    # Learning was successful - temperature is rising
                    self.state.last_learning_status = f"learned_indoor_{'cool' if is_cool else 'heat'}"
                    _LOGGER.info("%s - Auto TPI: Indoor coefficient learned successfully (Error: %.3f)", self._name, error)
                    self._learning_just_completed = True

                    # Reset consecutive Kint boosts counter since temperature is now rising
                    if self.state.consecutive_boosts > 0:
                        _LOGGER.debug("%s - Auto TPI: Resetting consecutive_boosts counter (was %d)", self._name, self.state.consecutive_boosts)
                        self.state.consecutive_boosts = 0

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
                _LOGGER.debug("%s - Auto TPI: Indoor conditions not met (progress=%.3f, target_diff=%.3f)", self._name, temp_progress, target_diff)
        else:
            _LOGGER.debug("%s - Auto TPI: Skipping indoor coeff learning because power is saturated (%.1f%%)", self._name, self.state.last_power * 100)

        # CASE 2: Outdoor Learning
        # ----------------------------
        # Executed when:
        # - Indoor was not applicable (conditions not met)
        # - OR indoor failed (_learn_indoor returned False)
        # Conditions:
        # - Relevant outdoor temperature (outdoor_condition)
        # - Significant remaining gap

        gap_in = target_temp - current_temp_in
        gap_threshold = 0.05

        if outdoor_condition and abs(gap_in) > gap_threshold:
            # Domain Separation: Far-Field vs Near-Field
            # If the gap is large (> KEXT_LEARNING_MAX_GAP), it's a transient state (Kint domain).
            # Kext (Steady State) should only be learned in Near-Field.
            if abs(gap_in) > KEXT_LEARNING_MAX_GAP:
                self.state.last_learning_status = f"gap_too_large_for_outdoor(gap={gap_in:.2f} > {KEXT_LEARNING_MAX_GAP})"
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning: Gap %.2f > %.2f - Far field stagnation is a Kint/Capacity issue, not Kext.",
                    self._name, abs(gap_in), KEXT_LEARNING_MAX_GAP
                )
                return
            elif self._learn_outdoor(current_temp_in, current_temp_out, is_cool):
                if "naturally" not in self.state.last_learning_status:
                    self.state.last_learning_status = f"learned_outdoor_{'cool' if is_cool else 'heat'}"
                    _LOGGER.info("%s - Auto TPI: Outdoor coefficient learned successfully", self._name)
                    self._learning_just_completed = True
                return  # Outdoor success
            else:
                _LOGGER.debug("%s - Auto TPI: Outdoor learning failed", self._name)
        else:
            _LOGGER.debug("%s - Auto TPI: Outdoor conditions not met (outdoor_condition=%s, gap_in=%.3f)", self._name, outdoor_condition, gap_in)

        # No learning was possible
        self.state.last_learning_status = f"no_learning_possible(progress={temp_progress:.2f},target_diff={target_diff:.2f},gap_in={gap_in:.2f})"
        _LOGGER.debug("%s - Auto TPI: No learning possible - %s", self._name, self.state.last_learning_status)

    def _learn_indoor(self, delta_theoretical: float, delta_real: float, efficiency: float = 1.0, is_cool: bool = False) -> Optional[float]:
        """Learn indoor coefficient and optionally capacity."""

        real_rise = delta_real
        rise_threshold = 0.01

        if real_rise <= rise_threshold:
            _LOGGER.debug("%s - Auto TPI: Cannot learn indoor - real_rise %.3f <= %.3f. Will try outdoor learning.", self._name, real_rise, rise_threshold)
            self.state.last_learning_status = "real_rise_too_small"
            return None


        # === KINT LEARNING ===
        # 1. Get adiabatic capacity
        ref_capacity_h = self.state.max_capacity_heat if not is_cool else self.state.max_capacity_cool

        # Fallback if not learned yet
        if ref_capacity_h <= 0:
            count = self.state.capacity_heat_learn_count
            
            if count == 0:
                ref_capacity_h = 0.5  # Very conservative for first cycle
                _LOGGER.warning(
                    "%s - First cycle: using very conservative capacity 0.5°C/h",
                    self._name
                )
            else:
                ref_capacity_h = 1.0  # Standard fallback
                _LOGGER.debug(
                    "%s - Capacity not yet converged (count=%d), using fallback 1.0°C/h",
                    self._name, count
                )

        # If no capacity defined, skip learning for this cycle
        if ref_capacity_h <= 0:
            _LOGGER.debug("%s - Auto TPI: Cannot learn indoor - no capacity defined (ref_capacity_h=%.2f)", self._name, ref_capacity_h)
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

        _LOGGER.debug(
            "%s - Auto TPI: Capacity calc: ref=%.3f °C/h, loss=%.2f, eff=%.3f °C/h, max_rise=%.3f °C (cycle=%.1f min, eff=%.2f)",
            self._name,
            ref_capacity_h,
            loss_factor,
            effective_capacity_h,
            max_achievable_rise,
            self._cycle_min,
            efficiency,
        )

        # 4. Calculate adjusted_theoretical: aim for full gap, capped by capacity
        adjusted_theoretical = min(delta_theoretical, max_achievable_rise)

        if max_achievable_rise < delta_theoretical:
            mode_str = "cooling" if is_cool else "heating"
            _LOGGER.debug("%s - Auto TPI: Target rise clamped from %.3f to %.3f (Max %s Capacity)", self._name, delta_theoretical, max_achievable_rise, mode_str)

        if adjusted_theoretical <= 0:
            _LOGGER.warning("%s - Auto TPI: Cannot learn indoor - adjusted_theoretical <= 0 (max_rise=%.3f, target_diff=%.3f)", self._name, max_achievable_rise, delta_theoretical)
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
            _LOGGER.warning("%s - Auto TPI: Invalid new indoor coeff: %.3f (non-finite or <= 0), skipping", self._name, coeff_new)
            self.state.last_learning_status = "invalid_indoor_coeff"
            return False

        # 4. Cap Coefficient
        MAX_COEFF = self._max_coef_int
        if coeff_new > MAX_COEFF:
            _LOGGER.info("%s - Auto TPI: Calculated indoor coeff %.3f > %.1f, capping to %.1f before averaging", self._name, coeff_new, MAX_COEFF, MAX_COEFF)
            coeff_new = MAX_COEFF

        old_coeff = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        count = self.state.coeff_indoor_cool_autolearn if is_cool else self.state.coeff_indoor_autolearn

        # 5. Calculation Method
        # 5. Calculation Method
        # Cap the effective count to keep the system responsive
        # Even if we have 1000 cycles history, we weigh the new sample as if we had at most 50 cycles.
        effective_count = min(count, 50)

        if self._calculation_method == "average":
            # Weighted average
            # avg_coeff = ((old_coeff * count + coeff_new) / (count + 1))
            # We must use the current count (not incremented) as weight for old_coeff

            # If count is 0 (should not happen for valid state), treat as 1
            weight_old = max(effective_count, 1)

            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Weighted Average: old=%.3f (weight=%d, real_count=%d), new=%.3f, result=%.3f", self._name, old_coeff, weight_old, count, coeff_new, avg_coeff)

        else:  # EMA
            # EMA Smoothing (20% weight by default)
            # new_avg = (old_avg * (1 - alpha)) + (new_sample * alpha)
            alpha = self._get_adaptive_alpha(effective_count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: EMA: old=%.3f, new=%.3f, alpha=%.3f (eff_count=%d, real_count=%d), result=%.3f", self._name, old_coeff, coeff_new, alpha, effective_count, count, avg_coeff)

        # Apply minimum Kint threshold to maintain temperature responsiveness
        if avg_coeff < MIN_KINT:
            _LOGGER.warning(
                "%s - Auto TPI: Calculated Kint %.4f is below minimum %.4f, capping to minimum",
                self._name, avg_coeff, MIN_KINT
            )
            avg_coeff = MIN_KINT

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
            self._name,
            "cool" if is_cool else "heat",
            old_coeff,
            coeff_new,
            real_rise,
            avg_coeff,
            new_count,
        )

        # Reset boost counter after successful learning
        if hasattr(self.state, "consecutive_boosts"):
            self.state.consecutive_boosts = 0

        # Reset regime change flag after consuming the boost
        if self._continuous_learning and self.state.regime_change_detected:
            _LOGGER.debug("%s - Auto TPI: Regime change alpha consumed, resetting flag", self._name)
            self.state.regime_change_detected = False

        return adjusted_theoretical - real_rise  # Return the error: Expected Rise - Actual Rise

    def _learn_outdoor(self, current_temp_in: float, current_temp_out: float, is_cool: bool = False) -> bool:
        """Learn outdoor coefficient."""
        gap_in = self.state.last_order - current_temp_in
        gap_out = self.state.last_order - current_temp_out

        # Validation delta_out (moved here)
        if abs(gap_out) < 0.05:
            _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - gap_out too small (%.3f)", self._name, abs(gap_out))
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
            _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - consigne changed during cycle (%.1f → %.1f)", self._name, self.state.last_order, self._current_target_temp)
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
                _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - Anomalous overcooling (gap_in=%.2f, power=%.1f%%)", self._name, gap_in, self.state.last_power * 100)
                self.state.last_learning_status = "anomalous_overcooling"
                return False

            # NEW: Directional Protection
            # If we are overcooling (below target) BUT the temperature is Rising (going back to target),
            # then natural recovery is happening. Do not lower Kext.
            if gap_in > 0 and current_temp_in > self.state.last_temp_in:
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning during natural undershoot recovery (Temp rising %.2f -> %.2f)",
                    self._name, self.state.last_temp_in, current_temp_in
                )
                self.state.last_learning_status = "warming_up_naturally"
                return True  # Considered handled (skipped)

        else:
            # In heat mode: overheated if gap_in < 0 (temp > target)
            # Acceptable only if we really heated (power > 1% instead of 20%)
            # If power is > 1% and we are overheating, it means Kext is too high and should be reduced.
            if gap_in < 0 and self.state.last_power < 0.01:
                _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - Anomalous overheating (gap_in=%.2f, power=%.1f%%)", self._name, gap_in, self.state.last_power * 100)
                self.state.last_learning_status = "anomalous_overheating"
                return False

            # NEW: Directional Protection
            # If we are overheating (above target) BUT the temperature is Falling (going back to target),
            # then natural recovery is happening. Do not lower Kext.
            if gap_in < 0 and current_temp_in < self.state.last_temp_in:
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning during natural overshoot recovery (Temp falling %.2f -> %.2f)",
                    self._name, self.state.last_temp_in, current_temp_in
                )
                self.state.last_learning_status = "cooling_down_naturally"
                return True  # Considered handled (skipped)

        # If we get here with an overshoot AND significant power:
        # → It is a real model error, we MUST learn from it
        # → The Kext correction will help correct the underestimated external influence
        _LOGGER.debug("%s - Auto TPI: Overshoot validation passed (gap_in=%.2f, power=%.1f%%) - proceeding with learning", self._name, gap_in, self.state.last_power * 100)

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
            _LOGGER.warning("%s - Auto TPI: Invalid new outdoor coeff: %.3f (non-finite or <= 0), skipping", self._name, coeff_new)
            self.state.last_learning_status = "invalid_outdoor_coeff"
            return False

        # Cap at 1.2 (Slightly relaxed to allow logic to work in extreme cases, but bounded)
        MAX_KEXT = 1.2
        if coeff_new > MAX_KEXT:
            _LOGGER.info("%s - Auto TPI: Calculated outdoor coeff %.3f > %.1f, capping to %.1f before averaging", self._name, coeff_new, MAX_KEXT, MAX_KEXT)
            coeff_new = MAX_KEXT

        count = self.state.coeff_outdoor_cool_autolearn if is_cool else self.state.coeff_outdoor_autolearn
        old_coeff = current_outdoor

        # Apply EMA or average
        effective_count = min(count, 50)

        if self._calculation_method == "average":
            weight_old = max(effective_count, 1)  # Same as _learn_indoor
            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Outdoor Weighted Average: old=%.3f (weight=%d, real_count=%d), new=%.3f, result=%.3f", self._name, old_coeff, weight_old, count, coeff_new, avg_coeff)
        else:  # EMA
            alpha = self._get_adaptive_alpha(effective_count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: Outdoor EMA: old=%.3f, new=%.3f, alpha=%.3f (eff_count=%d, real_count=%d), result=%.3f", self._name, old_coeff, coeff_new, alpha, effective_count, count, avg_coeff)

        new_count = count + 1

        # We only cap if continuous learning is OFF, and we want to stop learning
        if not self._continuous_learning:
            # The standard threshold is 50 + initial weight
            INT_CYCLES_THRESHOLD = 50 + self._avg_initial_weight

            indoor_autolearn_count = self.state.coeff_indoor_cool_autolearn if is_cool else self.state.coeff_indoor_autolearn
            is_indoor_finished = indoor_autolearn_count >= INT_CYCLES_THRESHOLD

            #  Kext learning stops (capped at 50) ONLY if:
            # (kext_cycles >= 50) AND (not keep_ext_learning OR kint_cycles >= 50 + initial_weight).
            # This ensures Kext always learns a minimum of 50 cycles (Standard minimum).

            EXT_CYCLES_THRESHOLD = 50
            is_kext_standard_finished = count >= EXT_CYCLES_THRESHOLD

            # stop_learning_now is not used here, only for final persistence check

            # new_count is NOT capped anymore to reflect the real number of cycles
            pass  # No cap

        if is_cool:
            self.state.coeff_outdoor_cool = avg_coeff
            self.state.coeff_outdoor_cool_autolearn = new_count
        else:
            self.state.coeff_outdoor_heat = avg_coeff
            self.state.coeff_outdoor_autolearn = new_count

        _LOGGER.info(
            "%s - Auto TPI: Learn outdoor (%s). Old: %.3f, Correction: %.3f, Target: %.3f, Averaged: %.3f (count: %d)",
            self._name,
            "cool" if is_cool else "heat",
            old_coeff,
            correction,
            coeff_new,
            avg_coeff,
            new_count,
        )
        return True

    def _should_learn_capacity(self) -> bool:
        """Check if capacity learning should occur this cycle."""
        
        # Determine if we are in bootstrap
        in_bootstrap = (
            self.state.max_capacity_heat == 0 or 
            self.state.capacity_heat_learn_count < 3
        )

        # Baseline thresholds
        power_threshold = 0.80
        rise_threshold = 0.05
        min_gap = 1.0 if self.state.capacity_heat_learn_count < 3 else 0.3

        # Timeout Strategy: Force default capacity if bootstrap fails too many times
        if in_bootstrap:
            failures = self.state.bootstrap_failure_count
            
            if failures > 5:
                # Force exit bootstrap with conservative capacity
                _LOGGER.warning(
                    "%s - Bootstrap timeout after %d failures. Forcing default capacity 0.3°C/h and exiting bootstrap.", 
                    self._name, failures
                )
                self.state.max_capacity_heat = 0.3
                # We interpret this forced exit as having "learned" enough to stabilize
                # Setting count to 3 ensures we use alpha=0.15 (stabilized) for future updates
                self.state.capacity_heat_learn_count = 3
                self.state.bootstrap_failure_count = 0 # Reset counter
                
                # Persist default capacity to config
                if self._hass and self._hass.loop and not self._hass.loop.is_closed():
                    self._hass.async_create_task(
                        self.async_update_capacity_config(0.3, is_heat_mode=True)
                    )
                
                return False # Cycle handled (we set default), skip calculation logic for this cycle
        
        # Check Condition 1: Power
        if self.state.last_power < power_threshold:
            _LOGGER.debug(
                "%s - Not learning capacity: power too low (%.1f%% < %.0f%%)",
                self._name, self.state.last_power * 100, power_threshold * 100
            )
            if in_bootstrap:
                self.state.bootstrap_failure_count += 1
            return False
        
        # Condition 2: Significant rise
        real_rise = self._current_temp_in - self.state.last_temp_in
        if real_rise < rise_threshold:
            _LOGGER.debug(
                "%s - Not learning capacity: rise too small (%.3f < %.2f°C)",
                self._name, real_rise, rise_threshold
            )
            if in_bootstrap:
                self.state.bootstrap_failure_count += 1
            return False
        
        # Condition 3: Adequate gap (stricter during bootstrap)
        target_diff = self._current_target_temp - self.state.last_temp_in
        if target_diff < min_gap:
            _LOGGER.debug(
                "%s - Not learning capacity: gap too small (%.2f < %.1f°C)",
                self._name, target_diff, min_gap
            )
            # Note: We don't necessarily increment failure count for "small gap" 
            # as this is not a "failed attempt" to heat, but rather "no need to heat much".
            # But if we are in bootstrap, we WANT larger gaps. 
            # Let's be conservative and NOT increment here to avoid relaxing just because setpoint is close.
            return False
        
        return True

    def _learn_capacity(self, power: float, delta_t: float, rise: float, 
                      efficiency: float, k_ext: float) -> bool:
        """Learn heating capacity using simple EWMA with adiabatic correction.
        
        Inspired by regul2.py parameter estimation approach.
        
        Args:
            power: Heating power ratio (0-1)
            delta_t: Temperature gap (Tin - Tout) in °C
            rise: Observed temperature rise in °C
            efficiency: Cycle efficiency (0-1)
            k_ext: Current external coefficient
        
        Returns:
            True if capacity was updated, False if validation failed
        """
        # Calculate observed capacity (with thermal losses included)
        cycle_duration_h = self._cycle_min / 60.0
        # Check for division by zero
        if cycle_duration_h * efficiency <= 0:
            return False

        observed_capacity = rise / (cycle_duration_h * efficiency)
        
        # Adiabatic correction: add back the estimated losses
        # This decouples heating capacity from thermal losses
        adiabatic_capacity = observed_capacity + k_ext * delta_t
        
        # Basic validation (physical bounds)
        if adiabatic_capacity <= 0 or adiabatic_capacity > 20.0:
            _LOGGER.debug(
                "%s - Capacity measurement out of bounds: %.2f°C/h, skipping",
                self._name, adiabatic_capacity
            )
            return False
        
        # EWMA with adaptive alpha
        # Higher alpha at start for fast convergence, lower after for stability
        if self.state.capacity_heat_learn_count < 3:
            alpha = 0.4  # Fast convergence during bootstrap
        else:
            alpha = 0.15  # Stabilization after bootstrap
        
        # Update capacity
        if self.state.max_capacity_heat == 0:
            # First measurement
            self.state.max_capacity_heat = adiabatic_capacity
        else:
            # EWMA update
            self.state.max_capacity_heat = (
                (1 - alpha) * self.state.max_capacity_heat + 
                alpha * adiabatic_capacity
            )
        
        self.state.capacity_heat_learn_count += 1
        
        # Store in history for confidence calculation
        if not hasattr(self, '_capacity_history'):
            self._capacity_history = []
        self._capacity_history.append(self.state.max_capacity_heat)
        if len(self._capacity_history) > 10:
            self._capacity_history.pop(0)
        
        _LOGGER.info(
            "%s - Capacity learned: %.2f°C/h (count: %d, alpha: %.2f)",
            self._name, self.state.max_capacity_heat,
            self.state.capacity_heat_learn_count, alpha
        )

        # Reset failure count on success
        self.state.bootstrap_failure_count = 0
        
        if self._hass and self._hass.loop and not self._hass.loop.is_closed():
            self._hass.async_create_task(
                self.async_update_capacity_config(self.state.max_capacity_heat, is_heat_mode=True)
            )

        return True

    def _get_capacity_confidence(self) -> float:
        """Calculate capacity learning confidence based on CV (coefficient of variation).
        
        Similar to tau_reliability() in regul2.py.
        
        Returns:
            Confidence score from 0.0 (no confidence) to 1.0 (high confidence)
        """
        # Need minimum samples
        if self.state.capacity_heat_learn_count < 3:
            return 0.3
        
        # Need history
        if not hasattr(self, '_capacity_history'):
            self._capacity_history = []
            
        if len(self._capacity_history) < 3:
            return 0.5
        
        # Calculate coefficient of variation (CV)
        mean_cap = statistics.mean(self._capacity_history)
        if mean_cap <= 0:
            return 0.0
        
        std_cap = statistics.pstdev(self._capacity_history)
        cv = std_cap / mean_cap
        
        # Confidence decreases with CV
        # CV = 0.1 → confidence = 0.90
        # CV = 0.3 → confidence = 0.70
        # CV = 0.5 → confidence = 0.50
        # CV > 1.0 → confidence = 0.0
        confidence = max(0.0, min(1.0, 1.0 - cv))
        
        return confidence

    def _check_deboost(self, is_heat: bool, real_rise: float, adjusted_theoretical: float):
        """Check if we should reduce indoor coefficient after good performance."""
        # If we achieved more than expected, consider reducing coefficient
        if real_rise > adjusted_theoretical * 1.2:  # 20% overshoot
            
            DEBOOST_FACTOR = 0.95
            
            if is_heat:
                count = self.state.coeff_indoor_autolearn
                current_kint = self.state.coeff_indoor_heat
            else:
                count = self.state.coeff_indoor_cool_autolearn
                current_kint = self.state.coeff_indoor_cool
            
            # Calculate target Kint
            target_kint = current_kint * DEBOOST_FACTOR
            effective_count = min(count, 50)
            old = current_kint

            # Apply same weighting logic as Kext overshoot correction
            if self._calculation_method == "average":
                boosted_weight = max(1, int(effective_count / OVERSHOOT_CORRECTION_BOOST))
                new_kint = ((old * boosted_weight) + target_kint) / (boosted_weight + 1)
                _LOGGER.debug(
                    "%s - Deboost Kint (Average): old=%.4f, target=%.4f, weight=%d (boosted from %d), result=%.4f",
                    self._name, old, target_kint, boosted_weight, effective_count, new_kint
                )
            else:  # EMA
                base_alpha = self._get_adaptive_alpha(effective_count)
                boosted_alpha = min(base_alpha * OVERSHOOT_CORRECTION_BOOST, 0.3)
                new_kint = (old * (1.0 - boosted_alpha)) + (target_kint * boosted_alpha)
                _LOGGER.debug(
                    "%s - Deboost Kint (EMA): old=%.4f, target=%.4f, alpha=%.3f (boosted from %.3f), result=%.4f",
                    self._name, old, target_kint, boosted_alpha, base_alpha, new_kint
                )

            if is_heat:
                if old > self._default_coef_int:
                    self.state.coeff_indoor_heat = max(new_kint, self._default_coef_int)
                    _LOGGER.info("%s - Deboosting Kint heat: %.3f → %.3f (weighted)", self._name, old, self.state.coeff_indoor_heat)
            else:
                if old > self._default_coef_int:
                    self.state.coeff_indoor_cool = max(new_kint, self._default_coef_int)
                    _LOGGER.info("%s - Deboosting Kint cool: %.3f → %.3f (weighted)", self._name, old, self.state.coeff_indoor_cool)
            # Reset boost counter
            if hasattr(self.state, "consecutive_boosts"):
                self.state.consecutive_boosts = 0

    def _correct_kext_overshoot(self, overshoot: float, is_cool: bool) -> bool:
        """Aggressively reduce Kext when room is overshooting with significant power.

        This method is called when the room temperature exceeds the setpoint
        while heat is still being applied. This indicates Kext is too high.

        Args:
            overshoot: Temperature above setpoint (positive value) in °C
            is_cool: True if in cooling mode

        Returns:
            True if correction was applied, False otherwise
        """
        # Feature flag check
        if not self.state.allow_kext_overshoot:
            return False

        current_kext = self.state.coeff_outdoor_cool if is_cool else self.state.coeff_outdoor_heat
        current_kint = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat

        # Calculate delta_ext for the correction
        delta_ext = self.state.last_order - self._current_temp_out
        if abs(delta_ext) < 0.1:
            _LOGGER.debug("%s - Auto TPI: Cannot correct Kext overshoot - delta_ext too small (%.2f)", self._name, delta_ext)
            return False

        # Calculate how much Kext should be reduced
        # At setpoint, Power = Kext * delta_ext
        # To allow temperature to fall, we need to reduce power by at least: overshoot * Kint
        # So: needed_power_reduction = overshoot * Kint
        # And: needed_kext_reduction = needed_power_reduction / delta_ext
        needed_reduction = (overshoot * current_kint) / delta_ext

        # Target Kext that would produce correct power at setpoint
        target_kext = max(0.001, current_kext - needed_reduction)

        # Get base alpha for calculation
        count = self.state.coeff_outdoor_cool_autolearn if is_cool else self.state.coeff_outdoor_autolearn
        effective_count = min(count, 50)

        old_kext = current_kext

        if self._calculation_method == "average":
            # For average mode: reduce effective weight to give more influence to correction
            # Instead of weight = effective_count, use weight / OVERSHOOT_CORRECTION_BOOST
            boosted_weight = max(1, int(effective_count / OVERSHOOT_CORRECTION_BOOST))
            new_kext = ((old_kext * boosted_weight) + target_kext) / (boosted_weight + 1)
            _LOGGER.debug(
                "%s - Auto TPI: Overshoot correction (Average): old=%.4f, target=%.4f, weight=%d (boosted from %d), result=%.4f",
                self._name, old_kext, target_kext, boosted_weight, effective_count, new_kext
            )
        else:  # EMA
            # Use boosted alpha for faster correction
            base_alpha = self._get_adaptive_alpha(effective_count)
            boosted_alpha = min(base_alpha * OVERSHOOT_CORRECTION_BOOST, 0.3)
            new_kext = (old_kext * (1.0 - boosted_alpha)) + (target_kext * boosted_alpha)
            _LOGGER.debug(
                "%s - Auto TPI: Overshoot correction (EMA): old=%.4f, target=%.4f, alpha=%.3f (boosted from %.3f), result=%.4f",
                self._name, old_kext, target_kext, boosted_alpha, base_alpha, new_kext
            )

        # Ensure Kext doesn't go below minimum
        new_kext = max(0.001, new_kext)

        if is_cool:
            self.state.coeff_outdoor_cool = new_kext
        else:
            self.state.coeff_outdoor_heat = new_kext

        self.state.last_learning_status = "corrected_kext_overshoot"
        self._learning_just_completed = True

        _LOGGER.info(
            "%s - Auto TPI: Overshoot correction applied! Kext: %.4f -> %.4f (overshoot=%.2f°C, power=%.1f%%)",
            self._name, old_kext, new_kext, overshoot, self.state.last_power * 100
        )

        return True

    def _correct_kint_insufficient_rise(self, target_diff: float, temp_progress: float, is_cool: bool) -> bool:
        """Boost Kint when temperature stagnates despite significant gap to setpoint.

        This method is called when:
        - target_diff > INSUFFICIENT_RISE_GAP_THRESHOLD (0.3°C)
        - temp_progress < 0.02 (temperature stagnating)
        - power < 0.99 (not saturated)

        Instead of incorrectly adjusting Kext (which would happen in outdoor learning),
        we boost Kint to increase power output.

        Args:
            target_diff: The gap between setpoint and room temperature (positive value)
            temp_progress: Temperature change during the cycle (can be negative)
            is_cool: True if in cooling mode

        Returns:
            True if correction was applied, False otherwise
        """
        # Feature flag check
        if not self.state.allow_kint_boost:
            return False

        # Check if we've hit the max consecutive boosts limit
        if self.state.consecutive_boosts >= MAX_CONSECUTIVE_KINT_BOOSTS:
            _LOGGER.warning(
                "%s - Auto TPI: Kint boost skipped - max consecutive boosts (%d) reached. Possible undersized heating.",
                self._name, MAX_CONSECUTIVE_KINT_BOOSTS
            )
            self.state.last_learning_status = "max_kint_boosts_reached"
            # Send notification if enabled (only once per limit hit)
            if self._enable_notification and self.state.consecutive_boosts == MAX_CONSECUTIVE_KINT_BOOSTS:
                self._hass.async_create_task(self._notify_undersized_heating())
            return False

        current_kint = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat

        # Calculate proportional boost based on gap size
        # Base boost is 8%, but increases slightly with larger gaps
        # For gap = 0.3°C: boost = 8%, for gap = 0.6°C: boost ≈ 10%
        gap_factor = min(target_diff / INSUFFICIENT_RISE_GAP_THRESHOLD, 2.0)  # Cap at 2x
        base_boost_percent = (INSUFFICIENT_RISE_BOOST_FACTOR - 1.0) * gap_factor
        
        target_kint = current_kint * (1.0 + base_boost_percent)
        
        count = self.state.coeff_indoor_cool_autolearn if is_cool else self.state.coeff_indoor_autolearn
        effective_count = min(count, 50)
        old_kint = current_kint

        # Apply same weighting logic as Kext overshoot correction
        if self._calculation_method == "average":
            boosted_weight = max(1, int(effective_count / OVERSHOOT_CORRECTION_BOOST))
            new_kint = ((old_kint * boosted_weight) + target_kint) / (boosted_weight + 1)
            _LOGGER.debug(
                "%s - Boost Kint (Average): old=%.4f, target=%.4f, weight=%d (boosted from %d), result=%.4f",
                self._name, old_kint, target_kint, boosted_weight, effective_count, new_kint
            )
        else:  # EMA
            base_alpha = self._get_adaptive_alpha(effective_count)
            boosted_alpha = min(base_alpha * OVERSHOOT_CORRECTION_BOOST, 0.3)
            new_kint = (old_kint * (1.0 - boosted_alpha)) + (target_kint * boosted_alpha)
            _LOGGER.debug(
                "%s - Boost Kint (EMA): old=%.4f, target=%.4f, alpha=%.3f (boosted from %.3f), result=%.4f",
                self._name, old_kint, target_kint, boosted_alpha, base_alpha, new_kint
            )

        # Cap to max coefficient
        new_kint = min(new_kint, self._max_coef_int)

        # Ensure minimum Kint
        new_kint = max(new_kint, MIN_KINT)

        # Check if we actually changed anything (might hit cap)
        if abs(new_kint - current_kint) < 0.001:
            _LOGGER.debug(
                "%s - Auto TPI: Kint correction skipped - already at limit (current=%.3f, max=%.3f)",
                self._name, current_kint, self._max_coef_int
            )
            return False

        old_kint = current_kint

        if is_cool:
            self.state.coeff_indoor_cool = new_kint
        else:
            self.state.coeff_indoor_heat = new_kint

        self.state.last_learning_status = "corrected_kint_insufficient_rise"
        self._learning_just_completed = True

        _LOGGER.info(
            "%s - Auto TPI: Kint correction applied! Kint: %.4f -> %.4f (gap=%.2f°C, progress=%.2f°C, power=%.1f%%, boost #%d)",
            self._name, old_kint, new_kint, target_diff, temp_progress, self.state.last_power * 100, self.state.consecutive_boosts + 1
        )

        # Increment consecutive boosts counter
        self.state.consecutive_boosts += 1

        return True

    async def _notify_undersized_heating(self):
        """Send notification when max consecutive Kint boosts is reached."""
        title = f"Versatile Thermostat: Auto TPI Warning for {self._name}"
        message = (
            f"Auto TPI has reached the maximum consecutive Kint boost limit ({MAX_CONSECUTIVE_KINT_BOOSTS}). "
            f"The temperature is not rising despite increased power demand. "
            f"This may indicate undersized heating or abnormal heat loss. "
            f"Learning will continue normally, but Kint boosting is paused until external temperature rises."
        )

        try:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"autotpi_undersized_heating_{self._unique_id}",
                },
                blocking=False,
            )
            _LOGGER.warning("%s - Auto TPI: Undersized heating notification sent.", self._name)
        except Exception as e:
            _LOGGER.error("%s - Auto TPI: Error sending undersized heating notification: %s", self._name, e)

    async def _detect_failures(self, current_temp_in: float):
        """Detect system failures."""
        OFFSET_FAILURE = 1.0
        MIN_LEARN_FOR_DETECTION = 25

        failure_detected = False
        reason = "unknown"

        if (
            self.state.last_state == "heat"
            and self.state.last_power >= self.saturation_threshold
            and current_temp_in < self.state.last_order - OFFSET_FAILURE
            and current_temp_in < self.state.last_temp_in
            and self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION
        ):
            failure_detected = True
            reason = "Temperature dropped while heating at full power"
            _LOGGER.warning("%s - Auto TPI: Failure detected in HEAT mode at saturation (power=%.1f%%)", self._name, self.state.last_power * 100)

        elif (
            self.state.last_state == "cool"
            and self.state.last_power >= self.saturation_threshold
            and current_temp_in > self.state.last_order + OFFSET_FAILURE
            and current_temp_in > self.state.last_temp_in
            and self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION
        ):
            failure_detected = True
            reason = "Temperature rose while cooling at full power"
            _LOGGER.warning("%s - Auto TPI: Failure detected in COOL mode at saturation (power=%.1f%%)", self._name, self.state.last_power * 100)

        if failure_detected:
            self.state.consecutive_failures += 1
            if self.state.consecutive_failures >= 3:
                if self._continuous_learning:
                    # In continuous learning mode, don't stop learning - just skip faulty cycles
                    _LOGGER.warning(
                        "%s - Auto TPI: %d consecutive failures detected in continuous mode. "
                        "Skipping faulty cycles and continuing learning. Reason: %s",
                        self._name,
                        self.state.consecutive_failures,
                        reason,
                    )
                    # Reset the counter to allow future failure detection
                    self.state.consecutive_failures = 0
                else:
                    # Standard mode: disable learning after 3 consecutive failures
                    self.state.autolearn_enabled = False
                    _LOGGER.error(
                        "%s - Auto TPI: Learning disabled due to %d consecutive failures.",
                        self._name,
                        self.state.consecutive_failures,
                    )

                    # Send persistent notification
                    # Retrieve the message from translations
                    # We use the "exceptions" category in strings.json
                    # The key is "component.versatile_thermostat.exceptions.auto_tpi_learning_stopped.message"
                    title = "Versatile Thermostat: Auto TPI Learning Stopped"
                    try:
                        translations = await translation.async_get_translations(
                            self._hass, 
                            self._hass.config.language, 
                            "exceptions", 
                            {DOMAIN}
                        )

                        # Key format for exceptions: component.{domain}.exceptions.{key}.message
                        key = f"component.{DOMAIN}.exceptions.auto_tpi_learning_stopped.message"
                        message_template = translations.get(key)

                        if message_template:
                            message = message_template.format(name=self._name, reason=reason)
                        else:
                            # Fallback if translation not found
                            message = f"Auto TPI learning for {self._name} has been stopped due to 3 consecutive failures. Reason: {reason}. Please check your configuration."

                        await self._hass.services.async_call(
                            "persistent_notification",
                            "create",
                            {
                                "title": title,
                                "message": message,
                                "notification_id": f"autotpi_learning_stopped_{self._unique_id}",
                            },
                            blocking=False,
                        )
                    except Exception as e:
                        _LOGGER.error("%s - Auto TPI: Error sending persistent notification: %s", self._name, e)

        else:
            self.state.consecutive_failures = 0

    @property
    def saturation_threshold(self) -> float:
        """The saturation power threshold (default 1.0, 100%)."""
        # This property is expected to be overridden by the mixing/main component.
        # Defaulting to 1.0 for self-contained use if not overridden.
        return 1.0

    def calculate_power(self, setpoint: float, temp_in: float, temp_out: float, state_str: str) -> float:
        """Calculate TPI power, using aggressive coefficients during bootstrap."""
        
        # Bootstrap logic: aggressive coefficients
        in_bootstrap = (
            state_str == "heat" and
            (self.state.max_capacity_heat == 0 or self.state.capacity_heat_learn_count < 3)
        )
        
        saved_kint = self.state.coeff_indoor_heat
        saved_kext = self.state.coeff_outdoor_heat
        
        if in_bootstrap:
            self.state.coeff_indoor_heat = 1.0
            self.state.coeff_outdoor_heat = 0.1
            
        try:
            return self._calculate_power_tpi(setpoint, temp_in, temp_out, state_str)
        finally:
            if in_bootstrap:
                 self.state.coeff_indoor_heat = saved_kint
                 self.state.coeff_outdoor_heat = saved_kext
    
    def _calculate_power_tpi(self, setpoint: float, temp_in: float, temp_out: float, state_str: str) -> float:
        """Normal TPI proportional control."""
        if temp_out is None:
            return 0.0
        
        direction = 1 if state_str == "heat" else -1
        delta_in = setpoint - temp_in
        delta_out = setpoint - temp_out

        if state_str == "cool":
            coeff_int = self.state.coeff_indoor_cool
            coeff_ext = self.state.coeff_outdoor_cool
        else:
            coeff_int = self.state.coeff_indoor_heat
            coeff_ext = self.state.coeff_outdoor_heat

        offset = self.state.offset
        power = (direction * delta_in * coeff_int) + (direction * delta_out * coeff_ext) + offset
        return max(0.0, min(1.0, power))

    @staticmethod
    def _remove_outliers_iqr(values: list[float]) -> list[float]:
        """
        Remove outliers using Interquartile Range (IQR) method.
        Keeps values within [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
        """
        if len(values) < 4:
            return values

        sorted_values = sorted(values)
        n = len(sorted_values)

        q1_idx = n // 4
        q3_idx = (3 * n) // 4

        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        return [v for v in values if lower_bound <= v <= upper_bound]

    def _interpolate_power_at(self, target_dt: datetime, power_history: list, start_idx: int = 0, tolerance_seconds: float = 120.0) -> tuple[Optional[float], int]:
        """
        Find the power value closest to target_dt within tolerance.
        Returns a tuple (power percentage, next index to search from).
        Optimization: Assumes power_history is sorted by time.
        """
        if not power_history:
            return None, 0

        best_idx = -1
        closest_diff = float("inf")

        # We start searching from start_idx to keep O(N+M) complexity
        for i in range(start_idx, len(power_history)):
            state = power_history[i]
            try:
                state_dt = state.last_changed
                diff = (state_dt - target_dt).total_seconds()
                abs_diff = abs(diff)

                if abs_diff <= tolerance_seconds:
                    if abs_diff < closest_diff:
                        closest_diff = abs_diff
                        best_idx = i

                # If we passed the target_dt by more than tolerance,
                # and we already found something or the diff is increasing, we can stop.
                if diff > tolerance_seconds:
                    break

            except (AttributeError, TypeError):
                continue

        if best_idx == -1:
            # If we didn't find anything but we are moving forward in time,
            # we should still return the current start_idx for the next call
            # unless we find that slope_dt is already way ahead of power_history.
            return None, start_idx

        try:
            state_value = getattr(power_history[best_idx], "state", None)
            if state_value in ["unknown", "unavailable", None]:
                return None, best_idx
            return float(state_value), best_idx
        except (ValueError, TypeError):
            return None, best_idx

    async def calculate_capacity_from_slope_sensor(
        self,
        slope_history: list,
        power_history: list,
        min_power_threshold: float = 0.95,
        kext_coeff: float = 0.0,
        current_indoor_temp: Optional[float] = None,
        current_outdoor_temp: Optional[float] = None,
    ) -> dict:
        """
        Calculate ADIABATIC capacity using temperature_slope and power_percent sensor histories.

        ALGORITHM:
        1. Match slope points with power values at the same time
        2. Keep points where power >= threshold AND slope direction is correct
        3. Remove outliers using IQR method
        4. Use 75th percentile (biases toward higher/adiabatic values)
        5. Add Kext compensation: capacity = percentile_75 + Kext × avg_delta_T

        Args:
            slope_history: History of temperature_slope sensor
            power_history: History of power_percent sensor
            min_power_threshold: Minimum power (0.0-1.0) to consider. Default 0.95 (95%)
            kext_coeff: Current Kext coefficient for adiabatic correction
            current_indoor_temp: Current indoor temperature for delta_T estimation
            current_outdoor_temp: Current outdoor temperature for delta_T estimation

        Returns:
            Dictionary with adiabatic capacity result and metrics
        """
        # Always True now
        is_heat_mode = True
        power_threshold_percent = min_power_threshold * 100.0

        _LOGGER.debug(
            "%s - Capacity Calibration: Analyzing %d slope points and %d power points (threshold=%.0f%%)",
            self._name,
            len(slope_history) if slope_history else 0,
            len(power_history) if power_history else 0,
            power_threshold_percent,
        )

        if not slope_history:
            return {"success": False, "error": "No temperature slope history found", "samples_used": 0}

        if not power_history:
            return {"success": False, "error": "No power percent history found", "samples_used": 0}

        # Collect valid slope values
        raw_slopes = []
        rejected_low_power = 0
        rejected_wrong_direction = 0
        rejected_invalid = 0

        # Sort histories by time to enable O(N+M) matching
        sorted_slopes = sorted(slope_history, key=lambda s: s.last_changed)
        sorted_power = sorted(power_history, key=lambda s: s.last_changed)

        power_idx = 0
        for slope_state in sorted_slopes:
            try:
                slope_dt = slope_state.last_changed
                slope_str = getattr(slope_state, "state", None)

                if slope_str in ["unknown", "unavailable", None]:
                    rejected_invalid += 1
                    continue

                slope_value = float(slope_str)

                # Find closest power value using optimized matching
                power, power_idx = self._interpolate_power_at(slope_dt, sorted_power, start_idx=power_idx)

                if power is None:
                    rejected_invalid += 1
                    continue

                # Check power threshold
                if power < power_threshold_percent:
                    rejected_low_power += 1
                    continue

                # Check slope direction (always heating check now)
                if slope_value <= 0:
                    rejected_wrong_direction += 1
                    continue

                raw_slopes.append(slope_value)

            except (ValueError, TypeError, AttributeError) as e:
                _LOGGER.debug("%s - Capacity Calibration: Invalid slope state: %s", self._name, e)
                rejected_invalid += 1
                continue

        _LOGGER.info(
            "%s - Capacity Calibration: Found %d valid samples (rejected: %d low-power, %d wrong-direction, %d invalid)",
            self._name,
            len(raw_slopes),
            rejected_low_power,
            rejected_wrong_direction,
            rejected_invalid,
        )

        if len(raw_slopes) < 2:
            return {
                "success": False,
                "error": f"Not enough valid samples ({len(raw_slopes)} found, minimum 2 required)",
                "samples_used": len(raw_slopes),
                "rejection_stats": {"low_power": rejected_low_power, "wrong_direction": rejected_wrong_direction, "invalid": rejected_invalid},
            }

        # Remove outliers
        filtered_slopes = self._remove_outliers_iqr(raw_slopes)
        outliers_removed = len(raw_slopes) - len(filtered_slopes)

        _LOGGER.debug("%s - Capacity Calibration: Removed %d outliers, %d samples remaining", self._name, outliers_removed, len(filtered_slopes))

        if len(filtered_slopes) < 2:
            return {
                "success": False,
                "error": f"Not enough samples after outlier removal ({len(filtered_slopes)} remaining)",
                "samples_used": len(filtered_slopes),
                "samples_before_filter": len(raw_slopes),
            }

        # Calculate 75th percentile (biases toward adiabatic - higher values)
        # Higher slopes = less heat loss = closer to adiabatic
        sorted_slopes = sorted(filtered_slopes)
        n = len(sorted_slopes)

        # 75th percentile index
        p75_idx = int(0.75 * (n - 1))
        observed_capacity = sorted_slopes[p75_idx]

        # Estimate average delta_T for Kext compensation
        # When power is at 100%, we typically have a significant delta_T
        # Use current temperatures if available, otherwise use typical value
        if current_indoor_temp is not None and current_outdoor_temp is not None:
            avg_delta_t = abs(current_indoor_temp - current_outdoor_temp)
        else:
            # Typical delta_T when heating at high power (rough estimate: 10-15°C)
            avg_delta_t = 12.0  # Conservative estimate

        # Apply Kext compensation for adiabatic capacity
        # Capacity_adiabatic = Slope_observed + Kext × delta_T
        kext_compensation = kext_coeff * avg_delta_t
        capacity = observed_capacity + kext_compensation

        _LOGGER.debug(
            "%s - Capacity Calibration: 75th percentile=%.3f, Kext=%.4f, delta_T=%.1f, compensation=%.3f, final=%.3f",
            self._name,
            observed_capacity,
            kext_coeff,
            avg_delta_t,
            kext_compensation,
            capacity,
        )

        # Ensure capacity is positive
        if capacity <= 0.0:
            _LOGGER.warning("%s - Capacity Calibration: Calculated capacity (%.3f) is not positive. Setting to 0.01.", self._name, capacity)
            capacity = 0.01

        # Calculate reliability based on sample count and variance
        mean_slope = sum(filtered_slopes) / len(filtered_slopes)
        variance = sum((s - mean_slope) ** 2 for s in filtered_slopes) / len(filtered_slopes)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0
        cv = std_dev / mean_slope if mean_slope > 0 else 0.0  # Coefficient of variation

        # Reliability: higher with more samples and lower variance
        sample_factor = min(1.0, len(filtered_slopes) / 20.0)  # Max at 20 samples
        variance_factor = max(0.0, 1.0 - (cv / 2.0))  # Lower if high variance
        reliability = 100.0 * sample_factor * variance_factor

        # Period calculation (in days)
        period_days = 0.0
        if slope_history:
            try:
                timestamps = [s.last_changed for s in slope_history]
                if timestamps:
                    start_date = min(timestamps)
                    end_date = max(timestamps)
                    period_days = (end_date - start_date).total_seconds() / 86400.0
            except (AttributeError, TypeError):
                pass

        _LOGGER.info(
            "%s - Capacity Calibration: Adiabatic Capacity=%.3f °C/h (observed=%.3f + Kext×ΔT=%.3f), Reliability=%.1f%%, Samples=%d",
            self._name,
            capacity,
            observed_capacity,
            kext_compensation,
            reliability,
            len(filtered_slopes),
        )

        return {
            "success": True,
            "capacity": round(capacity, 3),
            "observed_capacity": round(observed_capacity, 3),
            "kext_compensation": round(kext_compensation, 3),
            "avg_delta_t": round(avg_delta_t, 1),
            "samples_used": len(filtered_slopes),
            "samples_before_filter": len(raw_slopes),
            "outliers_removed": outliers_removed,
            "reliability": round(reliability, 1),
            "min_power_threshold": min_power_threshold,
            "period": round(period_days, 1),
        }

    async def service_calibrate_capacity(
        self,
        thermostat_entity_id: str,
        ext_temp_entity_id: str,
        save_to_config: bool,
        min_power_threshold: float,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
        capacity_safety_margin: float | None = None,
    ) -> dict:
        """
        Orchestrates the capacity calibration service using temperature_slope
        and power_percent sensor histories.

        NEW ALGORITHM:
        1. Derives slope and power sensor entity IDs from thermostat entity ID
        2. Fetches history for both sensors
        3. Matches points where power >= threshold and slope direction is correct
        4. Removes outliers and calculates median as Capacity

        Args:
            thermostat_entity_id: The climate entity ID (e.g., "climate.thermostat_salon")
            ext_temp_entity_id: External temperature sensor (unused in new algorithm but kept for API compatibility)
            save_to_config: Whether to save the result to config
            start_date: Start of history period (default: 30 days ago)
            end_date: End of history period (default: now)
            min_power_threshold: Minimum power percentage (0.0-1.0) to consider a sample.
                                 Default is 1.0 (100%). Lower values (e.g., 0.90) include more samples.
            capacity_safety_margin: Margin percentage (0.0-1.0) to subtract from the calculated capacity.
                                    Default is None (0%).
        """
        # 1. Derive sensor entity IDs from thermostat entity ID
        # climate.thermostat_salon -> sensor.thermostat_salon_temperature_slope
        # climate.thermostat_salon -> sensor.thermostat_salon_power_percent
        if thermostat_entity_id.startswith("climate."):
            base_name = thermostat_entity_id.replace("climate.", "")
        else:
            base_name = thermostat_entity_id.split(".")[-1]

        slope_sensor_id = f"sensor.{base_name}_temperature_slope"
        power_sensor_id = f"sensor.{base_name}_power_percent"

        _LOGGER.info("%s - Capacity calibration: Using slope sensor '%s' and power sensor '%s'", self._name, slope_sensor_id, power_sensor_id)

        # 2. Convert start_date and end_date to datetime objects
        if isinstance(start_date, str):
            _date = dt_util.parse_date(start_date)
            start_date = dt_util.start_of_local_day(_date) if _date else None

        if isinstance(end_date, str):
            _date = dt_util.parse_date(end_date)
            _end_day_start = dt_util.start_of_local_day(_date) if _date else None
            end_date = _end_day_start + timedelta(days=1) if _end_day_start else None

        # 3. Determine History Time Range
        now = dt_util.now()
        start_time = dt_util.as_utc(start_date) if start_date is not None else now - timedelta(days=30)
        end_time = dt_util.as_utc(end_date) if end_date is not None else now

        _LOGGER.info("%s - Calibrating capacity using history from %s to %s", self._name, start_time, end_time)

        # Handle percentage value for min_power_threshold (e.g. 95 -> 0.95)
        if min_power_threshold > 1.0:
            _LOGGER.debug("%s - Converting min_power_threshold from %.1f to %.2f", self._name, min_power_threshold, min_power_threshold / 100.0)
            min_power_threshold = min_power_threshold / 100.0

        # 4. Fetch sensor histories in chunks to avoid timeouts and cope with gaps
        entity_ids = [slope_sensor_id, power_sensor_id]
        slope_history = []
        power_history = []

        # We use 2-day chunks for robustness
        chunk_delta = timedelta(days=2)
        current_start = start_time

        while current_start < end_time:
            current_end = min(current_start + chunk_delta, end_time)
            _LOGGER.debug("%s - Fetching history chunk from %s to %s", self._name, current_start, current_end)

            try:
                chunk_states = await get_instance(self._hass).async_add_executor_job(
                    partial(
                        history.get_significant_states,
                        self._hass,
                        current_start,
                        end_time=current_end,
                        entity_ids=entity_ids,
                        significant_changes_only=False,
                    )
                )

                if chunk_states:
                    slope_history.extend(chunk_states.get(slope_sensor_id, []))
                    power_history.extend(chunk_states.get(power_sensor_id, []))

            except Exception as e:
                _LOGGER.warning("%s - Error fetching history chunk %s to %s: %s", self._name, current_start, current_end, e)

            current_start = current_end

        _LOGGER.debug("%s - Fetched %d slope sensor states and %d power sensor states for capacity calibration.", self._name, len(slope_history), len(power_history))

        # Check if sensors exist
        if not slope_history:
            _LOGGER.warning("%s - No history found for slope sensor '%s'. " "Make sure the sensor exists and has history enabled in recorder.", self._name, slope_sensor_id)
        if not power_history:
            _LOGGER.warning("%s - No history found for power sensor '%s'. " "Make sure the sensor exists and has history enabled in recorder.", self._name, power_sensor_id)

        # 5. Get Kext from HA config (not learned value) for adiabatic correction
        kext_coeff = self._default_coef_ext

        # Get current temperatures from thermostat for delta_T estimation
        current_indoor_temp = None
        current_outdoor_temp = None

        # Try to get current thermostat state for indoor temp
        thermostat_state = self._hass.states.get(thermostat_entity_id)
        if thermostat_state:
            try:
                current_indoor_temp = float(thermostat_state.attributes.get("current_temperature", 0))
            except (ValueError, TypeError):
                pass

        # Try to get outdoor temp from the external sensor
        if ext_temp_entity_id:
            outdoor_state = self._hass.states.get(ext_temp_entity_id)
            if outdoor_state and outdoor_state.state not in ["unknown", "unavailable"]:
                try:
                    current_outdoor_temp = float(outdoor_state.state)
                except (ValueError, TypeError):
                    pass

        _LOGGER.debug(
            "%s - Adiabatic correction params: Kext_config=%.4f, T_indoor=%.1f, T_outdoor=%.1f",
            self._name,
            kext_coeff,
            current_indoor_temp if current_indoor_temp else 0,
            current_outdoor_temp if current_outdoor_temp else 0,
        )

        # 6. Call calculation method with adiabatic correction
        result = await self.calculate_capacity_from_slope_sensor(
            slope_history,
            power_history,
            min_power_threshold=min_power_threshold,
            kext_coeff=kext_coeff,
            current_indoor_temp=current_indoor_temp,
            current_outdoor_temp=current_outdoor_temp,
        )

        _LOGGER.info("%s - Capacity calibration result: %s", self._name, result)

        # 6. Save to config if requested
        if result and isinstance(result, dict) and result.get("success"):

            max_capacity = result.get("capacity")
            # Calculate recommended capacity with margin
            if max_capacity is not None:
                # Ensure margin is valid (0-0.30)
                # capacity_safety_margin is required (defaults to 20 in services.yaml)
                # If None, we default to 0.20 (20%)

                if capacity_safety_margin is None:
                    margin = 0.20
                else:
                    # Handle percentage input (e.g. 20 -> 0.20)
                    # We assume if value > 1.0 it is a percentage (0-30)
                    val = capacity_safety_margin / 100.0 if capacity_safety_margin > 1.0 else capacity_safety_margin
                    margin = max(0.0, min(0.30, val))

                recommended_capacity = max_capacity * (1.0 - margin)

                # Rename capacity to max_capacity
                if "capacity" in result:
                    del result["capacity"]

                result["max_capacity"] = max_capacity
                result["recommended_capacity"] = recommended_capacity
                result["margin_percent"] = margin * 100

                # Update the displayed capacity in the result to be the recommended one or make it clear
                # The prompt asks: "The servcice output shoud display the max capacity , and the recommended capacity"
                # We add them to the dict.

                if save_to_config:
                    # Always heat mode
                    is_heat_mode = True

                    await self.async_update_capacity_config(capacity=recommended_capacity, is_heat_mode=is_heat_mode)

                    _LOGGER.info(
                        "%s - Heating capacity calibrated. Max: %.3f °C/h, Margin: %.0f%%, Saved: %.3f °C/h", 
                        self._name, max_capacity, margin * 100, recommended_capacity
                    )

        return result

    async def on_cycle_started(self, on_time_sec: float, off_time_sec: float, on_percent: float, hvac_mode: str):
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

        _LOGGER.debug("%s - Auto TPI: Cycle started. On: %.0fs, Off: %.0fs (%.1f%%), Mode: %s", self._name, on_time_sec, off_time_sec, on_percent * 100, hvac_mode)

        now = datetime.now()

        # Snapshot current state for learning at the end of the cycle
        self.state.last_temp_in = self._current_temp_in
        self.state.last_temp_out = self._current_temp_out
        self.state.last_order = self._current_target_temp
        self.state.last_power = on_percent if on_percent is not None else 0.0
        self.state.last_on_temp_in = 0.0  # Reset

        # Save previous state before updating last_state (for first cycle detection)
        self.state.previous_state = self.state.last_state

        # Map VThermHvacMode/HVACMode to internal state string
        # hvac_mode is expected to be VThermHvacMode or string representation
        mode_str = str(hvac_mode)
        if mode_str == "heat" or mode_str == "heating":
            self.state.last_state = "heat"
        elif mode_str == "cool" or mode_str == "cooling":
            self.state.last_state = "cool"
        else:
            self.state.last_state = "stop"

        self.state.cycle_start_date = now
        self.state.last_update_date = now

        # Schedule capture of temperature at the end of the ON pulse
        if on_time_sec > 0:
            self._timer_capture_remove_callback = async_call_later(self._hass, on_time_sec, self._capture_end_of_on_temp)

        # Calculate cold factor for this cycle
        self.state.current_cycle_cold_factor = 0.0
        if self._heater_cooling_time > 0 and self.state.last_heater_stop_time:
            elapsed_off = (now - self.state.last_heater_stop_time).total_seconds() / 60.0
            if elapsed_off >= 0:
                self.state.current_cycle_cold_factor = min(1.0, max(0.0, elapsed_off / self._heater_cooling_time))
                _LOGGER.debug(
                    "%s - Auto TPI: Cold factor calc: elapsed_off=%.1f min, cooling_time=%.1f min, factor=%.2f",
                    self._name,
                    elapsed_off,
                    self._heater_cooling_time,
                    self.state.current_cycle_cold_factor,
                )

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
        if self.state.last_state == "heat":
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

            _LOGGER.debug(
                "%s - Auto TPI: Power Efficiency calc: on_time=%.1f min, warm_up_time=%.1f, cold_factor=%.2f, eff_warm_up_time=%.1f, eff=%.2f",
                self._name,
                on_time_minutes,
                self._heater_heating_time,
                self.state.current_cycle_cold_factor,
                effective_warm_up_time,
                self._last_cycle_power_efficiency,
            )

        if self.learning_active:
            _LOGGER.info(
                "%s - Auto TPI: Cycle #%d completed after %.1f minutes (efficiency: %.2f)", self._name, self.state.total_cycles, elapsed_minutes, self._last_cycle_power_efficiency
            )
        else:
            _LOGGER.debug(
                "%s - Auto TPI: Cycle #%d completed after %.1f minutes (efficiency: %.2f)", self._name, self.state.total_cycles, elapsed_minutes, self._last_cycle_power_efficiency
            )

        # Attempt learning
        # Determine if in bootstrap
        in_bootstrap = (
            self._current_hvac_mode == "heat" and
            (self.state.max_capacity_heat == 0 or self.state.capacity_heat_learn_count < 3)
        )
        # Check if cycle is significant enough for learning
        # Significant if we had some effective heating time (efficiency > 0)
        is_significant_cycle = self._last_cycle_power_efficiency > 0.0

        if in_bootstrap:
            # During bootstrap: learn ONLY capacity, skip Kint/Kext
            # Calculate real_rise and efficiency locally for use here
            real_rise = self._current_temp_in - self.state.last_temp_in
            efficiency = self._last_cycle_power_efficiency
            
            if self._should_learn_capacity():
                learned = self._learn_capacity(
                    power=self.state.last_power,
                    delta_t=self._current_temp_in - self._current_temp_out,
                    rise=real_rise,
                    efficiency=efficiency,
                    k_ext=self.state.coeff_outdoor_heat
                )
                if learned:
                    _LOGGER.info(
                        "%s - Bootstrap cycle %d/%d completed, capacity: %.2f°C/h",
                        self._name,
                        self.state.capacity_heat_learn_count,
                        3,
                        self.state.max_capacity_heat
                    )
        
        elif self._should_learn() and is_significant_cycle:
            # NORMAL TPI MODE: Learn everything
            # After bootstrap: normal learning (capacity + Kint/Kext)
            _LOGGER.info("%s - Auto TPI: Attempting to learn from cycle data", self._name)
            await self._perform_learning(self._current_temp_in, self._current_temp_out)
        else:
            reason = self._get_no_learn_reason()
            if not is_significant_cycle and reason == "unknown":
                reason = "on_time_too_short_vs_heating_time"

            _LOGGER.debug("%s - Auto TPI: Not learning this cycle: %s", self._name, reason)
            self.state.last_learning_status = reason

        # Check for failures
        await self._detect_failures(self._current_temp_in)

        # The Max Capacity detection logic has been removed as capacity is now set by service.
        await self.async_save_data()
    


    def get_calculated_params(self) -> dict:
        return self._calculated_params

    @property
    def is_in_bootstrap(self) -> bool:
        """Return True if the algorithm is in bootstrap mode (learning capacity)."""
        return (
            self.state.max_capacity_heat == 0 or 
            self.state.capacity_heat_learn_count < 3
        )

    @property
    def learning_active(self) -> bool:
        return self.state.autolearn_enabled

    @property
    def int_cycles(self) -> int:
        """Number of ACTUAL learning cycles completed for internal coefficient"""
        is_cool_mode = self._current_hvac_mode == "cool"
        if is_cool_mode:
            return max(0, self.state.coeff_indoor_cool_autolearn - self._avg_initial_weight)
        return max(0, self.state.coeff_indoor_autolearn - self._avg_initial_weight)

    @property
    def ext_cycles(self) -> int:
        """Number of learning cycles completed for external coefficient"""
        is_cool_mode = self._current_hvac_mode == "cool"
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
        confidence_ext = min(ext_cycles, 50) / 50.0

        cycle_confidence = (confidence_int + confidence_ext) / 2.0

        if self.state.consecutive_failures > 0:
            failure_penalty = min(self.state.consecutive_failures * 0.15, 0.6)
            cycle_confidence = max(0.2, cycle_confidence - failure_penalty)

        return round(cycle_confidence, 2)

    async def start_learning(
        self,
        coef_int: float = None,
        coef_ext: float = None,
        reset_data: bool = True,
        allow_kint_boost: bool = True,
        allow_kext_overshoot: bool = False,
    ):
        """Start learning, optionally resetting coefficients and learning data.

        Args:
            coef_int: Target internal coefficient (defaults to configured value)
            coef_ext: Target external coefficient (defaults to configured value)
            reset_data: If True, reset all learning data; if False, resume with existing data
            allow_kint_boost: Enable Kint boost on stagnation
            allow_kext_overshoot: Enable Kext compensation on overshoot
        """
        # Update optional flags immediately (even if not resetting data)
        self.state.allow_kint_boost = allow_kint_boost
        self.state.allow_kext_overshoot = allow_kext_overshoot
        _LOGGER.info(
            "%s - Auto TPI: Optional parameters set: allow_kint_boost=%s, allow_kext_overshoot=%s",
            self._name, allow_kint_boost, allow_kext_overshoot
        )

        # Use provided values, or fallback to default (configured) values
        target_int = coef_int if coef_int is not None else self._default_coef_int
        target_ext = coef_ext if coef_ext is not None else self._default_coef_ext

        if reset_data:
            _LOGGER.info("%s - Auto TPI: Starting learning with coef_int=%.3f, coef_ext=%.3f (resetting all data)", self._name, target_int, target_ext)

            # Reset coefficients to target values
            self.state.coeff_indoor_heat = target_int
            self.state.coeff_indoor_cool = target_int
            self.state.coeff_outdoor_heat = target_ext
            self.state.coeff_outdoor_cool = target_ext

            # Reset all counters
            self.state.coeff_indoor_autolearn = self._avg_initial_weight
            self.state.coeff_outdoor_autolearn = 0
            self.state.coeff_indoor_cool_autolearn = self._avg_initial_weight
            self.state.coeff_outdoor_cool_autolearn = 0

            # Reset all learning data for fresh start
            self.state.last_power = 0.0
            self.state.last_order = 0.0
            self.state.last_temp_in = 0.0
            self.state.last_temp_out = 0.0
            self.state.last_state = "stop"
            self.state.last_update_date = None
            self.state.last_heater_stop_time = None
            self.state.total_cycles = 0
            self.state.consecutive_failures = 0
            self.state.last_learning_status = "learning_started"
            self.state.cycle_start_date = datetime.now()
            self.state.cycle_active = False
        else:
            _LOGGER.info(
                "%s - Auto TPI: Resuming learning with existing data (coef_int=%.3f, coef_ext=%.3f, cycles=%d)",
                self._name,
                self.state.coeff_indoor_heat,
                self.state.coeff_outdoor_heat,
                self.state.total_cycles,
            )

        # Always enable learning when activating
        self.state.autolearn_enabled = True

        # Set start date only if it's a new session (reset) or if it wasn't set (first start)
        if reset_data or self.state.learning_start_date is None:
            self.state.learning_start_date = datetime.now()

        # ===== BOOTSTRAP PHASE LOGIC =====
        # Determine bootstrap strategy (3 modes)
        manual_capacity = self._heating_rate  # From config (CONF_AUTO_TPI_HEATING_POWER)
        
        if manual_capacity > 0:
            # Mode 1: Manual capacity provided - skip bootstrap
            self.state.max_capacity_heat = manual_capacity
            self.state.capacity_heat_learn_count = 3  # Mark as learned
            
            _LOGGER.info(
                "%s - Auto TPI: Using manual capacity %.2f °C/h, skipping bootstrap",
                self._name, manual_capacity
            )
        
        elif self.state.max_capacity_heat > 0 and not reset_data:
            # Capacity already learned from previous session - skip bootstrap
            
            _LOGGER.info(
                "%s - Auto TPI: Capacity already known (%.2f °C/h), resuming in TPI mode",
                self._name, self.state.max_capacity_heat
            )
        
        else:
            # Mode 2: No manual capacity
            # Bootstrap will automatically activate (capacity_heat_learn_count < 3)
            # High coefficients will be used during first 3 cycles
            _LOGGER.info(
                "%s - Starting capacity bootstrap (TPI aggressive mode)",
                self._name
            )

        # Ensure max_capacity fallback for TPI mode (unchanged)
        if self.state.max_capacity_heat == 0.0:
            self.state.max_capacity_heat = 1.0
        if self.state.max_capacity_cool == 0.0:
            self.state.max_capacity_cool = 1.0

        await self.async_save_data()

    async def stop_learning(self):
        _LOGGER.info("%s - Auto TPI: Stopping learning", self._name)
        self.state.autolearn_enabled = False
        # Do not clear learning_start_date to allow resuming or display in history
        # self.state.learning_start_date = None
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

        self._timer_remove_callback = async_call_later(self._hass, self._cycle_min * 60, self._on_timer_fired)

    async def _on_timer_fired(self, _):
        """Called when timer fires."""
        await self._tick()

    async def _tick(self):
        """Perform a tick of the cycle loop."""
        if not self._data_provider:
            return

        now = datetime.now()

        # 1. Get fresh data from thermostat FIRST
        # This ensures we have current temperatures for "End of Cycle" validation
        new_params = None
        try:
            if asyncio.iscoroutinefunction(self._data_provider):
                new_params = await self._data_provider()
            else:
                new_params = self._data_provider()
        except Exception as e:
            _LOGGER.error("%s - Auto TPI: Error getting data from thermostat: %s", self._name, e)
            # Retry later ?
            self._schedule_next_timer()
            return

        if not new_params:
            _LOGGER.warning("%s - Auto TPI: No data received from thermostat", self._name)
            self._schedule_next_timer()
            return

        # 2. Handle previous cycle completion
        # We use self._current_cycle_params which contains the params at the start of the previous cycle
        if self.state.cycle_start_date is not None and self._current_cycle_params is not None:
            elapsed_minutes = (now - self.state.cycle_start_date).total_seconds() / 60
            expected_duration = self._cycle_min
            tolerance = max(expected_duration * 0.1, 1.0)

            if abs(elapsed_minutes - expected_duration) <= tolerance:
                _LOGGER.debug("%s - Cycle validation success: duration=%.1fmin (expected=%.1fmin). Triggering learning.", self._name, elapsed_minutes, expected_duration)
                # Use stored parameters from the PREVIOUS cycle
                prev_params = self._current_cycle_params
                await self.on_cycle_completed(
                    on_time_sec=prev_params.get("on_time_sec", 0), off_time_sec=prev_params.get("off_time_sec", 0), hvac_mode=prev_params.get("hvac_mode", "stop")
                )
            else:
                _LOGGER.debug(
                    "%s - Cycle validation failed: duration=%.1fmin (expected=%.1fmin, tolerance=%.1fmin). Skipping learning.",
                    self._name,
                    elapsed_minutes,
                    expected_duration,
                    tolerance,
                )

            # Reset previous cycle tracking
            # self._current_cycle_params = None # Will be overwritten below

        # 3. Update current params for the NEXT cycle tracking
        self._current_cycle_params = new_params

        on_time = new_params.get("on_time_sec", 0)
        off_time = new_params.get("off_time_sec", 0)
        on_percent = new_params.get("on_percent", 0)
        hvac_mode = new_params.get("hvac_mode", "stop")

        # 4. Notify start of cycle
        await self.on_cycle_started(on_time, off_time, on_percent, hvac_mode)

        # 5. Notify thermostat to apply changes
        if self._event_sender:
            try:
                if asyncio.iscoroutinefunction(self._event_sender):
                    await self._event_sender(new_params)
                else:
                    self._event_sender(new_params)
            except Exception as e:
                _LOGGER.error("%s - Auto TPI: Error sending event to thermostat: %s", self._name, e)

        # 6. Schedule next tick
        self._schedule_next_timer()
