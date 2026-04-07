# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the Window management """
import asyncio

from unittest.mock import patch, call, PropertyMock, MagicMock, AsyncMock
from datetime import datetime, timedelta

import logging

from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import SERVICE_SET_TEMPERATURE, SERVICE_SET_HVAC_MODE
from custom_components.versatile_thermostat.switch import (
    FollowUnderlyingTemperatureChange,
)

from custom_components.versatile_thermostat.config_flow import (
    VersatileThermostatBaseConfigFlow,
)
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)

from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler

from .commons import *


logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_63(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the safety_default_on_percent to 0"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.0,  # !! here
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.0,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    assert entity.safety_manager.safety_min_on_percent == 0
    assert entity.safety_manager.safety_default_on_percent == 0


# Waiting for answer in https://github.com/jmcollin78/versatile_thermostat/issues/64
# Repro case not evident
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_64(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the safety_default_on_percent to 0"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_272(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it not possible to set the target temperature under the min_temp setting"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # default value are min 15°, max 30°, step 0.1
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    # Min_temp is 15 and max_temp is 19
    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=VThermHvacMode_HEAT, min_temp=15.0, max_temp=19)

    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        # The VTherm value and not the underlying value
        assert entity.target_temperature_step == 0.1
        assert entity.target_temperature == entity.min_temp
        assert entity.is_regulated is True

        # Set the hvac_mode to HEAT
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)

        # In the accepted interval
        await entity.async_set_temperature(temperature=17.5)

        # MagicMock climate is already HEAT by default. So there is no SET_HAVC_MODE call
        assert mock_service_call.call_count > 1

        mock_service_call.assert_has_calls(
            [
                call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 17.5,
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                    False,
                    None,
                    None,
                    False,
                ),
            ]
        )

        # #1654 - the call is not done because the initial state of under is already HEAT
        assert not any(
            c
            == call(
                "climate",
                SERVICE_SET_HVAC_MODE,
                {"entity_id": "climate.mock_climate", "hvac_mode": VThermHvacMode_HEAT},
                False,
                None,
                None,
                False
            )
            for c in mock_service_call.call_args_list
        )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    event_timestamp: datetime = datetime.now(tz=tz)
    entity._set_now(now)

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        # Set room temperature to something very cold
        await send_temperature_change_event(entity, 13, now)
        await send_ext_temperature_change_event(entity, 9, now)

        event_timestamp = event_timestamp + timedelta(minutes=3)
        entity._set_now(event_timestamp)

        # Not in the accepted interval (15-19)
        await entity.async_set_temperature(temperature=10)
        # set temp recalculate now
        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 15,  # the minimum acceptable
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                    False,
                    None,
                    None,
                    False
                ),
            ]
        )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        # Set room temperature to something very cold
        event_timestamp = event_timestamp + timedelta(minutes=1)
        entity._set_now(event_timestamp)

        await send_temperature_change_event(entity, 13, event_timestamp)
        await send_ext_temperature_change_event(entity, 9, event_timestamp)

        # In the accepted interval
        event_timestamp = event_timestamp + timedelta(minutes=3)
        entity._set_now(event_timestamp)
        await entity.async_set_temperature(temperature=20.8)
        assert mock_service_call.call_count >= 1
        mock_service_call.assert_has_calls(
            [
                call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 19,  # the maximum acceptable
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                    False,
                    None,
                    None,
                    False
                ),
            ]
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_407(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager
):
    """Test the followin case in power management:
    1. a heater is active (heating). So the power consumption takes the heater power into account. We suppose the power consumption is near the threshold,
    2. the user switch preset let's say from Comfort to Boost,
    3. expected: no shredding should occur because the heater was already active,
    4. constated: the heater goes into shredding.

    """

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    switch = MockSwitch(hass, "mock_switch", "theSwitch1")
    await register_mock_entity(hass, switch, SWITCH_DOMAIN)

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    await send_temperature_change_event(entity, 16, now)
    await send_ext_temperature_change_event(entity, 10, now)

    # 1. An already active heater will not switch to overpowering
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 100),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 110),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "homeassistant.core.StateMachine.get",
        side_effect=side_effects.get_side_effects(),
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN
        assert entity.target_temperature == 18
        # waits that the heater starts
        await hass.async_block_till_done()

        # Send power max mesurement
        await send_max_power_change_event(entity, 110, now)
        # Send power mesurement (theheater is already in the power measurement)
        await send_power_change_event(entity, 100, now)
        # No overpowering yet
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.is_device_active is True

    # 2. An already active heater that switch preset will not switch to overpowering
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "homeassistant.core.StateMachine.get",
        side_effect=side_effects.get_side_effects(),
    ):
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        # change preset to Boost
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        # waits that the heater starts
        await asyncio.sleep(0.1)
        # doesn't work for call_later
        # await hass.async_block_till_done()

        # simulate a refresh for central power (not necessary)
        await do_central_power_refresh(hass)

        assert entity.power_manager.is_overpowering_detected is False
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

    # 3. Evenif heater is stopped (is_device_active==False) and power is over max, then overpowering should be started
    # due to check before start heating
    side_effects.add_or_update_side_effect("sensor.the_power_sensor", State("sensor.the_power_sensor", 150))
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.core.StateMachine.get",
        side_effect=side_effects.get_side_effects(),
    ):
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        # change preset to Comfort
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        # waits the eventual heater starts
        await asyncio.sleep(0.1)

        # simulate a refresh for central power (not necessary because it is checked before start)
        # await do_central_power_refresh(hass)

        assert entity.power_manager.is_overpowering_detected is True
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode is VThermPreset.POWER
        assert entity.power_manager.overpowering_state is STATE_ON


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_500_1(hass: HomeAssistant, init_vtherm_api) -> None:
    """Test that the form is served with no input"""

    config = {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_USE_WINDOW_CENTRAL_CONFIG: True,
        CONF_USE_POWER_CENTRAL_CONFIG: True,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
        CONF_USE_MOTION_FEATURE: True,
        CONF_MOTION_SENSOR: "sensor.theMotionSensor",
    }

    flow = VersatileThermostatBaseConfigFlow(config)

    assert flow._infos[CONF_USE_WINDOW_FEATURE] is False
    assert flow._infos[CONF_USE_POWER_FEATURE] is False
    assert flow._infos[CONF_USE_PRESENCE_FEATURE] is False
    # we have a motion sensor configured
    assert flow._infos[CONF_USE_MOTION_FEATURE] is True


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_500_2(hass: HomeAssistant, init_vtherm_api) -> None:
    """Test that the form is served with no input"""

    config = {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_FEATURE: False,
    }

    flow = VersatileThermostatBaseConfigFlow(config)

    assert flow._infos[CONF_USE_WINDOW_FEATURE] is False
    assert flow._infos[CONF_USE_POWER_FEATURE] is False
    assert flow._infos[CONF_USE_PRESENCE_FEATURE] is False
    assert flow._infos[CONF_USE_MOTION_FEATURE] is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_500_3(hass: HomeAssistant, init_vtherm_api) -> None:
    """Test that the form is served with no input"""

    config = {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_WINDOW_SENSOR: "sensor.theWindowSensor",
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_PRESENCE_SENSOR: "sensor.thePresenceSensor",
        CONF_USE_MOTION_FEATURE: True,  # motion sensor need to be checked AND a motion sensor set
        CONF_MOTION_SENSOR: "sensor.theMotionSensor",
    }

    flow = VersatileThermostatBaseConfigFlow(config)

    assert flow._infos[CONF_USE_WINDOW_FEATURE] is True
    assert flow._infos[CONF_USE_POWER_FEATURE] is False
    assert flow._infos[CONF_USE_PRESENCE_FEATURE] is True
    assert flow._infos[CONF_USE_MOTION_FEATURE] is True


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_465(hass: HomeAssistant, skip_hass_states_is_state):
    """Test store and restore hvac_mode on toggle hvac state"""

    # vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
        "eco_ac": 27.0,
        "comfort_ac": 25.0,
        "boost_ac": 23.0,
        "frost_away": 7.1,
        "eco_away": 17.1,
        "comfort_away": 19.1,
        "boost_away": 21.1,
        "eco_ac_away": 27.1,
        "comfort_ac_away": 25.1,
        "boost_ac_away": 23.1,
    }

    # 0. initialisation

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
            CONF_WINDOW_DELAY: 1,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass, "mock_climate", "MockClimateName", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT, VThermHvacMode_FAN_ONLY]
    )

    vtherm: ThermostatOverClimate = await create_thermostat(hass, config_entry, "climate.overclimate", temps)
    assert vtherm is not None

    now: datetime = datetime.now(tz=get_tz(hass))

    # 1. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, datetime.now())
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 21.0

    # 2. Toggle the VTherm state
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_OFF

    # 3. (re)Toggle the VTherm state
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_HEAT

    # 4. Toggle from COOL
    await vtherm.async_set_hvac_mode(VThermHvacMode_COOL)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 23.0

    # 5. Toggle the VTherm state
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_OFF

    # 6. (re)Toggle the VTherm state
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_COOL

    ###
    # Same test with an open window and initial state is COOL
    #
    # 7. open the window
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_window_condition = await send_window_change_event(
            vtherm, True, False, now, False
        )
        await try_window_condition(None)
        await hass.async_block_till_done()

    assert vtherm.window_state is STATE_ON
    assert vtherm.hvac_mode == VThermHvacMode_OFF
    assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION

    # 8. call toggle -> we should stay in OFF (command is ignored)
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_OFF
    assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION

    # 9. Close the window (we should come back to Cool this time)
    now = now + timedelta(minutes=2)
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_window_condition = await send_window_change_event(
            vtherm, False, True, now, False
        )
        await try_window_condition(None)
        await hass.async_block_till_done()

    assert vtherm.window_state is STATE_OFF
    assert vtherm.hvac_mode == VThermHvacMode_COOL

    # 9. call toggle -> we should come back in OFF
    await vtherm.async_toggle()
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_OFF


