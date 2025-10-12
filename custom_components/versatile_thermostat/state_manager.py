"""StateManager for Versatile Thermostat.

This class manages both the current and the requested state of a VTherm.
"""

from typing import Optional, TYPE_CHECKING
from .const import EventType, HVAC_OFF_REASON_SAFETY
from .vtherm_state import VthermState
from .vtherm_hvac_mode import VThermHvacMode
from .vtherm_preset import VThermPreset

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
        self._current_state = VthermState(hvac_mode=VThermHvacMode.OFF, preset=VThermPreset.NONE)
        self._requested_state = VthermState(hvac_mode=VThermHvacMode.OFF, preset=VThermPreset.NONE)

    @property
    def current_state(self) -> Optional[VthermState]:
        """Get or set the current state."""
        return self._current_state

    @property
    def requested_state(self) -> Optional[VthermState]:
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

        # vtherm_api = VersatileThermostatAPI.get_vtherm_api()

        # check overpowering first
        if vtherm.power_manager.is_overpowering_detected:
            await vtherm.async_underlying_entity_turn_off()
            self._current_state.set_preset(VThermPreset.POWER)

        # then check safety
        elif vtherm.safety_manager.is_safety_detected:
            await self._current_state.set_preset(VThermPreset.SAFETY)
            if vtherm.is_over_climate or vtherm.safety_default_on_percent <= 0.0:
                self._current_state.set_hvac_mode(VThermHvacMode.OFF)
                vtherm.set_hvac_off_reason(HVAC_OFF_REASON_SAFETY)

        # all is fine set current_state = requested_state
        else:
            self._current_state.set_hvac_mode(self._requested_state.hvac_mode)
            self._current_state.set_preset(self._requested_state.preset)

        # Send events if preset or hvac_mode have changed
        if self._current_state.is_preset_changed:
            vtherm.send_event(EventType.PRESET_EVENT, {"preset": vtherm.preset_mode})
        if self._current_state.is_hvac_mode_changed:
            vtherm.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": vtherm.hvac_mode})

        # calculate the temperature of the preset
        if self._current_state.preset != VThermPreset.NONE:
            self._requested_state.set_target_temperature(vtherm.find_preset_temp(self._requested_state.preset))
            self._current_state.set_target_temperature(vtherm.find_preset_temp(self._current_state.preset))

        if self._current_state.is_target_temperature_changed:
            await vtherm.change_target_temperature(self._current_state.target_temperature)

        is_changed = self._current_state.is_changed
        self._current_state.reset_changed()
        return is_changed
