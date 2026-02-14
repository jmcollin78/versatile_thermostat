""" Implements the Timed Preset Feature Manager """

# pylint: disable=line-too-long

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import (
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_point_in_time

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .commons import write_event_log

from .base_manager import BaseFeatureManager
from .vtherm_preset import VThermPreset


_LOGGER = logging.getLogger(__name__)


class FeatureTimedPresetManager(BaseFeatureManager):
    """The implementation of the TimedPreset feature.

    This feature allows forcing a preset for a given duration.
    When the duration expires, the original preset (from requested_state) is restored.
    """

    unrecorded_attributes = frozenset(
        {
            "timed_preset_manager",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)

        self._is_timed_preset_active: bool = False
        self._timed_preset: VThermPreset | None = None
        self._timed_preset_end_time: datetime | None = None
        self._cancel_timer: Any | None = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        # The timed preset feature is always available, no configuration needed
        pass

    @overrides
    async def start_listening(self):
        """Start listening - nothing to listen to for this feature"""
        pass

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""
        self._cancel_timed_preset_timer()
        super().stop_listening()

    @callback
    def restore_state(self, old_state: Any):
        """Implement the restoration hook to re-populate timed presets after restart."""

        # 1. Retrieve the persistence dictionary from attributes
        # Matches the key used in add_custom_attributes
        manager_attr = old_state.attributes.get("timed_preset_manager")
        if not manager_attr or not manager_attr.get("is_active"):
            return

        end_time_str = manager_attr.get("end_time")
        preset_str = manager_attr.get("preset")

        if not end_time_str or not preset_str:
            return

        try:
            # 2. Re-parse the end_time and preset mode
            end_time = datetime.fromisoformat(end_time_str)
            now = self._vtherm.now

            # 3. Re-populate internal manager variables
            self._is_timed_preset_active = True
            self._timed_preset = VThermPreset(preset_str)
            self._timed_preset_end_time = end_time

            # 4. Reschedule the expiration task if time remains
            if end_time > now:
                _LOGGER.info("%s - Resuming timed preset %s. Reverting at %s", self, preset_str, end_time)
                self._cancel_timer = async_track_point_in_time(
                    self._hass,
                    self._async_timed_preset_expired,
                    self._timed_preset_end_time,
                )
            else:
                _LOGGER.info("%s - Timed preset expired during downtime. Cleanup will follow.", self)
                # The existing safety check in refresh_state() will handle the cleanup
                # and revert to requested_state during the startup cycle.
        except (ValueError, TypeError) as err:
            _LOGGER.error("%s - Failed to restore timed preset state: %s", self, err)

    @overrides
    async def refresh_state(self) -> bool:
        """Check if the timed preset is still active.
        Return True if timed preset is active"""

        if not self._is_timed_preset_active:
            return False

        # Check if the timer has expired (safety check in case timer callback failed)
        if self._timed_preset_end_time and self._vtherm.now >= self._timed_preset_end_time:
            _LOGGER.debug("%s - timed preset has expired (safety check)", self)
            await self._end_timed_preset()
            return False

        return self._is_timed_preset_active

    async def set_timed_preset(self, preset: VThermPreset, duration_minutes: float) -> bool:
        """Set a preset for a given duration in minutes.

        Args:
            preset: The preset to apply temporarily
            duration_minutes: The duration in minutes

        Returns:
            True if the timed preset was set successfully, False otherwise
        """
        if duration_minutes <= 0:
            _LOGGER.warning("%s - duration must be positive, got %s", self, duration_minutes)
            return False

        if preset not in self._vtherm.vtherm_preset_modes and preset not in [VThermPreset.NONE]:
            _LOGGER.warning("%s - preset %s is not available for this thermostat", self, preset)
            return False

        # Cancel any existing timer
        self._cancel_timed_preset_timer()

        # Store the timed preset information
        self._timed_preset = preset
        self._timed_preset_end_time = self._vtherm.now + timedelta(minutes=duration_minutes)
        self._is_timed_preset_active = True

        # Schedule the end of timed preset
        self._cancel_timer = async_track_point_in_time(
            self._hass,
            self._async_timed_preset_expired,
            self._timed_preset_end_time,
        )

        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Timed preset started: {preset} for {duration_minutes} minutes until {self._timed_preset_end_time}",
        )

        # Send an event
        self._vtherm.send_event(
            event_type=EventType.TIMED_PRESET_EVENT,
            data={
                "type": "start",
                "name": self.name,
                "preset": str(preset),
                "duration_minutes": duration_minutes,
                "end_time": self._timed_preset_end_time.isoformat(),
                "original_preset": str(self._vtherm.requested_state.preset),
            },
        )

        # Force update of the thermostat state
        self._vtherm.requested_state.force_changed()
        await self._vtherm.update_states(force=True)

        self._vtherm.update_custom_attributes()

        return True

    async def cancel_timed_preset(self) -> bool:
        """Cancel the current timed preset if active.

        Returns:
            True if a timed preset was cancelled, False if none was active
        """
        if not self._is_timed_preset_active:
            return False

        await self._end_timed_preset(cancelled=True)
        return True

    @callback
    async def _async_timed_preset_expired(self, _: datetime):
        """Called when the timed preset timer expires."""
        _LOGGER.debug("%s - timed preset timer expired", self)
        await self._end_timed_preset()

    async def _end_timed_preset(self, cancelled: bool = False):
        """End the timed preset and restore the original preset."""
        if not self._is_timed_preset_active:
            return

        old_preset = self._timed_preset

        # Cancel the timer if still active
        self._cancel_timed_preset_timer()

        # Reset state
        self._is_timed_preset_active = False
        self._timed_preset = None
        self._timed_preset_end_time = None

        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Timed preset ended: {old_preset} {'(cancelled)' if cancelled else '(expired)'}",
        )

        # Send an event
        self._vtherm.send_event(
            event_type=EventType.TIMED_PRESET_EVENT,
            data={
                "type": "end",
                "name": self.name,
                "preset": str(old_preset),
                "cause": "cancelled" if cancelled else "expired",
                "restored_preset": str(self._vtherm.requested_state.preset),
            },
        )

        # Force update of the thermostat state to restore original preset
        self._vtherm.requested_state.force_changed()
        await self._vtherm.update_states(force=True)

        self._vtherm.update_custom_attributes()

    def _cancel_timed_preset_timer(self):
        """Cancel the timed preset timer if active."""
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "timed_preset_manager": {
                    "is_active": self._is_timed_preset_active,
                    "preset": str(self._timed_preset) if self._timed_preset else None,
                    "end_time": self._timed_preset_end_time.isoformat() if self._timed_preset_end_time else None,
                    "remaining_time_min": self.remaining_time_min,
                }
            }
        )

    @property
    def remaining_time_min(self) -> int:
        """Return the remaining time in minutes, or 0 if not active or expired."""
        if not self._is_timed_preset_active or not self._timed_preset_end_time:
            return 0

        remaining = self._timed_preset_end_time - self._vtherm.now
        remaining_minutes = remaining.total_seconds() / 60
        return max(0, round(remaining_minutes))

    @property
    def is_timed_preset_active(self) -> bool:
        """Return True if a timed preset is currently active."""
        return self._is_timed_preset_active

    @property
    def timed_preset(self) -> VThermPreset | None:
        """Return the current timed preset, or None if not active."""
        return self._timed_preset if self._is_timed_preset_active else None

    @property
    def timed_preset_end_time(self) -> datetime | None:
        """Return the end time of the timed preset, or None if not active."""
        return self._timed_preset_end_time if self._is_timed_preset_active else None

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True - timed preset feature is always available."""
        return True

    def __str__(self):
        return f"TimedPresetManager-{self.name}"
