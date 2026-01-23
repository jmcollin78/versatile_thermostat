"""Cycle Manager for Versatile Thermostat."""

import logging
import asyncio
from typing import Callable, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant
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
        self._timer_capture_remove_callback: Callable[[], None] | None = None
        
        # State tracking
        self._current_cycle_params: dict | None = None
        self._cycle_start_date: datetime | None = None
        self._learning_just_completed = False

    async def process_cycle(self, timestamp: datetime, data_provider: Callable[[], dict], event_sender: Callable[[dict], None], force: bool = False):
        """Process a cycle tick. Called by Handlers during control_heating."""
        
        # 1. Initialization on first call
        if self._cycle_start_date is None:
            _LOGGER.debug("%s - CycleManager: Initializing first cycle at %s", self._name, timestamp)
            new_params = await self._get_data(data_provider)
            if not new_params:
                return
            
            self._cycle_start_date = timestamp
            self._current_cycle_params = new_params
            await self._start_new_cycle(new_params)
            return

        # 2. Check for cycle boundary
        elapsed_sec = (timestamp - self._cycle_start_date).total_seconds()
        
        if elapsed_sec >= self._cycle_min * 60 or force:
            _LOGGER.debug("%s - CycleManager: Cycle boundary reached (elapsed: %.1fs, force: %s)", self._name, elapsed_sec, force)
            
            new_params = await self._get_data(data_provider)
            if not new_params:
                return

            # Notify completion hook
            # If it returns False, we extend the current window (don't reset start date)
            should_reset = await self.on_cycle_completed(new_params, self._current_cycle_params)
            
            if should_reset is not False:
                self._cycle_start_date = timestamp
                self._current_cycle_params = new_params
                await self._start_new_cycle(new_params)
                
                # Notify thermostat to apply changes (event_sender)
                await self._send_event(event_sender, new_params)
            else:
                _LOGGER.debug("%s - CycleManager: Cycle extended (window extension)", self._name)

    async def _get_data(self, data_provider: Callable[[], dict]) -> dict | None:
        """Helper to get data from provider."""
        try:
            if asyncio.iscoroutinefunction(data_provider):
                return await data_provider()
            else:
                return data_provider()
        except Exception as e:
            _LOGGER.error("%s - CycleManager: Error getting data from thermostat: %s", self._name, e)
            return None

    async def _send_event(self, event_sender: Callable[[dict], None], params: dict):
        """Helper to send event."""
        try:
            if asyncio.iscoroutinefunction(event_sender):
                await event_sender(params)
            else:
                event_sender(params)
        except Exception as e:
            _LOGGER.error("%s - CycleManager: Error sending event to thermostat: %s", self._name, e)

    async def _start_new_cycle(self, params: dict):
        """Helper to initialize a new cycle."""
        on_time = params.get("on_time_sec", 0)
        off_time = params.get("off_time_sec", 0)
        on_percent = params.get("on_percent", 0)
        hvac_mode = params.get("hvac_mode", "stop")
        await self.on_cycle_started(on_time, off_time, on_percent, hvac_mode)

    async def on_cycle_started(self, on_time_sec: float, off_time_sec: float, on_percent: float, hvac_mode: str):
        """Called when a cycle starts. Override in subclass."""
        self.cycle_active = True
        _LOGGER.debug("%s - CycleManager: Cycle started. On: %.0fs, Off: %.0fs (%.1f%%)", self._name, on_time_sec, off_time_sec, on_percent * 100)

    async def on_cycle_completed(self, new_params: dict, prev_params: dict | None) -> bool:
        """Called when a cycle completes. Override in subclass.
        Return True to start a new cycle, False to extend the current one."""
        self.cycle_active = False
        return True
