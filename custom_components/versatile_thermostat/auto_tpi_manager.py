"""Auto TPI Manager implementing TPI algorithm."""

import logging
from vtherm_api.log_collector import get_vtherm_logger
import json
import os
import math
from datetime import datetime
from typing import Optional
from homeassistant.util.unit_conversion import TemperatureConverter
from homeassistant.const import UnitOfTemperature
from dataclasses import dataclass, asdict

import asyncio
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform, service
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
)
from .vtherm_central_api import async_update_entry_without_reload

_LOGGER = get_vtherm_logger(__name__)

STORAGE_VERSION = 8
STORAGE_KEY_PREFIX = "versatile_thermostat.auto_tpi"

# Configurable constants for learning algorithm behavior
MIN_KINT = 0.01  # Minimum Kint threshold to maintain temperature responsiveness
KINT_RELEARN_START = 0.6  # Default Kint a session starts from after the per-cycle learning
MAX_KINT = 3.0  # Weak or slow emitters (underfloor, low-temperature water) can need Kint above 1
NATURAL_RECOVERY_POWER_THRESHOLD = 0.10  # Max power (10%) to consider temperature change as natural recovery
KEXT_LEARNING_MAX_GAP = 1.0  # Max gap (°C) to allow Kext learning (Near-Field vs Far-Field)

