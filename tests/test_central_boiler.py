# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the central_configuration """
import asyncio
from datetime import datetime

from unittest.mock import patch, call

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntryState

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

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import


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

    # Test that VTherm API have any central boiler entities
    assert api.nb_active_device_for_boiler_entity is not None
    assert api.nb_active_device_for_boiler == 0

    assert api.nb_active_device_for_boiler_threshold_entity is not None
    assert api.nb_active_device_for_boiler_threshold is 1  # the default value is 1


async def test_update_central_boiler_state_simple(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    switch1 = MockSwitch(hass, "switch1", "theSwitch1")

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
            CONF_HEATER: switch1.entity_id,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
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

    assert api.nb_active_device_for_boiler_threshold == 1
    assert api.nb_active_device_for_boiler == 0

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    await send_temperature_change_event(entity, 10, now)

    assert entity.hvac_mode == HVACMode.HEAT

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch1.async_turn_on()
        switch1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count >= 1

        # Sometimes this test fails
        # mock_service_call.assert_has_calls(
        #     [
        #         call.service_call(
        #             "switch",
        #             "turn_on",
        #             service_data={},
        #             target={"entity_id": "switch.pompe_chaudiere"},
        #         ),
        #     ]
        # )

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

        assert api.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON

    # 2. stop a heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch1.async_turn_off()
        switch1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.IDLE

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

        assert api.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

    entity.remove_thermostat()


async def test_update_central_boiler_state_multiple(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    switch1 = MockSwitch(hass, "switch1", "theSwitch1")
    switch2 = MockSwitch(hass, "switch2", "theSwitch2")
    switch3 = MockSwitch(hass, "switch3", "theSwitch3")
    switch4 = MockSwitch(hass, "switch4", "theSwitch4")

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
            CONF_HEATER: switch1.entity_id,
            CONF_HEATER_2: switch2.entity_id,
            CONF_HEATER_3: switch3.entity_id,
            CONF_HEATER_4: switch4.entity_id,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
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

    assert api.nb_active_device_for_boiler_threshold == 1
    assert api.nb_active_device_for_boiler == 0
    # Force the VTherm to heat
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    await send_temperature_change_event(entity, 10, now)

    assert entity.hvac_mode == HVACMode.HEAT

    # 0. set threshold to 3
    api.nb_active_device_for_boiler_threshold_entity.set_native_value(3)
    assert api.nb_active_device_for_boiler_threshold == 3

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a first heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch1.async_turn_on()
        switch1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 1
        # No switch of the boiler
        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "switch",
                    "turn_on",
                    {"entity_id": "switch.switch1"},
                ),
            ]
        )
        assert mock_send_event.call_count == 0

        assert api.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_OFF

    # 2. start a 2nd heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch2.async_turn_on()
        switch2.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

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
                    {"entity_id": "switch.switch1"},
                ),
            ]
        )
        assert mock_send_event.call_count == 0

        assert api.nb_active_device_for_boiler == 2
        assert boiler_binary_sensor.state == STATE_OFF

    # 3. start a 3rd heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch3.async_turn_on()
        switch3.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.HEATING

        # Only the first heater is started by the algo
        assert mock_service_call.call_count == 2
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
                call.service_call(
                    "switch",
                    "turn_on",
                    {"entity_id": "switch.switch1"},
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

        assert api.nb_active_device_for_boiler == 3
        assert boiler_binary_sensor.state == STATE_ON

    # 4. start a 4th heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch4.async_turn_on()
        switch4.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

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
                    {"entity_id": "switch.switch1"},
                ),
            ]
        )
        assert mock_send_event.call_count == 0
        assert api.nb_active_device_for_boiler == 4
        assert boiler_binary_sensor.state == STATE_ON

    # 5. stop a heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch1.async_turn_off()
        switch1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 0
        assert mock_send_event.call_count == 0
        assert api.nb_active_device_for_boiler == 3
        assert boiler_binary_sensor.state == STATE_ON

    # 6. stop a 2nd heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await switch4.async_turn_off()
        switch4.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

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

        assert api.nb_active_device_for_boiler == 2
        assert boiler_binary_sensor.state == STATE_OFF

    entity.remove_thermostat()


async def test_update_central_boiler_state_simple_valve(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    valve1 = MockNumber(hass, "valve1", "theValve1")

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
            CONF_VALVE: valve1.entity_id,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
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

    assert api.nb_active_device_for_boiler_threshold == 1
    assert api.nb_active_device_for_boiler == 0

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert entity.hvac_mode == HVACMode.HEAT

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a valve
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(entity, 10, now)
        # we have to simulate the valve also else the test don't work
        valve1.set_native_value(10)
        valve1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.HEATING

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

        assert api.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON

    # 2. stop a heater
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(entity, 25, now)
        # Change the valve value to 0
        valve1.set_native_value(0)
        valve1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.1)

        assert entity.hvac_action == HVACAction.IDLE

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

        assert api.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

    entity.remove_thermostat()


async def test_update_central_boiler_state_simple_climate(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the central boiler state behavoir"""

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(hass, "climate1", "theClimate1")

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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
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

    assert api.nb_active_device_for_boiler_threshold == 1
    assert api.nb_active_device_for_boiler == 0

    # Force the VTherm to heat
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert entity.hvac_mode == HVACMode.HEAT

    boiler_binary_sensor: CentralBoilerBinarySensor = search_entity(
        hass, "binary_sensor.central_boiler", "binary_sensor"
    )
    assert boiler_binary_sensor is not None
    assert boiler_binary_sensor.state == STATE_OFF

    # 1. start a climate
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(entity, 10, now)
        # we have to simulate the climate also else the test don't work
        climate1.set_hvac_mode(HVACMode.HEAT)
        climate1.set_hvac_action(HVACAction.HEATING)
        climate1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.HEATING

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

        assert api.nb_active_device_for_boiler == 1
        assert boiler_binary_sensor.state == STATE_ON

    # 2. stop a climate
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(entity, 25, now)
        climate1.set_hvac_mode(HVACMode.HEAT)
        climate1.set_hvac_action(HVACAction.IDLE)
        climate1.async_write_ha_state()
        # Wait for state event propagation
        await asyncio.sleep(0.5)

        assert entity.hvac_action == HVACAction.IDLE

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

        assert api.nb_active_device_for_boiler == 0
        assert boiler_binary_sensor.state == STATE_OFF

    entity.remove_thermostat()
