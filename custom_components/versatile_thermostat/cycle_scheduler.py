"""CycleScheduler: orchestrates cycles for multiple underlyings within a master cycle.

For switches: manages staggered ON/OFF PWM timing to minimize overlap
and smooth electrical load.
For valves: passthrough mode that calls set_valve_open_percent() directly
without temporal scheduling.
"""

import logging
import time
from .log_collector import get_vtherm_logger
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
_LOGGER = get_vtherm_logger(__name__)


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
        # Active cycle parameters describe what is physically being executed
        # right now. They intentionally differ from _current_* when a running
        # cycle receives non-forced updates that should only apply to the next
        # repeat at cycle end.
        self._active_hvac_mode: VThermHvacMode | None = None
        self._active_on_time_sec: float = 0
        self._active_off_time_sec: float = 0
        self._active_on_percent: float = 0
        self._states: list[UnderlyingCycleState] = []
        self._penalty: float = 0.0
        self._cycle_start_time: float = 0.0
        # Guard flags to keep is_cycle_running=True during async yield points
        # where timers are not yet (re-)installed:
        # _is_cancelling: True while cancel_cycle() awaits _fire_cycle_end_callbacks()
        # _is_starting:   True while start_cycle() awaits callbacks or device-control
        #                 operations before the new timers are set
        self._is_cancelling: bool = False
        self._is_starting: bool = False
        # Detect valve mode from underlying types
        self._is_valve_mode: bool = self._detect_valve_mode()

    @property
    def is_cycle_running(self) -> bool:
        """Return True if a cycle is currently scheduled or in a lifecycle transition.

        _is_cancelling stays True while cancel_cycle() awaits _fire_cycle_end_callbacks(),
        preventing concurrent start_cycle(force=False) from seeing is_cycle_running=False
        and starting a duplicate cycle during that window (Race 1).

        _is_starting stays True while start_cycle() has finished cancellation but has not
        yet finished device-control setup (including _fire_cycle_start_callbacks and
        _start_cycle_switch/_start_cycle_valve), preventing concurrent start_cycle(force=False)
        from starting a duplicate cycle during that window (Race 2).
        """
        return self._tick_unsub is not None or self._cycle_end_unsub is not None or self._is_cancelling or self._is_starting

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

    def _set_pending_cycle(
        self,
        hvac_mode: VThermHvacMode | None,
        on_time_sec: float,
        off_time_sec: float,
        on_percent: float,
    ) -> None:
        """Store parameters that the next cycle repeat must use."""
        self._current_hvac_mode = hvac_mode
        self._current_on_time_sec = on_time_sec
        self._current_off_time_sec = off_time_sec
        self._current_on_percent = on_percent

    def _set_active_cycle(
        self,
        hvac_mode: VThermHvacMode | None,
        on_time_sec: float,
        off_time_sec: float,
        on_percent: float,
    ) -> None:
        """Store parameters of the master cycle currently being executed."""
        self._active_hvac_mode = hvac_mode
        self._active_on_time_sec = on_time_sec
        self._active_off_time_sec = off_time_sec
        self._active_on_percent = on_percent

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
            if self._is_valve_mode:
                # Valve mode must keep the current master-cycle window for
                # learning callbacks, but the physical valve command still has
                # to follow each new regulation result immediately.
                _LOGGER.debug(
                    "%s - Valve cycle already running, applying immediate update: "
                    "on_time=%.0f, off_time=%.0f, on_percent=%.2f",
                    self._thermostat,
                    on_time_sec,
                    off_time_sec,
                    on_percent,
                )
                self._set_pending_cycle(hvac_mode, on_time_sec, off_time_sec, on_percent)
                self._set_active_cycle(hvac_mode, on_time_sec, off_time_sec, on_percent)
                await self._apply_valve_command(hvac_mode, on_time_sec, off_time_sec)
                return
            if self._active_on_time_sec > 0:
                # A real cycle is actively running — don't interrupt it.
                # Just update stored params so the next auto-repeat uses them.
                _LOGGER.debug(
                    "%s - Cycle already running (on_time=%.0fs), skipping (force=%s). "
                    "Updating params for next repeat: on_time=%.0f, off_time=%.0f, on_percent=%.2f",
                    self._thermostat,
                    self._active_on_time_sec,
                    force,
                    on_time_sec,
                    off_time_sec,
                    on_percent,
                )
                self._set_pending_cycle(hvac_mode, on_time_sec, off_time_sec, on_percent)
                return
            # Current cycle is idle (on_time=0, device off).
            # Cancel it and allow a real cycle to start.
            _LOGGER.debug(
                "%s - Current cycle is idle (on_time=0), replacing with new cycle",
                self._thermostat,
            )

        await self._cancel_cycle_impl()

        # Compute realized on_percent after timing constraints (for learning callbacks)
        # This is the actual percentage that will be executed physically
        realized_on_percent = on_time_sec / self._cycle_duration_sec if self._cycle_duration_sec > 0 else 0.0

        # Store current cycle parameters for repeat
        self._set_pending_cycle(hvac_mode, on_time_sec, off_time_sec, realized_on_percent)
        self._set_active_cycle(hvac_mode, on_time_sec, off_time_sec, realized_on_percent)

        # _is_starting guards the Race window: after _cancel_cycle_impl() cleared all
        # timers and flags, but before the new timers are set by _start_cycle_switch() or
        # _start_cycle_valve(). During this window, is_cycle_running must return True to
        # prevent concurrent start_cycle(force=False) from starting a duplicate full cycle.
        self._is_starting = True
        try:
            # Fire cycle start callbacks with realized percent so learners see actual applied power
            await self._fire_cycle_start_callbacks(on_time_sec, off_time_sec, realized_on_percent, hvac_mode)

            if self._is_valve_mode:
                await self._start_cycle_valve(hvac_mode)
            else:
                await self._start_cycle_switch(hvac_mode, on_time_sec, off_time_sec, realized_on_percent)
        finally:
            self._is_starting = False

    async def _apply_valve_command(
        self,
        hvac_mode: VThermHvacMode,
        on_time_sec: float,
        off_time_sec: float,
    ) -> None:
        """Apply the latest valve command to all underlyings immediately."""
        for under in self._underlyings:
            under._on_time_sec = on_time_sec
            under._off_time_sec = off_time_sec
            under._hvac_mode = hvac_mode
            await under.set_valve_open_percent()

    async def _start_cycle_valve(self, hvac_mode: VThermHvacMode):
        """Valve passthrough: call set_valve_open_percent() on each underlying.

        Valves don't need temporal ON/OFF scheduling. They just need
        their open percentage updated. A master cycle window is still kept so
        cycle callbacks remain available to SmartPI in valve-based setups.
        """
        await self._apply_valve_command(
            hvac_mode,
            self._current_on_time_sec,
            self._current_off_time_sec,
        )

        self._cycle_start_time = time.time()
        self._cycle_end_unsub = async_call_later(
            self._hass,
            self._cycle_duration_sec,
            self._on_master_cycle_end,
        )

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

            if target_is_on:
                if not under.is_device_active:
                    action, new_on_t, pen_delta = evaluate_need_on(
                        under_dt, state_duration,
                        self.min_deactivation_delay, self.min_activation_delay,
                        state.on_t, current_t
                    )
                    if action == 'turn_on':
                        _LOGGER.info(
                            "%s - tick turn_on (state_duration=%.1fs, initial=%s)",
                            under, state_duration, _is_initial
                        )
                        try:
                            await under.turn_on()
                            under._should_be_on = True
                        except Exception as err:
                            _LOGGER.error("%s - tick turn_on failed: %s", under, err)
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
                elif _is_initial:
                    # Enforce state unconditionally on the first tick
                    if not under.is_device_active:
                        await under.turn_on()
                    under._should_be_on = True

            elif not target_is_on:
                if under.is_device_active:
                    action, new_off_t, pen_delta = evaluate_need_off(
                        under_dt, state_duration,
                        self.min_activation_delay, self.min_deactivation_delay,
                        state.off_t, current_t
                    )
                    if action == 'turn_off':
                        _LOGGER.info(
                            "%s - tick turn_off (state_duration=%.1fs, initial=%s)",
                            under, state_duration, _is_initial
                        )
                        try:
                            await under.turn_off()
                            under._should_be_on = False
                        except Exception as err:
                            _LOGGER.error("%s - tick turn_off failed: %s", under, err)
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
                elif _is_initial:
                    # Enforce state unconditionally on the first tick
                    if under.is_device_active:
                        try:
                            await under.turn_off()
                            under._should_be_on = False
                        except Exception as err:
                            _LOGGER.error("%s - initial turn_off failed: %s", under, err)

        # Ensure we do not schedule too fast (< 0.1s)
        next_global_tick = max(0.1, next_global_tick)

        # Schedule next tick
        self._tick_unsub = async_call_later(self._hass, next_global_tick, self._tick)

    async def _on_master_cycle_end(self, _now):
        """Called at the end of the master cycle. Restart with the same parameters.

        The cycle end callback (e_eff) is fired by cancel_cycle(), which is called
        inside start_cycle(force=True). This ensures exactly one callback per cycle
        end regardless of how the cycle terminates.
        """
        if not self.is_cycle_running:
            return

        # Increment energy counter
        self._thermostat.incremente_energy()

        # Restart cycle — cancel_cycle() inside start_cycle will fire the end callback.
        await self.start_cycle(
            self._current_hvac_mode,
            self._current_on_percent,
            force=True,
            _from_cycle_end=True,
        )

    def shutdown(self):
        """Cancel pending timers immediately without firing end-of-cycle callbacks.

        Must be called synchronously when the entity is being removed from HA so
        that leftover async_call_later handles cannot fire after the new entity
        (potentially with a different cycle duration) has already started.
        """
        if self._tick_unsub:
            self._tick_unsub()
            self._tick_unsub = None
        if self._cycle_end_unsub:
            self._cycle_end_unsub()
            self._cycle_end_unsub = None
        self._set_pending_cycle(None, 0, 0, 0.0)
        self._set_active_cycle(None, 0, 0, 0.0)
        self._is_cancelling = False
        self._is_starting = False

    async def cancel_cycle(self):
        """Cancel the current cycle if one is running."""
        await self._cancel_cycle_impl()

    async def _cancel_cycle_impl(self):
        """Internal cancel logic, shared by cancel_cycle() and start_cycle()."""
        was_running = self.is_cycle_running

        # Set before unsubscribing so that is_cycle_running stays True
        # throughout this coroutine, even during the async yield below (Race 1 guard).
        self._is_cancelling = True

        if self._tick_unsub:
            self._tick_unsub()
            self._tick_unsub = None
        if self._cycle_end_unsub:
            self._cycle_end_unsub()
            self._cycle_end_unsub = None

        elapsed_sec = time.time() - self._cycle_start_time if self._cycle_start_time > 0 else 0

        # Fire end-of-cycle callback for cycles that ran long enough.
        # This includes normal ends (via _on_master_cycle_end -> start_cycle(force=True))
        # and mid-cycle interruptions (force restart on setpoint change, etc.).
        # During this await, _is_cancelling=True keeps is_cycle_running=True so any
        # concurrent start_cycle(force=False) call takes the update path, not full start.
        if was_running and elapsed_sec > 1.0:
            realized_e_eff = self._calculate_realized_e_eff(elapsed_sec)
            elapsed_ratio = min(1.0, elapsed_sec / self._cycle_duration_sec) if self._cycle_duration_sec > 0 else 1.0

            _LOGGER.debug("%s - cycle end: elapsed_sec=%.1f, realized_e_eff=%.3f, elapsed_ratio=%.2f", self._thermostat, elapsed_sec, realized_e_eff, elapsed_ratio)
            await self._fire_cycle_end_callbacks(realized_e_eff, elapsed_ratio)

        self._states = []
        self._set_pending_cycle(None, 0, 0, 0.0)
        self._set_active_cycle(None, 0, 0, 0.0)
        self._cycle_start_time = 0.0
        # Reset only after all state is cleared so the guard stays active until fully done.
        self._is_cancelling = False
        _LOGGER.debug("%s - Cycle cancelled", self._thermostat)

    def _calculate_realized_e_eff(self, elapsed_sec: float) -> float:
        """Calculate the actual effective power applied over the given elapsed time."""
        if not self._underlyings or elapsed_sec <= 0:
            return 0.0

        if self._is_valve_mode:
            # Valve mode applies one constant opening command over the full
            # master cycle window, so the realized effective power is the
            # current cycle command itself.
            return max(0.0, min(1.0, self._active_on_percent))

        # When _states is empty the cycle ran at either 0% or 100% (no tick scheduling).
        # Infer from _active_on_time_sec: if it covers the full duration, e_eff = 1.0.
        if not self._states:
            if self._active_on_time_sec >= self._cycle_duration_sec:
                return 1.0
            return 0.0

        t_on_actual = 0.0
        for state in self._states:
            if state.off_t >= state.on_t:
                start_on = min(state.on_t, elapsed_sec)
                end_on = min(state.off_t, elapsed_sec)
                if end_on > start_on:
                    t_on_actual += (end_on - start_on)
            else:
                end_on_1 = min(state.off_t, elapsed_sec)
                t_on_actual += end_on_1

                start_on_2 = min(state.on_t, elapsed_sec)
                end_on_2 = elapsed_sec
                if end_on_2 > start_on_2:
                    t_on_actual += (end_on_2 - start_on_2)

        # e_eff is the true instantaneous duty cycle over the elapsed window.
        e_eff = max(0.0, t_on_actual - self._penalty) / (elapsed_sec * len(self._underlyings))
        return max(0.0, min(1.0, e_eff))

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

    async def _fire_cycle_end_callbacks(self, e_eff: float, elapsed_ratio: float = 1.0):
        """Fire all registered cycle end callbacks with e_eff and elapsed_ratio."""
        cycle_duration_min = self._cycle_duration_sec / 60.0
        for callback in self._on_cycle_end_callbacks:
            try:
                await callback(
                    e_eff=e_eff,
                    elapsed_ratio=elapsed_ratio,
                    cycle_duration_min=cycle_duration_min,
                )
            except Exception as ex:
                _LOGGER.warning(
                    "%s - Error calling cycle end callback %s: %s",
                    self._thermostat,
                    callback,
                    ex,
                )
