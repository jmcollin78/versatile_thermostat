"""Implements the Calendar scheduling Feature Manager"""

# pylint: disable=line-too-long

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from vtherm_api.log_collector import get_vtherm_logger

from .base_manager import BaseFeatureManager
from .commons import write_event_log
from .commons_type import ConfigData
from .const import (
    CALENDAR_END_PRESET_PREVIOUS,
    CONF_CALENDAR_END_PRESET,
    CONF_CALENDAR_ENTITY,
    CONF_CALENDAR_EVENT_PRESET,
    CONF_CALENDAR_MAX_PREHEAT_MIN,
    CONF_CALENDAR_PREHEAT_GRADIENT,
    CONF_USE_CALENDAR_FEATURE,
    DEFAULT_CALENDAR_MAX_PREHEAT_MIN,
    overrides,
)
from .vtherm_hvac_mode import VThermHvacMode_HEAT
from .vtherm_preset import VThermPreset

_LOGGER = get_vtherm_logger(__name__)

# The calendar is read at this pace. A removed event is released when it is still missing one read later.
CALENDAR_REFRESH_INTERVAL = timedelta(minutes=15)

CALENDAR_STATE_IDLE = "idle"
CALENDAR_STATE_PREHEAT = "preheat"
CALENDAR_STATE_EVENT = "event"


@dataclass(frozen=True)
class CalendarBlock:
    """A time span covered by one or several contiguous calendar events"""

    start: datetime
    end: datetime

    def overlaps(self, other: "CalendarBlock") -> bool:
        """True if both spans share some time"""
        return self.start < other.end and other.start < self.end


def merge_events(spans: Iterable[tuple[datetime, datetime]]) -> list[CalendarBlock]:
    """Merge overlapping and contiguous events into blocks sorted by start"""
    blocks: list[CalendarBlock] = []
    for start, end in sorted(span for span in spans if span[0] < span[1]):
        if blocks and start <= blocks[-1].end:
            blocks[-1] = CalendarBlock(blocks[-1].start, max(blocks[-1].end, end))
        else:
            blocks.append(CalendarBlock(start, end))
    return blocks


