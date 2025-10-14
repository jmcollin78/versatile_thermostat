""" A custom data class to manage specific HVAC modes for VTherm. """

from enum import Enum

from homeassistant.components.climate.const import HVACMode

from .const import HVACMODE_SLEEP


class VThermHvacMode(Enum):
    """
    Enumeration of supported HVAC operating modes
    """

    OFF = HVACMode.OFF
    HEAT = HVACMode.HEAT
    COOL = HVACMode.COOL
    AUTO = HVACMode.AUTO
    DRY = HVACMode.DRY
    FAN_ONLY = HVACMode.FAN_ONLY
    HEAT_COOL = HVACMode.HEAT_COOL
    SLEEP = HVACMODE_SLEEP
