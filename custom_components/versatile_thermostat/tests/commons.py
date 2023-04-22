""" Some common resources """
import asyncio
import logging
from unittest.mock import patch, MagicMock
import pytest  # pylint: disable=unused-import

from homeassistant.core import HomeAssistant, Event, EVENT_STATE_CHANGED, State
from homeassistant.const import UnitOfTemperature, STATE_ON, STATE_OFF

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity import Entity
from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

from ..climate import VersatileThermostat
from ..const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from ..underlyings import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .const import (  # pylint: disable=unused-import
    MOCK_TH_OVER_SWITCH_USER_CONFIG,
    MOCK_TH_OVER_4SWITCH_USER_CONFIG,
    MOCK_TH_OVER_CLIMATE_USER_CONFIG,
    MOCK_TH_OVER_SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_4SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_CONFIG,
    MOCK_TH_OVER_SWITCH_TPI_CONFIG,
    MOCK_PRESETS_CONFIG,
    MOCK_WINDOW_CONFIG,
    MOCK_MOTION_CONFIG,
    MOCK_POWER_CONFIG,
    MOCK_PRESENCE_CONFIG,
    MOCK_ADVANCED_CONFIG,
    # MOCK_DEFAULT_FEATURE_CONFIG,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_NONE,
    PRESET_ECO,
    PRESET_ACTIVITY,
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

FULL_4SWITCH_CONFIG = (
    MOCK_TH_OVER_4SWITCH_USER_CONFIG
    | MOCK_TH_OVER_4SWITCH_TYPE_CONFIG
    | MOCK_TH_OVER_SWITCH_TPI_CONFIG
    | MOCK_PRESETS_CONFIG
    | MOCK_WINDOW_CONFIG
    | MOCK_MOTION_CONFIG
    | MOCK_POWER_CONFIG
    | MOCK_PRESENCE_CONFIG
    | MOCK_ADVANCED_CONFIG
)

_LOGGER = logging.getLogger(__name__)


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


class MagicMockClimate(MagicMock):
    """A Magic Mock class for a underlying climate entity"""

    @property
    def temperature_unit(self):  # pylint: disable=missing-function-docstring
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self):  # pylint: disable=missing-function-docstring
        return HVACMode.HEAT

    @property
    def hvac_action(self):  # pylint: disable=missing-function-docstring
        return HVACAction.IDLE

    @property
    def target_temperature(self):  # pylint: disable=missing-function-docstring
        return 15

    @property
    def current_temperature(self):  # pylint: disable=missing-function-docstring
        return 14

    @property
    def target_temperature_step(  # pylint: disable=missing-function-docstring
        self,
    ) -> float | None:
        return 0.5

    @property
    def target_temperature_high(  # pylint: disable=missing-function-docstring
        self,
    ) -> float | None:
        return 35

    @property
    def target_temperature_low(  # pylint: disable=missing-function-docstring
        self,
    ) -> float | None:
        return 7

    @property
    def hvac_modes(  # pylint: disable=missing-function-docstring
        self,
    ) -> list[str] | None:
        return [HVACMode.HEAT, HVACMode.OFF, HVACMode.COOL]

    @property
    def fan_modes(  # pylint: disable=missing-function-docstring
        self,
    ) -> list[str] | None:
        return None

    @property
    def swing_modes(  # pylint: disable=missing-function-docstring
        self,
    ) -> list[str] | None:
        return None

    @property
    def fan_mode(self) -> str | None:  # pylint: disable=missing-function-docstring
        return None

    @property
    def swing_mode(self) -> str | None:  # pylint: disable=missing-function-docstring
        return None

    @property
    def supported_features(self):  # pylint: disable=missing-function-docstring
        return ClimateEntityFeature.TARGET_TEMPERATURE


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

        # def find_my_entity(entity_id) -> ClimateEntity:
        #     """Find my new entity"""
        #     component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
        #     for entity in component.entities:
        #         if entity.entity_id == entity_id:
        #             return entity

        return search_entity(hass, entity_id, CLIMATE_DOMAIN)


def search_entity(hass: HomeAssistant, entity_id, domain) -> Entity:
    """Search and return the entity in the domain"""
    component = hass.data[domain]
    for entity in component.entities:
        if entity.entity_id == entity_id:
            return entity
    return None


