"""Bang-Coast Manager for intelligent anticipation mode.

This module implements a state machine with three phases:
- BANG: Full power (on_percent=1.0) for large temperature gaps
- COAST: Zero power (on_percent=0) while thermal inertia carries temperature toward target
- MAINTAIN: TPI + D-term for small gaps and fine regulation

Learning: After each COAST phase, the system learns an inertia coefficient
that predicts how much temperature will rise after cutoff, based on the
current slope. This naturally adapts to the number of open valves on a
central boiler system.
"""

import logging
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    BANG_COAST_MIN_SLOPE_FOR_LEARNING,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "versatile_thermostat.bang_coast"
# Maximum duration of COAST phase (seconds) before forced return to MAINTAIN
MAX_COAST_DURATION_SEC = 1800  # 30 minutes


class BangCoastPhase(Enum):
    """The three phases of the Bang-Coast state machine."""

    BANG = "bang"
    COAST = "coast"
    MAINTAIN = "maintain"


@dataclass
class BangCoastLearningData:
    """Persistent learning data for Bang-Coast algorithm."""

    # Learned inertia coefficient (hours). Predicts coast rise as coeff * slope.
    learned_inertia_coeff: float = 0.4
    # Number of completed BANG-COAST cycles observed
    cycle_count: int = 0
    # Average coast rise in degrees (diagnostic)
    avg_coast_rise: float = 0.0
    # Average BANG phase duration in seconds (diagnostic)
    avg_bang_duration: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dict for persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BangCoastLearningData":
        """Create from persisted dict."""
        return cls(
            learned_inertia_coeff=data.get("learned_inertia_coeff", 0.4),
            cycle_count=data.get("cycle_count", 0),
            avg_coast_rise=data.get("avg_coast_rise", 0.0),
            avg_bang_duration=data.get("avg_bang_duration", 0.0),
        )


