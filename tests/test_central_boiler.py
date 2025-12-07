# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

# Warning: when running in parellel, some test fails ramdomly. I don't find any solution to this problem

""" Test the central_configuration """
import asyncio
import logging

from datetime import datetime, timedelta

from unittest.mock import patch, call

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

# @pytest.mark.parametrize("expected_lingering_tasks", [True])
# @pytest.mark.parametrize("expected_lingering_timers", [True])
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
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavior in a full normal conditions (with no mock)"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    switch1 = MockSwitch(hass, "switch1", "theSwitch1")
    await register_mock_entity(hass, switch1, SWITCH_DOMAIN)

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
    assert entity.underlying_entities[0].entity_id == "switch.switch1"

    api.central_boiler_manager._set_nb_active_device_threshold(1)

    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    # set temp to 23 to avoid heating and turn on the heater and the boiler
    await send_temperature_change_event(entity, 23, now)
    await send_ext_temperature_change_event(entity, 19, now)

    assert entity.hvac_mode == VThermHvacMode_HEAT

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
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
    assert api.central_boiler_manager.nb_active_device_for_boiler == 1
    # boiler binary sensor is on
    assert boiler_binary_sensor.state == STATE_ON

    assert nb_device_active_sensor.state == 1
    assert nb_device_active_sensor.active_device_ids == ["switch.switch1"]

    assert total_power_active_sensor.state == 1500
    assert total_power_active_sensor.active_device_ids == ["switch.switch1"]

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
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
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
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity.name == "TheOverSwitchMockName"
    assert entity.is_over_switch
    assert entity.underlying_entities[0].entity_id == "switch.switch1"
    assert entity.underlying_entities[1].entity_id == "switch.switch2"
    assert entity.underlying_entities[2].entity_id == "switch.switch3"
    assert entity.underlying_entities[3].entity_id == "switch.switch4"
    assert entity.device_actives == []

    assert api.nb_active_device_for_boiler_threshold == 1
    assert api.nb_active_device_for_boiler == 0

    nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(
        hass, "sensor.nb_device_active_for_boiler", "sensor"
    )
    assert nb_device_active_sensor is not None
    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # set temp to 23 to avoid heating and turn on the heater and the boiler

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    await send_temperature_change_event(entity, 23, now)

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    # tz = get_tz(hass)  # pylint: disable=invalid-name
    # now: datetime = datetime.now(tz=tz)
    # await send_temperature_change_event(entity, 10, now)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert switch_pompe_chaudiere.is_on is False

    # 0. set threshold to 3
    api.central_boiler_manager.nb_active_device_for_boiler_threshold_entity.set_native_value(3)
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 3

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a first heater
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        assert switch1.is_on is False
        # don't work anymore since HA 2025.9.3 - state change event is not thrown
        await switch1.async_turn_on()
        switch1.async_write_ha_state()
        # hass.states.async_set("switch.switch1", "on")
        await hass.async_block_till_done()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING
        assert entity.device_actives == ["switch.switch1"]

        # Switch1 is not started because the service is mocked
        assert mock_service_call.call_count == 0
        # No switch of the boiler
        # mock_service_call.assert_has_calls(
        #     [
        #         call.service_call(
        #             "switch",
        #             "turn_on",
        #             {"entity_id": "switch.switch1"},
        #         ),
        #     ]
        # )
        assert mock_send_event.call_count == 0

        assert api.central_boiler_manager.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 1
        assert nb_device_active_sensor.active_device_ids == ["switch.switch1"]

    # 2. start a 2nd heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await switch2.async_turn_on()
        switch2.async_write_ha_state()
        # Wait for state event propagation
        await hass.async_block_till_done()
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING
        assert entity.device_actives == ["switch.switch1", "switch.switch2"]

        # Only the first heater is started by the algo
        assert mock_service_call.call_count == 0
        # No switch of the boiler. Caution: each time a underlying heater state change itself,
        # the cycle restarts. So it is always the first heater that is started
        # mock_service_call.assert_has_calls(
        #     [
        #         call.service_call(
        #             "switch",
        #             "turn_on",
        #             {"entity_id": "switch.switch1"},
        #         ),
        #     ]
        # )
        assert mock_send_event.call_count == 0

        assert api.central_boiler_manager.nb_active_device_for_boiler == 2
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 2
        assert nb_device_active_sensor.active_device_ids == [
            "switch.switch1",
            "switch.switch2",
        ]

    # 3. start a 3rd heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await switch3.async_turn_on()
        switch3.async_write_ha_state()
        # Wait for state event propagation
        await hass.async_block_till_done()
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING

        # Only the first heater is started by the algo
        assert mock_service_call.call_count == 1
        # No switch of the boiler. Caution: each time a underlying heater state change itself,
        # the cycle restarts. So it is always the first heater that is started
        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "switch",
                    "turn_on",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                ),
            ],
            any_order=True,
        )
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": True},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 3
        assert boiler_binary_sensor.state == STATE_ON

        assert nb_device_active_sensor.state == 3
        assert nb_device_active_sensor.active_device_ids == [
            "switch.switch1",
            "switch.switch2",
            "switch.switch3",
        ]

    # 4. start a 4th heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await switch4.async_turn_on()
        switch4.async_write_ha_state()
        # Wait for state event propagation
        await hass.async_block_till_done()
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING

        # Only the first heater is started by the algo
        assert mock_service_call.call_count == 0
        # No switch of the boiler. Caution: each time a underlying heater state change itself,
        # the cycle restarts. So it is always the first heater that is started
        # mock_service_call.assert_has_calls(
        #     [
        #         call.service_call(
        #             "switch",
        #             "turn_on",
        #             {"entity_id": "switch.switch1"},
        #         ),
        #     ]
        # )
        assert mock_send_event.call_count == 0
        assert api.central_boiler_manager.nb_active_device_for_boiler == 4
        assert boiler_binary_sensor.state == STATE_ON

        assert nb_device_active_sensor.state == 4
        assert nb_device_active_sensor.active_device_ids == [
            "switch.switch1",
            "switch.switch2",
            "switch.switch3",
            "switch.switch4",
        ]

    # 5. stop a heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await switch1.async_turn_off()
        switch1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 0
        assert mock_send_event.call_count == 0
        assert api.central_boiler_manager.nb_active_device_for_boiler == 3
        assert boiler_binary_sensor.state == STATE_ON

        assert nb_device_active_sensor.state == 3
        assert nb_device_active_sensor.active_device_ids == [
            "switch.switch2",
            "switch.switch3",
            "switch.switch4",
        ]

    # 6. stop a 2nd heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await switch4.async_turn_off()
        switch4.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "switch",
                    "turn_off",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                )
            ]
        )

        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": False},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()


        assert api.central_boiler_manager.nb_active_device_for_boiler == 2
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 2
        assert nb_device_active_sensor.active_device_ids == [
            "switch.switch2",
            "switch.switch3",
        ]

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
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
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
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    entity: ThermostatOverValve = await create_thermostat(
        hass, entry, "climate.theovervalvemockname"
    )
    assert entity
    assert entity.name == "TheOverValveMockName"
    assert entity.is_over_valve
    assert entity.underlying_entities[0].entity_id == "number.valve1"

    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.device_actives == []

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(
        hass, "sensor.nb_device_active_for_boiler", "sensor"
    )
    assert nb_device_active_sensor is not None
    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # 1. start a valve
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await send_temperature_change_event(entity, 10, now)
        # we have to simulate the valve also else the test don't work
        valve1.set_native_value(10)
        valve1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING
        assert entity.device_actives == ["number.valve1"]

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "switch",
                    "turn_on",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                ),
            ]
        )
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": True},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON

        assert nb_device_active_sensor.state == 1
        assert nb_device_active_sensor.active_device_ids == [
            "number.valve1",
        ]

    # 2. stop a heater
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await send_temperature_change_event(entity, 25, now)
        # Change the valve value to 0
        valve1.set_native_value(0)
        valve1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.IDLE
        assert entity.device_actives == []

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "switch",
                    "turn_off",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                )
            ]
        )

        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": False},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 0
        assert nb_device_active_sensor.active_device_ids == []

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

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=climate1,
    ):
        entity: ThermostatOverClimate = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.underlying_entities[0].entity_id == "climate.climate1"

    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0

    nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(
        hass, "sensor.nb_device_active_for_boiler", "sensor"
    )
    assert nb_device_active_sensor is not None
    assert nb_device_active_sensor.state == 0
    assert nb_device_active_sensor.active_device_ids == []

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.device_actives == []

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await send_temperature_change_event(entity, 10, now)
        # we have to simulate the climate also else the test don't work
        climate1.set_hvac_mode(VThermHvacMode_HEAT)
        climate1.set_hvac_action(HVACAction.HEATING)
        climate1.async_write_ha_state()
        # Wait for state event propagation
        await hass.async_block_till_done()
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING
        assert entity.device_actives == ["climate.climate1"]

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "switch",
                    "turn_on",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                ),
            ]
        )
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": True},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON

        assert nb_device_active_sensor.state == 1
        assert nb_device_active_sensor.active_device_ids == [
            "climate.climate1",
        ]

    # 2. stop a climate
        # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event:
    # fmt: on

        await send_temperature_change_event(entity, 25, now)
        climate1.set_hvac_mode(VThermHvacMode_HEAT)
        climate1.set_hvac_action(HVACAction.IDLE)
        climate1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.IDLE
        assert entity.device_actives == []

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "switch",
                    "turn_off",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                )
            ]
        )

        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": False},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 0
        assert nb_device_active_sensor.active_device_ids == []

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_update_central_boiler_state_simple_climate_valve_regulation(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    # skip_hass_states_get,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavior with a climate with valve regulation"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(hass, "climate1", "theClimate1", hvac_mode=VThermHvacMode_OFF)
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
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [climate1.entity_id],
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
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    open_degree_entity = MockNumber(hass, "mock_opening_degree", "Opening degree")
    await register_mock_entity(hass, open_degree_entity, NUMBER_DOMAIN)
    open_degree_entity.set_native_value(0)
    await hass.async_block_till_done()

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    mock_get_state_side_effect = SideEffects(
        {
            open_degree_entity.entity_id: State(
                open_degree_entity.entity_id,
                open_degree_entity.state,
                {"min": 0, "max": 100},
            ),
            "number.mock_closing_degree": State(
                "number.mock_closing_degree", "0", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration": State(
                "number.mock_offset_calibration", "0", {"min": -12, "max": 12}
            ),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=climate1,
    ), patch(
        "homeassistant.core.StateMachine.get",
        side_effect=mock_get_state_side_effect.get_side_effects(),
    ):
        entity: ThermostatOverClimate = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.underlying_entities[0].entity_id == "climate.climate1"

        assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1
        assert api.central_boiler_manager.nb_active_device_for_boiler == 0

        nb_device_active_sensor: NbActiveDeviceForBoilerSensor = search_entity(
            hass, "sensor.nb_device_active_for_boiler", "sensor"
        )
        assert nb_device_active_sensor is not None
        assert nb_device_active_sensor.state == 0
        assert nb_device_active_sensor.active_device_ids == []

        # Force the VTherm to heat
        tz = get_tz(hass)  # pylint: disable=invalid-name
        now: datetime = datetime.now(tz=tz)
        entity._set_now(now)

        await send_temperature_change_event(entity, 30, now)
        await send_ext_temperature_change_event(entity, 30, now)
        await hass.async_block_till_done()

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        # the VTherm should not heat now
        assert entity.hvac_mode == VThermHvacMode_HEAT
        assert entity.hvac_action == HVACAction.OFF
        assert entity.activable_underlying_entities[0]._percent_open == 0
        assert entity.device_actives == []

        boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
            hass, "binary_sensor.central_boiler", "binary_sensor"
        )
        assert boiler_binary_sensor is not None
        assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate
    open_degree_entity.set_native_value(100)
    mock_get_state_side_effect = SideEffects(
        {
            open_degree_entity.entity_id: State(
                open_degree_entity.entity_id,
                open_degree_entity.state,
                {"min": 0, "max": 100},
            ),
            "number.mock_closing_degree": State(
                "number.mock_closing_degree", "0", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration": State(
                "number.mock_offset_calibration", "0", {"min": -12, "max": 12}
            ),
        },
        State("unknown.entity_id", "unknown"),
    )

    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event, \
        patch("homeassistant.core.StateMachine.get",side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on
        now = now + timedelta(minutes=1)
        entity._set_now(now)

        await send_temperature_change_event(entity, 10, now)
        # we have to simulate the climate also else the test don't work
        climate1.set_hvac_mode(VThermHvacMode_HEAT)
        climate1.set_hvac_action(HVACAction.HEATING)
        climate1.async_write_ha_state()
        open_degree_entity.set_native_value(100)
        # Wait for state event propagation
        await hass.async_block_till_done()
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING
        assert entity.device_actives == ["number.mock_opening_degree"]

        assert nb_device_active_sensor.state == 1
        assert nb_device_active_sensor.active_device_ids == [
            "number.mock_opening_degree",
        ]

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "switch",
                    "turn_on",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                ),
            ]
        )
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": True},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON



    # 2. stop a climate
    open_degree_entity.set_native_value(0)
    mock_get_state_side_effect = SideEffects(
        {
            open_degree_entity.entity_id: State(
                open_degree_entity.entity_id,
                open_degree_entity.state,
                {"min": 0, "max": 100},
            ),
            "number.mock_closing_degree": State(
                "number.mock_closing_degree", "0", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration": State(
                "number.mock_offset_calibration", "0", {"min": -12, "max": 12}
            ),
        },
        State("unknown.entity_id", "unknown"),
    )

    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("custom_components.versatile_thermostat.feature_central_boiler_manager.send_vtherm_event") as mock_send_event, \
        patch("homeassistant.core.StateMachine.get",side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on

        await send_temperature_change_event(entity, 25, now)
        climate1.set_hvac_mode(VThermHvacMode_HEAT)
        climate1.set_hvac_action(HVACAction.IDLE)
        climate1.async_write_ha_state()
        open_degree_entity.set_native_value(0)
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        # The underlying is idle but the valve are closed -> OFF
        assert entity.hvac_action == HVACAction.OFF
        assert entity.device_actives == []

        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "switch",
                    "turn_off",
                    service_data={},
                    target={"entity_id": "switch.pompe_chaudiere"},
                )
            ]
        )

        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": False},
                )
            ]
        )

        # really resend the event to trigger the boiler sensor
        hass.bus.fire(mock_send_event.mock_calls[0].kwargs["event_type"].value, mock_send_event.mock_calls[0].kwargs["data"])
        await hass.async_block_till_done()

        assert api.central_boiler_manager.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

        assert nb_device_active_sensor.state == 0
        assert nb_device_active_sensor.active_device_ids == []

    entity.remove_thermostat()


# @pytest.mark.skip(reason="This test don't work when execute in // of other tests. It should be run alone")
async def test_bug_339(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the counter of active Vtherm in central boiler is
    correctly updated with underlying is in auto and device is active
    """

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(
        hass=hass,
        unique_id="climate1",
        name="theClimate1",
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
            CONF_CLIMATE: climate1.entity_id,
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

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=climate1,
    ):
        entity: ThermostatOverValve = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.underlying_entities[0].entity_id == "climate.climate1"
        assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 1

    await entity.async_set_hvac_mode(VThermHvacMode_AUTO)
    # Simulate a state change in underelying
    await api.central_boiler_manager.nb_active_device_for_boiler_entity.calculate_nb_active_devices_or_power(None)

    # The VTherm should be active
    assert entity.underlying_entity(0).is_device_active is True
    assert entity.is_device_active is True
    assert api.central_boiler_manager.nb_active_device_for_boiler == 1

    entity.remove_thermostat()
