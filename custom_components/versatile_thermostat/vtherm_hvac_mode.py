""" A custom data class to manage specific HVAC modes for VTherm. """

from typing import Union

from homeassistant.components.climate.const import HVACMode

from .const import HVACMODE_SLEEP

VALID_HVAC_MODES = {mode.value for mode in HVACMode} | {HVACMODE_SLEEP}

class VThermHvacMode:
    """Data class to encapsulate a single HVAC mode value."""

    # Constants for all valid HVAC modes
    OFF = HVACMode.OFF
    HEAT = HVACMode.HEAT
    COOL = HVACMode.COOL
    AUTO = HVACMode.AUTO
    DRY = HVACMode.DRY
    FAN_ONLY = HVACMode.FAN_ONLY
    HEAT_COOL = HVACMode.HEAT_COOL
    SLEEP = HVACMODE_SLEEP

    def __init__(self, hvac_mode: Union[str, HVACMode]) -> None:
        self._hvac_mode: str = hvac_mode

    @property
    def hvac_mode(self) -> str:
        """Get the current HVAC mode."""
        return self._hvac_mode

    @hvac_mode.setter
    def hvac_mode(self, value: Union[str, HVACMode]) -> None:
        """Set the HVAC mode, validating against allowed values.

        Args:
            value: New HVAC mode (str or HVACMode).

        Raises:
            ValueError: If value is not a valid HVAC mode.
        """
        if isinstance(value, HVACMode):
            value = value.value
        if value not in VALID_HVAC_MODES:
            raise ValueError(
                f"Invalid hvac_mode '{value}'. Must be one of: {sorted(VALID_HVAC_MODES)}"
            )
        self._hvac_mode = value

    def __eq__(self, other: object) -> bool:
        """Compare two VThermHvacMode objects for equality based on their HVAC mode."""
        if not isinstance(other, VThermHvacMode):
            return NotImplemented
        return self._hvac_mode == other._hvac_mode
