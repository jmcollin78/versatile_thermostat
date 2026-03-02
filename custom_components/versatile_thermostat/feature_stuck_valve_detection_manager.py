# pylint: disable=line-too-long

""" Implements the Stuck Valve Detection as a Feature Manager"""

import logging
from typing import Any
from datetime import datetime, timedelta

from homeassistant.components.climate import HVACAction
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_USE_STUCK_VALVE_DETECTION_FEATURE,
    CONF_STUCK_VALVE_DETECTION_DELAY_SEC,
    CONF_STUCK_VALVE_MAX_CYCLES,
    DEFAULT_STUCK_VALVE_DETECTION_DELAY_SEC,
    DEFAULT_STUCK_VALVE_MAX_CYCLES,
    EventType,
    overrides,
)
from .commons import write_event_log
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager
from .vtherm_hvac_mode import VThermHvacMode_OFF

_LOGGER = logging.getLogger(__name__)


class FeatureStuckValveDetectionManager(BaseFeatureManager):
    """The implementation of the Stuck Valve Detection feature

    This feature detects when a TRV valve reports 'heating' but the room
    temperature is already above the VTherm target, and automatically cycles
    the valve off/on to unstick it.
    """

    unrecorded_attributes = frozenset(
        {
            "is_stuck_valve_detection_configured",
            "stuck_valve_detection_manager",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)

        self._is_configured: bool = False
        self._detection_delay_sec: int = DEFAULT_STUCK_VALVE_DETECTION_DELAY_SEC
        self._max_cycles: int = DEFAULT_STUCK_VALVE_MAX_CYCLES

        # Tracking state per underlying entity_id
        self._stuck_since: dict[str, datetime] = {}
        self._cycle_count: dict[str, int] = {}
        self._cycling_in_progress: set[str] = set()

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        use_feature = entry_infos.get(CONF_USE_STUCK_VALVE_DETECTION_FEATURE, False)

        if not use_feature:
            self._is_configured = False
            return

        self._detection_delay_sec = entry_infos.get(
            CONF_STUCK_VALVE_DETECTION_DELAY_SEC,
            DEFAULT_STUCK_VALVE_DETECTION_DELAY_SEC,
        )
        self._max_cycles = entry_infos.get(
            CONF_STUCK_VALVE_MAX_CYCLES,
            DEFAULT_STUCK_VALVE_MAX_CYCLES,
        )

        self._is_configured = True

        # Reset tracking
        self._stuck_since = {}
        self._cycle_count = {}
        self._cycling_in_progress = set()

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""
        # No external entity to listen to for this feature

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""

    @overrides
    async def refresh_state(self) -> bool:
        """Check for stuck valves.
        Return True if a stuck valve is detected."""

        if not self._is_configured:
            _LOGGER.debug(
                "%s - stuck valve detection is disabled (or not configured)", self
            )
            return False

        if self._vtherm.requested_state.hvac_mode == VThermHvacMode_OFF:
            self._reset_tracking()
            _LOGGER.debug(
                "%s - stuck valve detection is OFF because requested_state is OFF",
                self,
            )
            return False

        current_temp = self._vtherm.current_temperature
        target_temp = self._vtherm.target_temperature

        if current_temp is None or target_temp is None:
            _LOGGER.debug(
                "%s - stuck valve detection skipped (no temp or target_temp)", self
            )
            return False

        now = self._vtherm.now
        stuck_detected = False

        for under in self._vtherm._underlyings:
            entity_id = under.entity_id

            # Skip if a cycle is already in progress for this entity
            if entity_id in self._cycling_in_progress:
                continue

            should_be_idle = current_temp > target_temp
            is_stuck = should_be_idle and under.hvac_action == HVACAction.HEATING

            if is_stuck:
                stuck_detected = True
                if entity_id not in self._stuck_since:
                    self._stuck_since[entity_id] = now
                    _LOGGER.debug(
                        "%s - Starting stuck tracking for %s "
                        "(current_temp=%.1f > target_temp=%.1f, hvac_action=HEATING)",
                        self,
                        entity_id,
                        current_temp,
                        target_temp,
                    )
                else:
                    elapsed = now - self._stuck_since[entity_id]
                    if elapsed >= timedelta(seconds=self._detection_delay_sec):
                        cycle_count = self._cycle_count.get(entity_id, 0)
                        if cycle_count < self._max_cycles:
                            await self._force_cycle(under, entity_id)
                        else:
                            _LOGGER.warning(
                                "%s - Max off/on cycles (%d) reached for %s. "
                                "Valve may require manual intervention.",
                                self,
                                self._max_cycles,
                                entity_id,
                            )
                            write_event_log(
                                _LOGGER,
                                self._vtherm,
                                f"Stuck valve: max cycles ({self._max_cycles}) "
                                f"reached for {entity_id}",
                            )
                            self._vtherm.send_event(
                                EventType.STUCK_VALVE_EVENT,
                                {
                                    "type": "stuck_valve_max_cycles_reached",
                                    "entity_id": entity_id,
                                    "current_temp": current_temp,
                                    "target_temp": target_temp,
                                    "cycle_count": cycle_count,
                                    "max_cycles": self._max_cycles,
                                },
                            )
                            # Remove from tracking to stop repeated warnings
                            self._stuck_since.pop(entity_id, None)
            else:
                # Not stuck anymore
                if entity_id in self._stuck_since:
                    cycle_count = self._cycle_count.get(entity_id, 0)
                    if cycle_count > 0:
                        _LOGGER.info(
                            "%s - Valve %s unstuck after %d cycle(s)",
                            self,
                            entity_id,
                            cycle_count,
                        )
                        write_event_log(
                            _LOGGER,
                            self._vtherm,
                            f"Valve {entity_id} unstuck after {cycle_count} cycle(s)",
                        )
                    self._stuck_since.pop(entity_id, None)
                    self._cycle_count.pop(entity_id, None)

        return stuck_detected

    async def _force_cycle(self, under, entity_id: str):
        """Force an off/on cycle on the underlying valve to unstick it."""

        self._cycling_in_progress.add(entity_id)
        previous_mode = under.hvac_mode

        # Turn off the valve
        await under.set_hvac_mode(VThermHvacMode_OFF)

        cycle_num = self._cycle_count.get(entity_id, 0) + 1
        self._cycle_count[entity_id] = cycle_num

        _LOGGER.info(
            "%s - Forcing off/on cycle #%d for %s (previous_mode=%s)",
            self,
            cycle_num,
            entity_id,
            previous_mode,
        )
        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Stuck valve: forcing off/on cycle #{cycle_num} for {entity_id}",
        )
        self._vtherm.send_event(
            EventType.STUCK_VALVE_EVENT,
            {
                "type": "stuck_valve_cycle",
                "entity_id": entity_id,
                "cycle_number": cycle_num,
                "max_cycles": self._max_cycles,
                "current_temp": self._vtherm.current_temperature,
                "target_temp": self._vtherm.target_temperature,
            },
        )

        # Schedule turning back on after 5 seconds
        async def _restore_callback(_now):
            """Callback to restore the previous hvac mode."""
            try:
                await under.set_hvac_mode(previous_mode)
                _LOGGER.info(
                    "%s - Restored %s to mode %s after cycle #%d",
                    self,
                    entity_id,
                    previous_mode,
                    cycle_num,
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(
                    "%s - Error restoring %s to mode %s: %s",
                    self,
                    entity_id,
                    previous_mode,
                    err,
                )
            finally:
                self._cycling_in_progress.discard(entity_id)
                # Reset stuck_since to now so the timer restarts
                self._stuck_since[entity_id] = self._vtherm.now

        async_call_later(self._hass, 5, _restore_callback)

    def _reset_tracking(self):
        """Reset all tracking variables"""
        self._stuck_since = {}
        self._cycle_count = {}
        self._cycling_in_progress = set()

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""

        extra_state_attributes["is_stuck_valve_detection_configured"] = (
            self._is_configured
        )

        if self._is_configured:
            extra_state_attributes["stuck_valve_detection_manager"] = {
                "detection_delay_sec": self._detection_delay_sec,
                "max_cycles": self._max_cycles,
                "tracking": {
                    eid: str(t) for eid, t in self._stuck_since.items()
                },
                "cycle_counts": dict(self._cycle_count),
                "cycling_in_progress": list(self._cycling_in_progress),
            }

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if the stuck valve detection feature is configured"""
        return self._is_configured

    def __str__(self):
        return f"StuckValveDetectionManager-{self.name}"
