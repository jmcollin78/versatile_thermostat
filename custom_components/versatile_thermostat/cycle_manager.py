"""Cycle Manager for Versatile Thermostat."""

import logging
import asyncio
from typing import Callable, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class CycleManager:
    """Base class for managing thermostat cycles."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        cycle_min: int,
        minimal_deactivation_delay: int = 0,
    ):
        """Initialize the cycle manager."""
        self._hass = hass
        self._name = name
        self._cycle_min = cycle_min
        self._minimal_deactivation_delay_sec = minimal_deactivation_delay
        
        self.cycle_active = False
        self._timer_remove_callback: Callable[[], None] | None = None
        self._timer_capture_remove_callback: Callable[[], None] | None = None
        
        self._data_provider: Callable[[], dict] | None = None
        self._event_sender: Callable[[dict], None] | None = None
        
        # State tracking
        self._current_cycle_params: dict | None = None
        self._cycle_start_date: datetime | None = None
        self._learning_just_completed = False

    async def start_cycle_loop(self, data_provider: Callable[[], dict], event_sender: Callable[[dict], None]):
        """Start the cycle loop."""
        _LOGGER.debug("%s - CycleManager: Starting cycle loop", self._name)
        self._data_provider = data_provider
        self._event_sender = event_sender

        # Stop existing timer if any
        if self._timer_remove_callback:
            self._timer_remove_callback()
            self._timer_remove_callback = None

        # Execute immediately
        await self._tick()

    def stop_cycle_loop(self):
        """Stop the cycle loop."""
        _LOGGER.debug("%s - CycleManager: Stopping cycle loop", self._name)
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

        now = dt_util.now()

        # 1. Get fresh data from thermostat
        new_params = None
        try:
            if asyncio.iscoroutinefunction(self._data_provider):
                new_params = await self._data_provider()
            else:
                new_params = self._data_provider()
        except Exception as e:
            _LOGGER.error("%s - CycleManager: Error getting data from thermostat: %s", self._name, e)
            self._schedule_next_timer()
            return

        if not self._data_provider:
            return

        if not new_params:
            _LOGGER.warning("%s - CycleManager: No data received from thermostat", self._name)
            self._schedule_next_timer()
            return

        # 2. Handle previous cycle completion
        if self._cycle_start_date is not None:
             # Basic validation or logging can happen here
             pass
             
        # Notify completion hook
        await self.on_cycle_completed(new_params, self._current_cycle_params)

        if not self._data_provider:
            return

        # 3. Update current params for next cycle
        self._current_cycle_params = new_params
        self._cycle_start_date = now
        
        on_time = new_params.get("on_time_sec", 0)
        off_time = new_params.get("off_time_sec", 0)
        on_percent = new_params.get("on_percent", 0)
        hvac_mode = new_params.get("hvac_mode", "stop")

        # 4. Notify start of cycle
        await self.on_cycle_started(on_time, off_time, on_percent, hvac_mode)

        if not self._data_provider:
            return

        # 5. Notify thermostat to apply changes
        if self._event_sender:
            try:
                if asyncio.iscoroutinefunction(self._event_sender):
                    await self._event_sender(new_params)
                else:
                    self._event_sender(new_params)
            except Exception as e:
                _LOGGER.error("%s - CycleManager: Error sending event to thermostat: %s", self._name, e)

        if not self._data_provider:
            return

        # 6. Schedule next tick
        self._schedule_next_timer()

    async def on_cycle_started(self, on_time_sec: float, off_time_sec: float, on_percent: float, hvac_mode: str):
        """Called when a cycle starts. Override in subclass."""
        self.cycle_active = True
        _LOGGER.debug("%s - CycleManager: Cycle started. On: %.0fs, Off: %.0fs (%.1f%%)", self._name, on_time_sec, off_time_sec, on_percent * 100)

    async def on_cycle_completed(self, new_params: dict, prev_params: dict | None):
        """Called when a cycle completes. Override in subclass."""
        self.cycle_active = False
