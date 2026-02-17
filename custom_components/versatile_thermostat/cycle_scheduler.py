"""CycleScheduler: orchestrates cycles for multiple underlyings within a master cycle.

For switches: manages staggered ON/OFF PWM timing to minimize overlap
and smooth electrical load.
For valves: passthrough mode that calls set_valve_open_percent() directly
without temporal scheduling.
"""

import logging
from typing import Any, Callable

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_call_later


from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF

from .cycle_tick_logic import (
    UnderlyingCycleState,
    compute_circular_offsets,
    compute_target_state,
    evaluate_need_on,
    evaluate_need_off,
    compute_e_eff,
)
_LOGGER = logging.getLogger(__name__)


def calculate_cycle_times(
    on_percent: float,
    cycle_min: int,
    minimal_activation_delay: int | None = 0,
    minimal_deactivation_delay: int | None = 0,
) -> tuple[int, int, bool]:
    """Convert on_percent to on_time_sec and off_time_sec.

    Applies minimal activation and deactivation delays to avoid
    very short on/off periods that may damage equipment or be ineffective.

    Args:
        on_percent: The calculated heating percentage (0.0 to 1.0)
        cycle_min: The cycle duration in minutes
        minimal_activation_delay: Minimum on time in seconds (below this, turn off)
        minimal_deactivation_delay: Minimum off time in seconds (below this, stay on)

    Returns:
        Tuple of (on_time_sec, off_time_sec, forced_by_timing)
        - forced_by_timing: True if min_on or min_off delays modified the percentage significantly.
    """
    min_on = minimal_activation_delay if minimal_activation_delay is not None else 0
    min_off = minimal_deactivation_delay if minimal_deactivation_delay is not None else 0

    on_percent = max(0.0, min(1.0, on_percent))

    cycle_sec = cycle_min * 60
    on_time_sec = on_percent * cycle_sec
    forced_by_timing = False

    if on_time_sec > 0 and on_time_sec < min_on:
        on_time_sec = 0
        forced_by_timing = True

    off_time_sec = cycle_sec - on_time_sec

    if on_time_sec < cycle_sec and off_time_sec < min_off:
        on_time_sec = cycle_sec
        off_time_sec = 0
        forced_by_timing = True

    return int(on_time_sec), int(off_time_sec), forced_by_timing