# Kint learning: multiplicative steps toward a target closing rate of the gap.
# The room rate is measured over windows of several cycles. A window is accepted on
# its duration and starting gap only, never on the measured rise.
KINT_MIN_GAP = 0.3  # Min gap (°C) to the setpoint at the start of a Kint window
KINT_WINDOW_MIN_MINUTES = 30.0  # Max duration of a Kint window when the rise is slow (or T_cl if longer)
KINT_WINDOW_SHORTEST_MINUTES = 10.0  # Shortest Kint window (and at least 2 cycles)
KINT_WINDOW_RISE = 0.3  # Expected temperature change over a window (°C), used to size it from the previous rise
KINT_RATE_LOOKBACK_MINUTES = 20.0  # Span used to measure the rise before a window
KINT_MAX_STEP = 1.15  # Max multiplicative Kint change per window
KINT_WINDOWS_TO_FINISH = 15  # Kint windows needed to end the learning
KINT_TREND_TO_FINISH = 5  # The learning does not end while this many Kint steps in a row went the same way
KINT_TOO_HIGH_FACTOR = 1.5  # Kint above this factor of the Kint suggested by a rise at full power is too high
KINT_TOO_HIGH_RISES = 2  # Rises at full power, without Kint window, that show a Kint too high
CLOSED_LOOP_TIME_MIN_MINUTES = 30.0  # Bounds of the target closed-loop time constant
CLOSED_LOOP_TIME_MAX_MINUTES = 180.0
KEXT_SETTLE_FACTOR = 3.0  # Kext is learned only after KEXT_SETTLE_FACTOR closed-loop times since the last setpoint change
KEXT_FORCE_SETTLE_FACTOR = 12.0  # ... and once the room came near the setpoint, or after this many closed-loop times
CONTINUOUS_KEXT_ALPHA = 0.04  # Fixed smoothing of the continuous Kext learning
KINT_COUNT_START = 1  # Initial value of the Kint window counter
CONFIG_COEF_TOLERANCE = 0.0015  # Coefficients are written to the configuration with 3 decimals


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

    # Offsets.
    offset: float = 0.0

    # Previous cycle state (Snapshot for learning)
    last_power: float = 0.0
    last_order: float = 0.0
    last_temp_in: float = 0.0
    last_temp_out: float = 0.0
    last_state: str = "stop"  # 'heat', 'cool', 'stop'
    previous_state: str = "stop"  # State of the previous cycle
    last_update_date: Optional[datetime] = None

    # Cycle management
    cycle_start_date: Optional[datetime] = None  # Start of current cycle
    cycle_active: bool = False
    current_cycle_params: dict = None  # Parameters of the current/last cycle

    # Management
    autolearn_enabled: bool = False
    kint_trend_heat: int = 0  # Consecutive Kint steps in the same direction (sign = direction)
    kint_trend_cool: int = 0
    last_learning_status: str = "startup"
    total_cycles: int = 0  # Total number of TPI cycles
    learning_start_date: Optional[datetime] = None  # Date when learning started

    def to_dict(self):
        """Convert to a JSON-safe dict for HA state attributes and storage."""
        def make_json_safe(value):
            """Convert non-JSON-serializable types to JSON-safe equivalents."""
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, (list, tuple)):
                return [make_json_safe(v) for v in value]
            if isinstance(value, dict):
                return {k: make_json_safe(v) for k, v in value.items()}
            return value

        result = asdict(self)
        return {k: make_json_safe(v) for k, v in result.items()}

    @classmethod
    def from_dict(cls, data):
        d = data.copy()
        # Date conversion from ISO format
        for date_field in ["last_update_date", "cycle_start_date", "learning_start_date"]:
            if d.get(date_field):
                try:
                    # Use dt_util.parse_datetime to preserve timezone information
                    parsed = dt_util.parse_datetime(d[date_field])
                    d[date_field] = parsed if parsed else datetime.fromisoformat(d[date_field])
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
        coef_int: float = 0.6,
        coef_ext: float = 0.04,
        heater_heating_time: int = 5,
        continuous_kext: bool = False,
    ):
        self._hass = hass
        self._name = name
        self._cycle_min = cycle_min
        self._config_entry = config_entry
        self._enable_update_config = True
        self._enable_notification = True
        self._unique_id = unique_id
        self._entity_id: str | None = None  # Set by thermostat after entity registration
        self._heater_heating_time = heater_heating_time

        self._continuous_kext = continuous_kext
        self._continuous_kext_alpha = CONTINUOUS_KEXT_ALPHA

        self._temp_unit = self._hass.config.units.temperature_unit
        self._unit_factor = 1.8 if self._temp_unit == UnitOfTemperature.FAHRENHEIT else 1.0

        self._avg_initial_weight = KINT_COUNT_START
        self._max_coef_int = MAX_KINT

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
        self._save_lock = asyncio.Lock()

        self._learning_just_completed: bool = False  # Transient flag to suppress 'cycle interrupted' log after learning

        # Interruption management
        self._current_cycle_interrupted: bool = False
        self._central_boiler_off: bool = False
        self._current_is_heating_failure: bool = False

        # Kint learning window (transient)
        self._kint_window_start: tuple[datetime, float, float] | None = None  # (time, room temperature, duration min)
        self._recent_temps: list[tuple[datetime, float]] = []  # room temperature at the last cycle ends
        self._saturated_rise: list | None = None  # [start time, start temp, end time, end temp, is_cool]
        self._fast_saturated_rises = 0
        self._kint_window_hold_since: datetime | None = None  # last setpoint change or window reset
        self._last_setpoint_change: datetime | None = None
        self._setpoint_reached: bool = True  # room came within KINT_MIN_GAP of the setpoint since the last change
        self._last_target_seen: float | None = None
        self._last_hvac_mode_seen: str | None = None

        # Shutdown safety check
        self._is_vtherm_stopping_callback: Callable[[], bool] | None = None
        # Called with (coef_int, coef_ext) in user units when learned coefficients are written
        self._coefficients_written_callback: Callable[[float | None, float | None], None] | None = None
        self._previous_method_state = False

    def get_filtered_state(self) -> dict:
        """Get the AutoTpiState as a dict, but filtered for public exposure."""
        data = self.state.to_dict()

        # 2. Filter counters if learning session is NOT active (Continuous Kext only)
        if not self.state.autolearn_enabled:
            # If main learning is off, hide indoor counters as they are not updated/relevant in continuous mode
            # (Continuous mode only updates Kext/Outdoor)
            keys_to_hide = [
                "coeff_indoor_autolearn",
                "coeff_indoor_cool_autolearn",
                "learning_start_date",
                "last_learning_status"
            ]
            for k in keys_to_hide:
                if k in data:
                    del data[k]

        # 2. Filter based on Mode
        is_cool_mode = self._current_hvac_mode == "cool"

        keys_to_remove = []
        for key in data.keys():
            if is_cool_mode:
                # In Cool mode, remove heat-related keys
                if "_heat" in key:
                    keys_to_remove.append(key)
            else:
                # In Heat mode, remove cool-related keys
                if "_cool" in key:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del data[key]

        return data

    @property
    def _relearn_issue_id(self) -> str:
        """Repair issue id asking to learn the coefficients again."""
        return f"auto_tpi_relearn_{self._unique_id}"

    @property
    def _kint_too_high_issue_id(self) -> str:
        """Repair issue id telling that the starting Kint is too high to be learned."""
        return f"auto_tpi_kint_too_high_{self._unique_id}"

    def _report_previous_learning(self, data: dict) -> None:
        """Raise a repair issue when the stored state comes from the per-cycle learning.

        That learning stored a heating capacity and could drive Kint far too low.
        The issue asks for a new learning session; it is removed when one starts.
        """
        learned_kint = data.get("coeff_indoor_autolearn", 0) > KINT_COUNT_START
        if "capacity_heat_learn_count" not in data or not learned_kint:
            return
        self._previous_method_state = True
        _LOGGER.warning("%s - Auto TPI: coefficients learned by the previous learning method, a new learning session is advised", self._name)
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            self._relearn_issue_id,
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="auto_tpi_relearn",
            translation_placeholders={
                "name": self._name,
                "kint": f"{data.get('coeff_indoor_heat', 0) / self._unit_factor:.3f}",
                "kext": f"{data.get('coeff_outdoor_heat', 0) / self._unit_factor:.3f}",
            },
        )

    def set_coefficients_written_callback(self, callback: Callable[[float | None, float | None], None]):
        """Set a callback called when learned coefficients are written to the configuration."""
        self._coefficients_written_callback = callback

    def set_configured_coefficients(self, coef_int: float, coef_ext: float) -> None:
        """Follow coefficients written to the configuration outside Auto TPI (user, service).

        They become the reference for the next session start. Outside a session
        they also replace the stored ones, as when the configuration is loaded.
        """
        self._default_coef_int = coef_int * self._unit_factor
        self._default_coef_ext = coef_ext * self._unit_factor
        if not self.state.autolearn_enabled:
            self._align_with_configuration()

    def _align_with_configuration(self) -> None:
        """Replace the stored coefficients that differ from the configured ones beyond the write rounding."""
        for attr, configured in (
            ("coeff_indoor_heat", self._default_coef_int),
            ("coeff_indoor_cool", self._default_coef_int),
            ("coeff_outdoor_heat", self._default_coef_ext),
            ("coeff_outdoor_cool", self._default_coef_ext),
        ):
            stored = getattr(self.state, attr)
            if abs(stored - configured) > CONFIG_COEF_TOLERANCE * self._unit_factor:
                _LOGGER.info("%s - Auto TPI: %s %.4f differs from the configuration, using the configured %.4f", self._name, attr, stored, configured)
                setattr(self.state, attr, configured)

    def set_is_vtherm_stopping_callback(self, callback: Callable[[], bool]):
        """Set a callback to check if the VTherm is stopping."""
        self._is_vtherm_stopping_callback = callback


    def _to_celsius(self, temp: float) -> float:
        """Convert temperature to Celsius if needed."""
        if temp is None:
            return 0.0
        if self._temp_unit == UnitOfTemperature.FAHRENHEIT:
            return TemperatureConverter.convert(temp, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)
        return temp

    async def async_update_learning_data(self, coef_int: float = None, coef_ext: float = None):
        """Write the learned coefficients to the configuration in one update."""

        updates = {}

        if coef_int is not None:
            updates[CONF_TPI_COEF_INT] = round(coef_int / self._unit_factor, 3)

        if coef_ext is not None:
            updates[CONF_TPI_COEF_EXT] = round(coef_ext / self._unit_factor, 3)

        # The regulation uses the written coefficients right away (the configuration update does not reload)
        if self._coefficients_written_callback and updates:
            self._coefficients_written_callback(
                coef_int / self._unit_factor if coef_int is not None else None,
                coef_ext / self._unit_factor if coef_ext is not None else None,
            )

        # Always save to local storage (Persistence)
        await self.async_save_data()

        # Check if we should skip config update (Restart/Shutdown safety)
        if not self._enable_update_config:
             _LOGGER.debug("%s - Auto TPI: update_learning_data - enable_update_config is False", self._name)
             return

        if self._is_vtherm_stopping_callback and self._is_vtherm_stopping_callback():
             _LOGGER.debug("%s - Auto TPI: update_learning_data - VTherm is stopping, skipping config update", self._name)
             return

        if not updates:
            _LOGGER.debug("%s - Auto TPI: update_learning_data - no updates to apply", self._name)
            return

        # Apply atomic config update, without reload: the regulation already uses the coefficients
        async_update_entry_without_reload(self._hass, self._config_entry, {**self._config_entry.data, **updates})

        # The configuration is the reference outside sessions: follow what was written
        if CONF_TPI_COEF_INT in updates:
            self._default_coef_int = updates[CONF_TPI_COEF_INT] * self._unit_factor
        if CONF_TPI_COEF_EXT in updates:
            self._default_coef_ext = updates[CONF_TPI_COEF_EXT] * self._unit_factor

        _LOGGER.info(
            "%s - Auto TPI: ATOMIC UPDATE: Kint=%s, Kext=%s",
            self._name,
            f"{coef_int:.3f}" if coef_int is not None else "N/A",
            f"{coef_ext:.3f}" if coef_ext is not None else "N/A",
        )







    async def process_learning_completion(self) -> Optional[dict]:
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
            kint_trend = self.state.kint_trend_cool
        else:
            k_int = self.state.coeff_indoor_heat
            k_ext = self.state.coeff_outdoor_heat
            int_cycles_count = self.state.coeff_indoor_autolearn
            ext_cycles_count = self.state.coeff_outdoor_autolearn
            kint_trend = self.state.kint_trend_heat

        # 1. Learning ends when both Kint windows and Kext samples are sufficient.
        # The Kint counter starts at _avg_initial_weight.
        INT_CYCLES_THRESHOLD = KINT_WINDOWS_TO_FINISH + self._avg_initial_weight
        EXT_CYCLES_THRESHOLD = 50

        # Kint is not finished while its last steps all went the same way (start far from its value)
        is_int_finished = int_cycles_count >= INT_CYCLES_THRESHOLD and abs(kint_trend) < KINT_TREND_TO_FINISH
        is_ext_finished = ext_cycles_count >= EXT_CYCLES_THRESHOLD

        if not (is_int_finished and is_ext_finished):
            _LOGGER.debug(
                "%s - Auto TPI: Learning in progress (Kint windows: %d/%d, Kext cycles: %d/%d). Skipping persistence.",
                self._name,
                int_cycles_count - self._avg_initial_weight,
                INT_CYCLES_THRESHOLD - self._avg_initial_weight,
                ext_cycles_count,
                EXT_CYCLES_THRESHOLD,
            )
            return None

        _LOGGER.info("%s - Auto TPI: Learning completed. Persisting final coefficients and stopping learning.", self._name)
        await self.stop_learning()
        await self.async_update_learning_data(coef_int=k_int, coef_ext=k_ext)

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
            self._report_previous_learning(data)
            self.state = AutoTpiState.from_dict(data)

            # Clamping: Apply new max_coef_int to loaded coefficients immediately,
            # in case the user lowered the limit via config flow.
            self.state.coeff_indoor_heat = min(self.state.coeff_indoor_heat, self._max_coef_int)
            self.state.coeff_indoor_cool = min(self.state.coeff_indoor_cool, self._max_coef_int)

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
            elif not self.state.autolearn_enabled:
                # Outside a learning session the configuration is the reference:
                # a coefficient changed by the user replaces the stored one.
                self._align_with_configuration()

            _LOGGER.info("%s - Auto TPI: State loaded. Cycles: %d, Indoor learn count: %d", self._name, self.state.total_cycles, self.state.coeff_indoor_autolearn)
        else:
            self.state = AutoTpiState(
                coeff_indoor_heat=self._default_coef_int,
                coeff_outdoor_heat=self._default_coef_ext,
                coeff_indoor_cool=self._default_coef_int,
                coeff_outdoor_cool=self._default_coef_ext,
            )

        # Reset last_learning_status on load to avoid stale messages from previous sessions
        self.state.last_learning_status = "learning_started"

        # Reset cycle state to discard any cycle interrupted by the reboot
        # This prevents "cycle_gap_detected" or validation failures on the first cycle after restart
        self.state.cycle_active = False
        self.state.cycle_start_date = None


        await self.calculate()

    async def update(self, room_temp: float, ext_temp: float, hvac_mode: str, target_temp: float, is_overpowering_detected: bool = False, is_central_boiler_off: bool = False, is_heating_failure: bool = False) -> float:
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
        self._current_is_heating_failure = is_heating_failure

        # Track setpoint and mode changes: they restart the Kint window and delay Kext learning
        if (
            self._last_target_seen is None
            or abs(self._current_target_temp - self._last_target_seen) > 0.05
            or hvac_mode != self._last_hvac_mode_seen
        ):
            now = dt_util.now()
            self._last_setpoint_change = now
            self._setpoint_reached = False
            self._reset_kint_window(now)
        self._last_target_seen = self._current_target_temp
        self._last_hvac_mode_seen = hvac_mode
        if room_temp is not None and abs(self._current_target_temp - self._current_temp_in) < KINT_MIN_GAP:
            self._setpoint_reached = True

        # Calculate and return power
        # Use hvac_mode to force direction
        calc_state_str = "stop"
        if hvac_mode == "cool":
            calc_state_str = "cool"
        elif hvac_mode == "heat":
            calc_state_str = "heat"

        return self.calculate_power(self._current_target_temp, self._current_temp_in, self._current_temp_out, calc_state_str)

    async def calculate(self) -> Optional[dict]:
        """Return the current TPI coefficients for the regulation."""
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

    def _should_learn(self) -> bool:
        """Check if learning should be performed."""
        # We learn if:
        # 1. Main learning session is active (autolearn_enabled)
        # 2. OR Continuous Kext is enabled (we will filter Kint vs Kext inside _perform_learning)
        if not self.state.autolearn_enabled and not self._continuous_kext:
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

        if self._current_is_heating_failure:
            _LOGGER.debug("%s - Auto TPI: Not learning - Heating/Cooling failure detected", self._name)
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
        if not self.state.autolearn_enabled and not self._continuous_kext:
            return "learning_disabled"

        saturation_threshold = self.saturation_threshold  # pylint: disable=no-member
        if not (0 < self.state.last_power < saturation_threshold):
            return f"power_out_of_range({self.state.last_power * 100:.1f}% vs Saturation {saturation_threshold * 100:.1f}%)"

        if self._current_cycle_interrupted:
            return "cycle_interrupted_by_overpowering"

        if self._central_boiler_off:
            return "central_boiler_off"

        if self._current_is_heating_failure:
            return "heating_failure_detected"

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

        # Outdoor Learning (Kint is learned separately over multi-cycle windows)
        # ----------------------------
        # Conditions:
        # - The room has settled since the last setpoint change
        # - Relevant outdoor temperature (outdoor_condition)
        # - Significant remaining gap
        if not self._is_settled_for_kext():
            self.state.last_learning_status = "kext_waiting_settling"
            _LOGGER.debug("%s - Auto TPI: Skipping outdoor learning - room not settled since the last setpoint change", self._name)
            return

        gap_in = target_temp - current_temp_in
        gap_threshold = 0.05

        if outdoor_condition and abs(gap_in) > gap_threshold:
            # Domain Separation: Far-Field vs Near-Field
            # If the gap is large (> KEXT_LEARNING_MAX_GAP), it's a transient state (Kint domain).
            # Kext (Steady State) should only be learned in Near-Field.
            #
            # EXCEPTION: During overshoot with significant power, we MUST learn Kext regardless
            # of gap size. Overshoot means temp > target (heat) or temp < target (cool),
            # which is gap_in < 0 (heat) or gap_in > 0 (cool) - the opposite of normal Far-Field.
            is_overshoot_heat = is_heat and gap_in < 0
            is_overshoot_cool = is_cool and gap_in > 0
            has_significant_power = self.state.last_power >= NATURAL_RECOVERY_POWER_THRESHOLD
            is_active_overshoot = (is_overshoot_heat or is_overshoot_cool) and has_significant_power

            if abs(gap_in) > KEXT_LEARNING_MAX_GAP and not is_active_overshoot:
                self.state.last_learning_status = f"gap_too_large_for_outdoor(gap={gap_in:.2f} > {KEXT_LEARNING_MAX_GAP})"
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning: Gap %.2f > %.2f - Far field stagnation is a Kint/Capacity issue, not Kext.",
                    self._name, abs(gap_in), KEXT_LEARNING_MAX_GAP
                )
                return

            if self._learn_outdoor(current_temp_in, current_temp_out, is_cool):
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

    @property
    def closed_loop_time_min(self) -> float:
        """Target closed-loop time constant (min): twice the emitter delay plus half a cycle, bounded."""
        t_cl = 2.0 * (self._heater_heating_time + self._cycle_min / 2.0)
        return min(CLOSED_LOOP_TIME_MAX_MINUTES, max(CLOSED_LOOP_TIME_MIN_MINUTES, t_cl))

    def _track_saturated_rise(self, now: datetime, is_cool: bool) -> None:
        """Extend the rise at full power with the completed cycle when the room was far from the setpoint."""
        start_temp = self.state.last_temp_in
        gap = (start_temp - self.state.last_order) if is_cool else (self.state.last_order - start_temp)
        if gap < KINT_MIN_GAP or self.state.cycle_start_date is None:
            self._end_saturated_rise()
            return
        if self._saturated_rise is None or self._saturated_rise[4] != is_cool:
            self._saturated_rise = [self.state.cycle_start_date, start_temp, now, self._current_temp_in, is_cool]
        else:
            self._saturated_rise[2:4] = [now, self._current_temp_in]

    def _end_saturated_rise(self) -> None:
        """Check a finished rise at full power: a fast rise shows a Kint too high to be learned.

        With a Kint too high, the power stays at 100 % until the room is too close to the
        setpoint for a Kint window, so Kint never moves. The rise speed at full power gives
        the Kint that the target closed-loop time needs; a repair issue suggests it.
        """
        rise, self._saturated_rise = self._saturated_rise, None
        if rise is None or not self.learning_active:
            return
        start_time, start_temp, end_time, end_temp, is_cool = rise
        hours = (end_time - start_time).total_seconds() / 3600.0
        delta = (start_temp - end_temp) if is_cool else (end_temp - start_temp)
        if hours * 60.0 < KINT_RATE_LOOKBACK_MINUTES or delta < KINT_WINDOW_RISE:
            return
        suggested = min(self._max_coef_int, max(MIN_KINT, 1.0 / (delta / hours * self.closed_loop_time_min / 60.0)))
        kint = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        if kint <= KINT_TOO_HIGH_FACTOR * suggested:
            self._fast_saturated_rises = 0
            return
        self._fast_saturated_rises += 1
        _LOGGER.info(
            "%s - Auto TPI: rise at full power of %.2f° in %.0f min, Kint %.3f looks too high (about %.2f expected)",
            self._name, delta, hours * 60.0, kint / self._unit_factor, suggested / self._unit_factor,
        )
        if self._fast_saturated_rises >= KINT_TOO_HIGH_RISES:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                self._kint_too_high_issue_id,
                is_fixable=False,
                is_persistent=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="auto_tpi_kint_too_high",
                translation_placeholders={
                    "name": self._name,
                    "kint": f"{kint / self._unit_factor:.2f}",
                    "suggested": f"{suggested / self._unit_factor:.2f}",
                },
            )

    def _reset_kint_window(self, now: datetime | None = None) -> None:
        """Close the current Kint window without learning and hold the next start."""
        self._kint_window_start = None
        self._kint_window_hold_since = now if now is not None else dt_util.now()

    def _is_settled_for_kext(self) -> bool:
        """True when the room has settled since the last setpoint change, so that Kext can be learned.

        The transient after a setpoint change belongs to Kint. Kext is learned once
        KEXT_SETTLE_FACTOR closed-loop times have passed and the room came near the
        setpoint, or after KEXT_FORCE_SETTLE_FACTOR closed-loop times so that a large
        static offset (wrong Kext) can still be corrected.
        """
        if self._last_setpoint_change is None:
            return True
        elapsed_min = (dt_util.now() - self._last_setpoint_change).total_seconds() / 60.0
        t_cl = self.closed_loop_time_min
        if elapsed_min < KEXT_SETTLE_FACTOR * t_cl:
            return False
        return self._setpoint_reached or elapsed_min >= KEXT_FORCE_SETTLE_FACTOR * t_cl

    def _process_kint_window(self, cycle_valid: bool) -> None:
        """Advance the Kint window at the end of a cycle and learn when it is long enough.

        A window spans several consecutive valid cycles with the same setpoint and an
        unsaturated, non-zero power. It starts only half a closed-loop time after the
        last setpoint change or window reset (emitter delay), and only if the gap to
        the setpoint is at least KINT_MIN_GAP. Its acceptance never depends on the
        measured temperature change.
        """
        if not self.state.autolearn_enabled:
            self._kint_window_start = None
            return

        is_heat = self.state.last_state == "heat"
        is_cool = self.state.last_state == "cool"
        now = dt_util.now()

        if cycle_valid and (is_heat or is_cool) and self.state.last_power >= self.saturation_threshold:
            # A saturated cycle says nothing about Kint, but the emitter is already fully
            # running: close the window without waiting for the emitter delay again.
            if self._kint_window_start is not None:
                _LOGGER.debug("%s - Auto TPI: Kint window closed without learning (saturated cycle)", self._name)
            self._kint_window_start = None
            self._track_saturated_rise(now, is_cool)
            return

        self._end_saturated_rise()

        if not (cycle_valid and (is_heat or is_cool) and 0 < self.state.last_power < self.saturation_threshold):
            if self._kint_window_start is not None:
                _LOGGER.debug(
                    "%s - Auto TPI: Kint window closed without learning (cycle valid=%s, power=%.0f%%)",
                    self._name, cycle_valid, self.state.last_power * 100,
                )
            self._reset_kint_window(now)
            return

        temp = self._current_temp_in
        t_cl = self.closed_loop_time_min

        if self._kint_window_start is None:
            if self._kint_window_hold_since is not None and (now - self._kint_window_hold_since).total_seconds() / 60.0 < t_cl / 2.0:
                return
            gap = (temp - self._current_target_temp) if is_cool else (self._current_target_temp - temp)
            if gap >= KINT_MIN_GAP:
                self._kint_window_start = (now, temp, self._kint_window_duration(now))
                _LOGGER.debug(
                    "%s - Auto TPI: Kint window opened at %.2f° (gap %.2f°), duration %.0f min",
                    self._name, temp, gap, self._kint_window_start[2],
                )
            return

        start_time, start_temp, duration_min = self._kint_window_start
        elapsed_min = (now - start_time).total_seconds() / 60.0
        if elapsed_min < duration_min:
            return

        self._learn_kint_from_window(start_temp, temp, elapsed_min, is_cool)
        # The next window starts where this one ends, under the same starting gap condition
        gap = (temp - self._current_target_temp) if is_cool else (self._current_target_temp - temp)
        self._kint_window_start = (now, temp, self._kint_window_duration(now)) if gap >= KINT_MIN_GAP else None

    def _record_cycle_temperature(self, now: datetime) -> None:
        """Keep the room temperature of the recent cycle ends, used to size the Kint windows."""
        self._recent_temps.append((now, self._current_temp_in))
        horizon = KINT_RATE_LOOKBACK_MINUTES + 2 * self._cycle_min
        self._recent_temps = [(t, v) for t, v in self._recent_temps if (now - t).total_seconds() / 60.0 <= horizon]

    def _kint_window_duration(self, now: datetime) -> float:
        """Window duration (min) chosen at its start, from the rise measured before it.

        The window should see about KINT_WINDOW_RISE of temperature change: a fast rise
        gets a short window, a slow one up to max(30 min, T_cl). The duration only uses
        data older than the window, so it never depends on the change the window measures.
        """
        shortest = max(KINT_WINDOW_SHORTEST_MINUTES, 2 * self._cycle_min)
        longest = max(KINT_WINDOW_MIN_MINUTES, self.closed_loop_time_min)
        before = [(t, v) for t, v in self._recent_temps if t < now]
        if len(before) < 2:
            return longest
        (t_last, v_last) = before[-1]
        older = [(t, v) for t, v in before if (t_last - t).total_seconds() / 60.0 <= KINT_RATE_LOOKBACK_MINUTES]
        t_old, v_old = older[0]
        span_h = (t_last - t_old).total_seconds() / 3600.0
        if span_h <= 0:
            return longest
        rate = abs(v_last - v_old) / span_h
        if rate <= 0:
            return longest
        return min(longest, max(shortest, 60.0 * KINT_WINDOW_RISE / rate))

    def _learn_kint_from_window(self, start_temp: float, end_temp: float, elapsed_min: float, is_cool: bool) -> None:
        """Move Kint one bounded step toward the target closing rate of the gap.

        Target rate r* = mean gap / T_cl. Observed rate r = room temperature change / duration.
        With Kext compensating the losses, r = capacity * Kint * gap, so the fixed point is
        Kint = 1 / (capacity * T_cl). The bounded multiplicative step converges toward the
        median ratio, which keeps isolated noisy windows from driving Kint.
        """
        target = self._current_target_temp
        elapsed_h = elapsed_min / 60.0
        if is_cool:
            mean_gap = (start_temp + end_temp) / 2.0 - target
            rate = (start_temp - end_temp) / elapsed_h
        else:
            mean_gap = target - (start_temp + end_temp) / 2.0
            rate = (end_temp - start_temp) / elapsed_h

        if mean_gap <= 0:
            self.state.last_learning_status = "kint_window_crossed_setpoint"
            _LOGGER.debug("%s - Auto TPI: Kint window not used, the room crossed the setpoint (%.2f° -> %.2f°)", self._name, start_temp, end_temp)
            return

        target_rate = mean_gap / (self.closed_loop_time_min / 60.0)
        ratio = target_rate / rate if rate > 0 else KINT_MAX_STEP
        ratio = min(KINT_MAX_STEP, max(1.0 / KINT_MAX_STEP, ratio))

        old_coeff = self.state.coeff_indoor_cool if is_cool else self.state.coeff_indoor_heat
        new_coeff = min(self._max_coef_int, max(MIN_KINT, old_coeff * ratio))

        # Steps that keep going the same way mean Kint is still far from its value
        direction = (new_coeff > old_coeff) - (new_coeff < old_coeff)
        trend = self.state.kint_trend_cool if is_cool else self.state.kint_trend_heat
        trend = trend + direction if direction and trend * direction > 0 else direction

        if is_cool:
            self.state.coeff_indoor_cool = new_coeff
            self.state.coeff_indoor_cool_autolearn += 1
            self.state.kint_trend_cool = trend
            count = self.state.coeff_indoor_cool_autolearn
        else:
            self.state.coeff_indoor_heat = new_coeff
            self.state.coeff_indoor_autolearn += 1
            self.state.kint_trend_heat = trend
            count = self.state.coeff_indoor_autolearn

        # A learned window shows that Kint can be learned
        self._fast_saturated_rises = 0
        ir.async_delete_issue(self._hass, DOMAIN, self._kint_too_high_issue_id)

        self.state.last_learning_status = f"learned_indoor_{'cool' if is_cool else 'heat'}"
        self._learning_just_completed = True
        _LOGGER.info(
            "%s - Auto TPI: Learn indoor (%s) over %.0f min. Rate %.3f °C/h, target rate %.3f °C/h (mean gap %.2f). Kint %.3f -> %.3f (count: %d)",
            self._name,
            "cool" if is_cool else "heat",
            elapsed_min,
            rate,
            target_rate,
            mean_gap,
            old_coeff,
            new_coeff,
            count,
        )

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

            # Directional Protection
            # If we are overcooling (below target) BUT the temperature is Rising (going back to target)
            # AND power is low, then natural recovery is happening. Do not lower Kext.
            # However, if power is still significant, the system is actively cooling and Kext might be too high.
            if gap_in > 0 and current_temp_in > self.state.last_temp_in and self.state.last_power < NATURAL_RECOVERY_POWER_THRESHOLD:
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning during natural undershoot recovery (Temp rising %.2f -> %.2f, power=%.1f%%)",
                    self._name, self.state.last_temp_in, current_temp_in, self.state.last_power * 100
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

            # Directional Protection
            # If we are overheating (above target) BUT the temperature is Falling (going back to target)
            # AND power is low, then natural recovery is happening. Do not lower Kext.
            # However, if power is still significant, the system is actively heating and Kext is likely too high.
            if gap_in < 0 and current_temp_in < self.state.last_temp_in and self.state.last_power < NATURAL_RECOVERY_POWER_THRESHOLD:
                _LOGGER.debug(
                    "%s - Auto TPI: Skipping outdoor learning during natural overshoot recovery (Temp falling %.2f -> %.2f, power=%.1f%%)",
                    self._name, self.state.last_temp_in, current_temp_in, self.state.last_power * 100
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

        # Weighted average: the configured Kext has no weight (the Kext counter starts at 0),
        # then each sample weighs 1 / (count + 1), with the count capped at 50.
        weight_old = min(count, 50)
        avg_coeff = ((old_coeff * weight_old) + coeff_new) / (weight_old + 1)
        _LOGGER.debug("%s - Auto TPI: Outdoor Weighted Average: old=%.3f (weight=%d, real_count=%d), new=%.3f, result=%.3f", self._name, old_coeff, weight_old, count, coeff_new, avg_coeff)

        new_count = count + 1

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

    @property
    def saturation_threshold(self) -> float:
        """The saturation power threshold (default 1.0, 100%)."""
        # This property is expected to be overridden by the mixing/main component.
        # Defaulting to 1.0 for self-contained use if not overridden.
        return 1.0

    def calculate_power(self, setpoint: float, temp_in: float, temp_out: float, state_str: str) -> float:
        """Calculate TPI power with the current coefficients."""
        return self._calculate_power_tpi(setpoint, temp_in, temp_out, state_str)

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

    def shutdown(self) -> None:
        """Stop transient cycle activity owned by the manager."""
        self.state.cycle_active = False

    def update_realized_power(self, realized_percent: float):
        """Update the power actually applied to the underlyings.

        Called by the handler when the realized power differs from the
        requested on_percent. Sources of difference:
        - timing constraints (min_activation_delay, min_deactivation_delay)
        - max_on_percent clamping
        - safety mode override

        This ensures learning uses the actual applied power, not the requested one.
        """
        if self.state.cycle_active:
            old = self.state.last_power
            self.state.last_power = realized_percent
            if abs(old - realized_percent) > 0.001:
                _LOGGER.debug(
                    "%s - Auto TPI: Realized power updated: %.1f%% -> %.1f%%",
                    self._name, old * 100, realized_percent * 100
                )

    async def on_cycle_started(self, on_time_sec: float, off_time_sec: float, on_percent: float, hvac_mode: str):
        """Called when a TPI cycle starts."""
        # Detect if previous cycle was interrupted
        is_expected_interruption = self._learning_just_completed
        self._learning_just_completed = False  # Reset the flag after check

        if self.state.cycle_active and not is_expected_interruption:
            _LOGGER.info("%s - Auto TPI: Previous cycle was interrupted (not completed). Discarding it.", self._name)
            # You could add specific logic here if needed (stats, etc)

        self.state.cycle_active = True

        _LOGGER.debug("%s - Auto TPI: Cycle started. On: %.0fs, Off: %.0fs (%.1f%%), Mode: %s", self._name, on_time_sec, off_time_sec, on_percent * 100, hvac_mode)

        now = dt_util.now()

        # Snapshot current state for learning at the end of the cycle
        self.state.last_temp_in = self._current_temp_in
        self.state.last_temp_out = self._current_temp_out
        self.state.last_order = self._current_target_temp
        self.state.last_power = on_percent if on_percent is not None else 0.0

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

        # Store current cycle params so on_cycle_completed() can read them without params
        self.state.current_cycle_params = {
            "on_time_sec": on_time_sec,
            "off_time_sec": off_time_sec,
            "on_percent": on_percent,
            "hvac_mode": str(hvac_mode),
        }

        await self.async_save_data()

    def _should_learn_continuous_kext(self) -> bool:
        """Check if we should proceed with continuous Kext learning."""
        if not self._continuous_kext:
            return False

        # Must be bootstrapped (at least 1 outdoor sample)
        # We check both modes as we don't know the future mode yet,
        # but technically we should check the count for the CURRENT mode in _learn_kext_continuous.
        # Here we just check if it's generally possible (any learning done).
        # However, to be strict, we can defer the check to _learn_kext_continuous.
        if self.state.coeff_outdoor_autolearn == 0 and self.state.coeff_outdoor_cool_autolearn == 0:
            return False

        # Standard exclusions adapted from _should_learn
        saturation_threshold = self.saturation_threshold
        if not (0 < self.state.last_power < saturation_threshold):
            return False

        if self._current_cycle_interrupted:
            return False

        if self._central_boiler_off:
            return False

        if self._current_is_heating_failure:
            return False

        if self.state.previous_state == "stop":
            return False

        if self.state.last_order == 0:
            return False

        # Significant outdoor delta (> 1.0)
        delta_out = self.state.last_order - self._current_temp_out
        if abs(delta_out) < 1.0:
            return False

        return True

    async def _learn_kext_continuous(self, current_temp_in: float, current_temp_out: float):
        """Perform continuous Kext learning."""
        if not self._should_learn_continuous_kext():
            return

        is_heat = self.state.last_state == "heat"
        is_cool = self.state.last_state == "cool"

        if not (is_heat or is_cool):
            return

        # Check bootstrap for specific mode
        count = self.state.coeff_outdoor_autolearn if is_heat else self.state.coeff_outdoor_cool_autolearn
        if count == 0:
            _LOGGER.debug("%s - Continuous Kext: Not bootstrapped for %s mode", self._name, "heat" if is_heat else "cool")
            self.state.last_learning_status = "continuous_kext_not_bootstrapped"
            return

        # Check setpoint change
        if abs(self._current_target_temp - self.state.last_order) > 0.1:
            _LOGGER.debug("%s - Continuous Kext: Setpoint changed", self._name)
            self.state.last_learning_status = "continuous_kext_setpoint_changed"
            return

        if not self._is_settled_for_kext():
            _LOGGER.debug("%s - Continuous Kext: Room not settled since the last setpoint change", self._name)
            self.state.last_learning_status = "kext_waiting_settling"
            return

        target_temp = self.state.last_order
        gap_in = target_temp - current_temp_in
        gap_out = target_temp - current_temp_out

        # Avoid division by zero or small deltas
        if abs(gap_out) < 1.0:
             # Already checked in _should_learn but good to be safe
             return

        current_indoor = self.state.coeff_indoor_heat if is_heat else self.state.coeff_indoor_cool
        current_outdoor = self.state.coeff_outdoor_heat if is_heat else self.state.coeff_outdoor_cool

        # Formula: correction = Kint * (Gap_In / Gap_Out)
        correction = current_indoor * (gap_in / gap_out)
        target_outdoor = current_outdoor + correction

        # Validations
        if not math.isfinite(target_outdoor) or target_outdoor <= 0:
             _LOGGER.warning("%s - Continuous Kext: Invalid target Kext %.4f", self._name, target_outdoor)
             self.state.last_learning_status = "continuous_kext_invalid"
             return

        MAX_KEXT = 1.2
        if target_outdoor > MAX_KEXT:
             target_outdoor = MAX_KEXT

        # EMA
        alpha = self._continuous_kext_alpha
        new_kext = (current_outdoor * (1.0 - alpha)) + (target_outdoor * alpha)

        # Update state in memory
        if is_heat:
             self.state.coeff_outdoor_heat = new_kext
        else:
             self.state.coeff_outdoor_cool = new_kext

        self.state.last_learning_status = f"continuous_kext_learned_{'cool' if is_cool else 'heat'}"
        self._learning_just_completed = True

        _LOGGER.info(
            "%s - Continuous Kext Learning (%s): Old=%.4f, Target=%.4f, New=%.4f (Alpha=%.3f, GapIn=%.2f, GapOut=%.2f)",
            self._name, "heat" if is_heat else "cool", current_outdoor, target_outdoor, new_kext, alpha, gap_in, gap_out
        )

        # Write Kext once it differs from the configured value by the write resolution (0.001):
        # each EMA step is far smaller, so the comparison is made against the configuration,
        # not against the previous cycle.
        if abs(new_kext - self._default_coef_ext) > 0.001 * self._unit_factor:
            await self.async_update_learning_data(coef_ext=new_kext)

    async def on_cycle_completed(self, e_eff: float = None, **_kw) -> None:
        """Called when a TPI cycle completes."""
        # Validation logic (moved from old _tick)
        now = dt_util.now()

        prev_params = self.state.current_cycle_params or {}
        # A late cycle is judged on its own: the cycles after it learn again
        cycle_gap_detected = False
        if self.state.cycle_start_date is not None and self.state.current_cycle_params is not None:
             # Ensure cycle_start_date is timezone-aware
             cycle_start = self.state.cycle_start_date
             if cycle_start.tzinfo is None:
                 cycle_start = dt_util.as_local(cycle_start)

             elapsed_minutes = (now - cycle_start).total_seconds() / 60
             expected_duration = self._cycle_min
             tolerance = max(expected_duration * 0.1, 1.0)

             duration_diff = elapsed_minutes - expected_duration

             # Case 1: Cycle too short (likely forced restart due to preset/temp change or restart)
             if duration_diff < -tolerance:
                _LOGGER.debug(
                    "%s - Cycle too short: duration=%.1fmin (expected=%.1fmin). Likely forced restart. Skipping learning.",
                    self._name,
                    elapsed_minutes,
                    expected_duration,
                )
                self.state.last_learning_status = "cycle_too_short"
                # We return here because a short cycle shouldn't count towards total_cycles or update stop time
                # (it was interrupted actively)
                self.state.cycle_active = False
                return

             # Case 2: Cycle too long (Gap/Silence detected)
             if duration_diff > tolerance:
                _LOGGER.debug(
                    "%s - Cycle gap detected: duration=%.1fmin (expected=%.1fmin, tolerance=%.1fmin). Resetting cycle but skipping learning.",
                    self._name,
                    elapsed_minutes,
                    expected_duration,
                    tolerance,
                )
                # We do NOT return here. We allow update of total_cycles
                cycle_gap_detected = True
                self.state.last_learning_status = "cycle_gap_detected"
        else:
            # No start date or params, nothing to do
            return

        on_time_sec = prev_params.get("on_time_sec", 0)
        off_time_sec = prev_params.get("off_time_sec", 0)

        if not self.state.cycle_active:
            _LOGGER.debug("%s - Auto TPI: Cycle completed but no cycle active. Ignoring.", self._name)
            return

        self.state.cycle_active = False

        if e_eff is not None:
            self.state.last_power = e_eff

        elapsed_minutes = (on_time_sec + off_time_sec) / 60
        self.state.total_cycles += 1

        log = _LOGGER.info if self.learning_active else _LOGGER.debug
        log("%s - Auto TPI: Cycle #%d completed after %.1f minutes", self._name, self.state.total_cycles, elapsed_minutes)

        # PHASE 2: Kext Learning (per cycle, requires non-saturated power)
        if cycle_gap_detected:
            _LOGGER.debug("%s - Auto TPI: Skipping learning due to invalid cycle (gap detected)", self._name)
        elif self._should_learn():
            _LOGGER.info("%s - Auto TPI: Attempting to learn Kext from cycle data", self._name)
            await self._perform_learning(self._current_temp_in, self._current_temp_out)
        elif self._continuous_kext and self._should_learn_continuous_kext():
            _LOGGER.info("%s - Continuous Kext: Learning active...", self._name)
            await self._learn_kext_continuous(self._current_temp_in, self._current_temp_out)
        else:
            reason = self._get_no_learn_reason()
            _LOGGER.debug("%s - Auto TPI: Not learning Kext this cycle: %s", self._name, reason)
            self.state.last_learning_status = reason

        # PHASE 3: Kint Learning over multi-cycle windows
        self._process_kint_window(
            not cycle_gap_detected
            and not self._current_cycle_interrupted
            and not self._central_boiler_off
            and not self._current_is_heating_failure
        )
        self._record_cycle_temperature(now)

        # The interruption flag applies to the completed cycle only
        self._current_cycle_interrupted = False

        # Centralized persistence: Check if learning is finished and persist if needed
        if self.learning_active:
            await self.process_learning_completion()

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
        # Stability is reached with KINT_WINDOWS_TO_FINISH Kint windows and 50 Kext cycles
        int_cycles = self.int_cycles
        ext_cycles = self.ext_cycles

        if int_cycles == 0 and ext_cycles == 0:
            return 0.0

        # Average of progress for both
        confidence_int = min(int_cycles / KINT_WINDOWS_TO_FINISH, 1.0)
        confidence_ext = min(ext_cycles, 50) / 50.0

        return round((confidence_int + confidence_ext) / 2.0, 2)

    async def start_learning(
        self,
        coef_int: float = None,
        coef_ext: float = None,
        reset_data: bool = True,
    ):
        """Start learning, optionally resetting coefficients and learning data.

        Args:
            coef_int: Target internal coefficient (defaults to configured value)
            coef_ext: Target external coefficient (defaults to configured value)
            reset_data: If True, reset all learning data; if False, resume with existing data
        """
        if self._previous_method_state:
            # The per-cycle learning could drive Kint far too low and left its counters past
            # the end of a session: start again from the default Kint with fresh counters.
            _LOGGER.info("%s - Auto TPI: state of the previous learning method, starting again from Kint %.1f", self._name, KINT_RELEARN_START)
            self._previous_method_state = False
            reset_data = True
            coef_int = KINT_RELEARN_START * self._unit_factor

        # Use provided values, or fallback to default (configured) values
        target_int = coef_int if coef_int is not None else self._default_coef_int
        target_ext = coef_ext if coef_ext is not None else self._default_coef_ext

        if reset_data:
            _LOGGER.info("%s - Auto TPI: Starting learning with coef_int=%.3f, coef_ext=%.3f (resetting all data)", self._name, target_int, target_ext)
            ir.async_delete_issue(self._hass, DOMAIN, self._relearn_issue_id)

            # Reset coefficients to target values
            self.state.coeff_indoor_heat = target_int
            self.state.coeff_indoor_cool = target_int
            self.state.coeff_outdoor_heat = target_ext
            self.state.coeff_outdoor_cool = target_ext

            # Reset all counters
            self.state.kint_trend_heat = 0
            self.state.kint_trend_cool = 0
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
            self.state.total_cycles = 0
            self.state.last_learning_status = "learning_started"
            self.state.cycle_start_date = dt_util.now()
            self.state.cycle_active = False
            self.state.current_cycle_params = None  # Ensure first tick starts fresh
        else:
            # If start_learning is called with explicit target values that differ from defaults,
            # apply them as an update to the current state, even without a full reset.
            if coef_int is not None and abs(coef_int - self._default_coef_int) > 0.001:
                _LOGGER.info("%s - Auto TPI: Updating Kint to %.3f (Manual override in resume)", self._name, target_int)
                self.state.coeff_indoor_heat = target_int
                self.state.coeff_indoor_cool = target_int

            if coef_ext is not None and abs(coef_ext - self._default_coef_ext) > 0.001:
                _LOGGER.info("%s - Auto TPI: Updating Kext to %.3f (Manual override in resume)", self._name, target_ext)
                self.state.coeff_outdoor_heat = target_ext
                self.state.coeff_outdoor_cool = target_ext

            _LOGGER.info(
                "%s - Auto TPI: Resuming learning with existing data (coef_int=%.3f, coef_ext=%.3f, cycles=%d)",
                self._name,
                self.state.coeff_indoor_heat,
                self.state.coeff_outdoor_heat,
                self.state.total_cycles,
            )
            # Update status to indicate learning has resumed
            self.state.last_learning_status = "learning_resumed"

        # Always enable learning when activating
        self.state.autolearn_enabled = True
        self._saturated_rise = None
        self._fast_saturated_rises = 0
        ir.async_delete_issue(self._hass, DOMAIN, self._kint_too_high_issue_id)

        # Set start date only if it's a new session (reset) or if it wasn't set (first start)
        if reset_data or self.state.learning_start_date is None:
            self.state.learning_start_date = dt_util.now()

        self._kint_window_start = None

        await self.async_save_data()

    async def stop_learning(self):
        """Stop learning and keep the learned coefficients."""
        _LOGGER.info("%s - Auto TPI: Stopping learning", self._name)
        self.state.autolearn_enabled = False
        # Do not clear learning_start_date to allow resuming or display in history
        self.state.last_learning_status = "learning_stopped"
        self._kint_window_start = None
        await self.async_save_data()

    async def reset_learning_data(self):
        _LOGGER.info("%s - Auto TPI: Resetting all learning data", self._name)
        self.state = AutoTpiState()
        self.state.cycle_active = False
        await self.async_save_data()
