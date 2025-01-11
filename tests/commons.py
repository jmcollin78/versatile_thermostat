# pylint: disable=wildcard-import, unused-wildcard-import, unused-import, protected-access, unused-argument, line-too-long, abstract-method, too-many-lines, redefined-builtin

""" Some common resources """
import asyncio
import logging
from typing import Any, Dict, Callable
from unittest.mock import patch, MagicMock  # pylint: disable=unused-import
import pytest  # pylint: disable=unused-import

from homeassistant.core import HomeAssistant, Event, EVENT_STATE_CHANGED, State
from homeassistant.const import (
    UnitOfTemperature,
    STATE_ON,
    STATE_OFF,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_HOME,
    STATE_NOT_HOME,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.entity import Entity
from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)

from homeassistant.components.switch import (
    SwitchEntity,
)

from homeassistant.components.number import NumberEntity, DOMAIN as NUMBER_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.versatile_thermostat.underlyings import *  # pylint: disable=wildcard-import, unused-wildcard-import

from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI

from .const import (  # pylint: disable=unused-import
    MOCK_TH_OVER_SWITCH_USER_CONFIG,
    MOCK_TH_OVER_4SWITCH_USER_CONFIG,
    MOCK_TH_OVER_CLIMATE_USER_CONFIG,
    MOCK_TH_OVER_SWITCH_MAIN_CONFIG,
    MOCK_TH_OVER_SWITCH_CENTRAL_MAIN_CONFIG,
    MOCK_TH_OVER_SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_SWITCH_AC_TYPE_CONFIG,
    MOCK_TH_OVER_4SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_CLIMATE_MAIN_CONFIG,
    MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_USE_DEVICE_TEMP_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_AC_CONFIG,
    MOCK_TH_OVER_CLIMATE_TYPE_NOT_REGULATED_CONFIG,
    MOCK_TH_OVER_SWITCH_TPI_CONFIG,
    MOCK_WINDOW_CONFIG,
    MOCK_MOTION_CONFIG,
    MOCK_POWER_CONFIG,
    MOCK_PRESENCE_CONFIG,
    MOCK_PRESENCE_AC_CONFIG,
    MOCK_ADVANCED_CONFIG,
    # MOCK_DEFAULT_FEATURE_CONFIG,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_NONE,
    PRESET_ECO,
    PRESET_ACTIVITY,
    overrides,
)

MOCK_FULL_FEATURES = {
    CONF_USE_WINDOW_FEATURE: True,
    CONF_USE_MOTION_FEATURE: True,
    CONF_USE_POWER_FEATURE: True,
    CONF_USE_PRESENCE_FEATURE: True,
}

FULL_SWITCH_CONFIG = (
    MOCK_TH_OVER_SWITCH_USER_CONFIG
    | MOCK_TH_OVER_SWITCH_MAIN_CONFIG
    | MOCK_TH_OVER_SWITCH_CENTRAL_MAIN_CONFIG
    | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    | MOCK_TH_OVER_SWITCH_TPI_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_FULL_FEATURES
    | MOCK_WINDOW_CONFIG
    | MOCK_MOTION_CONFIG
    | MOCK_POWER_CONFIG
    | MOCK_PRESENCE_CONFIG
    | MOCK_ADVANCED_CONFIG
)

FULL_SWITCH_AC_CONFIG = (
    MOCK_TH_OVER_SWITCH_USER_CONFIG
    | MOCK_TH_OVER_SWITCH_MAIN_CONFIG
    | MOCK_TH_OVER_SWITCH_CENTRAL_MAIN_CONFIG
    | MOCK_TH_OVER_SWITCH_AC_TYPE_CONFIG
    | MOCK_TH_OVER_SWITCH_TPI_CONFIG
    | MOCK_FULL_FEATURES
    | MOCK_WINDOW_CONFIG
    | MOCK_MOTION_CONFIG
    | MOCK_POWER_CONFIG
    | MOCK_PRESENCE_AC_CONFIG
    | MOCK_ADVANCED_CONFIG
)

