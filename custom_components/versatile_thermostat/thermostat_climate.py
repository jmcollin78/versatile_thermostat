# pylint: disable=line-too-long
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

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(frozenset(
        {
            "is_over_climate", "start_hvac_action_date", "underlying_climate_0", "underlying_climate_1",
            "underlying_climate_2", "underlying_climate_3"
        }))

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

    def update_custom_attributes(self):
        """ Custom attributes """
        super().update_custom_attributes()

        self._attr_extra_state_attributes["is_over_climate"] = self.is_over_climate
        self._attr_extra_state_attributes["start_hvac_action_date"] = (
            self._underlying_climate_start_hvac_action_date)
        self._attr_extra_state_attributes["underlying_climate_0"] = (
                self._underlyings[0].entity_id)
        self._attr_extra_state_attributes["underlying_climate_1"] = (
                self._underlyings[1].entity_id if len(self._underlyings) > 1 else None
            )
        self._attr_extra_state_attributes["underlying_climate_2"] = (
                self._underlyings[2].entity_id if len(self._underlyings) > 2 else None
            )
        self._attr_extra_state_attributes["underlying_climate_3"] = (
                self._underlyings[3].entity_id if len(self._underlyings) > 3 else None
            )

        self.async_write_ha_state()
        _LOGGER.debug(
            "%s - Calling update_custom_attributes: %s",
            self,
            self._attr_extra_state_attributes,
        )

    def recalculate(self):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate all", self)
        self.update_custom_attributes()
        self.async_write_ha_state()
