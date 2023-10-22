""" A climate over switch classe """

from homeassistant.core import HomeAssistant


from .base_thermostat import BaseThermostat

class ThermostatOverSwitch(BaseThermostat):
    """Representation of a base class for a Versatile Thermostat over a switch."""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat over switch."""
        super().__init__(hass, unique_id, name, entry_infos)

    @property
    def is_over_switch(self):
        """ True if the Thermostat is over_switch"""
        return True