PARTIAL_CLIMATE_CONFIG = (
    MOCK_TH_OVER_CLIMATE_USER_CONFIG
    | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_ADVANCED_CONFIG
)

PARTIAL_CLIMATE_CONFIG_USE_DEVICE_TEMP = (
    MOCK_TH_OVER_CLIMATE_USER_CONFIG
    | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_TYPE_USE_DEVICE_TEMP_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_ADVANCED_CONFIG
)

PARTIAL_CLIMATE_NOT_REGULATED_CONFIG = (
    MOCK_TH_OVER_CLIMATE_USER_CONFIG
    | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_TYPE_NOT_REGULATED_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_ADVANCED_CONFIG
)

PARTIAL_CLIMATE_AC_CONFIG = (
    MOCK_TH_OVER_CLIMATE_USER_CONFIG
    | MOCK_TH_OVER_CLIMATE_TYPE_AC_CONFIG
    | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG
    | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_ADVANCED_CONFIG
)

FULL_4SWITCH_CONFIG = (
    MOCK_TH_OVER_4SWITCH_USER_CONFIG
    | MOCK_TH_OVER_4SWITCH_TYPE_CONFIG
    | MOCK_TH_OVER_SWITCH_TPI_CONFIG
    #    | MOCK_PRESETS_CONFIG
    | MOCK_WINDOW_CONFIG
    | MOCK_MOTION_CONFIG
    | MOCK_POWER_CONFIG
    | MOCK_PRESENCE_CONFIG
    | MOCK_ADVANCED_CONFIG
)

FULL_CENTRAL_CONFIG = {
    CONF_NAME: CENTRAL_CONFIG_NAME,
    CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
    CONF_TEMP_MIN: 15,
    CONF_TEMP_MAX: 30,
    CONF_STEP_TEMPERATURE: 0.1,
    CONF_TPI_COEF_INT: 0.5,
    CONF_TPI_COEF_EXT: 0.02,
    "frost_temp": 10,
    "eco_temp": 17.1,
    "comfort_temp": 0,
    "boost_temp": 19.1,
    "eco_ac_temp": 25.1,
    "comfort_ac_temp": 23.1,
    "boost_ac_temp": 21.1,
    "frost_away_temp": 15.1,
    "eco_away_temp": 15.2,
    "comfort_away_temp": 0,
    "boost_away_temp": 15.4,
    "eco_ac_away_temp": 30.5,
    "comfort_ac_away_temp": 0,
    "boost_ac_away_temp": 30.7,
    CONF_WINDOW_DELAY: 15,
    CONF_WINDOW_OFF_DELAY: 30,
    CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
    CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
    CONF_WINDOW_AUTO_MAX_DURATION: 31,
    CONF_MOTION_DELAY: 31,
    CONF_MOTION_OFF_DELAY: 301,
    CONF_MOTION_PRESET: "boost",
    CONF_NO_MOTION_PRESET: "frost",
    CONF_POWER_SENSOR: "sensor.mock_power_sensor",
    CONF_MAX_POWER_SENSOR: "sensor.mock_max_power_sensor",
    CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
    CONF_PRESET_POWER: 14,
    CONF_MINIMAL_ACTIVATION_DELAY: 11,
    CONF_SAFETY_DELAY_MIN: 61,
    CONF_SAFETY_MIN_ON_PERCENT: 0.5,
    CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
    CONF_USE_CENTRAL_BOILER_FEATURE: False,
}

