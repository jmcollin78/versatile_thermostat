# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

# Warning: when running in parellel, some test fails ramdomly. I don't find any solution to this problem

""" Test the central_configuration """
import asyncio
import logging

from datetime import datetime, timedelta

from unittest.mock import patch, call

from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntryState
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)

from custom_components.versatile_thermostat.thermostat_valve import (
    ThermostatOverValve,
)

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI
from custom_components.versatile_thermostat.binary_sensor import (
    CentralBoilerBinarySensor,
)

from custom_components.versatile_thermostat.sensor import NbActiveDeviceForBoilerSensor, TotalPowerActiveDeviceForBoilerSensor

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

_LOGGER = logging.getLogger(__name__)

async def test_add_a_central_config_with_boiler(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the clean_central_config_doubon of base_thermostat"""
    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data=FULL_CENTRAL_CONFIG_WITH_BOILER,
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(
        hass, "climate.thecentralconfigmockname", "climate"
    )

    assert entity is None

    assert count_entities(hass, "climate.thecentralconfigmockname", "climate") == 0

    # Test that VTherm API find the CentralConfig
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    central_configuration = api.find_central_configuration()
    assert central_configuration is not None

    central_boiler_manager = api.central_boiler_manager
    assert central_boiler_manager is not None

    # Test that VTherm API have any central boiler entities
    assert central_boiler_manager.nb_active_device_for_boiler == 0

    assert central_boiler_manager.nb_active_device_for_boiler_threshold == 0  # the default value is 0

    assert central_boiler_manager.total_power_active_for_boiler == 0  # the default value is 0
    assert central_boiler_manager.total_power_active_for_boiler_threshold == 0  # the default value is 0


async def test_update_central_boiler_state_simple(
    hass: HomeAssistant,
    init_central_config_with_boiler_fixture,
    fake_underlying_switch,
):
    switch1 = fake_underlying_switch
    """Test that the central boiler state behavior in a full normal conditions (with no mock)"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    # switch1 = MockSwitch(hass, "switch1", "theSwitch1")
    # await register_mock_entity(hass, switch1, SWITCH_DOMAIN)

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 18,
            # "frost_temp": 7,
            # "eco_temp": 17,
            # "comfort_temp": 18,
            # "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [switch1.entity_id],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1500,
        },
    )

    #
    # 0. start a heater because the temp is low
    #
    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverSwitchMockName"
    assert entity.is_over_switch
    assert entity.underlying_entities[0].entity_id == "switch.mock_switch"

    api.central_boiler_manager._set_nb_active_device_threshold(1)
    api.central_boiler_manager._set_total_power_active_threshold(1000)
    await hass.async_block_till_done()

    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0

    assert api.central_boiler_manager.total_power_active_for_boiler_threshold == 1000
    assert api.central_boiler_manager.total_power_active_for_boiler == 0

    # check custom attributes of boiler binary sensor
    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor")
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_configured"] is True
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_ready"] is True
    central_boiler_manager_attributes = boiler_binary_sensor.extra_state_attributes.get("central_boiler_manager")
    assert central_boiler_manager_attributes is not None
    assert central_boiler_manager_attributes["is_on"] is False
    assert central_boiler_manager_attributes["service_activate"] == {
        "service_domain": "switch",
        "service_name": "turn_on",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["service_deactivate"] == {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["nb_active_device_for_boiler"] == 0
    assert central_boiler_manager_attributes["nb_active_device_for_boiler_threshold"] == 1
    assert central_boiler_manager_attributes["total_power_active_for_boiler"] == 0
    assert central_boiler_manager_attributes["total_power_active_for_boiler_threshold"] == 1000

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    # set temp to 23 to avoid heating and turn on the heater and the boiler
    await send_temperature_change_event(entity, 23, now)
    await send_ext_temperature_change_event(entity, 19, now)

    assert entity.hvac_mode == VThermHvacMode_HEAT

    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")
    assert nb_device_active_sensor is not None
    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    total_power_active_sensor: TotalPowerActiveDeviceForBoilerSensor = search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")
    assert total_power_active_sensor is not None
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # check custom attributes of boiler binary sensor
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_configured"] is True
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_ready"] is True
    central_boiler_manager_attributes = boiler_binary_sensor.extra_state_attributes.get("central_boiler_manager")
    assert central_boiler_manager_attributes is not None
    assert central_boiler_manager_attributes["is_on"] is False
    assert central_boiler_manager_attributes["service_activate"] == {
        "service_domain": "switch",
        "service_name": "turn_on",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["service_deactivate"] == {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["nb_active_device_for_boiler"] == 0
    assert central_boiler_manager_attributes["nb_active_device_for_boiler_threshold"] == 1
    assert central_boiler_manager_attributes["total_power_active_for_boiler"] == 0
    assert central_boiler_manager_attributes["total_power_active_for_boiler_threshold"] == 1000

    #
    # 1. start a heater because the temp is low
    #
    _LOGGER.debug("---- 1. Turn on the switch1")
    now = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 10, now)

    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.HEATING)

    # Radiator and central boiler is on
    assert switch1.is_on
    assert switch_pompe_chaudiere.is_on

    # There should be one device active
    assert entity.is_initialized is True
    await wait_for_local_condition(lambda: api.central_boiler_manager.nb_active_device_for_boiler == 1)

    # boiler binary sensor is on
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == ["switch.mock_switch"]

    assert total_power_active_sensor.state == 1500
    assert total_power_active_sensor.active_device_ids == ["switch.mock_switch"]

    # check custom attributes of boiler binary sensor
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_ON
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_configured"] is True
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_ready"] is True
    central_boiler_manager_attributes = boiler_binary_sensor.extra_state_attributes.get("central_boiler_manager")
    assert central_boiler_manager_attributes is not None
    assert central_boiler_manager_attributes["is_on"] is True
    assert central_boiler_manager_attributes["service_activate"] == {
        "service_domain": "switch",
        "service_name": "turn_on",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["service_deactivate"] == {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["nb_active_device_for_boiler"] == 1
    assert central_boiler_manager_attributes["nb_active_device_for_boiler_threshold"] == 1
    assert central_boiler_manager_attributes["total_power_active_for_boiler"] == 1500
    assert central_boiler_manager_attributes["total_power_active_for_boiler_threshold"] == 1000

    #
    # 2. stop a heater by changing the preset
    #
    await entity.async_set_preset_mode(VThermPreset.FROST)
    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.IDLE)

    # Radiator and central boiler is off
    assert not switch1.is_on

    # Wait for all propagations
    await wait_for_local_condition(lambda: not switch_pompe_chaudiere.is_on)
    await wait_for_local_condition(lambda: api.central_boiler_manager.nb_active_device_for_boiler == 0)
    await wait_for_local_condition(lambda: boiler_binary_sensor.state == STATE_OFF)

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # check custom attributes of boiler binary sensor
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_configured"] is True
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_ready"] is True
    central_boiler_manager_attributes = boiler_binary_sensor.extra_state_attributes.get("central_boiler_manager")
    assert central_boiler_manager_attributes is not None
    assert central_boiler_manager_attributes["is_on"] is False
    assert central_boiler_manager_attributes["service_activate"] == {
        "service_domain": "switch",
        "service_name": "turn_on",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["service_deactivate"] == {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_domain": "switch",
        "entity_name": "pompe_chaudiere",
        "entity_id": "switch.pompe_chaudiere",
        "data": {},
    }
    assert central_boiler_manager_attributes["nb_active_device_for_boiler"] == 0
    assert central_boiler_manager_attributes["nb_active_device_for_boiler_threshold"] == 1
    assert central_boiler_manager_attributes["total_power_active_for_boiler"] == 0
    assert central_boiler_manager_attributes["total_power_active_for_boiler_threshold"] == 1000

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_update_central_boiler_state_multiple(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    switch1 = MockSwitch(hass, "switch1", "theSwitch1")
    await register_mock_entity(hass, switch1, SWITCH_DOMAIN)
    assert switch1.is_on is False

    switch2 = MockSwitch(hass, "switch2", "theSwitch2")
    await register_mock_entity(hass, switch2, SWITCH_DOMAIN)
    assert switch2.is_on is False

    switch3 = MockSwitch(hass, "switch3", "theSwitch3")
    await register_mock_entity(hass, switch3, SWITCH_DOMAIN)
    assert switch3.is_on is False

    switch4 = MockSwitch(hass, "switch4", "theSwitch4")
    await register_mock_entity(hass, switch4, SWITCH_DOMAIN)
    assert switch4.is_on is False

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)
    assert switch_pompe_chaudiere.is_on is False

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [
                switch1.entity_id,
                switch2.entity_id,
                switch3.entity_id,
                switch4.entity_id,
            ],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1500,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverSwitchMockName"
    assert entity.is_over_switch
    assert entity.underlying_entities[0].entity_id == "switch.switch1"
    assert entity.underlying_entities[1].entity_id == "switch.switch2"
    assert entity.underlying_entities[2].entity_id == "switch.switch3"
    assert entity.underlying_entities[3].entity_id == "switch.switch4"
    assert entity.device_actives == []

    api.central_boiler_manager._set_nb_active_device_threshold(1)
    api.central_boiler_manager._set_total_power_active_threshold(1000)
    await hass.async_block_till_done()

    nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(
        hass, "sensor.nb_device_active_for_boiler", "sensor"
    )
    assert nb_device_active_sensor is not None
    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    total_power_active_sensor: TotalPowerActiveDeviceForBoilerSensor = search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")
    assert total_power_active_sensor is not None
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # set temp to 23 to avoid heating and turn on the heater and the boiler

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    await send_temperature_change_event(entity, 23, now)

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert switch_pompe_chaudiere.is_on is False

    # 0. set threshold to 3
    api.central_boiler_manager._set_nb_active_device_threshold(3)
    await hass.async_block_till_done()
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 3

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # check custom attributes of boiler binary sensor
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_configured"] is True
    assert boiler_binary_sensor.extra_state_attributes["is_central_boiler_ready"] is True
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is False
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 0
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler_threshold"] == 3
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler_threshold"] == 1000

    #
    # 1. start a first heater
    #
    assert switch1.is_on is False
    await switch1.async_turn_on()
    switch1.async_write_ha_state()
    await hass.async_block_till_done()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["switch.switch1"]

    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == ["switch.switch1"]

    # on_percent is 0
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is False
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is False
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 1
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 2. start a 2nd heater
    #
    assert switch2.is_on is False
    await switch2.async_turn_on()
    switch2.async_write_ha_state()
    # Wait for state event propagation
    await hass.async_block_till_done()
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["switch.switch1", "switch.switch2"]

    assert api.central_boiler_manager.nb_active_device_for_boiler == 2
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 2
    assert nb_device_active_sensor.active_device_ids == [
        "switch.switch1",
        "switch.switch2",
    ]

    # on_percent is still 0
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is False
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is False
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 2
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 3. start a 3rd heater -> that will start the boiler
    #
    assert switch3.is_on is False
    await switch3.async_turn_on()
    switch3.async_write_ha_state()
    # Wait for state event propagation
    await hass.async_block_till_done()
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING

    assert api.central_boiler_manager.nb_active_device_for_boiler == 3
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 3
    assert nb_device_active_sensor.active_device_ids == [
        "switch.switch1",
        "switch.switch2",
        "switch.switch3",
    ]

    # on_percent is 0
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is True
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_ON
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is True
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 3
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 4. start a 4th heater. Nothing more
    #
    assert switch4.is_on is False
    await switch4.async_turn_on()
    switch4.async_write_ha_state()
    # Wait for state event propagation
    await hass.async_block_till_done()
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING

    assert api.central_boiler_manager.nb_active_device_for_boiler == 4
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 4
    assert nb_device_active_sensor.active_device_ids == ["switch.switch1", "switch.switch2", "switch.switch3", "switch.switch4"]

    # on_percent is 0
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is True
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_ON
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is True
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 4
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 5. stop a heater
    #
    assert switch1.is_on is True
    await switch1.async_turn_off()
    switch1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING

    assert api.central_boiler_manager.nb_active_device_for_boiler == 3
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 3
    assert nb_device_active_sensor.active_device_ids == [
        "switch.switch2",
        "switch.switch3",
        "switch.switch4",
    ]

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is True
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_ON
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is True
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 3
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 6. stop a 2nd heater -> boiler will be off
    #
    assert switch4.is_on is True
    await switch4.async_turn_off()
    switch4.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING

    assert api.central_boiler_manager.nb_active_device_for_boiler == 2
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 2
    assert nb_device_active_sensor.active_device_ids == [
        "switch.switch2",
        "switch.switch3",
    ]

    # on_percent is 0
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is False
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is False

    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_OFF
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is False
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 2
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 0

    #
    # 7. stop all heaters and set temperature to a low level so that on_percent is at 50%
    #
    api.central_boiler_manager._set_total_power_active_threshold(750)
    api.central_boiler_manager._set_nb_active_device_threshold(2)
    assert switch2.is_on is True
    await switch2.async_turn_off()
    switch2.async_write_ha_state()

    assert switch3.is_on is True
    await switch3.async_turn_off()
    switch3.async_write_ha_state()

    await send_temperature_change_event(entity, 20, now + timedelta(minutes=10))
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert boiler_binary_sensor.state == STATE_ON  # On by total power > threshold

    # A cycle has began with switch1 only
    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == ["switch.switch1"]

    # on_percent is 50
    assert entity.power_percent == 50
    assert total_power_active_sensor.state == 750
    assert total_power_active_sensor.active_device_ids == ["switch.switch1", "switch.switch2", "switch.switch3", "switch.switch4"]
    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is False
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is True

    # check custom attributes of boiler binary sensor
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_state"] == STATE_ON
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["is_on"] is True
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["nb_active_device_for_boiler"] == 1
    assert boiler_binary_sensor.extra_state_attributes["central_boiler_manager"]["total_power_active_for_boiler"] == 750

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_update_central_boiler_state_simple_valve(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    valve1 = MockNumber(hass, "valve1", "theValve1")
    await register_mock_entity(hass, valve1, NUMBER_DOMAIN)

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)
    assert switch_pompe_chaudiere.is_on is False

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [valve1.entity_id],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1500,
        },
    )

    entity: ThermostatOverValve = await create_thermostat(hass, entry, "climate.theovervalvemockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverValveMockName"
    assert entity.is_over_valve
    assert entity.underlying_entities[0].entity_id == "number.valve1"

    api.central_boiler_manager._set_nb_active_device_threshold(0)
    api.central_boiler_manager._set_total_power_active_threshold(1000)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 0
    assert api.central_boiler_manager.total_power_active_for_boiler_threshold == 1000

    assert (nb_device_active_sensor := search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")) is not None
    assert (total_power_active_sensor := search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")) is not None

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.device_actives == []

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # 1. start a valve
    await send_temperature_change_event(entity, 10, now)
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["number.valve1"]

    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == ["number.valve1"]
    assert total_power_active_sensor.state == 1500
    assert total_power_active_sensor.active_device_ids == ["number.valve1"]

    # 2. stop a heater
    await send_temperature_change_event(entity, 25, now)
    # Change the valve value to 0
    valve1.set_native_value(0)
    valve1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.IDLE
    assert entity.device_actives == []

    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_update_central_boiler_state_simple_climate(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(hass, "climate1", "theClimate1")
    await register_mock_entity(hass, climate1, CLIMATE_DOMAIN)

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)
    assert switch_pompe_chaudiere.is_on is False

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [climate1.entity_id],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate
    assert entity.underlying_entities[0].entity_id == "climate.climate1"

    api.central_boiler_manager._set_nb_active_device_threshold(1)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0

    assert (nb_device_active_sensor := search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")) is not None
    assert (total_power_active_sensor := search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")) is not None

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # Force the VTherm to heat
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    await send_temperature_change_event(entity, 25, now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.FROST)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.device_actives == []

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate
    now = now + timedelta(minutes=10)
    await send_temperature_change_event(entity, 10, now)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    # Simulate that the climate is heating
    climate1.set_hvac_mode(VThermHvacMode_HEAT)
    climate1.set_hvac_action(HVACAction.HEATING)
    climate1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["climate.climate1"]

    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == [
        "climate.climate1",
    ]

    # Power is not configured
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # 2. stop a climate
    await send_temperature_change_event(entity, 25, now)
    climate1.set_hvac_mode(VThermHvacMode_HEAT)
    climate1.set_hvac_action(HVACAction.IDLE)
    climate1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.IDLE
    assert entity.device_actives == []

    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # Power is not configured
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    entity.remove_thermostat()


async def test_update_central_boiler_state_simple_climate_power(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(hass, "climate1", "theClimate1")
    await register_mock_entity(hass, climate1, CLIMATE_DOMAIN)

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)
    assert switch_pompe_chaudiere.is_on is False

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [climate1.entity_id],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1001,
        },
    )

    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate
    assert entity.underlying_entities[0].entity_id == "climate.climate1"

    api.central_boiler_manager._set_nb_active_device_threshold(0)
    api.central_boiler_manager._set_total_power_active_threshold(1000)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 0
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert api.central_boiler_manager.total_power_active_for_boiler_threshold == 1000
    assert api.central_boiler_manager.total_power_active_for_boiler == 0

    assert (nb_device_active_sensor := search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")) is not None
    assert (total_power_active_sensor := search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")) is not None

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # Force the VTherm to heat
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    await send_temperature_change_event(entity, 25, now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.FROST)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.device_actives == []

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor")
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate
    now = now + timedelta(minutes=10)
    await send_temperature_change_event(entity, 10, now)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    # Simulate that the climate is heating
    climate1.set_hvac_mode(VThermHvacMode_HEAT)
    climate1.set_hvac_action(HVACAction.HEATING)
    climate1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["climate.climate1"]

    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert api.central_boiler_manager.total_power_active_for_boiler == 1001
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == [
        "climate.climate1",
    ]

    # Power is not configured
    assert total_power_active_sensor.state == 1001
    assert total_power_active_sensor.active_device_ids == ["climate.climate1"]

    # 2. stop a climate
    await send_temperature_change_event(entity, 25, now)
    climate1.set_hvac_mode(VThermHvacMode_HEAT)
    climate1.set_hvac_action(HVACAction.IDLE)
    climate1.async_write_ha_state()
    # Wait for state event propagation
    await asyncio.sleep(0.5)

    assert entity.hvac_action == HVACAction.IDLE
    assert entity.device_actives == []

    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # Power is not configured
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_update_central_boiler_state_simple_climate_valve_regulation(
    hass: HomeAssistant, init_central_config_with_boiler_fixture, fake_underlying_climate, fake_temp_sensor, fake_ext_temp_sensor
):
    """Test that the central boiler state behavior with a climate with valve regulation"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    switch_pompe_chaudiere = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, switch_pompe_chaudiere, SWITCH_DOMAIN)
    assert switch_pompe_chaudiere.is_on is False

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_OFFSET_CALIBRATION_LIST: [],
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0,
            CONF_AUTO_REGULATION_PERIOD_MIN: 0,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1500,
        },
    )

    fake_opening_degree = await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=0, min=0, max=100)
    await hass.async_block_till_done()

    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
    assert entity
    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate
    assert entity.underlying_entities[0].entity_id == "climate.mock_climate"

    # Boiler will be started only if 2 devices are active or more than 1000W (1 valve)
    api.central_boiler_manager._set_nb_active_device_threshold(2)
    api.central_boiler_manager._set_total_power_active_threshold(1000)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 2
    assert api.central_boiler_manager.total_power_active_for_boiler_threshold == 1000

    assert (nb_device_active_sensor := search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")) is not None
    assert (total_power_active_sensor := search_entity(hass, "sensor.total_power_active_for_boiler", "sensor")) is not None

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []
    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    # Force the VTherm to heat
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    entity._set_now(now)

    fake_temp_sensor.set_native_value(30)
    fake_ext_temp_sensor.set_native_value(18)
    # await send_temperature_change_event(entity, 30, now)
    # await send_ext_temperature_change_event(entity, 18, now)
    await hass.async_block_till_done()

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    # the VTherm should not heat now
    assert entity.hvac_mode == VThermHvacMode_HEAT
    # await asyncio.sleep(0.5)
    # a valve at 0 is considered as OFF
    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.OFF)
    assert entity.activable_underlying_entities[0]._percent_open == 0
    await wait_for_local_condition(lambda: entity.device_actives == [])

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(hass, "binary_sensor.central_configuration_central_boiler", "binary_sensor")
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate with not 100% open degree
    fake_opening_degree.set_native_value(100)

    now = now + timedelta(minutes=1)
    entity._set_now(now)

    # in Boost setpoint is 21°C
    fake_temp_sensor.set_native_value(19.5)
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    # await send_temperature_change_event(entity, 19.5, now)

    # we have to simulate the climate also else the test don't work
    fake_underlying_climate.set_hvac_mode(VThermHvacMode_HEAT)
    fake_underlying_climate.set_hvac_action(HVACAction.HEATING)
    # Wait for state event propagation
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    assert entity.hvac_action == HVACAction.HEATING
    assert entity.device_actives == ["number.mock_opening_degree"]

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == [
        "number.mock_opening_degree",
    ]

    assert entity.on_percent == 0.75  # (21-19.5)*0.3 + (21-18)*0.1 = 0.75
    assert total_power_active_sensor.state == 1125  # on_percent is 75% x 1500W = 1125W
    assert total_power_active_sensor.active_device_ids == [
        "number.mock_opening_degree",
    ]

    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is False
    assert api.central_boiler_manager.is_total_power_active_for_boiler_exceeded is True

    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert boiler_binary_sensor.state == STATE_ON

    # 2. stop a climate

    # await send_temperature_change_event(entity, 25, now)
    fake_temp_sensor.set_native_value(25)
    await asyncio.sleep(0.1)

    fake_underlying_climate.set_hvac_mode(VThermHvacMode_HEAT)
    fake_underlying_climate.set_hvac_action(HVACAction.IDLE)

    # Wait for state event propagation
    await hass.async_block_till_done()

    # The underlying is idle but the valve are closed -> OFF
    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.OFF)
    assert entity.device_actives == []

    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert boiler_binary_sensor.state == STATE_OFF

    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    assert total_power_active_sensor.state == 0
    assert total_power_active_sensor.active_device_ids == []

    entity.remove_thermostat()


async def test_bug_339(
    hass: HomeAssistant,
    init_central_config_with_boiler_fixture,
):
    """Test that the counter of active Vtherm in central boiler is
    correctly updated with underlying is in auto and device is active
    """

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = await create_and_register_mock_climate(
        hass,
        "climate1",
        "theClimate1",
        hvac_mode=VThermHvacMode_AUTO,
        hvac_modes=[VThermHvacMode_AUTO, VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL],
        hvac_action=HVACAction.HEATING,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [climate1.entity_id],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    entity: ThermostatOverValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate
    assert entity.underlying_entities[0].entity_id == "climate.climate1"
    api.central_boiler_manager._set_nb_active_device_threshold(1)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1

    assert (nb_device_active_sensor := search_entity(hass, "sensor.nb_device_active_for_boiler", "sensor")) is not None

    await entity.async_set_hvac_mode(VThermHvacMode_AUTO)
    # Simulate a state change in underlying
    await nb_device_active_sensor.calculate_nb_active_devices(None)

    # The VTherm should be active
    assert entity.underlying_entity(0).is_device_active is True
    assert entity.is_device_active is True
    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    assert api.central_boiler_manager.is_nb_active_active_for_boiler_exceeded is True

    entity.remove_thermostat()
