"""Auto TPI Manager implementing TPI algorithm."""

import logging
import json
import os
import math
from datetime import datetime, timedelta
from typing import Optional
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
        heater_heating_time: int = 0,
        heater_cooling_time: int = 0,
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

    async def async_update_coefficients_config(self, coef_int: float, coef_ext: float):
        """Update CONF_TPI_COEF_INT and CONF_TPI_COEF_EXT in the HA config entry."""

        if not self._enable_update_config:
            _LOGGER.debug("%s - Auto TPI: Skipping config update for coefficients as enable_update_config is False", self._name)
            return

        new_data = {
            **self._config_entry.data,
            CONF_TPI_COEF_INT: round(coef_int, 3),
            CONF_TPI_COEF_EXT: round(coef_ext, 3),
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
            rate_key: round(capacity, 3),
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
                _LOGGER.info("%s - Auto TPI: Learning completed. Persisting final coefficients.", self._name)

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

        await self.calculate()

    async def update(self, room_temp: float, ext_temp: float, hvac_mode: str, target_temp: float, is_overpowering_detected: bool = False) -> float:
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
        calc_state_str = "stop"
        if hvac_mode == "cool":
            calc_state_str = "cool"
        elif hvac_mode == "heat":
            calc_state_str = "heat"

        return self.calculate_power(target_temp, room_temp, ext_temp, calc_state_str)

    async def calculate(self) -> Optional[dict]:
        """Return the current calculated TPI parameters."""
        # Return current coefficients for the thermostat to use
        params = {}

        # Use hvac_mode to determine which coefficients to return
        # This prevents flapping when switching between heating/cooling actions while in the same mode (e.g. idle)
        # Note: hvac_mode usually comes from VThermHvacMode (heat, cool, off, auto...)

        is_cool_mode = self._current_hvac_mode == "cool"

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

        if self._current_cycle_interrupted:
            return "cycle_interrupted_by_overpowering"

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

        if outdoor_condition and abs(gap_in) > 0.05:
            if self._learn_outdoor(current_temp_in, current_temp_out, is_cool):
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
        """Learn indoor coefficient and return the learning error (expected_rise - actual_rise) if successful."""

        real_rise = delta_real
        # We use full cycle delta (passed as delta_real), not ON-time delta.

        if real_rise <= 0.01:  # Minimal rise required (0.01 to account for float precision/small sensors)
            _LOGGER.debug("%s - Auto TPI: Cannot learn indoor - real_rise %.3f <= 0.01. Will try outdoor learning.", self._name, real_rise)
            self.state.last_learning_status = "real_rise_too_small"
            return None  # Return None on failure

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
        if self._calculation_method == "average":
            # Weighted average
            # avg_coeff = ((old_coeff * count + coeff_new) / (count + 1))
            # We must use the current count (not incremented) as weight for old_coeff

            # If count is 0 (should not happen for valid state), treat as 1
            weight_old = max(count, 1)

            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Weighted Average: old=%.3f (weight=%d), new=%.3f, result=%.3f", self._name, old_coeff, weight_old, coeff_new, avg_coeff)

        else:  # EMA
            # EMA Smoothing (20% weight by default)
            # new_avg = (old_avg * (1 - alpha)) + (new_sample * alpha)
            alpha = self._get_adaptive_alpha(count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: EMA: old=%.3f, new=%.3f, alpha=%.2f (count=%d), result=%.3f", self._name, old_coeff, coeff_new, alpha, count, avg_coeff)

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
        else:
            # In heat mode: overheated if gap_in < 0 (temp > target)
            # Acceptable only if we really heated (power > 1% instead of 20%)
            # If power is > 1% and we are overheating, it means Kext is too high and should be reduced.
            if gap_in < 0 and self.state.last_power < 0.01:
                _LOGGER.debug("%s - Auto TPI: Cannot learn outdoor - Anomalous overheating (gap_in=%.2f, power=%.1f%%)", self._name, gap_in, self.state.last_power * 100)
                self.state.last_learning_status = "anomalous_overheating"
                return False

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
        if self._calculation_method == "average":
            weight_old = max(count, 1)  # Same as _learn_indoor
            avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
            _LOGGER.debug("%s - Auto TPI: Outdoor Weighted Average: old=%.3f (weight=%d), new=%.3f, result=%.3f", self._name, old_coeff, count, coeff_new, avg_coeff)
        else:  # EMA
            alpha = self._get_adaptive_alpha(count)
            avg_coeff = (old_coeff * (1.0 - alpha)) + (coeff_new * alpha)
            _LOGGER.debug("%s - Auto TPI: Outdoor EMA: old=%.3f, new=%.3f, alpha=%.2f (count=%d), result=%.3f", self._name, old_coeff, coeff_new, alpha, count, avg_coeff)

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

    def _boost_indoor_coeff(self, is_heat: bool):
        """Boost indoor coefficient when system is underpowered."""
        BOOST_FACTOR = 1.15  # increaase by 15%
        MAX_CONSECUTIVE_BOOSTS = 5  # limit consecutive boosts

        # Check if we've already boosted too many times
        if not hasattr(self.state, "consecutive_boosts"):
            self.state.consecutive_boosts = 0

        if self.state.consecutive_boosts >= MAX_CONSECUTIVE_BOOSTS:
            _LOGGER.info("%s - Auto TPI: Boost skipped - max consecutive boosts (%d) reached", self._name, MAX_CONSECUTIVE_BOOSTS)
            return

        if is_heat:
            old = self.state.coeff_indoor_heat
            self.state.coeff_indoor_heat = min(old * BOOST_FACTOR, self._max_coef_int)
            _LOGGER.info("%s - Boosting Kint heat: %.3f → %.3f (boost #%d)", self._name, old, self.state.coeff_indoor_heat, self.state.consecutive_boosts + 1)
        else:
            old = self.state.coeff_indoor_cool
            self.state.coeff_indoor_cool = min(old * BOOST_FACTOR, self._max_coef_int)
            _LOGGER.info("%s - Boosting Kint cool: %.3f → %.3f (boost #%d)", self._name, old, self.state.coeff_indoor_cool, self.state.consecutive_boosts + 1)

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
                    _LOGGER.info("%s - Deboosting Kint heat: %.3f → %.3f", self._name, old, self.state.coeff_indoor_heat)
            else:
                old = self.state.coeff_indoor_cool
                if old > self._default_coef_int:
                    self.state.coeff_indoor_cool = max(old * DEBOOST_FACTOR, self._default_coef_int)
                    _LOGGER.info("%s - Deboosting Kint cool: %.3f → %.3f", self._name, old, self.state.coeff_indoor_cool)
            # Reset boost counter
            if hasattr(self.state, "consecutive_boosts"):
                self.state.consecutive_boosts = 0

    async def _detect_failures(self, current_temp_in: float):
        """Detect system failures."""
        OFFSET_FAILURE = 1.0
        MIN_LEARN_FOR_DETECTION = 25

        failure_detected = False
        reason = "unknown"

        if (
            self.state.last_state == "heat"
            and current_temp_in < self.state.last_order - OFFSET_FAILURE
            and current_temp_in < self.state.last_temp_in
            and self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION
        ):
            failure_detected = True
            reason = "Temperature dropped while heating"
            _LOGGER.warning("%s - Auto TPI: Failure detected in HEAT mode", self._name)

        elif (
            self.state.last_state == "cool"
            and current_temp_in > self.state.last_order + OFFSET_FAILURE
            and current_temp_in > self.state.last_temp_in
            and self.state.coeff_indoor_autolearn > MIN_LEARN_FOR_DETECTION
        ):
            failure_detected = True
            reason = "Temperature rose while cooling"
            _LOGGER.warning("%s - Auto TPI: Failure detected in COOL mode", self._name)

        if failure_detected:
            self.state.consecutive_failures += 1
            if self.state.consecutive_failures >= 3:
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
        """Calculate power using TPI formula."""
        if setpoint is None or temp_in is None or temp_out is None:
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
        # Jeedom has an offset you can dynamically feed to the thermostat.
        # We keep it here for future addition if needed, it's not used yet.
        power = (direction * delta_in * coeff_int) + (direction * delta_out * coeff_ext) + offset
        return max(0.0, min(100.0, power))

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

    def _interpolate_power_at(self, target_dt: datetime, power_history: list, tolerance_seconds: float = 120.0) -> Optional[float]:
        """
        Find the power value closest to target_dt within tolerance.
        Returns power as percentage (0-100).
        """
        if not power_history:
            return None

        closest_state = None
        closest_diff = float("inf")

        for state in power_history:
            try:
                state_dt = state.last_changed
                diff = abs((state_dt - target_dt).total_seconds())

                if diff < closest_diff and diff <= tolerance_seconds:
                    closest_diff = diff
                    closest_state = state
            except (AttributeError, TypeError):
                continue

        if closest_state is None:
            return None

        try:
            state_value = getattr(closest_state, "state", None)
            if state_value in ["unknown", "unavailable", None]:
                return None
            return float(state_value)
        except (ValueError, TypeError):
            return None

    async def calculate_capacity_from_slope_sensor(
        self,
        slope_history: list,
        power_history: list,
        hvac_mode: str,
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
            hvac_mode: 'heat' or 'cool'
            min_power_threshold: Minimum power (0.0-1.0) to consider. Default 0.95 (95%)
            kext_coeff: Current Kext coefficient for adiabatic correction
            current_indoor_temp: Current indoor temperature for delta_T estimation
            current_outdoor_temp: Current outdoor temperature for delta_T estimation

        Returns:
            Dictionary with adiabatic capacity result and metrics
        """
        is_heat_mode = hvac_mode == "heat"
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

        for slope_state in slope_history:
            try:
                slope_dt = slope_state.last_changed
                slope_str = getattr(slope_state, "state", None)

                if slope_str in ["unknown", "unavailable", None]:
                    rejected_invalid += 1
                    continue

                slope_value = float(slope_str)

                # Find closest power value
                power = self._interpolate_power_at(slope_dt, power_history)

                if power is None:
                    rejected_invalid += 1
                    continue

                # Check power threshold
                if power < power_threshold_percent:
                    rejected_low_power += 1
                    continue

                # Check slope direction
                if is_heat_mode and slope_value <= 0:
                    rejected_wrong_direction += 1
                    continue
                elif not is_heat_mode and slope_value >= 0:
                    rejected_wrong_direction += 1
                    continue

                # For cooling, use absolute value (capacity is always positive)
                if not is_heat_mode:
                    slope_value = abs(slope_value)

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
        variance_factor = max(0.0, 1.0 - cv)  # Lower if high variance
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
        hvac_mode: str,
        save_to_config: bool,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
        min_power_threshold: float = 0.95,
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
            hvac_mode: 'heat' or 'cool'
            save_to_config: Whether to save the result to config
            start_date: Start of history period (default: 30 days ago)
            end_date: End of history period (default: now)
            min_power_threshold: Minimum power percentage (0.0-1.0) to consider a sample.
                                 Default is 1.0 (100%). Lower values (e.g., 0.90) include more samples.
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

        # 4. Fetch sensor histories
        entity_ids = [slope_sensor_id, power_sensor_id]

        states = await get_instance(self._hass).async_add_executor_job(
            partial(
                history.get_significant_states,
                self._hass,
                start_time,
                end_time=end_time,
                entity_ids=entity_ids,
                significant_changes_only=False,
            )
        )

        slope_history = states.get(slope_sensor_id, [])
        power_history = states.get(power_sensor_id, [])

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
            hvac_mode,
            min_power_threshold=min_power_threshold,
            kext_coeff=kext_coeff,
            current_indoor_temp=current_indoor_temp,
            current_outdoor_temp=current_outdoor_temp,
        )

        _LOGGER.info("%s - Capacity calibration result: %s", self._name, result)

        # 6. Save to config if requested
        if save_to_config and result and isinstance(result, dict) and result.get("success"):

            capacity = result.get("capacity")
            is_heat_mode = hvac_mode == "heat"

            if capacity is not None:
                await self.async_update_capacity_config(capacity=capacity, is_heat_mode=is_heat_mode)

                mode_str = "Heating" if is_heat_mode else "Cooling"
                _LOGGER.info("%s - %s capacity calibrated to %.3f °C/h and saved to config.", self._name, mode_str, capacity)

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
        # We check if the cycle was significant enough for learning.
        # The ON pulse must be longer than the estimated time used to warm up the radiator itself.
        is_significant_cycle = True
        if effective_warm_up_time > 0 and on_time_minutes <= effective_warm_up_time:
            is_significant_cycle = False
            _LOGGER.debug("%s - Auto TPI: Cycle ignored for learning - ON time (%.1f) <= Est. Warm-up Time (%.1f)", self._name, on_time_minutes, effective_warm_up_time)

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
        await self._detect_failures(self._current_temp_in)

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

    async def start_learning(self, coef_int: float = None, coef_ext: float = None, reset_data: bool = True):
        """Start learning, optionally resetting coefficients and learning data.

        Args:
            coef_int: Target internal coefficient (defaults to configured value)
            coef_ext: Target external coefficient (defaults to configured value)
            reset_data: If True, reset all learning data; if False, resume with existing data
        """
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

        # Ensure max_capacity is not 0, if it is, force default 1.0 (to allow proper indoor learning calc)
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