FULL_CENTRAL_CONFIG_WITH_BOILER = {
    CONF_NAME: CENTRAL_CONFIG_NAME,
    CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
    CONF_TEMP_MIN: 15,
    CONF_TEMP_MAX: 30,
    CONF_STEP_TEMPERATURE: 0.1,
    CONF_TPI_COEF_INT: 0.5,
    CONF_TPI_COEF_EXT: 0.02,
    "frost_temp": 10,
    "eco_temp": 17.1,
    "comfort_temp": 0,
    "boost_temp": 19.1,
    "eco_ac_temp": 25.1,
    "comfort_ac_temp": 23.1,
    "boost_ac_temp": 21.1,
    "frost_away_temp": 15.1,
    "eco_away_temp": 15.2,
    "comfort_away_temp": 0,
    "boost_away_temp": 15.4,
    "eco_ac_away_temp": 30.5,
    "comfort_ac_away_temp": 0,
    "boost_ac_away_temp": 30.7,
    CONF_WINDOW_DELAY: 15,
    CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
    CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
    CONF_WINDOW_AUTO_MAX_DURATION: 31,
    CONF_MOTION_DELAY: 31,
    CONF_MOTION_OFF_DELAY: 301,
    CONF_MOTION_PRESET: "boost",
    CONF_NO_MOTION_PRESET: "frost",
    CONF_POWER_SENSOR: "sensor.mock_power_sensor",
    CONF_MAX_POWER_SENSOR: "sensor.mock_max_power_sensor",
    CONF_PRESET_POWER: 14,
    CONF_MINIMAL_ACTIVATION_DELAY: 11,
    CONF_SAFETY_DELAY_MIN: 61,
    CONF_SAFETY_MIN_ON_PERCENT: 0.5,
    CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
    CONF_USE_CENTRAL_BOILER_FEATURE: True,
    CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_on",
    CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_off",
}


_LOGGER = logging.getLogger(__name__)