@pytest.mark.skip(reason="Disabled because it fails but works step by step")
async def test_bug_1220(hass: HomeAssistant, skip_hass_states_is_state):
    """Test VThermHvac_mode when underlying is unavailable"""

    # vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
        "eco_ac": 27.0,
        "comfort_ac": 25.0,
        "boost_ac": 23.0,
        "frost_away": 7.1,
        "eco_away": 17.1,
        "comfort_away": 19.1,
        "boost_away": 21.1,
        "eco_ac_away": 27.1,
        "comfort_ac_away": 25.1,
        "boost_ac_away": 23.1,
    }

    # 0. initialisation
    fake_underlying_climate = await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_mode=VThermHvacMode_COOL,
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT, VThermHvacMode_FAN_ONLY],
    )

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
            CONF_WINDOW_DELAY: 1,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    vtherm: ThermostatOverClimate = await create_thermostat(hass, config_entry, "climate.overclimate")
    assert vtherm is not None
    vtherm._set_now(now)

    # 1. turns follow on and change state to UNAVAILABLE
    assert vtherm.hvac_mode == VThermHvacMode_OFF

    follow_entity: FollowUnderlyingTemperatureChange = search_entity(
        hass,
        "switch.overclimate_follow_underlying_temp_change",
        SWITCH_DOMAIN,
    )

    assert follow_entity is not None
    assert follow_entity.state is STATE_OFF

    follow_entity.turn_on()

    assert vtherm.follow_underlying_temp_change is True
    assert follow_entity.state is STATE_ON

    now += timedelta(minutes=10)
    vtherm._set_now(now)
    await fake_underlying_climate.async_set_hvac_mode(STATE_UNAVAILABLE)

    await wait_for_local_condition(lambda: vtherm._underlyings[0].state_manager.get_state("climate.mock_climate").state == STATE_UNAVAILABLE, timeout=1)

    # no changes cause underlying state is not known
    assert vtherm.hvac_mode == HVACMode.OFF
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_OFF

    # 2 underlying comes back to life
    now += timedelta(minutes=10)
    vtherm._set_now(now)
    await fake_underlying_climate.async_set_hvac_mode(HVACMode.HEAT)
    await asyncio.sleep(0.1)
    # await hass.async_block_till_done()

    await wait_for_local_condition(lambda: vtherm._underlyings[0].state_manager.get_state("climate.mock_climate").state == HVACMode.HEAT, timeout=10)

    # Hvac_mode should HEAT now
    await wait_for_local_condition(lambda: vtherm.hvac_mode == HVACMode.HEAT, timeout=10)
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT

    vtherm.remove_thermostat()


