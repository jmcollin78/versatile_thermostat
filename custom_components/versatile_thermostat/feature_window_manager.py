""" Implements the Window Feature Manager """

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


from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData
from .vtherm_hvac_mode import VThermHvacMode

from .base_manager import BaseFeatureManager
from .open_window_algorithm import WindowOpenDetectionAlgorithm

_LOGGER = logging.getLogger(__name__)


class FeatureWindowManager(BaseFeatureManager):
    """The implementation of the Window feature"""

    unrecorded_attributes = frozenset(
        {
            "window_sensor_entity_id",
            "is_window_configured",
            "window_delay_sec",
            "window_off_delay_sec",
            "window_auto_configured",
            "window_auto_open_threshold",
            "window_auto_close_threshold",
            "window_auto_max_duration",
            "window_action",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._window_sensor_entity_id: str = None
        self._window_state: str = STATE_UNAVAILABLE
        self._window_auto_open_threshold: float = 0
        self._window_auto_close_threshold: float = 0
        self._window_auto_max_duration: int = 0
        self._window_auto_state: bool = False
        self._window_auto_algo: WindowOpenDetectionAlgorithm = None
        self._is_window_bypass: bool = False
        self._window_action: str = None
        self._window_delay_sec: int | None = 0
        self._window_off_delay_sec: int | None = 0
        self._is_configured: bool = False
        self._is_window_auto_configured: bool = False
        self._window_call_cancel: callable = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self.dearm_window_timer()

        self._window_auto_state = STATE_UNAVAILABLE
        self._window_state = STATE_UNAVAILABLE

        self._window_sensor_entity_id = entry_infos.get(CONF_WINDOW_SENSOR)
        self._window_delay_sec = entry_infos.get(CONF_WINDOW_DELAY)
        # default is the WINDOW_ON delay if not configured
        self._window_off_delay_sec = entry_infos.get(CONF_WINDOW_OFF_DELAY, self._window_delay_sec)

        self._window_action = (
            entry_infos.get(CONF_WINDOW_ACTION) or CONF_WINDOW_TURN_OFF
        )

        self._window_auto_open_threshold = entry_infos.get(
            CONF_WINDOW_AUTO_OPEN_THRESHOLD
        )
        self._window_auto_close_threshold = entry_infos.get(
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD
        )
        self._window_auto_max_duration = entry_infos.get(CONF_WINDOW_AUTO_MAX_DURATION)

        use_window_feature = entry_infos.get(CONF_USE_WINDOW_FEATURE, False)

        if (  # pylint: disable=too-many-boolean-expressions
            use_window_feature
            and self._window_sensor_entity_id is None
            and self._window_auto_open_threshold is not None
            and self._window_auto_open_threshold > 0.0
            and self._window_auto_close_threshold is not None
            and self._window_auto_max_duration is not None
            and self._window_auto_max_duration > 0
            and self._window_action is not None
        ):
            self._is_window_auto_configured = True
            self._window_auto_state = STATE_UNKNOWN

        self._window_auto_algo = WindowOpenDetectionAlgorithm(
            alert_threshold=self._window_auto_open_threshold,
            end_alert_threshold=self._window_auto_close_threshold,
        )

        if self._is_window_auto_configured or (
            use_window_feature
            and self._window_sensor_entity_id is not None
            and self._window_delay_sec is not None
            and self._window_action is not None
        ):
            self._is_configured = True
            self._window_state = STATE_UNKNOWN

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""

        # Try to get last window bypass state
        old_state = await self._vtherm.async_get_last_state()
        self._is_window_bypass = old_state is not None and hasattr(old_state, "attributes") and old_state.attributes.get("is_window_bypass") is True

        if self._is_configured:
            self.stop_listening()
            if self._window_sensor_entity_id:
                self.add_listener(
                    async_track_state_change_event(
                        self.hass,
                        [self._window_sensor_entity_id],
                        self._window_sensor_changed,
                    )
                )

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""
        self.dearm_window_timer()
        super().stop_listening()

    def dearm_window_timer(self):
        """Dearm the eventual motion time running"""
        if self._window_call_cancel:
            self._window_call_cancel()
            self._window_call_cancel = None

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured and self._window_sensor_entity_id is not None:

            window_state = self.hass.states.get(self._window_sensor_entity_id)
            if window_state and window_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug(
                    "%s - Window state have been retrieved: %s",
                    self,
                    self._window_state,
                )
                # recalculate the right target_temp in activity mode
                ret = await self.update_window_state(window_state.state)

        return ret

    @callback
    async def _window_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle window sensor changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        _LOGGER.info(
            "%s - Window changed. Event.new_state is %s, _hvac_mode=%s",
            self,
            new_state,
            self._vtherm.hvac_mode,
        )

        # Check delay condition
        async def try_window_condition(_):
            try:
                long_enough = condition.state(
                    self._hass,
                    self._window_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=delay),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Window delay condition is not satisfied. Ignore window event"
                )
                self._window_state = old_state.state or STATE_OFF
                return

            _LOGGER.debug("%s - Window delay condition is satisfied", self)

            if self._window_state == new_state.state:
                _LOGGER.debug("%s - no change in window state. Forget the event")
                return

            _LOGGER.debug("%s - Window ByPass is : %s", self, self._is_window_bypass)
            if self._is_window_bypass:
                _LOGGER.info(
                    "%s - Window ByPass is activated. Ignore window event", self
                )
                # We change the state but we don't apply the change
                self._window_state = new_state.state
            else:
                await self.update_window_state(new_state.state)

            self._vtherm.update_custom_attributes()

        delay = self._window_delay_sec if new_state.state == STATE_ON else self._window_off_delay_sec
        if new_state is None or old_state is None or new_state.state == old_state.state:
            return try_window_condition

        self.dearm_window_timer()
        self._window_call_cancel = async_call_later(self.hass, timedelta(seconds=delay), try_window_condition)
        # For testing purpose we need to access the inner function
        return try_window_condition

    async def update_window_state(self, new_state: str | None = None, bypass: bool = False) -> bool:
        """Change the window detection state.
        new_state is on if an open window have been detected or off else
        return True if the state have changed
        """

        # No changes
        if (old_state := self._window_state) == new_state and not bypass:
            return False

        # Windows is now closed
        if new_state != STATE_ON:
            _LOGGER.info("%s - Window is detected as closed.", self)

            # if self._window_action in [
            #     CONF_WINDOW_FROST_TEMP,
            #     CONF_WINDOW_ECO_TEMP,
            # ]:
            #     await self._vtherm.restore_target_temp(force=True)

            # default to TURN_OFF
            # elif self._window_action in [CONF_WINDOW_TURN_OFF]:
            #     if (
            #         self._vtherm.last_central_mode != CENTRAL_MODE_STOPPED
            #         and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
            #     ):
            #         self._vtherm.set_hvac_off_reason(None)
            #         await self._vtherm.restore_hvac_mode(True)
            # elif self._window_action in [CONF_WINDOW_FAN_ONLY]:
            #     if self._vtherm.last_central_mode != CENTRAL_MODE_STOPPED:
            #         self._vtherm.set_hvac_off_reason(None)
            #         await self._vtherm.restore_hvac_mode(True)
            # else:
            #     _LOGGER.error(
            #         "%s - undefined window_action %s. Please open a bug in the github of this project with this log",
            #         self,
            #         self._window_action,
            #     )
            #     return False
        # Window is now opened
        else:
            _LOGGER.info("%s - Window is detected as open. Eventually apply window action %s", self, self._window_action)
            # if self._window_action == CONF_WINDOW_TURN_OFF and not self._vtherm.is_on:
            #    _LOGGER.debug(
            #        "%s is already off. Forget turning off VTherm due to window detection"
            #    )
            #    if not bypass:
            #        self._window_state = new_state
            #    return False
            #
            ## self._window_state = new_state
            # if self._window_action in [
            #    CONF_WINDOW_TURN_OFF,
            #    CONF_WINDOW_FAN_ONLY,
            # ]:
            #    self._vtherm.save_hvac_mode()
            # elif self._window_action in [
            #    CONF_WINDOW_FROST_TEMP,
            #    CONF_WINDOW_ECO_TEMP,
            # ]:
            #    self._vtherm.save_target_temp()
            #
            # if (
            #    self._window_action == CONF_WINDOW_FAN_ONLY
            #    and VThermHvacMode_FAN_ONLY in self._vtherm.hvac_modes
            # ):
            #    await self._vtherm.async_set_hvac_mode(VThermHvacMode_FAN_ONLY)
            # elif (
            #    self._window_action == CONF_WINDOW_FROST_TEMP
            #    and self._vtherm.is_preset_configured(VThermPreset.FROST)
            # ):
            #    await self._vtherm.change_target_temperature(self._vtherm.find_preset_temp(VThermPreset.FROST), True)
            # elif (
            #    self._window_action == CONF_WINDOW_ECO_TEMP
            #    and self._vtherm.is_preset_configured(VThermPreset.ECO)
            # ):
            #    await self._vtherm.change_target_temperature(self._vtherm.find_preset_temp(VThermPreset.ECO), True)
            # else:  # default is to turn_off
            #    self._vtherm.set_hvac_off_reason(HVAC_OFF_REASON_WINDOW_DETECTION)
            #    await self._vtherm.async_set_hvac_mode(VThermHvacMode_OFF)

        # if bypass:
        #     _LOGGER.info("%s - Window is bypassed. Forget the window detection", self)
        #     return False

        self._window_state = new_state
        if old_state != new_state:
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(True)
            return True

        return False

    async def manage_window_auto(self, in_cycle=False) -> callable:
        """The management of the window auto feature
        Returns the dearm function used to deactivate the window auto"""

        async def dearm_window_auto(_):
            """Callback that will be called after end of WINDOW_AUTO_MAX_DURATION"""
            _LOGGER.info("Unset window auto because MAX_DURATION is exceeded")
            await deactivate_window_auto(auto=True)

        async def deactivate_window_auto(auto=False):
            """Deactivation of the Window auto state"""
            _LOGGER.warning(
                "%s - End auto detection of open window slope=%.3f", self, slope
            )
            # Send an event
            cause = "max duration expiration" if auto else "end of slope alert"
            self._vtherm.send_event(
                EventType.WINDOW_AUTO_EVENT,
                {"type": "end", "cause": cause, "curve_slope": slope},
            )
            # Set attributes
            self._window_auto_state = STATE_OFF
            await self.update_window_state(self._window_auto_state)
            # await self.restore_hvac_mode(True)

            self.dearm_window_timer()

        if not self._window_auto_algo:
            return None

        if in_cycle:
            slope = self._window_auto_algo.check_age_last_measurement(
                temperature=self._vtherm.ema_temperature,
                datetime_now=self._vtherm.now,
            )
        else:
            slope = self._window_auto_algo.add_temp_measurement(
                temperature=self._vtherm.ema_temperature,
                datetime_measure=self._vtherm.last_temperature_measure,
            )

        _LOGGER.debug(
            "%s - Window auto is on, check the alert. last slope is %.3f",
            self,
            slope if slope is not None else 0.0,
        )

        if self.is_window_bypass or not self._is_window_auto_configured:
            _LOGGER.debug(
                "%s - Window auto event is ignored because bypass is ON or window auto detection is disabled",
                self,
            )
            return None

        if self._window_auto_algo.is_window_open_detected() and self._window_auto_state in [STATE_UNKNOWN, STATE_OFF] and self._vtherm.hvac_mode != VThermHvacMode_OFF:
            if (
                self._vtherm.proportional_algorithm
                and self._vtherm.proportional_algorithm.on_percent <= 0.0
            ):
                _LOGGER.info(
                    "%s - Start auto detection of open window slope=%.3f but no heating detected (on_percent<=0). Forget the event",
                    self,
                    slope,
                )
                return dearm_window_auto

            _LOGGER.warning(
                "%s - Start auto detection of open window slope=%.3f", self, slope
            )

            # Send an event
            self._vtherm.send_event(
                EventType.WINDOW_AUTO_EVENT,
                {"type": "start", "cause": "slope alert", "curve_slope": slope},
            )
            # Set attributes
            self._window_auto_state = STATE_ON
            await self.update_window_state(self._window_auto_state)

            # Arm the end trigger
            self.dearm_window_timer()
            self._window_call_cancel = async_call_later(
                self.hass,
                timedelta(minutes=self._window_auto_max_duration),
                dearm_window_auto,
            )

        elif (
            self._window_auto_algo.is_window_close_detected()
            and self._window_auto_state == STATE_ON
        ):
            await deactivate_window_auto(False)

        # For testing purpose we need to return the inner function
        return dearm_window_auto

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "window_state": self.window_state,
                "window_auto_state": self.window_auto_state,
                "window_action": self.window_action,
                "is_window_bypass": self._is_window_bypass,
                "window_sensor_entity_id": self._window_sensor_entity_id,
                "window_delay_sec": self._window_delay_sec,
                "window_off_delay_sec": self._window_off_delay_sec,
                "is_window_configured": self._is_configured,
                "is_window_auto_configured": self._is_window_auto_configured,
                "window_auto_open_threshold": self._window_auto_open_threshold,
                "window_auto_close_threshold": self._window_auto_close_threshold,
                "window_auto_max_duration": self._window_auto_max_duration,
            }
        )

    async def set_window_bypass(self, window_bypass: bool) -> bool:
        """Set the window bypass flag
        Return True if state have been changed"""
        self._is_window_bypass = window_bypass

        _LOGGER.info("%s - Last window state was %s & ByPass is now %s.",self,self._window_state,self._is_window_bypass,)
        self._vtherm.requested_state.force_changed()
        await self._vtherm.update_states(True)
        # if self._is_window_bypass:
        #     return await self.update_window_state(STATE_OFF, True)
        # else:
        #     return await self.update_window_state(self._window_state, True)

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the window feature is configured"""
        return self._is_configured

    @property
    def is_window_auto_configured(self) -> bool:
        """Return True of the window automatic detection is configured"""
        return self._is_window_auto_configured

    @property
    def window_state(self) -> str | None:
        """Return the current window state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._window_state

    @property
    def window_auto_state(self) -> str | None:
        """Return the current window auto state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._window_auto_state

    @property
    def is_window_bypass(self) -> str | None:
        """Return True if the window bypass is activated"""
        if not self._is_configured:
            return False
        return self._is_window_bypass

    @property
    def is_window_detected(self) -> bool:
        """Return true if the window is configured and open and bypass is not ON"""
        return self._is_configured and (
            self._window_state == STATE_ON or self._window_auto_state == STATE_ON
        ) and not self._is_window_bypass

    @property
    def window_sensor_entity_id(self) -> bool:
        """Return true if the presence is configured and presence sensor is OFF"""
        return self._window_sensor_entity_id

    @property
    def window_delay_sec(self) -> bool:
        """Return the window on delay"""
        return self._window_delay_sec

    @property
    def window_off_delay_sec(self) -> bool:
        """Return the window off delay"""
        return self._window_off_delay_sec

    @property
    def window_action(self) -> bool:
        """Return the window action"""
        return self._window_action

    @property
    def window_auto_open_threshold(self) -> bool:
        """Return the window_auto_open_threshold"""
        return self._window_auto_open_threshold

    @property
    def window_auto_close_threshold(self) -> bool:
        """Return the window_auto_close_threshold"""
        return self._window_auto_close_threshold

    @property
    def window_auto_max_duration(self) -> bool:
        """Return the window_auto_max_duration"""
        return self._window_auto_max_duration

    @property
    def last_slope(self) -> float:
        """Return the last slope (in °C/hour)"""
        if not self._window_auto_algo:
            return None
        return self._window_auto_algo.last_slope

    def __str__(self):
        return f"WindowManager-{self.name}"
