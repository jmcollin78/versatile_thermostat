""" Some common resources """

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import ClimateEntity
from homeassistant.const import UnitOfTemperature

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    ATTR_PRESET_MODE,
    HVACMode,
    HVACAction,
)


class MockClimate(ClimateEntity):
    """A Mock Climate class used for Underlying climate mode"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat."""

        super().__init__()

        self._hass = hass
        self._attr_extra_state_attributes = {}
        self._unique_id = unique_id
        self._name = name
        self._attr_hvac_action = HVACAction.OFF
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
