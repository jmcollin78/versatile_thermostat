""" Implements the Auto-start/stop Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any

from homeassistant.core import (
    HomeAssistant,
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .commons import write_event_log

from .base_manager import BaseFeatureManager

from .auto_start_stop_algorithm import (
    AutoStartStopDetectionAlgorithm,
)


_LOGGER = logging.getLogger(__name__)


class FeatureAutoStartStopManager(BaseFeatureManager):
    """The implementation of the AutoStartStop feature"""

    unrecorded_attributes = frozenset(
        {
            "auto_start_stop_level",
            "auto_start_stop_dtmin",
            "auto_start_stop_enable",
            "auto_start_stop_accumulated_error",
            "auto_start_stop_accumulated_error_threshold",
            "auto_start_stop_last_switch_date",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)

        self._auto_start_stop_level: str = AUTO_START_STOP_LEVEL_NONE
        self._auto_start_stop_algo: AutoStartStopDetectionAlgorithm | None = None
        self._is_configured: bool = False
        self._is_auto_start_stop_enabled: bool = False
        self._is_auto_stop_detected: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        if not self._vtherm.is_over_climate or self._vtherm.have_valve_regulation:
            return

        use_auto_start_stop = entry_infos.get(CONF_USE_AUTO_START_STOP_FEATURE, False)
        if use_auto_start_stop:
            self._auto_start_stop_level = (
                entry_infos.get(CONF_AUTO_START_STOP_LEVEL, None)
                or AUTO_START_STOP_LEVEL_NONE
            )
            self._is_configured = True
        else:
            self._auto_start_stop_level = AUTO_START_STOP_LEVEL_NONE
            self._is_configured = False

        # Instanciate the auto start stop algo
        self._auto_start_stop_algo = AutoStartStopDetectionAlgorithm(
            self._auto_start_stop_level, self.name
        )

        # Fix an eventual incoherent state
        if self._vtherm.is_on and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP:
            self._vtherm.hvac_off_reason = None

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""

    @overrides
    async def refresh_state(self) -> bool:
        """Check the auto-start-stop and an eventual action
        Return True is auto stop is detected"""

        if not self._is_configured or not self._is_auto_start_stop_enabled:
            _LOGGER.debug("%s - auto start/stop is disabled (or not configured)", self)
            self._is_auto_stop_detected = False
        else:
            # Do the auto-start-stop calculation
            slope = (self._vtherm.last_temperature_slope or 0) / 60  # to have the slope in °/min
            should_be_off = self._auto_start_stop_algo.should_be_turned_off(
                self._vtherm.requested_state.hvac_mode,
                self._vtherm.target_temperature,
                self._vtherm.current_temperature,
                slope,
                self._vtherm.now,
            )
            _LOGGER.debug("%s - auto_start_stop should be off is %s", self, should_be_off)
            if should_be_off:
                _LOGGER.info("%s - VTherm should be OFF due to auto-start-stop conditions", self)
                # self._vtherm.set_hvac_off_reason(HVAC_OFF_REASON_AUTO_START_STOP)
                # await self._vtherm.async_turn_off()

                # Send an event if vtherm is on
                if not self._is_auto_stop_detected:
                    self._vtherm.send_event(
                        event_type=EventType.AUTO_START_STOP_EVENT,
                        data={
                            "type": "stop",
                            "name": self.name,
                            "cause": "Auto stop conditions reached",
                            "hvac_mode": str(VThermHvacMode_OFF),
                            "saved_hvac_mode": str(self._vtherm.requested_state.hvac_mode),
                            "target_temperature": self._vtherm.target_temperature,
                            "current_temperature": self._vtherm.current_temperature,
                            "temperature_slope": round(slope, 3),
                            "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                            "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                        },
                    )
                self._is_auto_stop_detected = True

            else:
                _LOGGER.info("%s - VTherm should be ON due to auto-start-stop conditions", self)

                # await self._vtherm.async_turn_on()

                # Send an event
                if self._is_auto_stop_detected:
                    self._vtherm.send_event(
                        event_type=EventType.AUTO_START_STOP_EVENT,
                        data={
                            "type": "start",
                            "name": self.name,
                            "cause": "Auto start conditions reached",
                            "hvac_mode": str(self._vtherm.requested_state.hvac_mode),
                            "saved_hvac_mode": str(self._vtherm.requested_state.hvac_mode),
                            "target_temperature": self._vtherm.target_temperature,
                            "current_temperature": self._vtherm.current_temperature,
                            "temperature_slope": round(slope, 3),
                            "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                            "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                        },
                    )
                self._is_auto_stop_detected = False

        # returns True if we should stop
        return self._is_auto_stop_detected

    async def refresh_and_update_if_changed(self) -> bool:
        """Refresh the auto start/stop state and update_states of VTherm if changed
        Returns True if the state has changed, False otherwise"""
        old_auto_start_stop: bool = self.is_auto_stop_detected
        if old_auto_start_stop != await self.refresh_state():
            write_event_log(_LOGGER, self._vtherm, f"Auto start/stop state changed from {old_auto_start_stop} to {self.is_auto_stop_detected}")
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(force=True)
            return True

        return False

    async def set_auto_start_stop_enable(self, is_enabled: bool):
        """Enable/Disable the auto-start/stop feature"""
        if self._is_auto_start_stop_enabled != is_enabled:
            self._is_auto_start_stop_enabled = is_enabled

            # Send an event if the vtherm was off due to auto-start/stop and enable has been set to false
            if not is_enabled and self._vtherm.hvac_mode == VThermHvacMode_OFF and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP:
                _LOGGER.debug("%s - the vtherm is off cause auto-start/stop and enable have been set to false -> starts the VTherm")
                # Send an event
                self._vtherm.send_event(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "start",
                        "name": self.name,
                        "cause": "Auto start stop disabled",
                        "hvac_mode": str(self._vtherm.requested_state.hvac_mode),
                        "saved_hvac_mode": str(self._vtherm.requested_state.hvac_mode),
                        "target_temperature": self._vtherm.target_temperature,
                        "current_temperature": self._vtherm.current_temperature,
                        "temperature_slope": round(self._vtherm.last_temperature_slope or 0, 3),
                        "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                        "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                    },
                )

            await self.refresh_state()
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(True)

            self._vtherm.update_custom_attributes()

        # if self._vtherm.hvac_mode == VThermHvacMode_OFF and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP:
        #    _LOGGER.debug(
        #        "%s - the vtherm is off cause auto-start/stop and enable have been set to false -> starts the VTherm"
        #    )
        #    self.hass.create_task(self._vtherm.async_turn_on())
        #
        #    # Send an event
        #    self._vtherm.send_event(
        #        event_type=EventType.AUTO_START_STOP_EVENT,
        #        data={
        #            "type": "start",
        #            "name": self.name,
        #            "cause": "Auto start stop disabled",
        #            "hvac_mode": self._vtherm.hvac_mode,
        #            "saved_hvac_mode": self._vtherm.requested_state.hvac_mode,
        #            "target_temperature": self._vtherm.target_temperature,
        #            "current_temperature": self._vtherm.current_temperature,
        #            "temperature_slope": round(self._vtherm.last_temperature_slope or 0, 3),
        #            "accumulated_error": self._auto_start_stop_algo.accumulated_error,
        #            "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
        #        },
        #    )
        #
        # self._vtherm.update_custom_attributes()

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "is_auto_start_stop_configured": self.is_configured,
            }
        )
        if self.is_configured:
            extra_state_attributes.update(
                {
                    "auto_start_stop_manager": {
                        "auto_start_stop_enable": self.auto_start_stop_enable,
                        "auto_start_stop_level": self._auto_start_stop_algo.level,
                        "auto_start_stop_dtmin": self._auto_start_stop_algo.dt_min,
                        "auto_start_stop_accumulated_error": self._auto_start_stop_algo.accumulated_error,
                        "auto_start_stop_accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                        "auto_start_stop_last_switch_date": self._auto_start_stop_algo.last_switch_date,
                        "is_auto_stop_detected": self.is_auto_stop_detected,
                    }
                }
            )

    @property
    def is_auto_stop_detected(self) -> bool:
        """Return True if the auto-start/stop feature is detected"""
        return self._is_auto_stop_detected

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the aiuto-start/stop feature is configured"""
        return self._is_configured

    @property
    def auto_start_stop_level(self) -> str:
        """Return the auto start/stop level."""
        return self._auto_start_stop_level

    @property
    def auto_start_stop_enable(self) -> bool:
        """Returns the auto_start_stop_enable"""
        return self._is_auto_start_stop_enabled

    @property
    def is_auto_stopped(self) -> bool:
        """Returns the is vtherm is stopped and reason is AUTO_START_STOP"""
        return self._vtherm.hvac_mode == VThermHvacMode_OFF and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

    def reset_switch_delay(self):
        """Reset the switch delay in the algorithm to allow immediate restart.
        Should be called when target temperature changes significantly.
        """
        if self._auto_start_stop_algo:
            self._auto_start_stop_algo.reset_switch_delay()

    def __str__(self):
        return f"AutoStartStopManager-{self.name}"
