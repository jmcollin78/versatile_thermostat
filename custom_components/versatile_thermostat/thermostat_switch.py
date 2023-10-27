""" A climate over switch classe """
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_HEATER,
    CONF_HEATER_2,
    CONF_HEATER_3,
    CONF_HEATER_4
)

from .base_thermostat import BaseThermostat

from .underlyings import UnderlyingSwitch

_LOGGER = logging.getLogger(__name__)

class ThermostatOverSwitch(BaseThermostat):
    """Representation of a base class for a Versatile Thermostat over a switch."""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat over switch."""
        super().__init__(hass, unique_id, name, entry_infos)

    @property
    def is_over_switch(self) -> bool:
        """ True if the Thermostat is over_switch"""
        return True

    def post_init(self, entry_infos):
        """ Initialize the Thermostat"""

        super().post_init(entry_infos)
        lst_switches = [entry_infos.get(CONF_HEATER)]
        if entry_infos.get(CONF_HEATER_2):
            lst_switches.append(entry_infos.get(CONF_HEATER_2))
        if entry_infos.get(CONF_HEATER_3):
            lst_switches.append(entry_infos.get(CONF_HEATER_3))
        if entry_infos.get(CONF_HEATER_4):
            lst_switches.append(entry_infos.get(CONF_HEATER_4))

        delta_cycle = self._cycle_min * 60 / len(lst_switches)
        for idx, switch in enumerate(lst_switches):
            self._underlyings.append(
                UnderlyingSwitch(
                    hass=self._hass,
                    thermostat=self,
                    switch_entity_id=switch,
                    initial_delay_sec=idx * delta_cycle,
                )
            )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener to all underlying entities
        for switch in self._underlyings:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [switch.entity_id], self._async_switch_changed
                )
        )

        self.hass.create_task(self.async_control_heating())