def _parse(value: str) -> datetime:
    """Parse the start or end of an event. An all-day event starts and ends at local midnight"""
    return dt_util.as_local(dt_util.parse_datetime(value, raise_on_error=True))


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class FeatureCalendarManager(BaseFeatureManager):
    """The implementation of the Calendar scheduling feature.

    A preset is applied while an event of the calendar is running and another one when it ends.
    With a preheat gradient, the event preset is applied early enough for the room to be warm when the event starts.
    The presets are only applied on transitions, so a manual change is kept until the next one.
    """

    unrecorded_attributes = frozenset(
        {
            "is_calendar_configured",
            "calendar_manager",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._is_configured: bool = False
        self._calendar_entity_id: str | None = None
        self._event_preset: VThermPreset = VThermPreset.COMFORT
        # None restores the preset which was active before the event
        self._end_preset: VThermPreset | None = VThermPreset.ECO
        self._gradient: float = 0.0
        self._max_preheat: timedelta = timedelta(0)

        self._blocks: list[CalendarBlock] = []
        self._is_calendar_available: bool = False
        # True when the calendar has been read since the last evaluation
        self._is_fresh: bool = False
        # The block being preheated or running. It is kept once set, whatever the temperature does
        self._target: CalendarBlock | None = None
        self._previous_preset: VThermPreset | None = None
        self._missing_since: datetime | None = None
        self._upcoming: CalendarBlock | None = None
        self._preheat_start: datetime | None = None

        self._cancel_wakeup: CALLBACK_TYPE | None = None
        self._read_lock = asyncio.Lock()
        self._evaluate_lock = asyncio.Lock()

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._calendar_entity_id = entry_infos.get(CONF_CALENDAR_ENTITY)
        self._is_configured = entry_infos.get(CONF_USE_CALENDAR_FEATURE, False) is True and self._calendar_entity_id is not None
        self._event_preset = VThermPreset(entry_infos.get(CONF_CALENDAR_EVENT_PRESET) or VThermPreset.COMFORT)
        end_preset = entry_infos.get(CONF_CALENDAR_END_PRESET) or VThermPreset.ECO
        self._end_preset = None if end_preset == CALENDAR_END_PRESET_PREVIOUS else VThermPreset(end_preset)
        self._gradient = float(entry_infos.get(CONF_CALENDAR_PREHEAT_GRADIENT) or 0)
        max_preheat_min = entry_infos.get(CONF_CALENDAR_MAX_PREHEAT_MIN)
        self._max_preheat = timedelta(minutes=float(DEFAULT_CALENDAR_MAX_PREHEAT_MIN if max_preheat_min is None else max_preheat_min))

    @overrides
    async def start_listening(self):
        """Start listening the calendar and read it without waiting for the answer"""
        if not self._is_configured:
            return
        self.stop_listening()
        self.add_listener(async_track_state_change_event(self.hass, [self._calendar_entity_id], self._async_refresh))
        self.add_listener(async_track_time_interval(self.hass, self._async_refresh, CALENDAR_REFRESH_INTERVAL))
        self.hass.async_create_task(self._async_refresh(), f"{self} - first read")

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""
        self._clear_wakeup()
        super().stop_listening()

    @overrides
    def restore_state(self, old_state: Any):
        """Restore the running block so that a restart neither stops nor restarts the heating"""
        manager_attr = old_state.attributes.get("calendar_manager")
        if not self._is_configured or not manager_attr or manager_attr.get("calendar_entity_id") != self._calendar_entity_id or not manager_attr.get("event_start"):
            return

        try:
            target = CalendarBlock(datetime.fromisoformat(manager_attr["event_start"]), datetime.fromisoformat(manager_attr["event_end"]))
            previous_preset = manager_attr.get("previous_preset")
            missing_since = manager_attr.get("missing_since")
            self._previous_preset = VThermPreset(previous_preset) if previous_preset else None
            self._missing_since = datetime.fromisoformat(missing_since) if missing_since else None
            self._target = target
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.error("%s - Failed to restore calendar state: %s", self, err)

    @overrides
    async def refresh_state(self) -> bool:
        """Follow the schedule from the events already read. This is also called when the room temperature changes.
        Return True if the scheduled preset has changed"""
        if not self._is_configured or not self._vtherm.is_ready or not self._active_listener:
            return False

        async with self._evaluate_lock:
            now = self._vtherm.now
            blocks = [block for block in self._blocks if block.end > now]
            target = self._target

            if target:
                if match := next((block for block in blocks if block.overlaps(target)), None):
                    target, self._missing_since = match, None
                elif self._is_fresh:
                    self._missing_since = self._missing_since or now
                    if now - self._missing_since >= CALENDAR_REFRESH_INTERVAL:
                        target = None
                if target and target.end <= now:
                    target = None
            self._is_fresh = False

            self._upcoming = self._preheat_start = None
            if target is None:
                self._missing_since = None
                if blocks:
                    self._upcoming = blocks[0]
                    self._preheat_start = self._upcoming.start - self._lead_time()
                    if self._preheat_start <= now:
                        target, self._upcoming, self._preheat_start = self._upcoming, None, None

            self._schedule_wakeup(now, target)
            return await self._async_set_target(target)

    async def _async_refresh(self, _=None):
        """Read the calendar, follow the schedule and publish the result"""
        async with self._read_lock:
            blocks = await self._async_read_blocks()
            self._is_calendar_available = blocks is not None
            if blocks is not None:
                self._blocks, self._is_fresh = blocks, True

        await self.refresh_state()
        if self._vtherm.is_ready and self._active_listener:
            self._vtherm.update_custom_attributes()
            self._vtherm.async_write_ha_state()

    async def _async_read_blocks(self) -> list[CalendarBlock] | None:
        """Read the upcoming events. Return None if the calendar cannot be read: the events already known are then kept"""
        state = self.hass.states.get(self._calendar_entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None

        now = self._vtherm.now
        try:
            response = await self.hass.services.async_call(
                Platform.CALENDAR,
                "get_events",
                {
                    ATTR_ENTITY_ID: self._calendar_entity_id,
                    "start_date_time": now,
                    "end_date_time": now + self._max_preheat + 2 * CALENDAR_REFRESH_INTERVAL,
                },
                blocking=True,
                return_response=True,
            )
            events = response[self._calendar_entity_id]["events"]
            return merge_events((_parse(event["start"]), _parse(event["end"])) for event in events)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("%s - Cannot read the events of %s: %s", self, self._calendar_entity_id, err)
            return None

    def _heating_duration(self) -> timedelta | None:
        """The time needed to heat the room up to the event preset, or None if it cannot be estimated"""
        vtherm = self._vtherm
        if self._gradient <= 0 or vtherm.requested_state.hvac_mode != VThermHvacMode_HEAT:
            return None
        current_temp = vtherm.current_temperature
        target_temp = vtherm.find_preset_temp(self._event_preset)
        if current_temp is None or not target_temp:
            return None
        return timedelta(hours=max(target_temp - current_temp, 0) / self._gradient)

    def _lead_time(self) -> timedelta:
        """How long before an event the preheat has to start"""
        return min(self._heating_duration() or timedelta(0), self._max_preheat)

    def _schedule_wakeup(self, now: datetime, target: CalendarBlock | None):
        """Read the calendar again at the next expected transition"""
        self._clear_wakeup()
        if target:
            wakeups = [target.end]
            if self._missing_since:
                wakeups.append(self._missing_since + CALENDAR_REFRESH_INTERVAL)
        else:
            wakeups = [self._preheat_start] if self._preheat_start else []

        if wakeups := [wakeup for wakeup in wakeups if wakeup > now]:
            self._cancel_wakeup = async_track_point_in_time(self.hass, self._async_refresh, min(wakeups))

    def _clear_wakeup(self):
        if self._cancel_wakeup:
            self._cancel_wakeup()
            self._cancel_wakeup = None

    async def _async_set_target(self, target: CalendarBlock | None) -> bool:
        """Change the running block and apply the preset when the schedule starts or ends"""
        previous_target, self._target = self._target, target

        if target and not previous_target:
            timed_preset_manager = self._vtherm.timed_preset_manager
            self._previous_preset = timed_preset_manager.original_preset if timed_preset_manager.is_timed_preset_active else self._vtherm.requested_state.preset
            write_event_log(_LOGGER, self._vtherm, f"Calendar {self.calendar_state} started for the event from {target.start} to {target.end}")
            await self._async_apply_preset(self._event_preset)
            return True

        if previous_target and not target:
            preset = self._end_preset or self._previous_preset
            self._previous_preset = None
            write_event_log(_LOGGER, self._vtherm, f"Calendar event ended. Applying preset {preset}")
            if preset:
                await self._async_apply_preset(preset)
            return True

        return False

    async def _async_apply_preset(self, preset: VThermPreset):
        """Apply a preset as a scheduler does. A running timed preset is kept and returns to this preset when it ends"""
        vtherm = self._vtherm
        if preset != VThermPreset.NONE and preset not in vtherm.vtherm_preset_modes:
            _LOGGER.warning("%s - preset %s is not available for this thermostat", self, preset)
            return

        if vtherm.timed_preset_manager.is_timed_preset_active:
            vtherm.timed_preset_manager.set_original_preset(preset)
        else:
            vtherm.requested_state.set_preset(preset)
            await vtherm.update_states(force=True)

        vtherm.update_custom_attributes()
        vtherm.async_write_ha_state()

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update({"is_calendar_configured": self._is_configured})
        if not self._is_configured:
            return

        heating_duration = self._heating_duration() if self._target else None
        extra_state_attributes.update(
            {
                "calendar_manager": {
                    "calendar_entity_id": self._calendar_entity_id,
                    "event_preset": str(self._event_preset),
                    "end_preset": str(self._end_preset or CALENDAR_END_PRESET_PREVIOUS),
                    "preheat_gradient": self._gradient,
                    "max_preheat_min": self._max_preheat.total_seconds() / 60,
                    "is_calendar_available": self._is_calendar_available,
                    "state": self.calendar_state,
                    "event_start": _isoformat(self._target.start if self._target else None),
                    "event_end": _isoformat(self._target.end if self._target else None),
                    "previous_preset": str(self._previous_preset) if self._previous_preset else None,
                    "missing_since": _isoformat(self._missing_since),
                    "estimated_ready_time": _isoformat(self._vtherm.now + heating_duration if heating_duration else None),
                    "next_event_start": _isoformat(self._upcoming.start if self._upcoming else None),
                    "preheat_start": _isoformat(self._preheat_start),
                }
            }
        )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if the calendar scheduling is configured"""
        return self._is_configured

    @property
    def calendar_state(self) -> str:
        """Return idle, preheat or event"""
        if self._target is None:
            return CALENDAR_STATE_IDLE
        return CALENDAR_STATE_PREHEAT if self._vtherm.now < self._target.start else CALENDAR_STATE_EVENT

    @property
    def is_detected(self) -> bool:
        """Return True while an event is preheated or running"""
        return self._target is not None

    def __str__(self):
        return f"CalendarManager-{self.name}"