class BangCoastManager:
    """Manages the Bang-Coast state machine and inertia learning.

    Args:
        hass: Home Assistant instance
        unique_id: Unique identifier for this thermostat (used for storage key)
        name: Display name for logging
        bang_activation_threshold: Temperature gap (°C) to trigger BANG phase
        initial_inertia_coeff: Initial inertia coefficient before learning (hours)
        learning_alpha: EMA learning rate (0-1)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        bang_activation_threshold: float = 1.0,
        initial_inertia_coeff: float = 0.4,
        learning_alpha: float = 0.3,
    ) -> None:
        """Initialize the Bang-Coast Manager."""
        self._hass = hass
        self._unique_id = unique_id
        self._name = name
        self._bang_activation_threshold = bang_activation_threshold
        self._initial_inertia_coeff = initial_inertia_coeff
        self._learning_alpha = learning_alpha

        # Persistence
        storage_key = f"{STORAGE_KEY_PREFIX}.{unique_id.replace('.', '_')}"
        self._store = Store(hass, STORAGE_VERSION, storage_key)
        self._data = BangCoastLearningData(
            learned_inertia_coeff=initial_inertia_coeff
        )

        # State machine
        self._phase = BangCoastPhase.MAINTAIN
        self._bang_start_time: datetime | None = None
        self._coast_start_time: datetime | None = None
        self._coast_start_temp: float | None = None
        self._coast_peak_temp: float | None = None
        self._slope_at_cutoff: float | None = None

        _LOGGER.debug(
            "%s - BangCoastManager created: threshold=%.1f, initial_coeff=%.2f, alpha=%.2f",
            self._name,
            bang_activation_threshold,
            initial_inertia_coeff,
            learning_alpha,
        )

    @property
    def current_phase(self) -> BangCoastPhase:
        """Return the current phase of the state machine."""
        return self._phase

    @property
    def learned_inertia_coeff(self) -> float:
        """Return the current learned inertia coefficient."""
        return self._data.learned_inertia_coeff

    @property
    def learning_data(self) -> BangCoastLearningData:
        """Return the learning data for diagnostics."""
        return self._data

    def reset_to_maintain(self) -> None:
        """Reset the state machine to MAINTAIN phase.

        Call this when the thermostat is turned off (HVAC_OFF) to ensure
        the state machine doesn't carry stale BANG/COAST state across
        off/on transitions.
        """
        if self._phase != BangCoastPhase.MAINTAIN:
            _LOGGER.info(
                "%s - BangCoast: Resetting from %s to MAINTAIN (thermostat off or mode change).",
                self._name,
                self._phase.value,
            )
        self._phase = BangCoastPhase.MAINTAIN
        self._bang_start_time = None
        self._coast_start_time = None
        self._coast_start_temp = None
        self._coast_peak_temp = None
        self._slope_at_cutoff = None

    def process(
        self,
        target_temp: float,
        current_temp: float,
        slope: float | None,
        base_on_percent: float,
        coef_d: float,
    ) -> float:
        """Process one TPI cycle and return the final on_percent.

        This method manages the state machine transitions and returns:
        - 1.0 during BANG phase (full power)
        - 0.0 during COAST phase (zero power, coasting on inertia)
        - TPI-D value during MAINTAIN phase (base_on_percent - coef_d * slope)

        Args:
            target_temp: Target temperature
            current_temp: Current room temperature
            slope: Temperature slope in °C/h (positive = rising)
            base_on_percent: TPI-calculated on_percent (P-only, for reference)
            coef_d: Derivative coefficient for D-term

        Returns:
            final_on_percent: The on_percent to send to the valve [0, 1]
        """
        # Safety: if temperature data is unavailable, return base_on_percent unchanged
        if target_temp is None or current_temp is None:
            _LOGGER.debug(
                "%s - BangCoast: target or current temp is None, skipping state machine.",
                self._name,
            )
            return max(0.0, min(1.0, base_on_percent))

        delta_t = target_temp - current_temp
        safe_slope = slope if slope is not None else 0.0

        # --- State transitions ---
        if self._phase == BangCoastPhase.MAINTAIN:
            self._process_maintain(delta_t, target_temp, current_temp, safe_slope)
        elif self._phase == BangCoastPhase.BANG:
            self._process_bang(target_temp, current_temp, safe_slope)
        elif self._phase == BangCoastPhase.COAST:
            self._process_coast(delta_t, target_temp, current_temp, safe_slope)

        # --- Compute output based on current phase ---
        if self._phase == BangCoastPhase.BANG:
            final_on_percent = 1.0
        elif self._phase == BangCoastPhase.COAST:
            final_on_percent = 0.0
        else:
            # MAINTAIN: apply TPI + D-term
            d_correction = coef_d * safe_slope if safe_slope > 0 else 0.0
            final_on_percent = base_on_percent - d_correction
            final_on_percent = max(0.0, min(1.0, final_on_percent))

        _LOGGER.debug(
            "%s - BangCoast: phase=%s, delta_T=%.2f, slope=%.2f, base=%.2f, final=%.2f, coeff=%.3f",
            self._name,
            self._phase.value,
            delta_t,
            safe_slope,
            base_on_percent,
            final_on_percent,
            self._data.learned_inertia_coeff,
        )

        return final_on_percent

    def _process_maintain(
        self,
        delta_t: float,
        target_temp: float,
        current_temp: float,
        slope: float,
    ) -> None:
        """Process transitions from MAINTAIN phase."""
        if delta_t > self._bang_activation_threshold:
            self._enter_bang(current_temp)

    def _process_bang(
        self,
        target_temp: float,
        current_temp: float,
        slope: float,
    ) -> None:
        """Process transitions from BANG phase.

        Transition to COAST when predicted final temperature reaches target:
        current_temp + learned_inertia_coeff * slope >= target_temp
        """
        if slope <= 0:
            # Temperature not rising yet during BANG - stay in BANG
            return

        predicted_coast_rise = self._data.learned_inertia_coeff * slope
        predicted_final_temp = current_temp + predicted_coast_rise

        if predicted_final_temp >= target_temp:
            self._enter_coast(current_temp, slope)

    def _process_coast(
        self,
        delta_t: float,
        target_temp: float,
        current_temp: float,
        slope: float,
    ) -> None:
        """Process transitions from COAST phase.

        Track peak temperature and transition to MAINTAIN when:
        - slope becomes negative (peak reached, temperature starts falling)
        Safety: return to BANG if temperature drops too much.
        """
        # Track peak temperature during coast
        if self._coast_peak_temp is None or current_temp > self._coast_peak_temp:
            self._coast_peak_temp = current_temp

        # Transition: peak reached (temperature starts falling)
        if slope < 0:
            self._end_coast_and_learn(target_temp)
            return

        # Safety: timeout to avoid getting stuck in COAST (e.g., slope stays at 0)
        if self._coast_start_time is not None:
            coast_elapsed = (dt_util.utcnow() - self._coast_start_time).total_seconds()
            if coast_elapsed > MAX_COAST_DURATION_SEC:
                _LOGGER.warning(
                    "%s - BangCoast: COAST timeout after %ds. Forcing return to MAINTAIN.",
                    self._name,
                    int(coast_elapsed),
                )
                self._end_coast_and_learn(target_temp)
                return

        # Safety: if temperature dropped too much, go back to BANG
        if delta_t > self._bang_activation_threshold:
            _LOGGER.warning(
                "%s - BangCoast: Safety trigger during COAST. delta_T=%.2f > threshold=%.1f. Returning to BANG.",
                self._name,
                delta_t,
                self._bang_activation_threshold,
            )
            self._enter_bang(current_temp)

    def _enter_bang(self, current_temp: float) -> None:
        """Transition to BANG phase."""
        self._phase = BangCoastPhase.BANG
        self._bang_start_time = dt_util.utcnow()
        self._coast_start_time = None
        self._coast_start_temp = None
        self._coast_peak_temp = None
        self._slope_at_cutoff = None

        _LOGGER.info(
            "%s - BangCoast: Entering BANG phase at %.1f°C",
            self._name,
            current_temp,
        )

    def _enter_coast(self, current_temp: float, slope: float) -> None:
        """Transition to COAST phase."""
        self._phase = BangCoastPhase.COAST
        self._coast_start_time = dt_util.utcnow()
        self._coast_start_temp = current_temp
        self._coast_peak_temp = current_temp
        self._slope_at_cutoff = slope

        _LOGGER.info(
            "%s - BangCoast: Entering COAST phase at %.1f°C (slope=%.2f°C/h, predicted_rise=%.2f°C)",
            self._name,
            current_temp,
            slope,
            self._data.learned_inertia_coeff * slope,
        )

    def _end_coast_and_learn(self, target_temp: float) -> None:
        """End COAST phase and learn from the experience."""
        self._phase = BangCoastPhase.MAINTAIN

        # Calculate BANG duration for diagnostics
        bang_duration = 0.0
        if self._bang_start_time is not None:
            bang_duration = (dt_util.utcnow() - self._bang_start_time).total_seconds()

        # Learn from COAST phase
        if (
            self._coast_start_temp is not None
            and self._coast_peak_temp is not None
            and self._slope_at_cutoff is not None
            and self._slope_at_cutoff >= BANG_COAST_MIN_SLOPE_FOR_LEARNING
        ):
            actual_coast_rise = self._coast_peak_temp - self._coast_start_temp
            observed_coeff = actual_coast_rise / self._slope_at_cutoff

            # EMA update
            old_coeff = self._data.learned_inertia_coeff
            self._data.learned_inertia_coeff = (
                (1 - self._learning_alpha) * old_coeff
                + self._learning_alpha * observed_coeff
            )
            # Clamp to reasonable range (0.01 to 2.0 hours)
            self._data.learned_inertia_coeff = max(
                0.01, min(2.0, self._data.learned_inertia_coeff)
            )

            # Update diagnostics
            self._data.cycle_count += 1
            n = self._data.cycle_count
            self._data.avg_coast_rise = (
                (self._data.avg_coast_rise * (n - 1) + actual_coast_rise) / n
            )
            self._data.avg_bang_duration = (
                (self._data.avg_bang_duration * (n - 1) + bang_duration) / n
            )

            overshoot = self._coast_peak_temp - target_temp

            _LOGGER.info(
                "%s - BangCoast: Learning from COAST. "
                "coast_rise=%.2f°C, slope_at_cutoff=%.2f°C/h, "
                "observed_coeff=%.3fh, new_coeff=%.3fh (was %.3fh), "
                "overshoot=%.2f°C, cycles=%d",
                self._name,
                actual_coast_rise,
                self._slope_at_cutoff,
                observed_coeff,
                self._data.learned_inertia_coeff,
                old_coeff,
                overshoot,
                self._data.cycle_count,
            )
        else:
            reason = "slope too low" if (
                self._slope_at_cutoff is not None
                and self._slope_at_cutoff < BANG_COAST_MIN_SLOPE_FOR_LEARNING
            ) else "incomplete data"
            _LOGGER.debug(
                "%s - BangCoast: Skipping learning (%s). Entering MAINTAIN.",
                self._name,
                reason,
            )

        # Reset transient state
        self._bang_start_time = None
        self._coast_start_time = None
        self._coast_start_temp = None
        self._coast_peak_temp = None
        self._slope_at_cutoff = None

    async def async_load_data(self) -> None:
        """Load persisted learning data."""
        data = await self._store.async_load()
        if data:
            self._data = BangCoastLearningData.from_dict(data)
            _LOGGER.info(
                "%s - BangCoast: Data loaded. coeff=%.3fh, cycles=%d",
                self._name,
                self._data.learned_inertia_coeff,
                self._data.cycle_count,
            )
        else:
            self._data = BangCoastLearningData(
                learned_inertia_coeff=self._initial_inertia_coeff
            )
            _LOGGER.info(
                "%s - BangCoast: No persisted data. Using initial coeff=%.3fh",
                self._name,
                self._initial_inertia_coeff,
            )

    async def async_save_data(self) -> None:
        """Save learning data to persistent storage."""
        await self._store.async_save(self._data.to_dict())

    def get_state_for_attributes(self) -> dict:
        """Return state data for HA entity attributes (diagnostics)."""
        return {
            "bang_coast_phase": self._phase.value,
            "bang_coast_inertia_coeff": round(self._data.learned_inertia_coeff, 3),
            "bang_coast_cycle_count": self._data.cycle_count,
            "bang_coast_avg_coast_rise": round(self._data.avg_coast_rise, 2),
            "bang_coast_avg_bang_duration": round(self._data.avg_bang_duration, 0),
        }
