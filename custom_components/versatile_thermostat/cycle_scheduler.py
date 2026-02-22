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
        self._scheduled_actions: list[CALLBACK_TYPE] = []
        self._on_cycle_start_callbacks: list[Callable] = []
        self._on_cycle_end_callbacks: list[Callable] = []
        # Current cycle parameters (for repeat at cycle end)
        self._current_hvac_mode: VThermHvacMode | None = None
        self._current_on_time_sec: float = 0
        self._current_off_time_sec: float = 0
        self._current_on_percent: float = 0
        # Detect valve mode from underlying types
        self._is_valve_mode: bool = self._detect_valve_mode()

    @property
    def is_cycle_running(self) -> bool:
        """Return True if a cycle is currently scheduled."""
        return len(self._scheduled_actions) > 0

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

    @staticmethod
    def compute_offsets(
        on_time_sec: float,
        cycle_duration_sec: float,
        n: int,
    ) -> list[float]:
        """Compute start offsets for n underlyings to minimize ON overlap.

        Uses uniform distribution: offsets are spread evenly across
        [0, cycle_duration - on_time] for optimal electrical load smoothing.

        Returns:
            List of start offsets in seconds for each underlying (0-indexed).
        """
        if n <= 1:
            return [0.0]

        if on_time_sec <= 0:
            return [0.0] * n

        if on_time_sec >= cycle_duration_sec:
            # 100% power: all start at 0
            return [0.0] * n

        # Maximum offset so the last underlying finishes at cycle end
        max_offset = cycle_duration_sec - on_time_sec

        # Distribute offsets evenly across [0, max_offset]
        step = max_offset / (n - 1)

        return [round(i * step, 1) for i in range(n)]

    def register_cycle_start_callback(self, callback: Callable):
        """Register a callback to be called at the start of each master cycle.

        Callback signature: async def callback(on_time_sec, off_time_sec, on_percent, hvac_mode)
        """
        self._on_cycle_start_callbacks.append(callback)

    def register_cycle_end_callback(self, callback: Callable):
        """Register a callback to be called at the end of each master cycle."""
        self._on_cycle_end_callbacks.append(callback)

    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
        on_percent: float,
        force: bool = False,
    ):
        """Start a new master cycle for all underlyings.

        Computes on_time_sec and off_time_sec from on_percent, applying
        min_activation_delay and min_deactivation_delay constraints.

        Args:
            hvac_mode: Current HVAC mode.
            on_percent: Power percentage as a fraction (0.0 to 1.0).
            force: If True, cancel any running cycle and restart immediately.
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

        if self._scheduled_actions and not force:
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
        """Switch PWM scheduling: stagger ON/OFF periods across underlyings."""
        n = len(self._underlyings)

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
            self._schedule(self._cycle_duration_sec, self._on_master_cycle_end)
            return

        offsets = self.compute_offsets(on_time_sec, self._cycle_duration_sec, n)

        _LOGGER.debug(
            "%s - Starting master cycle: on_time=%.0fs, off_time=%.0fs, "
            "on_percent=%.0f%%, offsets=%s",
            self._thermostat,
            on_time_sec,
            off_time_sec,
            on_percent,
            offsets,
        )

        for i, under in enumerate(self._underlyings):
            start = offsets[i]
            end = start + on_time_sec

            # Schedule turn ON
            if start == 0:
                _LOGGER.info(
                    "%s - start heating for %d min %d sec",
                    under,
                    on_time_sec // 60,
                    on_time_sec % 60,
                )
                await under.turn_on()
                under._should_be_on = True
            else:
                # This underlying's ON phase starts later.
                # If it is currently ON (e.g. from a previous 100%-power cycle),
                # turn it off immediately so the new staggered offset takes effect.
                if under.is_device_active:
                    _LOGGER.info("%s - turning off (waiting for offset %ds)", under, start)
                    await under.turn_off()
                    under._should_be_on = False
                self._schedule(start, self._make_turn_on(under, on_time_sec))

            # Schedule turn OFF
            if end >= self._cycle_duration_sec:
                # This underlying stays ON until cycle end;
                # turn_off handled by _on_master_cycle_end
                pass
            else:
                self._schedule(end, self._make_turn_off(under))

        # Schedule master cycle end
        self._schedule(self._cycle_duration_sec, self._on_master_cycle_end)

    def _schedule(self, delay_sec: float, callback) -> None:
        """Schedule a callback after delay_sec seconds."""
        cancel = async_call_later(self._hass, delay_sec, callback)
        self._scheduled_actions.append(cancel)

    def _make_turn_on(self, under, on_time_sec: float):
        """Create a turn_on callback for a specific underlying."""

        async def _callback(_now):
            _LOGGER.info(
                "%s - start heating for %d min %d sec",
                under,
                on_time_sec // 60,
                on_time_sec % 60,
            )
            await under.turn_on()
            under._should_be_on = True

        return _callback

    def _make_turn_off(self, under):
        """Create a turn_off callback for a specific underlying."""

        async def _callback(_now):
            _LOGGER.info(
                "%s - stop heating for %d min %d sec",
                under,
                self._current_off_time_sec // 60,
                self._current_off_time_sec % 60,
            )
            await under.turn_off()
            under._should_be_on = False

        return _callback

    async def _on_master_cycle_end(self, _now):
        """Called at the end of the master cycle. Turn off remaining and restart."""
        # Turn off any underlying still ON (unless 100% power)
        if self._current_on_time_sec < self._cycle_duration_sec:
            for under in self._underlyings:
                if under.is_device_active:
                    await under.turn_off()
                    under._should_be_on = False

        # Fire cycle end callbacks
        await self._fire_cycle_end_callbacks()

        # Increment energy
        self._thermostat.incremente_energy()

        # Restart cycle with same parameters
        # Note: cancel_cycle() inside start_cycle(force=True) will clear _scheduled_actions atomically.
        await self.start_cycle(
            self._current_hvac_mode,
            self._current_on_percent,
            force=True,
        )

    def cancel_cycle(self):
        """Cancel all scheduled actions."""
        for cancel in self._scheduled_actions:
            cancel()
        self._scheduled_actions.clear()

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

    async def _fire_cycle_end_callbacks(self):
        """Fire all registered cycle end callbacks."""
        for callback in self._on_cycle_end_callbacks:
            try:
                await callback()
            except Exception as ex:
                _LOGGER.warning(
                    "%s - Error calling cycle end callback %s: %s",
                    self._thermostat,
                    callback,
                    ex,
                )
