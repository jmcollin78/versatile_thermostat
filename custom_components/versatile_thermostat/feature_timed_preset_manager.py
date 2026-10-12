""" Implements the Timed Preset Feature Manager """

# pylint: disable=line-too-long

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import (
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_point_in_time

from vtherm_api.log_collector import get_vtherm_logger
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .commons import write_event_log

from .base_manager import BaseFeatureManager
from .vtherm_preset import VThermPreset


_LOGGER = get_vtherm_logger(__name__)


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
        self._original_preset: VThermPreset | None = None
        self._timed_preset_end_time: datetime | None = None
        self._cancel_timer: Any | None = None
        self._manual_override_duration_min: int = 0
        # Manual override: a timed preset of NONE started by a manual temperature change
        self._is_manual_override: bool = False
        # The regular timed preset interrupted by the manual override, to resume it at the end
        self._resume_preset: VThermPreset | None = None
        self._resume_end_time: datetime | None = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        # The timed preset feature is always available, no configuration needed
        # The manual override duration comes from the advanced configuration (0 = disabled)
        self._manual_override_duration_min = int(entry_infos.get(CONF_MANUAL_OVERRIDE_DURATION_MIN) or 0)

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
        original_preset_str = manager_attr.get("original_preset")

        if not end_time_str or not preset_str:
            return

        try:
            # 2. Parse everything into locals first: a corrupt value must leave the manager untouched
            end_time = datetime.fromisoformat(end_time_str)
            now = self._vtherm.now
            timed_preset = VThermPreset(preset_str)
            original_preset = VThermPreset(original_preset_str) if original_preset_str else None
            is_manual_override = bool(manager_attr.get("is_manual_override", False))
            resume_preset_str = manager_attr.get("resume_preset")
            resume_end_time_str = manager_attr.get("resume_end_time")
            resume_preset = VThermPreset(resume_preset_str) if resume_preset_str else None
            resume_end_time = datetime.fromisoformat(resume_end_time_str) if resume_end_time_str else None

            # 3. Re-populate internal manager variables
            self._is_timed_preset_active = True
            self._timed_preset = timed_preset
            self._original_preset = original_preset
            self._timed_preset_end_time = end_time
            self._is_manual_override = is_manual_override
            self._resume_preset = resume_preset
            self._resume_end_time = resume_end_time

            # 4. Reschedule the expiration task if time remains
            if end_time > now:
                # While the timed preset is active, requested_state must carry it so
                # other managers like auto start/stop recalculate from the forced preset.
                self._vtherm.requested_state.set_preset(self._timed_preset)
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

        # Capture the original preset before overriding it
        if not self._is_timed_preset_active:
            self._original_preset = self._vtherm.requested_state.preset

        # A timed preset set during a manual override replaces it
        self._is_manual_override = False
        self._resume_preset = None
        self._resume_end_time = None

        await self._activate_timed_preset(preset, self._vtherm.now + timedelta(minutes=duration_minutes), duration_minutes)
        return True

    async def start_manual_override(self, previous_preset: VThermPreset | None) -> bool:
        """Start a manual override after a manual temperature change.

        The manual override is a timed preset of NONE which reverts to the previous preset
        (or resumes the interrupted timed preset) when the configured duration expires.

        Args:
            previous_preset: The requested preset before the manual change

        Returns:
            True if the manual override was started, False if it is disabled or there is nothing to revert to
        """
        duration_minutes = self._manual_override_duration_min
        if duration_minutes <= 0:
            return False

        if not self._is_timed_preset_active and (previous_preset is None or previous_preset == VThermPreset.NONE):
            return False

        self._cancel_timed_preset_timer()

        if not self._is_timed_preset_active:
            self._original_preset = previous_preset
        elif not self._is_manual_override:
            # A regular timed preset is interrupted: remember it to resume it later
            self._resume_preset = self._timed_preset
            self._resume_end_time = self._timed_preset_end_time
        # else a manual override is already active: keep the original preset and the resume record

        self._is_manual_override = True
        await self._activate_timed_preset(VThermPreset.NONE, self._vtherm.now + timedelta(minutes=duration_minutes), duration_minutes)
        return True

    async def _activate_timed_preset(self, preset: VThermPreset, end_time: datetime, duration_minutes: float):
        """Activate the timed preset until end_time, schedule its end and update the VTherm"""
        self._timed_preset = preset
        self._timed_preset_end_time = end_time
        self._is_timed_preset_active = True

        # Keep requested_state aligned with the timed preset while it is active so
        # state recalculation uses the forced preset even if HVAC is currently off.
        self._vtherm.requested_state.set_preset(preset)

        # Schedule the end of timed preset
        self._cancel_timer = async_track_point_in_time(
            self._hass,
            self._async_timed_preset_expired,
            self._timed_preset_end_time,
        )

        write_event_log(
            _LOGGER,
            self._vtherm,
            f"{'Manual override' if self._is_manual_override else 'Timed preset'} started: {preset} for {duration_minutes} minutes until {self._timed_preset_end_time}",
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
                "original_preset": str(self._original_preset),
                "manual_override": self._is_manual_override,
            },
        )

        # Force update of the thermostat state
        self._vtherm.requested_state.force_changed()
        await self._vtherm.update_states(force=True)

        self._vtherm.update_custom_attributes()

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
        """End the timed preset and restore the original preset.
        At the end of a manual override, the interrupted timed preset is resumed if it is not over."""
        if not self._is_timed_preset_active:
            return

        old_preset = self._timed_preset
        was_manual_override = self._is_manual_override
        original_preset = self._original_preset
        resume_preset = self._resume_preset
        resume_end_time = self._resume_end_time

        # Cancel the timer if still active
        self._cancel_timed_preset_timer()

        # An explicit cancel never resumes: it goes back to the original preset
        resume = was_manual_override and not cancelled and resume_preset is not None and resume_end_time is not None and resume_end_time > self._vtherm.now

        # Restore the original preset explicitly (handles the post-restart case)
        if not resume and original_preset is not None:
            self._vtherm.requested_state.set_preset(original_preset)

        # Reset state
        self._reset_state()

        write_event_log(
            _LOGGER,
            self._vtherm,
            f"{'Manual override' if was_manual_override else 'Timed preset'} ended: {old_preset} {'(cancelled)' if cancelled else '(expired)'}",
        )

        # Send an event
        self._vtherm.send_event(
            event_type=EventType.TIMED_PRESET_EVENT,
            data={
                "type": "end",
                "name": self.name,
                "preset": str(old_preset),
                "cause": "cancelled" if cancelled else "expired",
                "restored_preset": str(resume_preset if resume else self._vtherm.requested_state.preset),
                "manual_override": was_manual_override,
            },
        )

        if resume:
            # Resume the interrupted timed preset until its own end time, keeping the original preset
            self._original_preset = original_preset
            remaining_minutes = (resume_end_time - self._vtherm.now).total_seconds() / 60
            await self._activate_timed_preset(resume_preset, resume_end_time, remaining_minutes)
            return

        # Force update of the thermostat state to restore original preset
        self._vtherm.requested_state.force_changed()
        await self._vtherm.update_states(force=True)

        self._vtherm.update_custom_attributes()

    def cancel_manual_override_without_revert(self, selected_preset: VThermPreset | None = None):
        """Drop the manual override without restoring the original preset.
        Used when the user selects a preset during the manual override: the selected preset applies.
        The end event has the cause "preset_selected" and its restored_preset is the selected preset
        (None when not given). The HA attributes and state are refreshed at once, so that a
        cancelled override is never shown (nor restored after a restart) when the state does not change.

        Args:
            selected_preset: The preset selected by the user, reported in the end event
        """
        if not self._is_timed_preset_active or not self._is_manual_override:
            return

        old_preset = self._timed_preset
        self._cancel_timed_preset_timer()
        self._reset_state()

        write_event_log(_LOGGER, self._vtherm, f"Manual override ended: {old_preset} (cancelled by a preset change)")

        self._vtherm.send_event(
            event_type=EventType.TIMED_PRESET_EVENT,
            data={
                "type": "end",
                "name": self.name,
                "preset": str(old_preset),
                "cause": "preset_selected",
                "restored_preset": str(selected_preset) if selected_preset is not None else None,
                "manual_override": True,
            },
        )

        self._vtherm.update_custom_attributes()
        self._vtherm.async_write_ha_state()

    def _reset_state(self):
        """Reset the timed preset and manual override state"""
        self._is_timed_preset_active = False
        self._timed_preset = None
        self._original_preset = None
        self._timed_preset_end_time = None
        self._is_manual_override = False
        self._resume_preset = None
        self._resume_end_time = None

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
                    "original_preset": str(self._original_preset) if self._original_preset else None,
                    "end_time": self._timed_preset_end_time.isoformat() if self._timed_preset_end_time else None,
                    "remaining_time_min": self.remaining_time_min,
                    "is_manual_override": self._is_manual_override,
                    "resume_preset": str(self._resume_preset) if self._resume_preset else None,
                    "resume_end_time": self._resume_end_time.isoformat() if self._resume_end_time else None,
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
    def manual_override_duration_min(self) -> int:
        """Return the manual override duration in minutes (0 = disabled)."""
        return self._manual_override_duration_min

    @property
    def is_manual_override(self) -> bool:
        """Return True if the active timed preset is a manual override."""
        return self._is_timed_preset_active and self._is_manual_override

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

    @property
    def is_detected(self) -> bool:
        """Return the overall state of the feature manager based on timed preset states"""
        return self.is_timed_preset_active

    def __str__(self):
        return f"TimedPresetManager-{self.name}"
