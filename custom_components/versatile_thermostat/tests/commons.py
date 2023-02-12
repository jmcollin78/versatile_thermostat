""" Some common resources """
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfTemperature

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers.entity_component import EntityComponent

from ..climate import VersatileThermostat
from ..const import DOMAIN

from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
    ATTR_PRESET_MODE,
    HVACMode,
    HVACAction,
)

from .const import (
    MOCK_TH_OVER_SWITCH_USER_CONFIG,
    MOCK_TH_OVER_CLIMATE_USER_CONFIG,
    MOCK_TH_OVER_SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_CONFIG,
    MOCK_TH_OVER_SWITCH_TPI_CONFIG,
    MOCK_PRESETS_CONFIG,
    MOCK_WINDOW_CONFIG,
    MOCK_MOTION_CONFIG,
    MOCK_POWER_CONFIG,
    MOCK_PRESENCE_CONFIG,
    MOCK_ADVANCED_CONFIG,
    # MOCK_DEFAULT_FEATURE_CONFIG,
)

FULL_SWITCH_CONFIG = (
    MOCK_TH_OVER_SWITCH_USER_CONFIG
    | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    | MOCK_TH_OVER_SWITCH_TPI_CONFIG
    | MOCK_PRESETS_CONFIG
    | MOCK_WINDOW_CONFIG
    | MOCK_MOTION_CONFIG
    | MOCK_POWER_CONFIG
    | MOCK_PRESENCE_CONFIG
    | MOCK_ADVANCED_CONFIG
)

PARTIAL_CLIMATE_CONFIG = (
    MOCK_TH_OVER_CLIMATE_USER_CONFIG
    | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG
    | MOCK_PRESETS_CONFIG
    | MOCK_ADVANCED_CONFIG
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


async def create_thermostat(
    hass: HomeAssistant, entry: MockConfigEntry, entity_id: str
) -> VersatileThermostat:
    """Creates and return a TPI Thermostat"""
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        entity = find_my_entity(entity_id)

        return entity
