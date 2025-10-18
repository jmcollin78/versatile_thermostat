"""StateManager for Versatile Thermostat.

This class manages both the current and the requested state of a VTherm.
"""

import logging
from typing import Optional, TYPE_CHECKING
from .const import (
    HVAC_OFF_REASON_SAFETY,
    HVAC_OFF_REASON_MANUAL,
    HVAC_OFF_REASON_WINDOW_DETECTION,
    HVAC_OFF_REASON_AUTO_START_STOP,
    HVAC_OFF_REASON_SLEEP_MODE,
    CONF_WINDOW_ECO_TEMP,
    CONF_WINDOW_FAN_ONLY,
    CONF_WINDOW_FROST_TEMP,
    CONF_WINDOW_TURN_OFF,
)
from .vtherm_state import VThermState
from .vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_FAN_ONLY
from .vtherm_preset import VThermPreset

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .base_thermostat import BaseThermostat

class StateManager:
    """Manages the current and requested state for a VTherm.

    Attributes:
        current_state: The actual state of the thermostat.
        requested_state: The desired/requested state to be applied.
    """

    def __init__(self):
        """Initialize the StateManager with empty initial states.
        """
        self._current_state = VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE)
        self._requested_state = VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE)

    @property
    def current_state(self) -> Optional[VThermState]:
        """Get or set the current state."""
        return self._current_state

    @property
    def requested_state(self) -> Optional[VThermState]:
        """Get or set the requested state."""
        return self._requested_state

    async def calculate_current_state(self, vtherm: "BaseThermostat") -> bool:
        """Calculate and update the current state from the given base_thermostat.

        Args:
            vtherm: The thermostat object to use for calculation.

        Returns:
            bool: True or False according to rules to be defined later.
        """
        if not vtherm:
            return False

        change_hvac_mode = await self.calculate_current_hvac_mode(vtherm)
        change_preset = await self.calculate_current_preset(vtherm)
        change_target_temp = await self.calculate_current_target_temperature(vtherm)

        return change_hvac_mode or change_preset or change_target_temp

    async def calculate_current_hvac_mode(self, vtherm: "BaseThermostat") -> bool:
        """Calculate and update the current HVAC mode from the given base_thermostat.

        - check if safety manager is detected has an impact on hvac_mode
        - if not check if window manager has an impact on hvac_mode
        - if not check if auto start/stop manager has an impact on hvac_mode
        - else set hvac_mode to requested_state.hvac_mode

        then publish an event if hvac_mode has changed

        Args:
            vtherm: The thermostat object to use for calculation.

        Returns:
            bool: True or False according to preceeding rules

        """
        if not vtherm:
            return False

        # Implement HVAC mode calculation logic here
        # overpowering never change the hvac_mode
        # if vtherm.power_manager.is_overpowering_detected:

        # First check safety
        if vtherm.safety_manager.is_safety_detected and (vtherm.is_over_climate or vtherm.safety_default_on_percent <= 0.0):
            self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_SAFETY)

        # then check if window is open
        elif vtherm.window_manager.is_window_detected:
            if vtherm.window_manager.window_action == CONF_WINDOW_FAN_ONLY and VThermHvacMode_FAN_ONLY in vtherm.hvac_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_FAN_ONLY)
            elif vtherm.window_manager.window_action == CONF_WINDOW_TURN_OFF or (
                vtherm.window_manager.window_action == CONF_WINDOW_FAN_ONLY and VThermHvacMode_FAN_ONLY not in vtherm.hvac_modes
            ):  # default is to turn_off
                self._current_state.set_hvac_mode(VThermHvacMode_OFF)
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_WINDOW_DETECTION)

        elif vtherm.auto_start_stop_manager and vtherm.auto_start_stop_manager.is_auto_stop_detected:
            self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_AUTO_START_STOP)

        # all is fine set current_state = requested_state
        else:
            if self._current_state.hvac_mode == VThermHvacMode_OFF and self._requested_state.hvac_mode == VThermHvacMode_OFF:
                _LOGGER.info("%s - already in OFF. Change the reason to MANUAL and erase the saved_hvac_mode", vtherm)
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL if not vtherm.is_sleeping else HVAC_OFF_REASON_SLEEP_MODE)

            self._current_state.set_hvac_mode(self._requested_state.hvac_mode)

        if self._current_state.hvac_mode != VThermHvacMode_OFF:
            vtherm.set_hvac_off_reason(None)

        return self._current_state.is_hvac_mode_changed

    async def calculate_current_preset(self, vtherm: "BaseThermostat") -> bool:
        """Calculate and update the current preset state from the given base_thermostat.

        - check if power manager is detected has an impact on preset
        - if not check if safety manager has an impact on preset
        - else set preset to requested_state.preset

        Send an event if preset has changed

        Args:
            vtherm: The thermostat object to use for calculation.

        Returns:
            bool: True or False according to rules to be preceeding rules
        """

        # check overpowering first
        if vtherm.power_manager.is_overpowering_detected:
            # turn off underlying and take the hvac_mode
            self._current_state.set_preset(VThermPreset.POWER)

        # then check safety
        elif vtherm.safety_manager.is_safety_detected:
            self._current_state.set_preset(VThermPreset.SAFETY)

        # all is fine set current_state = requested_state
        else:
            self._current_state.set_preset(self._requested_state.preset)

        return self._current_state.is_preset_changed

    async def calculate_current_target_temperature(self, vtherm: "BaseThermostat") -> bool:
        """Calculate and update the current target temperature from the given base_thermostat.

        - check if window manager is detected has an impact on target temperature
        - if not check if presence manager has an impact on target temperature
        - if not check if motion manager has an impact on target temperature
        - else set target temperature to requested_state.target_temperature

        Send an event if target temperature has changed

        Args:
            vtherm: The thermostat object to use for calculation.

        Returns:
            bool: True or False according to rules to be preceeding rules
        """

        window_action = vtherm.window_manager.window_action

        if vtherm.window_manager.is_window_detected:
            if (window_action == CONF_WINDOW_FROST_TEMP and vtherm.is_preset_configured(VThermPreset.FROST)) or (
                window_action == CONF_WINDOW_ECO_TEMP and vtherm.is_preset_configured(VThermPreset.ECO)
            ):
                self._current_state.set_target_temperature(vtherm.find_preset_temp(VThermPreset.ECO if window_action == CONF_WINDOW_ECO_TEMP else VThermPreset.FROST))
            # else don't touche the temperature (window is open with TURN_OFF should keep the current temperature)

        elif vtherm.presence_manager.is_absence_detected:
            new_temp = vtherm.find_preset_temp(vtherm.vtherm_preset_mode)
            _LOGGER.debug(
                "%s - presence will set new target temperature: %.2f",
                self,
                new_temp,
            )
            self._current_state.set_target_temperature(new_temp)

        elif vtherm.motion_manager.is_motion_detected:
            new_preset = vtherm.motion_manager.get_current_motion_preset()
            _LOGGER.debug(
                "%s - motion will set new target temperature: %.2f",
                self,
                new_preset,
            )
            self._current_state.set_target_temperature(vtherm.find_preset_temp(new_preset))
        else:
            # calculate the temperature of the preset
            if self._current_state.preset != VThermPreset.NONE:
                self._current_state.set_target_temperature(vtherm.find_preset_temp(self._current_state.preset))
            elif self._requested_state.target_temperature is not None:
                self._current_state.set_target_temperature(self._requested_state.target_temperature)
            else:
                # affect the min or max temp according to is_ac
                if vtherm.ac_mode:
                    self._current_state.set_target_temperature(vtherm.max_temp)
                else:
                    self._current_state.set_target_temperature(vtherm.min_temp)
            if self._requested_state.preset != VThermPreset.NONE:
                self._requested_state.set_target_temperature(vtherm.find_preset_temp(self._requested_state.preset))

        return self._current_state.is_target_temperature_changed
