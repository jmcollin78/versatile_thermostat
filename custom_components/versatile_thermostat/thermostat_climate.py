""" A climate over switch classe """
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from homeassistant.components.climate import HVACAction

from .base_thermostat import BaseThermostat

from .const import CONF_CLIMATE, CONF_CLIMATE_2, CONF_CLIMATE_3, CONF_CLIMATE_4

from .underlyings import UnderlyingClimate

_LOGGER = logging.getLogger(__name__)

class ThermostatOverClimate(BaseThermostat):
    """Representation of a base class for a Versatile Thermostat over a climate"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat over switch."""
        super().__init__(hass, unique_id, name, entry_infos)

    @property
    def is_over_climate(self) -> bool:
        """ True if the Thermostat is over_climate"""
        return True

    @property
    def hvac_action(self) -> HVACAction | None:
        """ Returns the current hvac_action by checking all hvac_action of the underlyings """

        # if one not IDLE or OFF -> return it
        # else if one IDLE -> IDLE
        # else OFF
        one_idle = False
        for under in self._underlyings:
            if (action := under.hvac_action) not in [
                HVACAction.IDLE,
                HVACAction.OFF,
            ]:
                return action
            if under.hvac_action == HVACAction.IDLE:
                one_idle = True
        if one_idle:
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).hvac_modes
        else:
            return super.hvac_modes

    def post_init(self, entry_infos):
        """ Initialize the Thermostat"""

        super().post_init(entry_infos)
        for climate in [
            CONF_CLIMATE,
            CONF_CLIMATE_2,
            CONF_CLIMATE_3,
            CONF_CLIMATE_4,
        ]:
            if entry_infos.get(climate):
                self._underlyings.append(
                    UnderlyingClimate(
                        hass=self._hass,
                        thermostat=self,
                        climate_entity_id=entry_infos.get(climate),
                    )
                )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener to all underlying entities
        for climate in self._underlyings:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [climate.entity_id], self._async_climate_changed
                )
            )

        # Start the control_heating
        # starts a cycle
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self.async_control_heating,
                interval=timedelta(minutes=self._cycle_min),
            )
        )