async def test_bug_1379(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that switching from preset mode to no preset mode conserve the last target temperature set manually"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # default value are min 15°, max 30°, step 0.1
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    # Min_temp is 15 and max_temp is 19
    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, min_temp=15.0, max_temp=19.0)

    # fmt:off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"):
    # fmt:on
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # 1. Set a manual temperature first (no preset)
    await entity.async_set_temperature(temperature=17.5)

    # check that the requested temperature is set
    assert entity.target_temperature == 17.5
    assert entity.requested_state.target_temperature == 17.5

    # 2. Set preset to Comfort
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    assert entity.preset_mode == VThermPreset.COMFORT
    # target temperature should be the comfort temperature
    assert entity.target_temperature == 19
    assert entity.requested_state.target_temperature == 17.5
    assert entity.current_state.target_temperature == 19

    # 3. set back to manual mode (no preset)
    await entity.async_set_preset_mode(VThermPreset.NONE)
    assert entity.preset_mode == VThermPreset.NONE
    # target temperature should be the last manual temperature
    assert entity.target_temperature == 17.5
    assert entity.requested_state.target_temperature == 17.5
    assert entity.current_state.target_temperature == 17.5

    entity.remove_thermostat()


@patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
async def test_bug_1777(mock_call_later, hass):
    """Test that cycle correctly handles on_percent transitions (bug 1777).

    When start_cycle is called while a cycle is running (force=False), it
    should only update stored params without restarting. At the next cycle end,
    the updated params are used.
    """
    mock_cancel = MagicMock()
    mock_call_later.return_value = mock_cancel

    fake_thermostat = MagicMock()
    fake_thermostat.incremente_energy = MagicMock()
    fake_thermostat.minimal_activation_delay = 0
    fake_thermostat.minimal_deactivation_delay = 0

    under = MagicMock()
    async def turn_on_side_effect():
        under.is_device_active = True

    async def turn_off_side_effect():
        under.is_device_active = False

    under.turn_on = AsyncMock(side_effect=turn_on_side_effect)
    under.turn_off = AsyncMock(side_effect=turn_off_side_effect)
    under.is_device_active = False
    under._should_be_on = False
    under._on_time_sec = 0
    under._off_time_sec = 0
    under._hvac_mode = None
    under.last_change = None

    scheduler = CycleScheduler(hass, fake_thermostat, [under], 100)

    # 1. No cycle running: start_cycle with non-zero on_percent starts fresh
    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.9, False)

    assert under._should_be_on is True
    assert under._on_time_sec == 90
    assert under._off_time_sec == 10
    assert scheduler._current_on_time_sec == 90
    assert scheduler._current_off_time_sec == 10

    assert under.turn_on.await_count == 1   # turned on immediately (single underlying, offset=0)
    assert under.turn_off.await_count == 0
    assert mock_call_later.call_count == 2  # turn_off at 90s + cycle_end at 100s
    assert scheduler.is_cycle_running is True

    # 2. Cycle already running with on_time>0: update params but don't restart
    under.turn_on.reset_mock()
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()

    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.8, False)

    assert under._should_be_on is True
    assert under._on_time_sec == 90          # unchanged on underlying
    assert under._off_time_sec == 10         # unchanged on underlying
    assert scheduler._current_on_time_sec == 80   # updated in scheduler
    assert scheduler._current_off_time_sec == 20  # updated in scheduler

    assert under.turn_on.await_count == 0
    assert under.turn_off.await_count == 0
    assert mock_call_later.call_count == 0   # no new scheduling
    assert scheduler.is_cycle_running is True

    # 3. Simulate master cycle end: restarts using updated params (80/20)
    under.turn_on.reset_mock()
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()

    await scheduler._on_master_cycle_end(None)

    assert under._should_be_on is True
    assert under._on_time_sec == 80          # updated to new values
    assert under._off_time_sec == 20
    assert scheduler._current_on_time_sec == 80
    assert scheduler._current_off_time_sec == 20

    assert under.turn_on.await_count == 0    # device already ON, no redundant turn_on
    assert under.turn_off.await_count == 0   # no turn_off at cycle end
    assert mock_call_later.call_count == 2   # next_tick + cycle_end
    assert fake_thermostat.incremente_energy.call_count == 1

    # 4. Cycle running with on_time>0: update params to 0 (no restart)
    under.turn_on.reset_mock()
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()
    fake_thermostat.incremente_energy.reset_mock()

    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.0, False)

    assert under._should_be_on is True       # unchanged (cycle still running)
    assert under._on_time_sec == 80          # unchanged on underlying
    assert under._off_time_sec == 20         # unchanged on underlying
    assert scheduler._current_on_time_sec == 0    # updated in scheduler
    assert scheduler._current_off_time_sec == 100  # updated in scheduler

    assert under.turn_on.await_count == 0
    assert under.turn_off.await_count == 0
    assert mock_call_later.call_count == 0   # no new scheduling
    assert scheduler.is_cycle_running is True

    # 5. Simulate master cycle end: device turns OFF (on_time=0)
    under.turn_on.reset_mock()
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()
    under.is_device_active = True            # device currently on
    await scheduler._on_master_cycle_end(None)

    assert under._should_be_on is False      # device should be off
    assert under._on_time_sec == 0
    assert under._off_time_sec == 100
    assert scheduler._current_on_time_sec == 0
    assert scheduler._current_off_time_sec == 100

    assert under.turn_on.await_count == 0
    # turn_off called once at cycle end cleanup. Redundant tick off is skipped by True Tick!
    assert under.turn_off.await_count == 1
    assert mock_call_later.call_count == 1   # only cycle_end scheduled (on_time=0)
    assert fake_thermostat.incremente_energy.call_count == 1


@patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
async def test_bug_1921_keep_active_cycle_when_next_repeat_becomes_zero(mock_call_later, hass):
    """A pending 0% next cycle must not cancel an already-running physical cycle."""
    mock_cancel = MagicMock()
    mock_call_later.return_value = mock_cancel

    fake_thermostat = MagicMock()
    fake_thermostat.incremente_energy = MagicMock()
    fake_thermostat.minimal_activation_delay = 480
    fake_thermostat.minimal_deactivation_delay = 480

    under = MagicMock()

    async def turn_on_side_effect():
        under.is_device_active = True

    async def turn_off_side_effect():
        under.is_device_active = False

    under.turn_on = AsyncMock(side_effect=turn_on_side_effect)
    under.turn_off = AsyncMock(side_effect=turn_off_side_effect)
    under.is_device_active = False
    under._should_be_on = False
    under._on_time_sec = 0
    under._off_time_sec = 0
    under._hvac_mode = None
    under.last_change = None

    scheduler = CycleScheduler(
        hass,
        fake_thermostat,
        [under],
        1800,
        min_activation_delay=480,
        min_deactivation_delay=480,
    )

    # 1. Start a real running cycle (0.28 * 1800 = 504s).
    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.28, False)

    assert under.is_device_active is True
    assert scheduler._active_on_time_sec == 504
    assert scheduler._current_on_time_sec == 504

    # 2. A temperature update lowers the next repeat below min_on.
    # 0.26 * 1800 = 468s, so timing constraints clamp the next repeat to 0s.
    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.26, False)

    assert under.is_device_active is True
    assert scheduler._active_on_time_sec == 504
    assert scheduler._current_on_time_sec == 0

    # 3. Another update before the current cycle ends must still preserve
    # the active 504s cycle. Before the fix, this second call replaced the
    # cycle because _current_on_time_sec was already 0.
    under.turn_on.reset_mock()
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()

    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.26, False)

    assert under.is_device_active is True
    assert scheduler._active_on_time_sec == 504
    assert scheduler._current_on_time_sec == 0
    assert under.turn_on.await_count == 0
    assert under.turn_off.await_count == 0
    assert mock_call_later.call_count == 0

    # 4. The pending 0% value must only apply when the master cycle ends.
    under.turn_off.reset_mock()
    mock_call_later.reset_mock()
    await scheduler._on_master_cycle_end(None)

    assert under.is_device_active is False
    assert scheduler._active_on_time_sec == 0
    assert scheduler._current_on_time_sec == 0
    assert under.turn_off.await_count == 1
    assert fake_thermostat.incremente_energy.call_count == 1


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_activity_preset_temperature_change(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """Test that changing the temperature of a preset used by activity
    updates the current target temperature.

    Bug: when VTherm is in activity preset, the motion manager delegates to a
    sub-preset (e.g. comfort or boost). If the user changes the temperature of
    that sub-preset via set_preset_temperature, the condition
    `preset.startswith(self.preset_mode)` evaluates to False because
    preset_mode == 'activity' and preset == 'comfort', so the current target
    temperature is never updated.
    """

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,  # important to not be obliged to wait
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. Start heating in activity mode. No motion detected -> no_motion_preset = comfort -> 18°
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # no motion detected -> using no_motion_preset = comfort = 18
        assert entity.target_temperature == 18

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

    # 2. Now change the comfort preset temperature (the active sub-preset of activity)
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"):
        await entity.set_preset_temperature("comfort", temperature=20.0)
        # Wait for async jobs
        await hass.async_block_till_done()
        await asyncio.sleep(0.1)

        # The target temperature should now reflect the new comfort temp
        assert entity._presets["comfort"] == 20.0
        assert entity.target_temperature == 20.0  # <-- This is the bug: stays at 18

    # 3. Also test with motion detected -> boost sub-preset
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ), patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, True, False, event_timestamp)
        assert entity.target_temperature == 19  # boost temp

        # Change boost preset temperature while motion is active
        await entity.set_preset_temperature("boost", temperature=22.0)
        await hass.async_block_till_done()
        await asyncio.sleep(0.1)

        assert entity._presets["boost"] == 22.0
        assert entity.target_temperature == 22.0  # <-- Same bug for boost sub-preset


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_1884(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):
    """Test that an underlying switch which was ON before HA restart is not
    spuriously turned off when the temperature sensor is unavailable at startup.

    Scenario:
    1. Before HA restart: VTherm was in HEAT mode and the switch was ON (heating).
    2. HA restarts: the temperature sensor is unavailable.
    3. VTherm starts with the restored HEAT/COMFORT state.
    4. Bug: on_percent=0 (no temperature data) causes turn_off on the active switch.
    5. Temperature becomes available.
    6. Bug: switch is turned back ON → unwanted OFF/ON cycle damages sensitive equipment.
    """
    now = datetime.now(tz=get_tz(hass))

    # Pre-condition: switch was ON before HA restart
    hass.states.async_set("switch.mock_switch", STATE_ON)
    # Temperature sensor is unavailable at startup (HA restart scenario)
    hass.states.async_set("sensor.mock_temp_sensor", STATE_UNAVAILABLE)
    # External temperature sensor is available
    hass.states.async_set("sensor.mock_ext_temp_sensor", "10.0")
    await hass.async_block_till_done()

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
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 60,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_DEVICE_POWER: 200,
        },
    )

    # Simulate a previously saved thermostat state: HEAT mode with COMFORT preset
    # Use MagicMock so that .state holds an HVACMode enum instance (not a plain string),
    # which is required for from_ha_hvac_mode() to resolve the mode correctly.
    mock_previous_state = MagicMock()
    mock_previous_state.state = HVACMode.HEAT
    mock_previous_state.attributes = {
        "preset_mode": VThermPreset.COMFORT,
        "temperature": 19.0,
    }

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=mock_previous_state,
    ), patch(
        "custom_components.versatile_thermostat.cycle_scheduler.async_call_later",
        return_value=MagicMock(),
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off",
        new_callable=AsyncMock,
    ) as mock_turn_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_turn_on:
        entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
        assert entity
        await wait_for_local_condition(lambda: entity.is_ready is True)
        await hass.async_block_till_done()

        # VTherm should have restored HEAT mode from previous state
        assert entity.hvac_mode == VThermHvacMode_HEAT

        # --- Bug 1884 evidence ---
        # At startup, temp is unavailable → on_percent=0 → turn_off is called
        # on the active switch. This assertion FAILS with the current bug.
        assert mock_turn_off.call_count == 0, (
            f"Bug 1884: underlying switch was spuriously turned off " f"{mock_turn_off.call_count} time(s) during startup when the " "temperature sensor was unavailable"
        )

        # Now the temperature sensor becomes available (temp=18, target=19 → heating needed)
        mock_turn_off.reset_mock()
        mock_turn_on.reset_mock()

        await send_temperature_change_event(entity, 18.0, now)
        await hass.async_block_till_done()

        # The key fix: no spurious OFF/ON cycle should have occurred.
        # After temperature arrives, the cycle scheduler takes over.
        # Since the device was already active and target_is_on=True, the
        # scheduler correctly keeps it on without an explicit turn_on call.
        assert mock_turn_off.call_count == 0, "Bug 1884: spurious turn_off after temperature became available"
        # Confirm that the thermostat is now in a proper heating state
        assert entity.hvac_mode == VThermHvacMode_HEAT
        assert entity.on_percent is not None, "on_percent should be a float once temperature is available"
        assert entity.on_percent > 0, f"on_percent should be > 0 (temp=18 < target=19), got {entity.on_percent}"

    entity.remove_thermostat()
