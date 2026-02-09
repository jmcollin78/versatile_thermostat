# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from unittest.mock import patch, call
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import HVACAction

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.thermostat_valve import (
    ThermostatOverValve,
)
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_over_switch_full_start(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data=FULL_SWITCH_CONFIG,
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entity = await create_thermostat(hass, entry, "climate.theoverswitchmockname")

        assert entity
        assert isinstance(entity, ThermostatOverSwitch)

        assert entity.name == "TheOverSwitchMockName"
        assert entity.is_over_climate is False
        await wait_for_local_condition(lambda: entity.is_ready is True)

        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None
        assert entity.have_valve_regulation is False

        assert entity.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_OFF]

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ],
            # any_order=True,
        )

    entity.remove_thermostat()


async def test_over_climate_full_start(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG,
    )

    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_modes=[VThermHvacMode_HEAT, VThermHvacMode_OFF, VThermHvacMode_HEAT_COOL])

    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True

        await wait_for_local_condition(lambda: entity.is_ready is True)

        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNAVAILABLE
        assert entity.motion_state is STATE_UNAVAILABLE
        assert entity.presence_state is STATE_UNAVAILABLE
        assert entity.have_valve_regulation is False

        # hvac_modes comes from underlying entity + OFF. there is no AC mode in underlying entity
        assert entity.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_OFF, VThermHvacMode_COOL]

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ]
        )

    entity.remove_thermostat()


async def test_over_4switch_full_start(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_switch with 4 switches type"""

    for switch_id in ["mock_4switch0", "mock_4switch1", "mock_4switch2", "mock_4switch3"]:
        switch = MockSwitch(hass, switch_id, switch_id + "_name")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4SwitchMockName",
        unique_id="uniqueId",
        data=FULL_4SWITCH_CONFIG,
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entity = await create_thermostat(hass, entry, "climate.theover4switchmockname")

        assert entity

        assert entity.name == "TheOver4SwitchMockName"
        assert entity.is_over_switch
        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None

        assert entity.nb_underlying_entities == 4

        # Checks that we have the 4 UnderlyingEntity correctly configured
        for idx in range(4):
            under = entity.underlying_entity(idx)
            assert under is not None
            assert isinstance(under, UnderlyingSwitch)
            assert under.entity_id == "switch.mock_4switch" + str(idx)
            assert under.initial_delay_sec == 8 * 60 / 4 * idx

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ]
        )

    entity.remove_thermostat()


async def test_over_switch_deactivate_preset(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "frost_temp": 0,
            "eco_temp": 17,
            "comfort_temp": 0,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_SAFETY_DELAY_MIN: 10,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert isinstance(entity, ThermostatOverSwitch)

    assert entity.preset_modes == [
        VThermPreset.NONE,
        # VThermPreset.FROST,
        VThermPreset.ECO,
        # VThermPreset.COMFORT,
        VThermPreset.BOOST,
    ]
    assert entity.preset_mode is VThermPreset.NONE

    # try to set the COMFORT Preset which is absent
    try:
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
    except ValueError as err:
        print(err)
    else:
        assert False
    finally:
        assert entity.preset_mode is VThermPreset.NONE

    entity.remove_thermostat()


async def test_over_climate_deactivate_preset(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_climate type with deactivated presets and COOL only hvac mode"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 0,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_SAFETY_DELAY_MIN: 10,
            CONF_AC_MODE: True,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.preset_modes == [
        VThermPreset.NONE,
        VThermPreset.FROST,
        VThermPreset.ECO,
        # VThermPreset.COMFORT,
        VThermPreset.BOOST,
    ]

    # create the underlying climate with COOL only hvac mode
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[HVACMode.COOL],
    )
    await hass.async_block_till_done()

    assert entity.preset_modes == [
        VThermPreset.NONE,
        # VThermPreset.FROST,
        VThermPreset.ECO,
        # VThermPreset.COMFORT,
        VThermPreset.BOOST,
    ]
    assert entity.preset_mode is VThermPreset.NONE

    # try to set the COMFORT Preset which is absent
    try:
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
    except ValueError as err:
        print(err)
    else:
        assert False
    finally:
        assert entity.preset_mode is VThermPreset.NONE

    entity.remove_thermostat()


async def test_over_switch_start_heating(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Test that a thermostat over switch starts heating and turns on the switch"""

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
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 19,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 60,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert isinstance(entity, ThermostatOverSwitch)

    # Check that VTherm is OFF at startup
    assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
    assert entity.hvac_action is HVACAction.OFF
    assert fake_underlying_switch.is_on is False

    # Enable heating mode
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Set a target temperature and send a low current temperature
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.target_temperature == 21

    # Send a low temperature to trigger heating
    await send_temperature_change_event(entity, 15, datetime.now())
    await hass.async_block_till_done()

    # Wait for the switch to turn on
    # The TPI algorithm will calculate an on_percent and start the cycle
    # With a temperature of 15° and a target of 21°, the delta is 6°
    # The on_percent should be close to 1 (100%)
    await wait_for_local_condition(lambda: fake_underlying_switch.is_on is True)

    # Check that the underlying switch is turned on
    assert fake_underlying_switch.is_on is True, "The switch should be on after heating starts"
    assert entity.hvac_action is HVACAction.HEATING

    entity.remove_thermostat()


async def test_over_climate_start_heating(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_climate: MockClimate):
    """Test that a thermostat over climate starts heating and sends hvac_mode and target_temperature to underlying climate"""

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
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 19,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_SAFETY_DELAY_MIN: 60,
            CONF_AC_MODE: False,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    # Check that VTherm is OFF at startup
    assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
    assert entity.hvac_action is HVACAction.OFF
    assert fake_underlying_climate.hvac_mode == VThermHvacMode_OFF

    # Enable heating mode
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Set a target temperature and send a low current temperature
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.target_temperature == 21

    # Send a low temperature to trigger heating
    await send_temperature_change_event(entity, 15, datetime.now())
    await hass.async_block_till_done()

    # Wait for the underlying climate to receive the hvac_mode
    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_mode == VThermHvacMode_HEAT)

    # Check that the underlying climate has received the correct hvac_mode
    assert fake_underlying_climate.hvac_mode == VThermHvacMode_HEAT, "The underlying climate should be in HEAT mode"

    # Check that the underlying climate has received the correct target_temperature
    assert fake_underlying_climate.target_temperature == 21, "The underlying climate should have target_temperature = 21"

    # MockClimate now automatically calculates hvac_action based on hvac_mode and temperatures
    # Since hvac_mode=HEAT and target_temperature (21) > current_temperature (15), hvac_action should be HEATING
    await hass.async_block_till_done()

    # Wait for VTherm to update its hvac_action
    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.HEATING)

    # Check that VTherm hvac_action is HEATING
    assert entity.hvac_action is HVACAction.HEATING, "VTherm should be in HEATING action"

    entity.remove_thermostat()


