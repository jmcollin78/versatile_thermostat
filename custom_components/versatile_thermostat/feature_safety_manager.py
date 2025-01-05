# pylint: disable=line-too-long

""" Implements the Safety as a Feature Manager"""

import logging
from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode, HVACAction

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData

from .base_manager import BaseFeatureManager
from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class FeatureSafetyManager(BaseFeatureManager):
    """The implementation of the Safety feature"""

    unrecorded_attributes = frozenset(
        {
            "safety_delay_min",
            "safety_min_on_percent",
            "safety_default_on_percent",
            "is_safety_configured",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)

        self._is_configured: bool = False
        self._safety_delay_min = None
        self._safety_min_on_percent = None
        self._safety_default_on_percent = None
        self._safety_state = STATE_UNAVAILABLE

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._safety_delay_min = entry_infos.get(CONF_SAFETY_DELAY_MIN)
        self._safety_min_on_percent = (
            entry_infos.get(CONF_SAFETY_MIN_ON_PERCENT)
            if entry_infos.get(CONF_SAFETY_MIN_ON_PERCENT) is not None
            else DEFAULT_SAFETY_MIN_ON_PERCENT
        )
        self._safety_default_on_percent = (
            entry_infos.get(CONF_SAFETY_DEFAULT_ON_PERCENT)
            if entry_infos.get(CONF_SAFETY_DEFAULT_ON_PERCENT) is not None
            else DEFAULT_SAFETY_DEFAULT_ON_PERCENT
        )

        if (
            self._safety_delay_min is not None
            and self._safety_default_on_percent is not None
            and self._safety_default_on_percent is not None
        ):
            self._safety_state = STATE_UNKNOWN
            self._is_configured = True

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""

    @overrides
    async def refresh_state(self) -> bool:
        """Check the safety and an eventual action
        Return True is safety should be active"""

        if not self._is_configured:
            _LOGGER.debug("%s - safety is disabled (or not configured)", self)
            return False

        now = self._vtherm.now
        current_tz = dt_util.get_time_zone(self._hass.config.time_zone)

        is_safety_detected = self.is_safety_detected

        delta_temp = (
            now - self._vtherm.last_temperature_measure.replace(tzinfo=current_tz)
        ).total_seconds() / 60.0
        delta_ext_temp = (
            now - self._vtherm.last_ext_temperature_measure.replace(tzinfo=current_tz)
        ).total_seconds() / 60.0

        mode_cond = self._vtherm.hvac_mode != HVACMode.OFF

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()
        is_outdoor_checked = (
            not api.safety_mode
            or api.safety_mode.get("check_outdoor_sensor") is not False
        )

        temp_cond: bool = delta_temp > self._safety_delay_min or (
            is_outdoor_checked and delta_ext_temp > self._safety_delay_min
        )
        climate_cond: bool = (
            self._vtherm.is_over_climate
            and self._vtherm.hvac_action
            not in [
                HVACAction.COOLING,
                HVACAction.IDLE,
            ]
        )
        switch_cond: bool = (
            not self._vtherm.is_over_climate
            and self._vtherm.proportional_algorithm is not None
            and self._vtherm.proportional_algorithm.calculated_on_percent
            >= self._safety_min_on_percent
        )

        _LOGGER.debug(
            "%s - checking safety delta_temp=%.1f delta_ext_temp=%.1f mod_cond=%s temp_cond=%s climate_cond=%s switch_cond=%s",
            self,
            delta_temp,
            delta_ext_temp,
            mode_cond,
            temp_cond,
            climate_cond,
            switch_cond,
        )

        # Issue 99 - a climate is regulated by the device itself and not by VTherm. So a VTherm should never be in safety !
        should_climate_be_in_security = False  # temp_cond and climate_cond
        should_switch_be_in_security = temp_cond and switch_cond
        should_be_in_security = (
            should_climate_be_in_security or should_switch_be_in_security
        )

        should_start_security = (
            mode_cond and not is_safety_detected and should_be_in_security
        )
        # attr_preset_mode is not necessary normaly. It is just here to be sure
        should_stop_security = (
            is_safety_detected
            and not should_be_in_security
            and self._vtherm.preset_mode == PRESET_SAFETY
        )

        # Logging and event
        if should_start_security:
            if should_climate_be_in_security:
                _LOGGER.warning(
                    "%s - No temperature received for more than %.1f minutes (dt=%.1f, dext=%.1f) and underlying climate is %s. Setting it into safety mode",
                    self,
                    self._safety_delay_min,
                    delta_temp,
                    delta_ext_temp,
                    self.hvac_action,
                )
            elif should_switch_be_in_security:
                _LOGGER.warning(
                    "%s - No temperature received for more than %.1f minutes (dt=%.1f, dext=%.1f) and on_percent (%.2f %%) is over defined value (%.2f %%). Set it into safety mode",
                    self,
                    self._safety_delay_min,
                    delta_temp,
                    delta_ext_temp,
                    self._vtherm.proportional_algorithm.on_percent * 100,
                    self._safety_min_on_percent * 100,
                )

            self._vtherm.send_event(
                EventType.TEMPERATURE_EVENT,
                {
                    "last_temperature_measure": self._vtherm.last_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._vtherm.last_ext_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "current_temp": self._vtherm.current_temperature,
                    "current_ext_temp": self._vtherm.current_outdoor_temperature,
                    "target_temp": self._vtherm.target_temperature,
                },
            )

        # Start safety mode
        if should_start_security:
            self._safety_state = STATE_ON
            self._vtherm.save_hvac_mode()
            self._vtherm.save_preset_mode()
            if self._vtherm.proportional_algorithm:
                self._vtherm.proportional_algorithm.set_safety(
                    self._safety_default_on_percent
                )
            await self._vtherm.async_set_preset_mode_internal(PRESET_SAFETY)
            # Turn off the underlying climate or heater if safety default on_percent is 0
            if self._vtherm.is_over_climate or self._safety_default_on_percent <= 0.0:
                await self._vtherm.async_set_hvac_mode(HVACMode.OFF, False)

            self._vtherm.send_event(
                EventType.SECURITY_EVENT,
                {
                    "type": "start",
                    "last_temperature_measure": self._vtherm.last_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._vtherm.last_ext_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "current_temp": self._vtherm.current_temperature,
                    "current_ext_temp": self._vtherm.current_outdoor_temperature,
                    "target_temp": self._vtherm.target_temperature,
                },
            )

        # Stop safety mode
        elif should_stop_security:
            _LOGGER.warning(
                "%s - End of safety mode. restoring hvac_mode to %s and preset_mode to %s",
                self,
                self._vtherm.saved_hvac_mode,
                self._vtherm.saved_preset_mode,
            )
            self._safety_state = STATE_OFF
            if self._vtherm.proportional_algorithm:
                self._vtherm.proportional_algorithm.unset_safety()
            # Restore hvac_mode if previously saved
            if self._vtherm.is_over_climate or self._safety_default_on_percent <= 0.0:
                await self._vtherm.restore_hvac_mode(False)
            await self._vtherm.restore_preset_mode()
            self._vtherm.send_event(
                EventType.SECURITY_EVENT,
                {
                    "type": "end",
                    "last_temperature_measure": self._vtherm.last_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "last_ext_temperature_measure": self._vtherm.last_ext_temperature_measure.replace(
                        tzinfo=current_tz
                    ).isoformat(),
                    "current_temp": self._vtherm.current_temperature,
                    "current_ext_temp": self._vtherm.current_outdoor_temperature,
                    "target_temp": self._vtherm.target_temperature,
                },
            )

        # Initialize the safety_state if not already done
        elif not should_be_in_security and self._safety_state in [STATE_UNKNOWN]:
            self._safety_state = STATE_OFF

        return should_be_in_security

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""

        extra_state_attributes.update(
            {
                "is_safety_configured": self._is_configured,
                "safety_state": self._safety_state,
            }
        )

        if self._is_configured:
            extra_state_attributes.update(
                {
                    "safety_delay_min": self._safety_delay_min,
                    "safety_min_on_percent": self._safety_min_on_percent,
                    "safety_default_on_percent": self._safety_default_on_percent,
                }
            )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the safety feature is configured"""
        return self._is_configured

    def set_safety_delay_min(self, safety_delay_min):
        """Set the delay min"""
        self._safety_delay_min = safety_delay_min

    def set_safety_min_on_percent(self, safety_min_on_percent):
        """Set the min on percent"""
        self._safety_min_on_percent = safety_min_on_percent

    def set_safety_default_on_percent(self, safety_default_on_percent):
        """Set the default on_percent"""
        self._safety_default_on_percent = safety_default_on_percent

    @property
    def is_safety_detected(self) -> bool:
        """Returns the is vtherm is in safety mode"""
        return self._safety_state == STATE_ON

    @property
    def safety_state(self) -> str:
        """Returns the safety state: STATE_ON, STATE_OFF, STATE_UNKWNON, STATE_UNAVAILABLE"""
        return self._safety_state

    @property
    def safety_delay_min(self) -> bool:
        """Returns the safety delay min"""
        return self._safety_delay_min

    @property
    def safety_min_on_percent(self) -> bool:
        """Returns the safety min on percent"""
        return self._safety_min_on_percent

    @property
    def safety_default_on_percent(self) -> bool:
        """Returns the safety safety_default_on_percent"""
        return self._safety_default_on_percent

    def __str__(self):
        return f"SafetyManager-{self.name}"
