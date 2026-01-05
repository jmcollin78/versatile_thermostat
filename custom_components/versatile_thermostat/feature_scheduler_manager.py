""" Implements the Scheduler Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any
from datetime import datetime, timedelta

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    EventStateChangedData,
)
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN

from .const import (
    CONF_USE_SCHEDULER_FEATURE,
    CONF_SCHEDULER_CALENDAR,
    CONF_SCHEDULER_DEFAULT_PRESET,
    PRESET_PRIORITY,
    EventType,
    overrides,
)
from .commons import write_event_log
from .commons_type import ConfigData
from .vtherm_preset import VThermPreset

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)

# Mapping of event title keywords to presets
PRESET_KEYWORDS = {
    "boost": VThermPreset.BOOST,
    "comfort": VThermPreset.COMFORT,
    "confort": VThermPreset.COMFORT,  # French spelling
    "eco": VThermPreset.ECO,
    "frost": VThermPreset.FROST,
    "hg": VThermPreset.FROST,  # Hors Gel
    "hors gel": VThermPreset.FROST,
    "away": VThermPreset.FROST,
}


class FeatureSchedulerManager(BaseFeatureManager):
    """The implementation of the Scheduler feature based on calendar entities"""

    unrecorded_attributes = frozenset(
        {
            "scheduler_calendar_entity_id",
            "is_scheduler_configured",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._calendar_entity_id: str | None = None
        self._default_preset: str = VThermPreset.FROST
        self._is_configured: bool = False
        self._scheduled_preset: str | None = None
        self._current_event_title: str | None = None
        self._last_check_time: datetime | None = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._calendar_entity_id = entry_infos.get(CONF_SCHEDULER_CALENDAR)
        self._default_preset = entry_infos.get(
            CONF_SCHEDULER_DEFAULT_PRESET, VThermPreset.FROST
        )

        if (
            entry_infos.get(CONF_USE_SCHEDULER_FEATURE, False)
            and self._calendar_entity_id is not None
        ):
            self._is_configured = True
            self._scheduled_preset = None
            _LOGGER.debug(
                "%s - Scheduler configured with calendar %s, default preset %s",
                self,
                self._calendar_entity_id,
                self._default_preset,
            )

    @overrides
    async def start_listening(self):
        """Start listening the calendar entity and periodic updates"""
        if self._is_configured:
            self.stop_listening()

            # Listen to calendar state changes
            self.add_listener(
                async_track_state_change_event(
                    self.hass,
                    [self._calendar_entity_id],
                    self._calendar_state_changed,
                )
            )

            # Also check periodically (every minute) in case calendar state doesn't update
            self.add_listener(
                async_track_time_interval(
                    self.hass,
                    self._async_periodic_check,
                    timedelta(minutes=1),
                )
            )

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the current state from calendar
        Returns True if a change has been made"""
        if not self._is_configured:
            return False

        return await self._update_scheduled_preset()

    @callback
    async def _calendar_state_changed(self, event: Event[EventStateChangedData]):
        """Handle calendar state changes."""
        new_state = event.data.get("new_state")
        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Calendar state changed to {new_state.state if new_state else None}",
        )

        if new_state is None:
            return

        await self._update_scheduled_preset()

    async def _async_periodic_check(self, _now=None):
        """Periodic check for calendar updates"""
        await self._update_scheduled_preset()

    async def _update_scheduled_preset(self) -> bool:
        """Update the scheduled preset based on current calendar state.
        Returns True if preset changed."""
        if not self._is_configured:
            return False

        old_preset = self._scheduled_preset
        old_event_title = self._current_event_title

        # Get calendar state
        calendar_state = self.hass.states.get(self._calendar_entity_id)

        if calendar_state is None or calendar_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            _LOGGER.debug(
                "%s - Calendar %s is unavailable",
                self,
                self._calendar_entity_id,
            )
            self._scheduled_preset = None
            self._current_event_title = None
        elif calendar_state.state == STATE_ON:
            # Calendar has an active event
            event_title = calendar_state.attributes.get("message", "")
            self._current_event_title = event_title
            self._scheduled_preset = self._get_preset_from_event_title(event_title)

            _LOGGER.debug(
                "%s - Calendar event active: '%s' -> preset: %s",
                self,
                event_title,
                self._scheduled_preset,
            )
        else:
            # No active event (STATE_OFF)
            self._scheduled_preset = None
            self._current_event_title = None
            _LOGGER.debug(
                "%s - No active calendar event, using default preset",
                self,
            )

        self._last_check_time = datetime.now()

        # Check if preset changed
        if old_preset != self._scheduled_preset:
            _LOGGER.info(
                "%s - Scheduled preset changed: %s -> %s (event: '%s')",
                self,
                old_preset,
                self._scheduled_preset,
                self._current_event_title,
            )

            # Fire event
            self._vtherm.send_event(
                EventType.SCHEDULER_EVENT,
                {
                    "old_preset": old_preset,
                    "new_preset": self._scheduled_preset,
                    "event_title": self._current_event_title,
                    "calendar_entity_id": self._calendar_entity_id,
                },
            )

            # Notify VTherm to update state
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(True)
            return True

        return False

    def _get_preset_from_event_title(self, title: str) -> str | None:
        """Extract preset from calendar event title.
        The title should contain a preset keyword (case-insensitive).
        Returns the preset or None if no match found.
        """
        if not title:
            return None

        title_lower = title.lower().strip()

        # Check for exact matches first
        for keyword, preset in PRESET_KEYWORDS.items():
            if keyword == title_lower:
                return preset

        # Then check for partial matches (keyword contained in title)
        for keyword, preset in PRESET_KEYWORDS.items():
            if keyword in title_lower:
                return preset

        _LOGGER.warning(
            "%s - Calendar event '%s' does not match any preset keyword",
            self,
            title,
        )
        return None

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "is_scheduler_configured": self._is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "scheduler_manager": {
                        "calendar_entity_id": self._calendar_entity_id,
                        "default_preset": self._default_preset,
                        "scheduled_preset": self._scheduled_preset,
                        "current_event_title": self._current_event_title,
                        "last_check_time": (
                            self._last_check_time.isoformat()
                            if self._last_check_time
                            else None
                        ),
                    }
                }
            )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if the scheduler is configured"""
        return self._is_configured

    @property
    def scheduled_preset(self) -> str | None:
        """Return the current scheduled preset or None if no event is active"""
        if not self._is_configured:
            return None
        return self._scheduled_preset

    @property
    def effective_preset(self) -> str:
        """Return the effective preset (scheduled or default)"""
        if not self._is_configured:
            return None
        return self._scheduled_preset if self._scheduled_preset else self._default_preset

    @property
    def has_active_event(self) -> bool:
        """Return True if there's an active calendar event"""
        return self._is_configured and self._scheduled_preset is not None

    @property
    def default_preset(self) -> str:
        """Return the default preset"""
        return self._default_preset

    @property
    def calendar_entity_id(self) -> str | None:
        """Return the calendar entity id"""
        return self._calendar_entity_id

    @property
    def current_event_title(self) -> str | None:
        """Return the current event title"""
        return self._current_event_title

    def __str__(self):
        return f"SchedulerManager-{self.name}"
