"""StateManager for Versatile Thermostat.

This class manages both the current and the requested state of a VTherm.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any
from .const import (
    HVAC_OFF_REASON_SAFETY,
    HVAC_OFF_REASON_MANUAL,
    HVAC_OFF_REASON_WINDOW_DETECTION,
    HVAC_OFF_REASON_AUTO_START_STOP,
    HVAC_OFF_REASON_SLEEP_MODE,
    HVAC_OFF_REASON_CENTRAL_MODE,
    CONF_WINDOW_ECO_TEMP,
    CONF_WINDOW_FAN_ONLY,
    CONF_WINDOW_FROST_TEMP,
    CONF_WINDOW_TURN_OFF,
    CENTRAL_MODE_STOPPED,
    CENTRAL_MODE_COOL_ONLY,
    CENTRAL_MODE_HEAT_ONLY,
    CENTRAL_MODE_FROST_PROTECTION,
    ATTR_CURRENT_STATE,
    ATTR_REQUESTED_STATE,
    MSG_TARGET_TEMP_POWER,
    MSG_TARGET_TEMP_WINDOW_ECO,
    MSG_TARGET_TEMP_WINDOW_FROST,
    MSG_TARGET_TEMP_CENTRAL_MODE,
    MSG_TARGET_TEMP_ACTIVITY_DETECTED,
    MSG_TARGET_TEMP_ACTIVITY_NOT_DETECTED,
    MSG_TARGET_TEMP_ABSENCE_DETECTED,
)
from .vtherm_state import VThermState
from .vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_FAN_ONLY, VThermHvacMode_COOL, VThermHvacMode_HEAT, VThermHvacMode_SLEEP
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

        vtherm.set_temperature_reason(None)
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
        if vtherm.last_central_mode == CENTRAL_MODE_STOPPED:
            self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_CENTRAL_MODE)

        elif vtherm.safety_manager.is_safety_detected and (vtherm.is_over_climate or vtherm.safety_manager.safety_default_on_percent <= 0.0):
            self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_SAFETY)

        # then check if window is open
        elif vtherm.window_manager.is_window_detected and self._requested_state.hvac_mode != VThermHvacMode_OFF:
            if vtherm.window_manager.window_action == CONF_WINDOW_FAN_ONLY and VThermHvacMode_FAN_ONLY in vtherm.vtherm_hvac_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_FAN_ONLY)
            elif vtherm.window_manager.window_action == CONF_WINDOW_TURN_OFF or (
                vtherm.window_manager.window_action == CONF_WINDOW_FAN_ONLY and VThermHvacMode_FAN_ONLY not in vtherm.vtherm_hvac_modes
            ):  # default is to turn_off
                self._current_state.set_hvac_mode(VThermHvacMode_OFF)
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_WINDOW_DETECTION)

        elif vtherm.auto_start_stop_manager and vtherm.auto_start_stop_manager.is_auto_stop_detected and self._requested_state.hvac_mode != VThermHvacMode_OFF:
            self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_AUTO_START_STOP)

        elif vtherm.last_central_mode == CENTRAL_MODE_COOL_ONLY and self._requested_state.hvac_mode != VThermHvacMode_OFF:
            if VThermHvacMode_COOL in vtherm.vtherm_hvac_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_COOL)
            else:
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_CENTRAL_MODE)
                self._current_state.set_hvac_mode(VThermHvacMode_OFF)

        elif vtherm.last_central_mode == CENTRAL_MODE_HEAT_ONLY and self._requested_state.hvac_mode != VThermHvacMode_OFF:
            if VThermHvacMode_HEAT in vtherm.vtherm_hvac_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_HEAT)
            else:
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_CENTRAL_MODE)
                self._current_state.set_hvac_mode(VThermHvacMode_OFF)

        elif vtherm.last_central_mode == CENTRAL_MODE_FROST_PROTECTION and self._requested_state.hvac_mode != VThermHvacMode_OFF:
            if VThermPreset.FROST not in vtherm.vtherm_preset_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_OFF)
            elif vtherm.vtherm_hvac_mode != VThermHvacMode_HEAT and VThermHvacMode_HEAT in vtherm.vtherm_hvac_modes:
                self._current_state.set_hvac_mode(VThermHvacMode_HEAT)

        # all is fine set current_state = requested_state
        else:
            if self._current_state.hvac_mode == VThermHvacMode_OFF and self._requested_state.hvac_mode == VThermHvacMode_OFF:
                _LOGGER.info("%s - already in OFF. Change the reason to MANUAL", vtherm)
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_MANUAL if not vtherm.is_sleeping else HVAC_OFF_REASON_SLEEP_MODE)

            self._current_state.set_hvac_mode(self._requested_state.hvac_mode)

        # Calculate hvac_off_reason
        if self._current_state.hvac_mode != VThermHvacMode_OFF and vtherm.hvac_off_reason is not None:
            vtherm.set_hvac_off_reason(None)
        elif self._current_state.hvac_mode == VThermHvacMode_SLEEP:
            vtherm.set_hvac_off_reason(HVAC_OFF_REASON_SLEEP_MODE)

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
        if vtherm.power_manager.is_overpowering_detected and self._current_state.hvac_mode != VThermHvacMode_OFF:
            # turn off underlying and take the hvac_mode
            self._current_state.set_preset(VThermPreset.POWER)
            vtherm.set_temperature_reason(MSG_TARGET_TEMP_POWER)

        # then check safety
        elif vtherm.safety_manager.is_safety_detected and self._current_state.hvac_mode != VThermHvacMode_OFF:
            self._current_state.set_preset(VThermPreset.SAFETY)

        elif vtherm.last_central_mode == CENTRAL_MODE_FROST_PROTECTION:
            if VThermPreset.FROST in vtherm.vtherm_preset_modes and vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT:
                self._current_state.set_preset(VThermPreset.FROST)
                vtherm.set_temperature_reason(MSG_TARGET_TEMP_CENTRAL_MODE)

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

        updated = False
        window_action = vtherm.window_manager.window_action

        # note that window_manager.is_window_detected is False if bypass is on (so no need to test it here)
        if vtherm.window_manager.is_window_detected:
            if (window_action == CONF_WINDOW_FROST_TEMP and vtherm.is_preset_configured(VThermPreset.FROST)) or (
                window_action == CONF_WINDOW_ECO_TEMP and vtherm.is_preset_configured(VThermPreset.ECO)
            ):
                self._current_state.set_target_temperature(vtherm.find_preset_temp(VThermPreset.ECO if window_action == CONF_WINDOW_ECO_TEMP else VThermPreset.FROST))
                vtherm.set_temperature_reason(MSG_TARGET_TEMP_WINDOW_ECO if window_action == CONF_WINDOW_ECO_TEMP else MSG_TARGET_TEMP_WINDOW_FROST)
                updated = True

        elif vtherm.motion_manager.is_configured and self._current_state.preset == VThermPreset.ACTIVITY:
            new_preset = vtherm.motion_manager.get_current_motion_preset()
            _LOGGER.debug("%s - motion will set new target preset: %s", self, new_preset)
            self._current_state.set_target_temperature(vtherm.find_preset_temp(new_preset))
            vtherm.set_temperature_reason(MSG_TARGET_TEMP_ACTIVITY_DETECTED if vtherm.motion_manager.is_motion_detected else MSG_TARGET_TEMP_ACTIVITY_NOT_DETECTED)
            updated = True

        elif vtherm.presence_manager.is_absence_detected:
            if vtherm.vtherm_preset_mode != VThermPreset.NONE:
                new_temp = vtherm.find_preset_temp(vtherm.vtherm_preset_mode)
                _LOGGER.debug("%s - presence will set new target temperature: %.2f", self, new_temp)
                self._current_state.set_target_temperature(new_temp)
                vtherm.set_temperature_reason(MSG_TARGET_TEMP_ABSENCE_DETECTED)
                updated = True

        if not updated:
            # calculate the temperature of the preset
            self.update_current_temp_from_requested(vtherm)

        # update requested state temperature to set it in concordance with preset
        if self._requested_state.preset != VThermPreset.NONE:
            self._requested_state.set_target_temperature(vtherm.find_preset_temp(self._requested_state.preset))

        return self._current_state.is_target_temperature_changed

    def update_current_temp_from_requested(self, vtherm: "BaseThermostat"):
        """Update the current temperature from the requested state preset if any."""
        if self._current_state.preset == VThermPreset.SAFETY:
            self._current_state.set_target_temperature(vtherm.find_preset_temp(self._requested_state.preset))
        elif self._current_state.preset != VThermPreset.NONE:
            self._current_state.set_target_temperature(vtherm.find_preset_temp(self._current_state.preset))
        elif self._requested_state.target_temperature is not None:
            self._current_state.set_target_temperature(self._requested_state.target_temperature)
        else:
            # affect the min or max temp according to is_ac
            if vtherm.ac_mode:
                self._current_state.set_target_temperature(vtherm.max_temp)
            else:
                self._current_state.set_target_temperature(vtherm.min_temp)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                ATTR_CURRENT_STATE: self.current_state.to_dict(),
                ATTR_REQUESTED_STATE: self.requested_state.to_dict(),
            }
        )