class CycleScheduler:
    """Orchestrates cycles for multiple underlyings within a master cycle.

    For switches: all underlyings operate within the same time window.
    ON periods are staggered using computed offsets to minimize overlap.
    For valves: passthrough mode — calls set_valve_open_percent() directly.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        underlyings: list,
        cycle_duration_sec: float,
        min_activation_delay: int = 0,
        min_deactivation_delay: int = 0,
    ):
        self._hass = hass
        self._thermostat = thermostat
        self._underlyings = underlyings
        self._cycle_duration_sec = cycle_duration_sec
        self.min_activation_delay: int = min_activation_delay
        self.min_deactivation_delay: int = min_deactivation_delay
        self._tick_unsub: CALLBACK_TYPE | None = None
        self._cycle_end_unsub: CALLBACK_TYPE | None = None
        self._on_cycle_start_callbacks: list[Callable] = []
        self._on_cycle_end_callbacks: list[Callable] = []
        # Current cycle parameters (for repeat at cycle end)
        self._current_hvac_mode: VThermHvacMode | None = None
        self._current_on_time_sec: float = 0
        self._current_off_time_sec: float = 0
        self._current_on_percent: float = 0
        self._states: list[UnderlyingCycleState] = []
        self._penalty: float = 0.0
        self._cycle_start_time: float = 0.0
        # Detect valve mode from underlying types
        self._is_valve_mode: bool = self._detect_valve_mode()

    @property
    def is_cycle_running(self) -> bool:
        """Return True if a cycle is currently scheduled."""
        return self._tick_unsub is not None or self._cycle_end_unsub is not None

    @property
    def is_valve_mode(self) -> bool:
        """Return True if managing valve underlyings (passthrough mode)."""
        return self._is_valve_mode

    def _detect_valve_mode(self) -> bool:
        """Detect if underlyings are valves by checking entity_type."""
        from .underlyings import UnderlyingEntityType  # pylint: disable=import-outside-toplevel
        if not self._underlyings:
            return False
        return self._underlyings[0].entity_type in (
            UnderlyingEntityType.VALVE,
            UnderlyingEntityType.VALVE_REGULATION,
        )

    def register_cycle_start_callback(self, callback: Callable):
        """Register a callback to be called at the start of each master cycle.

        Callback signature: async def callback(on_time_sec, off_time_sec, on_percent, hvac_mode)
        """
        self._on_cycle_start_callbacks.append(callback)

    def register_cycle_end_callback(self, callback: Callable[[float], Any]):
        """Register a callback to be called at the end of each master cycle."""
        self._on_cycle_end_callbacks.append(callback)

    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
        on_percent: float,
        force: bool = False,
        _from_cycle_end: bool = False,
    ):
        """Start a new master cycle for all underlyings.

        Computes on_time_sec and off_time_sec from on_percent, applying
        min_activation_delay and min_deactivation_delay constraints.

        Args:
            hvac_mode: Current HVAC mode.
            on_percent: Power percentage as a fraction (0.0 to 1.0).
            force: If True, cancel any running cycle and restart immediately.
            _from_cycle_end: Internal flag — True when called from _on_master_cycle_end.
        """
        cycle_min = self._cycle_duration_sec / 60
        on_time_sec, off_time_sec, _ = calculate_cycle_times(
            on_percent,
            cycle_min,
            self.min_activation_delay,
            self.min_deactivation_delay,
        )

        # Always update thermostat timing attributes immediately so sensors
        # reflect the latest computed value, even when the cycle returns early.
        self._thermostat._on_time_sec = on_time_sec
        self._thermostat._off_time_sec = off_time_sec

        if self.is_cycle_running and not force:
            if self._current_on_time_sec > 0:
                # A real cycle is actively running — don't interrupt it.
                # Just update stored params so the next auto-repeat uses them.
                _LOGGER.debug(
                    "%s - Cycle already running (on_time=%.0fs), skipping (force=%s). "
                    "Updating params for next repeat: on_time=%.0f, off_time=%.0f, on_percent=%.2f",
                    self._thermostat,
                    self._current_on_time_sec,
                    force,
                    on_time_sec,
                    off_time_sec,
                    on_percent,
                )
                self._current_hvac_mode = hvac_mode
                self._current_on_time_sec = on_time_sec
                self._current_off_time_sec = off_time_sec
                self._current_on_percent = on_percent
                return
            # Current cycle is idle (on_time=0, device off).
            # Cancel it and allow a real cycle to start.
            _LOGGER.debug(
                "%s - Current cycle is idle (on_time=0), replacing with new cycle",
                self._thermostat,
            )

        self.cancel_cycle()

        # Store current cycle parameters for repeat
        self._current_hvac_mode = hvac_mode
        self._current_on_time_sec = on_time_sec
        self._current_off_time_sec = off_time_sec
        self._current_on_percent = on_percent

        # Compute realized on_percent after timing constraints (for learning callbacks)
        realized_on_percent = on_time_sec / self._cycle_duration_sec if self._cycle_duration_sec > 0 else 0.0

        # Fire cycle start callbacks with realized percent so learners see actual applied power
        await self._fire_cycle_start_callbacks(
            on_time_sec, off_time_sec, realized_on_percent, hvac_mode
        )

        if self._is_valve_mode:
            await self._start_cycle_valve(hvac_mode)
        else:
            await self._start_cycle_switch(
                hvac_mode, on_time_sec, off_time_sec, on_percent
            )

    async def _start_cycle_valve(self, hvac_mode: VThermHvacMode):
        """Valve passthrough: call set_valve_open_percent() on each underlying.

        Valves don't need temporal ON/OFF scheduling. They just need
        their open percentage updated. No master cycle repeat is needed
        because control_heating is called periodically by async_track_time_interval.
        """
        for under in self._underlyings:
            under._hvac_mode = hvac_mode
            await under.set_valve_open_percent()

    async def _start_cycle_switch(
        self,
        hvac_mode: VThermHvacMode,
        on_time_sec: float,
        off_time_sec: float,
        on_percent: float,
    ):
        """Switch True Tick scheduling: initialize cycle and start ticking."""
        # Update on_time/off_time on each underlying for keep-alive and monitoring
        for under in self._underlyings:
            under._on_time_sec = on_time_sec
            under._off_time_sec = off_time_sec
            under._hvac_mode = hvac_mode

        if hvac_mode == VThermHvacMode_OFF or on_time_sec <= 0:
            # Turn off all underlyings
            for under in self._underlyings:
                if under.is_device_active:
                    await under.turn_off()
                under._should_be_on = False
            # Schedule next cycle evaluation
            self._cycle_end_unsub = async_call_later(self._hass, self._cycle_duration_sec, self._on_master_cycle_end)
            return

        if on_time_sec >= self._cycle_duration_sec:
            # 100% power: Turn on all underlyings unconditionally to enforce state
            for under in self._underlyings:
                await under.turn_on()
                under._should_be_on = True
            # Schedule next cycle evaluation
            self._cycle_end_unsub = async_call_later(self._hass, self._cycle_duration_sec, self._on_master_cycle_end)
            return

        self._init_cycle(on_percent)

        # Start ticking immediately with is_initial=True to enforce state
        await self._tick(_is_initial=True)
        
        # Also ensure master cycle end is scheduled independently to wrap up the cycle
        self._cycle_end_unsub = async_call_later(self._hass, self._cycle_duration_sec, self._on_master_cycle_end)

    def _init_cycle(self, on_percent: float):
        """Initialize states and penalty for the new cycle.

        Uses circular offsets for evenly distributed power across underlyings,
        with natural wrap-around for smooth load distribution.
        """
        self._penalty = 0.0
        import time
        self._cycle_start_time = time.time()

        n = len(self._underlyings)
        on_time = self._cycle_duration_sec * on_percent
        offsets = compute_circular_offsets(self._cycle_duration_sec, n)

        self._states = []
        for i, under in enumerate(self._underlyings):
            state = UnderlyingCycleState(under, offsets[i])
            state.on_t = offsets[i]
            state.on_time = on_time
            state.off_t = (state.on_t + state.on_time) % self._cycle_duration_sec
            self._states.append(state)

        _LOGGER.debug(
            "%s - Initialized true tick cycle: on_percent=%.2f, offsets=%s",
            self._thermostat, on_percent, offsets
        )

    async def _tick(self, _now=None, _is_initial: bool = False):
        """Evaluate all underlyings and schedule the next tick.

        When _is_initial=True (called at cycle start), current_t is forced to 0.0
        to avoid floating-point drift, and the is_device_active check is skipped so
        the desired state is always enforced unconditionally on the first tick.
        """
        import time
        from homeassistant.util import dt as dt_util
        now = time.time()
        current_t = 0.0 if _is_initial else (now - self._cycle_start_time)

        if not _is_initial and current_t >= self._cycle_duration_sec:
            # We reached the end of the cycle; let the master cycle end handle it.
            return

        next_global_tick = self._cycle_duration_sec - current_t

        for state in self._states:
            under = state.underlying

            target_is_on, next_tick, state_duration = compute_target_state(
                state.on_t, state.off_t, current_t, self._cycle_duration_sec
            )

            # Update global next tick to the earliest upcoming event
            time_to_next = next_tick - current_t
            if time_to_next > 0 and time_to_next < next_global_tick:
                next_global_tick = time_to_next

            under_dt = 0.0
            if under.last_change:
                under_dt = (dt_util.utcnow() - under.last_change).total_seconds()
            else:
                under_dt = 999999.0  # Safe large value if no history

            if target_is_on and (_is_initial or not under.is_device_active):
                action, new_on_t, pen_delta = evaluate_need_on(
                    under_dt, state_duration,
                    self.min_deactivation_delay, self.min_activation_delay,
                    state.on_t, current_t
                )
                if action == 'turn_on':
                    if not under.is_device_active:
                        _LOGGER.info(
                            "%s - tick turn_on (state_duration=%.1fs, initial=%s)",
                            under, state_duration, _is_initial
                        )
                        await under.turn_on()
                        under._should_be_on = True
                elif action == 'skip' and new_on_t is not None:
                    _LOGGER.debug(
                        "%s - tick skip turn_on (racollage), on_t shifted %.1f -> %.1f, penalty=%.1f",
                        under, state.on_t, new_on_t, pen_delta
                    )
                    state.on_t = new_on_t
                    self._penalty += pen_delta
                    resched_time = new_on_t - current_t
                    if 0 < resched_time < next_global_tick:
                        next_global_tick = resched_time

            elif not target_is_on and (_is_initial or under.is_device_active):
                action, new_off_t, pen_delta = evaluate_need_off(
                    under_dt, state_duration,
                    self.min_activation_delay, self.min_deactivation_delay,
                    state.off_t, current_t
                )
                if action == 'turn_off':
                    if under.is_device_active:
                        _LOGGER.info(
                            "%s - tick turn_off (state_duration=%.1fs, initial=%s)",
                            under, state_duration, _is_initial
                        )
                        await under.turn_off()
                        under._should_be_on = False
                elif action == 'skip' and new_off_t is not None:
                    _LOGGER.debug(
                        "%s - tick skip turn_off (racollage), off_t shifted %.1f -> %.1f, penalty=%.1f",
                        under, state.off_t, new_off_t, pen_delta
                    )
                    state.off_t = new_off_t
                    self._penalty += pen_delta
                    resched_time = new_off_t - current_t
                    if 0 < resched_time < next_global_tick:
                        next_global_tick = resched_time

        # Ensure we do not schedule too fast (< 0.1s)
        next_global_tick = max(0.1, next_global_tick)

        # Schedule next tick
        self._tick_unsub = async_call_later(self._hass, next_global_tick, self._tick)

    async def _on_master_cycle_end(self, _now):
        """Called at the end of the master cycle. Compute e_eff and restart."""
        # Compute real cycle duration since _init_cycle based on time
        # If no states exist (e.g. 0% or 100% fixed), e_eff logic might differ
        # But compute_e_eff handles it if we pass proper values
        
        # 0% or OFF will have no states initialization if it didn't call _init_cycle
        # We can just fall back to standard calculation for these limits
        import time
        real_cycle_duration = self._cycle_duration_sec
        if self._cycle_start_time > 0:
            elapsed = time.time() - self._cycle_start_time
            if elapsed > 0:
                real_cycle_duration = elapsed

        e_eff = compute_e_eff(
            self._current_on_percent, 
            self._penalty, 
            real_cycle_duration, 
            len(self._underlyings)
        )

        _LOGGER.debug(
            "%s - cycle end: dur=%.1f, on_pct=%.2f, pen=%.1f -> e_eff=%.3f",
            self._thermostat, real_cycle_duration, self._current_on_percent, self._penalty, e_eff
        )

        # Fire cycle end callbacks with e_eff
        await self._fire_cycle_end_callbacks(e_eff)

        # Increment energy
        self._thermostat.incremente_energy()

        # Restart cycle with same parameters
        await self.start_cycle(
            self._current_hvac_mode,
            self._current_on_percent,
            force=True,
            _from_cycle_end=True,
        )

    def cancel_cycle(self):
        """Cancel the current cycle if one is running."""
        if self._tick_unsub:
            self._tick_unsub()
            self._tick_unsub = None
        if self._cycle_end_unsub:
            self._cycle_end_unsub()
            self._cycle_end_unsub = None
        self._states = []
        self._current_on_time_sec = 0
        self._current_off_time_sec = 0
        _LOGGER.debug("%s - Cycle cancelled", self._thermostat)

    async def _fire_cycle_start_callbacks(
        self, on_time_sec, off_time_sec, on_percent, hvac_mode
    ):
        """Fire all registered cycle start callbacks."""
        for callback in self._on_cycle_start_callbacks:
            try:
                await callback(
                    on_time_sec=on_time_sec,
                    off_time_sec=off_time_sec,
                    on_percent=on_percent,
                    hvac_mode=hvac_mode,
                )
            except Exception as ex:
                _LOGGER.warning(
                    "%s - Error calling cycle start callback %s: %s",
                    self._thermostat,
                    callback,
                    ex,
                )

    async def _fire_cycle_end_callbacks(self, e_eff: float):
        """Fire all registered cycle end callbacks with e_eff."""
        for callback in self._on_cycle_end_callbacks:
            try:
                await callback(e_eff=e_eff)
            except Exception as ex:
                _LOGGER.warning(
                    "%s - Error calling cycle end callback %s: %s",
                    self._thermostat,
                    callback,
                    ex,
                )
