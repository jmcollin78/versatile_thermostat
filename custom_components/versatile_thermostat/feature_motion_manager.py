""" Implements the Motion Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any
from datetime import timedelta

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
    EventStateChangedData,
    async_call_later,
)

from homeassistant.components.climate import (
    PRESET_ACTIVITY,
)

from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)


class FeatureMotionManager(BaseFeatureManager):
    """The implementation of the Motion feature"""

    unrecorded_attributes = frozenset(
        {
            "motion_sensor_entity_id",
            "is_motion_configured",
            "motion_delay_sec",
            "motion_off_delay_sec",
            "motion_preset",
            "no_motion_preset",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._motion_state: str = STATE_UNAVAILABLE
        self._motion_sensor_entity_id: str = None
        self._motion_delay_sec: int | None = 0
        self._motion_off_delay_sec: int | None = 0
        self._motion_preset: str | None = None
        self._no_motion_preset: str | None = None
        self._is_configured: bool = False
        self._motion_call_cancel: callable = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self.dearm_motion_timer()

        self._motion_sensor_entity_id = entry_infos.get(CONF_MOTION_SENSOR, None)
        self._motion_delay_sec = entry_infos.get(CONF_MOTION_DELAY, 0)
        self._motion_off_delay_sec = entry_infos.get(CONF_MOTION_OFF_DELAY, None)
        if not self._motion_off_delay_sec:
            self._motion_off_delay_sec = self._motion_delay_sec

        self._motion_preset = entry_infos.get(CONF_MOTION_PRESET)
        self._no_motion_preset = entry_infos.get(CONF_NO_MOTION_PRESET)
        if (
            self._motion_sensor_entity_id is not None
            and self._motion_preset is not None
            and self._no_motion_preset is not None
        ):
            self._is_configured = True
            self._motion_state = STATE_UNKNOWN

    @overrides
    def start_listening(self):
        """Start listening the underlying entity"""
        if self._is_configured:
            self.stop_listening()
            self.add_listener(
                async_track_state_change_event(
                    self.hass,
                    [self._motion_sensor_entity_id],
                    self._motion_sensor_changed,
                )
            )

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""
        self.dearm_motion_timer()
        super().stop_listening()

    def dearm_motion_timer(self):
        """Dearm the eventual motion time running"""
        if self._motion_call_cancel:
            self._motion_call_cancel()
            self._motion_call_cancel = None

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured:

            motion_state = self.hass.states.get(self._motion_sensor_entity_id)
            if motion_state and motion_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug(
                    "%s - Motion state have been retrieved: %s",
                    self,
                    self._motion_state,
                )
                # recalculate the right target_temp in activity mode
                ret = await self.update_motion_state(motion_state.state, False)

        return ret

    @callback
    async def _motion_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle motion sensor changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Motion changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._vtherm.preset_mode,
            PRESET_ACTIVITY,
        )

        if new_state is None or new_state.state not in (STATE_OFF, STATE_ON):
            return

        # Check delay condition
        async def try_motion_condition(_):
            self.dearm_motion_timer()

            try:
                delay = (
                    self._motion_delay_sec
                    if new_state.state == STATE_ON
                    else self._motion_off_delay_sec
                )
                long_enough = condition.state(
                    self.hass,
                    self._motion_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=delay),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Motion delay condition is not satisfied (the sensor have change its state during the delay). Check motion sensor state"
                )
                # Get sensor current state
                motion_state = self.hass.states.get(self._motion_sensor_entity_id)
                _LOGGER.debug(
                    "%s - motion_state=%s, new_state.state=%s",
                    self,
                    motion_state.state,
                    new_state.state,
                )
                if (
                    motion_state.state == new_state.state
                    and new_state.state == STATE_ON
                ):
                    _LOGGER.debug(
                        "%s - the motion sensor is finally 'on' after the delay", self
                    )
                    long_enough = True
                else:
                    long_enough = False

            if long_enough:
                _LOGGER.debug("%s - Motion delay condition is satisfied", self)
                await self.update_motion_state(new_state.state)
            else:
                await self.update_motion_state(
                    STATE_ON if new_state.state == STATE_OFF else STATE_OFF
                )

        im_on = self._motion_state == STATE_ON
        delay_running = self._motion_call_cancel is not None
        event_on = new_state.state == STATE_ON

        def arm():
            """Arm the timer"""
            delay = (
                self._motion_delay_sec
                if new_state.state == STATE_ON
                else self._motion_off_delay_sec
            )
            self._motion_call_cancel = async_call_later(
                self.hass, timedelta(seconds=delay), try_motion_condition
            )

        # if I'm off
        if not im_on:
            if event_on and not delay_running:
                _LOGGER.debug(
                    "%s - Arm delay cause i'm off and event is on and no delay is running",
                    self,
                )
                arm()
                return try_motion_condition
            # Ignore the event
            _LOGGER.debug("%s - Event ignored cause i'm already off", self)
            return None
        else:  # I'm On
            if not event_on and not delay_running:
                _LOGGER.info("%s - Arm delay cause i'm on and event is off", self)
                arm()
                return try_motion_condition
            if event_on and delay_running:
                _LOGGER.debug(
                    "%s - Desarm off delay cause i'm on and event is on and a delay is running",
                    self,
                )
                self.dearm_motion_timer()
                return None
            # Ignore the event
            _LOGGER.debug("%s - Event ignored cause i'm already on", self)
            return None

    async def update_motion_state(
        self, new_state: str = None, recalculate: bool = True
    ) -> bool:
        """Update the value of the motion sensor and update the VTherm state accordingly
        Return true if a change has been made"""

        _LOGGER.info("%s - Updating motion state. New state is %s", self, new_state)
        old_motion_state = self._motion_state
        if new_state is not None:
            self._motion_state = STATE_ON if new_state == STATE_ON else STATE_OFF

        if self._vtherm.preset_mode == PRESET_ACTIVITY:
            new_preset = self.get_current_motion_preset()
            _LOGGER.info(
                "%s - Motion condition have changes. New preset temp will be %s",
                self,
                new_preset,
            )
            # We do not change the preset which is kept to ACTIVITY but only the target_temperature
            # We take the motion into account
            new_temp = self._vtherm.find_preset_temp(new_preset)
            old_temp = self._vtherm.target_temperature
            if new_temp != old_temp:
                await self._vtherm.change_target_temperature(new_temp)

            if new_temp != old_temp and recalculate:
                self._vtherm.recalculate()
                await self._vtherm.async_control_heating(force=True)

        return old_motion_state != self._motion_state

    def get_current_motion_preset(self) -> str:
        """Calculate and return the current motion preset"""
        return (
            self._motion_preset
            if self._motion_state == STATE_ON
            else self._no_motion_preset
        )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "motion_sensor_entity_id": self._motion_sensor_entity_id,
                "motion_state": self._motion_state,
                "is_motion_configured": self._is_configured,
                "motion_delay_sec": self._motion_delay_sec,
                "motion_off_delay_sec": self._motion_off_delay_sec,
                "motion_preset": self._motion_preset,
                "no_motion_preset": self._no_motion_preset,
            }
        )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the motion is configured"""
        return self._is_configured

    @property
    def motion_state(self) -> str | None:
        """Return the current motion state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._motion_state

    @property
    def is_motion_detected(self) -> bool:
        """Return true if the motion is configured and motion sensor is OFF"""
        return self._is_configured and self._motion_state in [
            STATE_ON,
        ]

    @property
    def motion_sensor_entity_id(self) -> bool:
        """Return true if the motion is configured and motion sensor is OFF"""
        return self._motion_sensor_entity_id

    @property
    def motion_delay_sec(self) -> bool:
        """Return the motion delay"""
        return self._motion_delay_sec

    @property
    def motion_off_delay_sec(self) -> bool:
        """Return motion delay off"""
        return self._motion_off_delay_sec

    @property
    def motion_preset(self) -> bool:
        """Return motion preset"""
        return self._motion_preset

    @property
    def no_motion_preset(self) -> bool:
        """Return no motion preset"""
        return self._no_motion_preset

    def __str__(self):
        return f"MotionManager-{self.name}"
