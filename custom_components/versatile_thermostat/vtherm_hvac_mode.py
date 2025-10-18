""" A custom data class to manage specific HVAC modes for VTherm. """

from homeassistant.components.climate.const import HVACMode

HVACMODE_SLEEP = "sleep"

class VThermHvacMode:
    """
    Container and validator for supported HVAC operating modes.
    """

    OFF = HVACMode.OFF
    HEAT = HVACMode.HEAT
    COOL = HVACMode.COOL
    AUTO = HVACMode.AUTO
    DRY = HVACMode.DRY
    FAN_ONLY = HVACMode.FAN_ONLY
    HEAT_COOL = HVACMode.HEAT_COOL
    SLEEP = HVACMODE_SLEEP

    VALID_HVAC_MODES = {OFF, HEAT, COOL, AUTO, DRY, FAN_ONLY, HEAT_COOL, SLEEP}

    def __init__(self, hvac_mode: str):
        """
        Initialize a VThermHvacMode instance.

        Args:
            hvac_mode (str): The HVAC mode to set.

        Raises:
            ValueError: If the mode is not supported.
        """
        if hvac_mode not in self.VALID_HVAC_MODES:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        self._hvac_mode = hvac_mode

    @property
    def hvac_mode(self) -> str:
        """
        Get the current HVAC mode.

        Returns:
            str: The current HVAC mode.
        """
        return self._hvac_mode

    def __str__(self):
        return self._hvac_mode

    @staticmethod
    def from_ha_hvac_mode(ha_hvac_mode: HVACMode | str):
        """
        Convert a Home Assistant HVACMode (enum or str) to a VThermHvacMode instance.

        Args:
            ha_hvac_mode (HVACMode | str): The Home Assistant HVAC mode.

        Returns:
            VThermHvacMode: The corresponding VThermHvacMode instance.
        """
        if hasattr(ha_hvac_mode, "value"):
            mode_str = ha_hvac_mode.value
        else:
            mode_str = str(ha_hvac_mode)
        return VThermHvacMode(mode_str)