async def send_temperature_change_event(
    entity: VersatileThermostat, new_temp, date, sleep=True
):
    """Sending a new temperature event simulating a change on temperature sensor"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_temp=%.2f date=%s on %s",
        new_temp,
        date,
        entity,
    )
    temp_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=new_temp,
                last_changed=date,
                last_updated=date,
            )
        },
    )
    await entity._async_temperature_changed(temp_event)
    if sleep:
        await asyncio.sleep(0.1)


async def send_ext_temperature_change_event(
    entity: VersatileThermostat, new_temp, date, sleep=True
):
    """Sending a new external temperature event simulating a change on temperature sensor"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_temp=%.2f date=%s on %s",
        new_temp,
        date,
        entity,
    )
    temp_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=new_temp,
                last_changed=date,
                last_updated=date,
            )
        },
    )
    await entity._async_ext_temperature_changed(temp_event)
    if sleep:
        await asyncio.sleep(0.1)


async def send_power_change_event(
    entity: VersatileThermostat, new_power, date, sleep=True
):
    """Sending a new power event simulating a change on power sensor"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_power=%.2f date=%s on %s",
        new_power,
        date,
        entity,
    )
    power_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=new_power,
                last_changed=date,
                last_updated=date,
            )
        },
    )
    await entity._async_power_changed(power_event)
    if sleep:
        await asyncio.sleep(0.1)


async def send_max_power_change_event(
    entity: VersatileThermostat, new_power_max, date, sleep=True
):
    """Sending a new power max event simulating a change on power max sensor"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_power_max=%.2f date=%s on %s",
        new_power_max,
        date,
        entity,
    )
    power_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=new_power_max,
                last_changed=date,
                last_updated=date,
            )
        },
    )
    await entity._async_max_power_changed(power_event)
    if sleep:
        await asyncio.sleep(0.1)


async def send_window_change_event(
    entity: VersatileThermostat, new_state: bool, old_state: bool, date, sleep=True
):
    """Sending a new window event simulating a change on the window state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_state=%s old_state=%s date=%s on %s",
        new_state,
        old_state,
        date,
        entity,
    )
    window_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if new_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if old_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
        },
    )
    ret = await entity._async_windows_changed(window_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


async def send_motion_change_event(
    entity: VersatileThermostat, new_state: bool, old_state: bool, date, sleep=True
):
    """Sending a new motion event simulating a change on the window state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_state=%s old_state=%s date=%s on %s",
        new_state,
        old_state,
        date,
        entity,
    )
    motion_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if new_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if old_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
        },
    )
    ret = await entity._async_motion_changed(motion_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


async def send_presence_change_event(
    entity: VersatileThermostat, new_state: bool, old_state: bool, date, sleep=True
):
    """Sending a new presence event simulating a change on the window state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_state=%s old_state=%s date=%s on %s",
        new_state,
        old_state,
        date,
        entity,
    )
    presence_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if new_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=entity.entity_id,
                state=STATE_ON if old_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
        },
    )
    ret = await entity._async_presence_changed(presence_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


async def send_climate_change_event(
    entity: VersatileThermostat,
    new_hvac_mode: HVACMode,
    old_hvac_mode: HVACMode,
    new_hvac_action: HVACAction,
    old_hvac_action: HVACAction,
    date,
    sleep=True,
):
    """Sending a new climate event simulating a change on the underlying climate state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_hvac_mode=%s old_hvac_mode=%s new_hvac_action=%s old_hvac_action=%s date=%s on %s",
        new_hvac_mode,
        old_hvac_mode,
        new_hvac_action,
        old_hvac_action,
        date,
        entity,
    )
    climate_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=new_hvac_mode,
                attributes={"hvac_action": new_hvac_action},
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=entity.entity_id,
                state=old_hvac_mode,
                attributes={"hvac_action": old_hvac_action},
                last_changed=date,
                last_updated=date,
            ),
        },
    )
    ret = await entity._async_climate_changed(climate_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


def cancel_switchs_cycles(entity: VersatileThermostat):
    """This method will cancel all running cycle on all underlying switch entity"""
    if entity._is_over_climate:
        return
    for under in entity._underlyings:
        under._cancel_cycle()
