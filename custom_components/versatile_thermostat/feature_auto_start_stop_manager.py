""" Implements the Auto-start/stop Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any

from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.components.climate import HVACMode

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager

from .auto_start_stop_algorithm import (
    AutoStartStopDetectionAlgorithm,
    AUTO_START_STOP_ACTION_OFF,
    AUTO_START_STOP_ACTION_ON,
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

        self._auto_start_stop_level: TYPE_AUTO_START_STOP_LEVELS = (
            AUTO_START_STOP_LEVEL_NONE
        )
        self._auto_start_stop_algo: AutoStartStopDetectionAlgorithm | None = None
        self._is_configured: bool = False
        self._is_auto_start_stop_enabled: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

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
        Return False if we should stop the control_heating method"""

        if not self._is_configured or not self._is_auto_start_stop_enabled:
            _LOGGER.debug("%s - auto start/stop is disabled (or not configured)", self)
            return True

        slope = (
            self._vtherm.last_temperature_slope or 0
        ) / 60  # to have the slope in °/min
        action = self._auto_start_stop_algo.calculate_action(
            self._vtherm.hvac_mode,
            self._vtherm.saved_hvac_mode,
            self._vtherm.target_temperature,
            self._vtherm.current_temperature,
            slope,
            self._vtherm.now,
        )
        _LOGGER.debug("%s - auto_start_stop action is %s", self, action)
        if action == AUTO_START_STOP_ACTION_OFF and self._vtherm.is_on:
            _LOGGER.info(
                "%s - Turning OFF the Vtherm due to auto-start-stop conditions",
                self,
            )
            self._vtherm.set_hvac_off_reason(HVAC_OFF_REASON_AUTO_START_STOP)
            await self._vtherm.async_turn_off()

            # Send an event
            self._vtherm.send_event(
                event_type=EventType.AUTO_START_STOP_EVENT,
                data={
                    "type": "stop",
                    "name": self.name,
                    "cause": "Auto stop conditions reached",
                    "hvac_mode": self._vtherm.hvac_mode,
                    "saved_hvac_mode": self._vtherm.saved_hvac_mode,
                    "target_temperature": self._vtherm.target_temperature,
                    "current_temperature": self._vtherm.current_temperature,
                    "temperature_slope": round(slope, 3),
                    "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                    "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                },
            )

            # Stop here
            return False
        elif (
            action == AUTO_START_STOP_ACTION_ON
            and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        ):
            _LOGGER.info(
                "%s - Turning ON the Vtherm due to auto-start-stop conditions", self
            )
            await self._vtherm.async_turn_on()

            # Send an event
            self._vtherm.send_event(
                event_type=EventType.AUTO_START_STOP_EVENT,
                data={
                    "type": "start",
                    "name": self.name,
                    "cause": "Auto start conditions reached",
                    "hvac_mode": self._vtherm.hvac_mode,
                    "saved_hvac_mode": self._vtherm.saved_hvac_mode,
                    "target_temperature": self._vtherm.target_temperature,
                    "current_temperature": self._vtherm.current_temperature,
                    "temperature_slope": round(slope, 3),
                    "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                    "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                },
            )

            self._vtherm.update_custom_attributes()

        return True

    def set_auto_start_stop_enable(self, is_enabled: bool):
        """Enable/Disable the auto-start/stop feature"""
        self._is_auto_start_stop_enabled = is_enabled
        if (
            self._vtherm.hvac_mode == HVACMode.OFF
            and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        ):
            _LOGGER.debug(
                "%s - the vtherm is off cause auto-start/stop and enable have been set to false -> starts the VTherm"
            )
            self.hass.create_task(self._vtherm.async_turn_on())

            # Send an event
            self._vtherm.send_event(
                event_type=EventType.AUTO_START_STOP_EVENT,
                data={
                    "type": "start",
                    "name": self.name,
                    "cause": "Auto start stop disabled",
                    "hvac_mode": self._vtherm.hvac_mode,
                    "saved_hvac_mode": self._vtherm.saved_hvac_mode,
                    "target_temperature": self._vtherm.target_temperature,
                    "current_temperature": self._vtherm.current_temperature,
                    "temperature_slope": round(
                        self._vtherm.last_temperature_slope or 0, 3
                    ),
                    "accumulated_error": self._auto_start_stop_algo.accumulated_error,
                    "accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                },
            )

        self._vtherm.update_custom_attributes()

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
                    "auto_start_stop_enable": self.auto_start_stop_enable,
                    "auto_start_stop_level": self._auto_start_stop_algo.level,
                    "auto_start_stop_dtmin": self._auto_start_stop_algo.dt_min,
                    "auto_start_stop_accumulated_error": self._auto_start_stop_algo.accumulated_error,
                    "auto_start_stop_accumulated_error_threshold": self._auto_start_stop_algo.accumulated_error_threshold,
                    "auto_start_stop_last_switch_date": self._auto_start_stop_algo.last_switch_date,
                }
            )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the aiuto-start/stop feature is configured"""
        return self._is_configured

    @property
    def auto_start_stop_level(self) -> TYPE_AUTO_START_STOP_LEVELS:
        """Return the auto start/stop level."""
        return self._auto_start_stop_level

    @property
    def auto_start_stop_enable(self) -> bool:
        """Returns the auto_start_stop_enable"""
        return self._is_auto_start_stop_enabled

    @property
    def is_auto_stopped(self) -> bool:
        """Returns the is vtherm is stopped and reason is AUTO_START_STOP"""
        return (
            self._vtherm.hvac_mode == HVACMode.OFF
            and self._vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        )

    def __str__(self):
        return f"AutoStartStopManager-{self.name}"
