# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the Window management """
import asyncio

from unittest.mock import patch, call, PropertyMock
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

        assert mock_service_call.call_count >= 1
        assert entity.is_device_active is True

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
        assert mock_service_call.call_count >= 1

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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
    await send_climate_change_event(vtherm, STATE_UNAVAILABLE, HVACMode.OFF, HVACAction.OFF, HVACAction.OFF, now, True, fake_underlying_climate.entity_id)
    await hass.async_block_till_done()

    # no changes cause underlying state is not known
    assert vtherm.hvac_mode == HVACMode.OFF
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_OFF

    # 2 underlying comes back to life
    now += timedelta(minutes=10)
    vtherm._set_now(now)
    await fake_underlying_climate.async_set_hvac_mode(HVACMode.HEAT)

    await send_climate_change_event(vtherm, HVACMode.HEAT, STATE_UNAVAILABLE, HVACAction.OFF, HVACAction.OFF, now, True, fake_underlying_climate.entity_id)
    await hass.async_block_till_done()

    # No changes on hvac_mode (but only on temperature or hvac_action)
    assert vtherm.hvac_mode == HVACMode.OFF
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_OFF


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