async def test_over_valve_start_heating(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_valve: MockNumber):  # pylint: disable=unused-argument
    """Test that when VTherm over_valve starts heating, the underlying number entity receives the valve_open_percent value"""

    # Create the entry for a thermostat_over_valve type VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueIdValve",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_UNDERLYING_LIST: ["number.mock_valve"],
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            VThermPreset.FROST + PRESET_TEMP_SUFFIX: 7,
            VThermPreset.ECO + PRESET_TEMP_SUFFIX: 17,
            VThermPreset.COMFORT + PRESET_TEMP_SUFFIX: 19,
            VThermPreset.BOOST + PRESET_TEMP_SUFFIX: 21,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_AC_MODE: False,
        },
    )

    # Create the VTherm entity
    entity: ThermostatOverValve = await create_thermostat(hass, entry, "climate.theovervalvemockname")

    assert entity
    assert isinstance(entity, ThermostatOverValve)
    assert entity.is_over_valve is True

    # Initially, the VTherm should be OFF with hvac_action OFF
    assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
    assert entity.hvac_action is HVACAction.OFF

    assert fake_underlying_valve.native_value == 0, "The underlying number entity should have received valve_open_percent = 0"

    # Set the VTherm to HEAT mode with BOOST preset
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    # Check that the VTherm is now in HEAT mode
    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 21

    # Send a temperature event to trigger heating (current temp < target temp)
    await send_temperature_change_event(entity, 15, datetime.now())
    await hass.async_block_till_done()

    # Wait for the VTherm to activate heating and send valve_open_percent to the underlying number entity
    # The valve should open (native_value > 0) when the VTherm activates heating
    await wait_for_local_condition(lambda: fake_underlying_valve.native_value > 0)

    # Check that the underlying valve has received a non-zero valve_open_percent
    assert fake_underlying_valve.native_value == 100, "The underlying number entity should have received valve_open_percent > 0"

    # Check that VTherm hvac_action is HEATING
    assert entity.hvac_action is HVACAction.HEATING, "VTherm should be in HEATING action"

    entity.remove_thermostat()