class MockClimate(ClimateEntity):
    """A Mock Climate class used for Underlying climate mode"""

    def __init__(  # pylint: disable=unused-argument, dangerous-default-value
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        entry_infos={},
        hvac_mode: HVACMode = HVACMode.OFF,
        hvac_action: HVACAction = HVACAction.OFF,
        fan_modes: list[str] = None,
        hvac_modes: list[str] = None,
    ) -> None:
        """Initialize the thermostat."""

        super().__init__()

        self.hass = hass
        self.platform = "climate"
        self.entity_id = self.platform + "." + unique_id
        self._attr_extra_state_attributes = {}
        self._unique_id = unique_id
        self._name = name
        self._attr_hvac_action = (
            HVACAction.OFF if hvac_mode == HVACMode.OFF else HVACAction.HEATING
        )
        self._attr_hvac_mode = hvac_mode
        self._attr_hvac_modes = (
            hvac_modes
            if hvac_modes is not None
            else [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature = 20
        self._attr_current_temperature = 15
        self._attr_hvac_action = hvac_action
        self._attr_target_temperature_step = 0.2
        self._fan_modes = fan_modes if fan_modes else None
        self._attr_fan_mode = None

    @property
    def name(self) -> str:
        """The name"""
        return self._name

    @property
    def hvac_action(self):
        """The hvac action of the mock climate"""
        return self._attr_hvac_action

    @property
    def fan_modes(self) -> list[str] | None:
        """The list of fan_modes"""
        return self._fan_modes

    def set_fan_mode(self, fan_mode):
        """Set the fan mode"""
        self._attr_fan_mode = fan_mode

    @property
    def supported_features(self) -> int:
        """The supported feature of this climate entity"""
        ret = ClimateEntityFeature.TARGET_TEMPERATURE
        if self._fan_modes:
            ret = ret | ClimateEntityFeature.FAN_MODE
        return ret

    def set_temperature(self, **kwargs):
        """Set the target temperature"""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self._attr_target_temperature = temperature

    async def async_set_hvac_mode(self, hvac_mode):
        """The hvac mode"""
        self._attr_hvac_mode = hvac_mode

    def set_hvac_mode(self, hvac_mode):
        """The hvac mode"""
        self._attr_hvac_mode = hvac_mode

    def set_hvac_action(self, hvac_action: HVACAction):
        """Set the HVACaction"""
        self._attr_hvac_action = hvac_action

    def set_current_temperature(self, current_temperature):
        """Set the current_temperature"""
        self._attr_current_temperature = current_temperature


class MockUnavailableClimate(ClimateEntity):
    """A Mock Climate class used for Underlying climate mode"""

    def __init__(
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
        """Initialize the thermostat."""

        super().__init__()

        self._hass = hass
        self._attr_extra_state_attributes = {}
        self._unique_id = unique_id
        self._name = name
        self._attr_hvac_action = None
        self._attr_hvac_mode = None
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_fan_mode = None


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

    @property
    def min_temp(self):  # pylint: disable=missing-function-docstring
        return 15

    @property
    def max_temp(self):  # pylint: disable=missing-function-docstring
        return 19


class MagicMockClimateWithTemperatureRange(MagicMock):
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
        return ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

    @property
    def min_temp(self):  # pylint: disable=missing-function-docstring
        return 10

    @property
    def max_temp(self):  # pylint: disable=missing-function-docstring
        return 31


class MockSwitch(SwitchEntity):
    """A fake switch to be used instead real switch"""

    def __init__(  # pylint: disable=unused-argument, dangerous-default-value
        self, hass: HomeAssistant, unique_id, name, entry_infos={}
    ):
        """Init the switch"""
        super().__init__()

        self.hass = hass
        self.platform = "switch"
        self.entity_id = self.platform + "." + unique_id
        self._name = name
        self._attr_is_on = False

    @property
    def name(self) -> str:
        """The name"""
        return self._name

    @overrides
    def turn_on(self, **kwargs: Any):
        """Turns the switch on and notify the state change"""
        self._attr_is_on = True
        # self.async_write_ha_state()

    @overrides
    def turn_off(self, **kwargs: Any):
        """Turns the switch on and notify the state change"""
        self._attr_is_on = False
        # self.async_write_ha_state()


class MockNumber(NumberEntity):
    """A fake switch to be used instead real switch"""

    def __init__(  # pylint: disable=unused-argument, dangerous-default-value
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        min=0,
        max=100,
        step=1,
        entry_infos={},
    ):
        """Init the switch"""
        super().__init__()

        self.hass = hass
        self.platform = "number"
        self.entity_id = self.platform + "." + unique_id
        self._name = name
        self._attr_native_value = 0
        self._attr_native_min_value = min
        self._attr_native_max_value = max
        self._attr_step = step

    @property
    def name(self) -> str:
        """The name"""
        return self._name

    @overrides
    def set_native_value(self, value: float):
        """Change the value"""
        self._attr_native_value = value
        self.async_write_ha_state()


async def create_thermostat(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    entity_id: str,
    temps: dict | None = None,
) -> BaseThermostat:
    """Creates and return a TPI Thermostat"""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity = search_entity(hass, entity_id, CLIMATE_DOMAIN)

    if entity and temps:
        await set_all_climate_preset_temp(
            hass, entity, temps, entity.entity_id.replace("climate.", "")
        )

    return entity


async def create_central_config(  # pylint: disable=dangerous-default-value
    hass: HomeAssistant, entry: MockConfigEntry = FULL_CENTRAL_CONFIG
):
    """Creates a Central Configuration from entry given in argument"""
    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data=entry,
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    # Test that VTherm API find the CentralConfig
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    central_configuration = api.find_central_configuration()
    assert central_configuration is not None

    return central_configuration


def search_entity(hass: HomeAssistant, entity_id, domain) -> Entity:
    """Search and return the entity in the domain"""
    component = hass.data[domain]
    for entity in component.entities:
        _LOGGER.debug("Found %s entity: %s", domain, entity.entity_id)
        if entity.entity_id == entity_id:
            return entity
    return None


def count_entities(hass: HomeAssistant, entity_id, domain) -> Entity:
    """Search and return the entity in the domain"""
    component = hass.data[domain]
    return len(list(component.entities)) if component.entities else 0


async def send_temperature_change_event(
    entity: BaseThermostat, new_temp, date, sleep=True
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
    dearm_window_auto = await entity._async_temperature_changed(temp_event)
    if sleep:
        await asyncio.sleep(0.1)

    return dearm_window_auto


async def send_last_seen_temperature_change_event(
    entity: BaseThermostat, date, sleep=True
):
    """Sending a new last seen event simulating a change on last seen temperature sensor"""
    _LOGGER.info(
        "------- Testu: sending send_last_seen_temperature_change_event, date=%s on %s",
        date,
        entity,
    )
    last_seen_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=entity.entity_id,
                state=date,
                last_changed=date,
                last_updated=date,
            )
        },
    )
    await entity._async_last_seen_temperature_changed(last_seen_event)
    if sleep:
        await asyncio.sleep(0.1)


async def send_ext_temperature_change_event(
    entity: BaseThermostat, new_temp, date, sleep=True
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


async def send_power_change_event(entity: BaseThermostat, new_power, date, sleep=True):
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
    vtherm_api = VersatileThermostatAPI.get_vtherm_api()
    await vtherm_api.central_power_manager._power_sensor_changed(power_event)
    await vtherm_api.central_power_manager._do_immediate_shedding()
    if sleep:
        await entity.hass.async_block_till_done()


async def send_max_power_change_event(
    entity: BaseThermostat, new_power_max, date, sleep=True
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
    vtherm_api = VersatileThermostatAPI.get_vtherm_api()
    await vtherm_api.central_power_manager._max_power_sensor_changed(power_event)
    await vtherm_api.central_power_manager._do_immediate_shedding()
    if sleep:
        await entity.hass.async_block_till_done()


async def send_window_change_event(
    entity: BaseThermostat, new_state: bool, old_state: bool, date, sleep=True
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
    ret = await entity.window_manager._window_sensor_changed(window_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


async def send_motion_change_event(
    entity: BaseThermostat, new_state: bool, old_state: bool, date, sleep=True
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
    ret = await entity.motion_manager._motion_sensor_changed(motion_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


async def send_presence_change_event(
    vtherm: BaseThermostat, new_state: bool, old_state: bool, date, sleep=True
):
    """Sending a new presence event simulating a change on the window state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_state=%s old_state=%s date=%s on %s",
        new_state,
        old_state,
        date,
        vtherm,
    )
    presence_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=vtherm.entity_id,
                state=STATE_ON if new_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=vtherm.entity_id,
                state=STATE_ON if old_state else STATE_OFF,
                last_changed=date,
                last_updated=date,
            ),
        },
    )
    ret = await vtherm._presence_manager._presence_sensor_changed(presence_event)
    if sleep:
        await asyncio.sleep(0.1)
    return ret


async def send_climate_change_event(
    entity: BaseThermostat,
    new_hvac_mode: HVACMode,
    old_hvac_mode: HVACMode,
    new_hvac_action: HVACAction,
    old_hvac_action: HVACAction,
    date,
    sleep=True,
    underlying_entity_id: str = None,
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

    send_from_entity_id = (
        underlying_entity_id if underlying_entity_id is not None else entity.entity_id
    )

    climate_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=send_from_entity_id,
                state=new_hvac_mode,
                attributes={"hvac_action": new_hvac_action},
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=send_from_entity_id,
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


async def send_climate_change_event_with_temperature(
    entity: BaseThermostat,
    new_hvac_mode: HVACMode,
    old_hvac_mode: HVACMode,
    new_hvac_action: HVACAction,
    old_hvac_action: HVACAction,
    date,
    temperature,
    sleep=True,
    underlying_entity_id=None,
):
    """Sending a new climate event simulating a change on the underlying climate state"""
    _LOGGER.info(
        "------- Testu: sending send_temperature_change_event, new_hvac_mode=%s old_hvac_mode=%s new_hvac_action=%s old_hvac_action=%s date=%s temperature=%s on %s",
        new_hvac_mode,
        old_hvac_mode,
        new_hvac_action,
        old_hvac_action,
        date,
        temperature,
        entity,
    )
    if not underlying_entity_id:
        underlying_entity_id = entity.entity_id

    climate_event = Event(
        EVENT_STATE_CHANGED,
        {
            "new_state": State(
                entity_id=underlying_entity_id,
                state=new_hvac_mode,
                attributes={"hvac_action": new_hvac_action, "temperature": temperature},
                last_changed=date,
                last_updated=date,
            ),
            "old_state": State(
                entity_id=underlying_entity_id,
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


def cancel_switchs_cycles(entity: BaseThermostat):
    """This method will cancel all running cycle on all underlying switch entity"""
    if entity.is_over_climate:
        return
    for under in entity._underlyings:
        under._cancel_cycle()


async def set_climate_preset_temp(
    entity: BaseThermostat, temp_number_name: str, temp: float
):
    """Set a preset value in the temp Number entity"""
    number_entity_id = (
        NUMBER_DOMAIN
        + "."
        + entity.entity_id.split(".")[1]
        + "_preset_"
        + temp_number_name
        + PRESET_TEMP_SUFFIX
    )

    temp_entity = search_entity(
        entity.hass,
        number_entity_id,
        NUMBER_DOMAIN,
    )
    if temp_entity:
        await temp_entity.async_set_native_value(temp)
    else:
        _LOGGER.warning(
            "commons tests set_climate_preset_temp: cannot find number entity with entity_id '%s'",
            number_entity_id,
        )


# The temperatures to set
default_temperatures_ac_away = {
    "frost": 7.0,
    "eco": 17.0,
    "comfort": 19.0,
    "boost": 21.0,
    "eco_ac": 27.0,
    "comfort_ac": 25.0,
    "boost_ac": 23.0,
    "frost_away": 7.1,
    "eco_away": 17.1,
    "comfort_away": 17.2,
    "boost_away": 17.3,
    "eco_ac_away": 27.1,
    "comfort_ac_away": 25.1,
    "boost_ac_away": 23.1,
}

default_temperatures_away = {
    "frost": 7.0,
    "eco": 17.0,
    "comfort": 19.0,
    "boost": 21.0,
    "frost_away": 7.1,
    "eco_away": 17.1,
    "comfort_away": 17.2,
    "boost_away": 17.3,
}

default_temperatures = {
    "frost": 7.0,
    "eco": 17.0,
    "comfort": 19.0,
    "boost": 21.0,
}


async def set_all_climate_preset_temp(
    hass, vtherm: BaseThermostat, temps: dict | None, number_entity_base_name: str
):
    """Initialize all temp of preset for a VTherm entity"""
    local_temps = temps if temps is not None else default_temperatures
    # We initialize
    for preset_name, value in local_temps.items():

        await set_climate_preset_temp(vtherm, preset_name, value)

        # Search the number entity to control it is correctly set
        number_entity_name = (
            f"number.{number_entity_base_name}_preset_{preset_name}{PRESET_TEMP_SUFFIX}"
        )
        temp_entity: NumberEntity = search_entity(
            hass,
            number_entity_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        if not temp_entity:
            raise ConfigurationNotCompleteError(
                f"'{number_entity_name}' don't exists as number entity"
            )
        # Because set_value is not implemented in Number class (really don't understand why...)
        assert temp_entity.state == value

    await hass.async_block_till_done()

#
# Side effects management
#
SideEffectDict = Dict[str, Any]


class SideEffects:
    """A class to manage sideEffects for mock"""

    def __init__(self, side_effects: SideEffectDict, default_side_effect: Any):
        """Initialise the side effects"""
        self._current_side_effects: SideEffectDict = side_effects
        self._default_side_effect: Any = default_side_effect

    def get_side_effects(self) -> Callable[[str], Any]:
        """returns the method which apply the side effects"""

        def side_effect_method(arg) -> Any:
            """Search a side effect definition and return it"""
            return self._current_side_effects.get(arg, self._default_side_effect)

        return side_effect_method

    def add_or_update_side_effect(self, key: str, new_value: Any):
        """Update the value of a side effect"""
        self._current_side_effects[key] = new_value


async def do_central_power_refresh(hass):
    """Do a central power refresh"""
    await VersatileThermostatAPI.get_vtherm_api().central_power_manager.refresh_state()
    return hass.async_block_till_done()
