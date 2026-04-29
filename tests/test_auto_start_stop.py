# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable, too-many-lines

""" Test the Auto Start Stop algorithm management """
from datetime import datetime, timedelta
import logging
from unittest.mock import patch, call

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.auto_start_stop_algorithm import (
    AutoStartStopDetectionAlgorithm,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_auto_start_stop_algo_slow_heat_off(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_SLOW, "testu"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert algo._dt == 30
    assert algo._vtherm_name == "testu"

    # 1. should not stop (accumulated_error too low)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
        now=now,
    )
    assert ret is False
    assert algo.accumulated_error == -1
    assert algo.last_switch_date is None

    # 2. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=5)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert ret is False
    assert algo.accumulated_error == -6
    assert algo.last_switch_date is None

    # 3. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=2)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -8
    assert ret is False
    assert algo.last_switch_date is None

    # 4 .No change on accumulated error because the new measure is too near the last one
    now = now + timedelta(seconds=11)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -8
    assert ret is False
    assert algo.last_switch_date is None

    # 5. should stop now because accumulated_error is > ERROR_THRESHOLD for slow (10)
    now = now + timedelta(minutes=4)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -10
    assert ret is True
    assert algo.last_switch_date is not None
    assert algo.last_switch_date == now
    last_now = now

    # 6. inverse the temperature (target > current) -> accumulated_error should be divided by 2
    now = now + timedelta(minutes=2)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=22,
        current_temp=21,
        slope_min=-0.1,
        now=now,
    )
    assert algo.accumulated_error == -4  # -10/2 + 1
    assert ret is True
    assert algo.last_switch_date == last_now

    # 7. change level to slow (no real change) -> error_accumulated should not reset to 0
    algo.set_level(AUTO_START_STOP_LEVEL_SLOW)
    assert algo.accumulated_error == -4
    assert algo.last_switch_date == last_now

    # 8. change level -> error_accumulated should reset to 0
    algo.set_level(AUTO_START_STOP_LEVEL_FAST)
    assert algo.accumulated_error == 0
    assert algo.last_switch_date == last_now


async def test_auto_start_stop_too_fast_change(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_SLOW, "testu"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert algo._dt == 30
    assert algo._vtherm_name == "testu"

    #
    # Testing with turn_on
    #

    # 1. should stop
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=10,
        current_temp=21,
        slope_min=0.5,
        now=now,
    )

    assert ret is True
    assert algo.last_switch_date is not None
    assert algo.last_switch_date == now
    last_now = now

    # 2. now we should turn on but to near the last change -> no nothing to do
    now = now + timedelta(minutes=2)
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_HEAT,
        target_temp=21,
        current_temp=17,
        slope_min=-0.1,
        now=now,
    )
    assert ret is True
    assert algo.last_switch_date == last_now

    # 3. now we should turn on and now is much later ->
    now = now + timedelta(minutes=30)
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_HEAT,
        target_temp=21,
        current_temp=17,
        slope_min=-0.1,
        now=now,
    )
    assert ret is False
    assert algo.last_switch_date == now
    last_now = now

    #
    # Testing with turn_off
    #

    # 4. try to turn_off but too speed (29 min)
    now = now + timedelta(minutes=29)
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=17,
        current_temp=21,
        slope_min=0.5,
        now=now,
    )
    assert ret is False
    assert algo.last_switch_date == last_now

    # 5. turn_off much later (29 min + 1 min)
    now = now + timedelta(minutes=1)
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=17,
        current_temp=21,
        slope_min=0.5,
        now=now,
    )
    assert ret is True
    assert algo.last_switch_date == now


async def test_auto_start_stop_algo_medium_cool_off(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_MEDIUM, "testu"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert algo._dt == 15
    assert algo._vtherm_name == "testu"

    # 1. should not stop (accumulated_error too low)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_COOL,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=22,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret is False
    assert algo.accumulated_error == 1

    # 2. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=3)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_COOL,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=23,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret is False
    assert algo.accumulated_error == 4

    # 2. should stop
    now = now + timedelta(minutes=15)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_COOL,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=23,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret is True
    assert algo.accumulated_error == 5  # should be 9 but is capped at error threshold

    # 6. inverse the temperature (target > current) -> accumulated_error should be divided by 2
    now = now + timedelta(minutes=2)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_COOL,
        # saved_hvac_mode=VThermHvacMode_OFF,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
        now=now,
    )
    assert algo.accumulated_error == 1.5  # 5/2 - 1
    assert ret is True


async def test_auto_start_stop_reset_switch_delay(hass: HomeAssistant):
    """Test that reset_switch_delay allows immediate restart.
    This test simulates the bug where VTherm stays OFF when preset changes
    because nb_minutes_since_last_switch < dt_min.
    """
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_FAST, "testu"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert algo._dt == 7  # FAST level has dt_min = 7 minutes

    # 1. First stop the VTherm (simulate auto-stop)
    algo._accumulated_error = -100
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        target_temp=17,  # ECO preset
        current_temp=20,  # Current temp is above target
        slope_min=0.1,
        now=now,
    )
    assert ret is True
    assert algo.last_switch_date == now
    last_switch = now

    # 2. Now simulate a preset change from ECO (17°) to BOOST (21°) just 2 minutes later
    # Without reset_switch_delay, this would NOT restart because 2 < 7 (dt_min)
    now = now + timedelta(minutes=2)
    algo._accumulated_error = 100  # Reset to positive to simulate need for heating

    # Without reset, should_be_turned_off should still return True (stay OFF)
    # because nb_minutes_since_last_switch (2) < dt_min (7)
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        target_temp=21,  # BOOST preset
        current_temp=19,  # Current temp is now below target
        slope_min=-0.1,
        now=now,
    )
    # BUG: Without the fix, ret would still be True (stays OFF) because dt_min delay not reached
    assert ret is True
    assert algo.last_switch_date == last_switch  # No change in switch date

    # 3. Now call reset_switch_delay (simulating what happens when preset changes)
    algo.reset_switch_delay()
    assert algo.last_switch_date is None

    # 4. Now should_be_turned_off should return False (restart) immediately
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        target_temp=21,  # BOOST preset
        current_temp=19,  # Current temp is below target
        slope_min=-0.1,
        now=now,
    )
    assert ret is False  # Should restart because dt_min delay is bypassed
    # Note: last_switch_date stays None because _last_should_be_off was already reset to
    # False by reset_switch_delay(), so should_be_turned_off() sees no state change
    # (False → False). The important result is ret=False (VTherm restarts).


async def test_auto_start_stop_reset_switch_delay_grey_zone(hass: HomeAssistant):
    """Test that reset_switch_delay exits the stop state even in the 'grey zone'
    where neither the turn-on nor the turn-off condition is explicitly met.

    Regression test for the bug where a preset change did not exit the auto-stop
    state when the predicted temperature (current_temp + slope * dt) was between
    (target - TEMP_HYSTERESIS) and (target + TEMP_HYSTERESIS), causing _last_should_be_off
    to stay True because neither condition was triggered.
    """
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(AUTO_START_STOP_LEVEL_FAST, "testu")

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    assert algo._dt == 7  # FAST level has dt_min = 7 minutes

    # 1. Simulate the auto-stopped state: room at 19°C, target 17°C → auto-stop
    algo._accumulated_error = -2  # at threshold → fully "stopped"
    algo._last_should_be_off = True
    algo._last_switch_date = now

    # 2. User immediately changes preset to BOOST (21°C). Room still at 19°C with
    # a slight positive slope (thermal inertia after heater stopped).
    # Grey zone: temp_at_dt = 19 + 0.2 * 7 = 20.4 which is < 20.5 (target - hysteresis)
    # but > 20.5... wait, let's use 19.5°C room and slope 0.2 to land in the grey zone:
    # temp_at_dt = 19.5 + 0.2 * 7 = 20.9 which is > 20.5 (turn-on cond. false)
    # AND accumulated_error after reset calc won't reach -threshold (turn-off cond. false)
    now = now + timedelta(minutes=0)  # immediate preset change
    algo.reset_switch_delay()

    # Verify reset_switch_delay cleared the last decision flag
    assert algo._last_should_be_off is False
    assert algo._last_switch_date is None
    assert algo._last_calculation_date is None

    # 3. Call should_be_turned_off in the grey zone:
    #    - room at 19.5°C, new target 21°C, positive slope 0.2°/min
    #    - temp_at_dt = 19.5 + 0.2 * 7 = 20.9
    #    - turn-on condition: 20.9 <= 21 - 0.5 = 20.5? NO → condition not met
    #    - turn-off: accumulated_error won't be at -threshold (positive error) → NO
    #    - NEITHER condition → _last_should_be_off stays False (from reset)
    #    - BUG (without fix): returned True because _last_should_be_off was still True
    ret = algo.should_be_turned_off(
        requested_hvac_mode=VThermHvacMode_HEAT,
        target_temp=21.0,  # BOOST preset
        current_temp=19.5,  # Room still warm but below target
        slope_min=0.2,  # Slight positive slope (thermal inertia)
        now=now,
    )
    # With the fix: _last_should_be_off was reset to False, so grey zone defaults to False
    assert ret is False, "Preset change should exit auto-stop state even in the grey zone " "(neither turn-on nor turn-off condition explicitly met)"


async def test_auto_start_stop_none_vtherm(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop is disabled with a real over_climate VTherm in NONE level"""

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")
    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes.get("auto_start_stop_level") is None
    assert vtherm._attr_extra_state_attributes.get("auto_start_stop_dtmin") is None

    # 1. Vtherm auto-start/stop should be in NONE mode
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_NONE
    )

    # 2. We should not find any switch Enable entity
    assert (
        search_entity(hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN)
        is None
    )

    vtherm.remove_thermostat()


async def test_auto_start_stop_medium_heat_vtherm(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop works with a real over_climate VTherm in MEDIUM level"""

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_MEDIUM

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 15

    # 1. Vtherm auto-start/stop should be in MEDIUM mode and an enable entity should exists
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_MEDIUM
    )
    enable_entity = search_entity(
        hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
    )
    assert enable_entity is not None
    assert enable_entity.state == STATE_ON

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == VThermHvacMode_HEAT

    # 3. Set current temperature to 19 5 min later
    now = now + timedelta(minutes=5)
    # reset accumulated error (only for testing)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 19, now, False)
        await wait_for_local_condition(lambda: vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == 0, timeout=3.0, hass=hass)

        # VTherm should still be heating
        assert vtherm.hvac_mode == VThermHvacMode_HEAT
        assert mock_send_event.call_count == 0
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == 0
        )  # target = current = 19

    # 4. Set current temperature to 20 5 min later
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 20, now, False)
        await wait_for_local_condition(lambda: abs(vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error + 2.5) < 0.01, timeout=3.0, hass=hass)

        # VTherm should still be heating
        assert vtherm.hvac_mode == VThermHvacMode_HEAT
        assert mock_send_event.call_count == 0
        # accumulated_error = target - current = -1 x 5 min / 2
        assert abs(vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error + 2.5) < 0.01

    # 5. Set current temperature to 21 5 min later -> should turn off
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 21, now, False)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

        # accumulated_error = -2.5 + target - current = -2 x 5 min / 2 capped to 5
        assert abs(vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error + 5) < 0.01

        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "stop",
                        "name": "overClimate",
                        "cause": "Auto stop conditions reached",
                        "hvac_mode": VThermHvacMode_OFF,
                        "saved_hvac_mode": VThermHvacMode_HEAT,
                        "target_temperature": 19.0,
                        "current_temperature": 21.0,
                        "temperature_slope": 0.167,
                        "accumulated_error": -5,
                        "accumulated_error_threshold": 5,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_OFF,
                    },
                )
            ]
        )

    # 6. Set temperature to small over the target, so that it will stay to OFF
    now = now + timedelta(minutes=10)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 19.5, now, False)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # accumulated_error = .... capped to -5
        assert abs(vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error + 5) < 0.01

        # VTherm should stay stopped cause slope is too low to allow the turn to On
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

    # 7. Set temperature to over the target, so that it will turn to heat
    now = now + timedelta(minutes=20)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 18, now, True)
        await hass.async_block_till_done()

        # accumulated_error = -5/2 + target - current = 1 x 20 min / 2 capped to 5
        assert abs(vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error - 5) < 0.01

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_HEAT
        assert vtherm.hvac_off_reason is None

        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "start",
                        "name": "overClimate",
                        "cause": "Auto start conditions reached",
                        "hvac_mode": VThermHvacMode_HEAT,
                        "saved_hvac_mode": VThermHvacMode_HEAT,  # saved don't change
                        "target_temperature": 19.0,
                        "current_temperature": 18.0,
                        "temperature_slope": -0.034,
                        "accumulated_error": 5,
                        "accumulated_error_threshold": 5,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_HEAT,
                    },
                )
            ]
        )

    vtherm.remove_thermostat()


async def test_auto_start_stop_fast_ac_vtherm(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop works with a real over_climate VTherm in FAST level and AC mode"""

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in MEDIUM mode
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_FAST
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 27, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_COOL)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 25.0
    # VTherm should be cooling
    assert vtherm.hvac_mode == VThermHvacMode_COOL

    # 3. Set current temperature to 19 5 min later
    now = now + timedelta(minutes=5)
    # reset accumulated error for test
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 25, now, True)
        await hass.async_block_till_done()

        # VTherm should still be cooling
        assert vtherm.hvac_mode == VThermHvacMode_COOL
        assert mock_send_event.call_count == 0
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error
            == 0  # target = current = 25
        )

    # 4. Set current temperature to 23 5 min later -> should turn off
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 23, now, True)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_OFF

        # accumulated_error = target - current = 2 x 5 min / 2 capped to 2
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == 2
        )

        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "stop",
                        "name": "overClimate",
                        "cause": "Auto stop conditions reached",
                        "hvac_mode": VThermHvacMode_OFF,
                        "saved_hvac_mode": VThermHvacMode_COOL,
                        "target_temperature": 25.0,
                        "current_temperature": 23.0,
                        "temperature_slope": -0.28,
                        "accumulated_error": 2,
                        "accumulated_error_threshold": 2,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_OFF,
                    },
                )
            ]
        )

    # 5. Set temperature to over the target, but slope is too low -> no change
    now = now + timedelta(minutes=30)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 25.5, now, True)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # accumulated_error = 2/2 + target - current = -1 x 20 min / 2 capped to 2
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == -2
        )

        # VTherm should stay stopped
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        # a message should have been sent
        assert mock_send_event.call_count == 0

    # 6. Set temperature to over the target, so that it will turn to COOL
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 26.5, now, True)
        await hass.async_block_till_done()

        # accumulated_error = 2/2 + target - current = -1 x 20 min / 2 capped to 2
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == -2
        )

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_COOL
        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "start",
                        "name": "overClimate",
                        "cause": "Auto start conditions reached",
                        "hvac_mode": VThermHvacMode_COOL,
                        "saved_hvac_mode": VThermHvacMode_COOL,  # saved don't change
                        "target_temperature": 25.0,
                        "current_temperature": 26.5,
                        "temperature_slope": 0.112,
                        "accumulated_error": -2,
                        "accumulated_error_threshold": 2,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_COOL,
                    },
                )
            ]
        )

    vtherm.remove_thermostat()


async def test_auto_start_stop_medium_heat_vtherm_preset_change(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop restart a VTherm stopped upon preset_change (in fast mode)"""

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in MEDIUM mode
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_FAST
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 16, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.ECO)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 17.0
    # VTherm should be heating
    assert vtherm.hvac_mode == VThermHvacMode_HEAT

    # 3. Set current temperature to 21 5 min later to auto-stop
    now = now + timedelta(minutes=5)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 19, now, False)

        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

        assert vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == -2

        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "stop",
                        "name": "overClimate",
                        "cause": "Auto stop conditions reached",
                        "hvac_mode": VThermHvacMode_OFF,
                        "saved_hvac_mode": VThermHvacMode_HEAT,
                        "target_temperature": 17.0,
                        "current_temperature": 19.0,
                        "temperature_slope": 0.3,
                        "accumulated_error": -2,
                        "accumulated_error_threshold": 2,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_OFF,
                    },
                )
            ]
        )

    # 4.1 reduce the slope (because slope is smoothed and was very high)
    now = now + timedelta(minutes=5)
    await send_temperature_change_event(vtherm, 19, now, True)

    now = now + timedelta(minutes=5)
    await send_temperature_change_event(vtherm, 18, now, True)

    now = now + timedelta(minutes=5)
    await send_temperature_change_event(vtherm, 17, now, True)

    # 4. Change preset to auto restart the Vtherm
    now = now + timedelta(minutes=10)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await vtherm.async_set_preset_mode(VThermPreset.BOOST)
        await wait_for_local_condition(lambda: vtherm.target_temperature == 21, timeout=3.0, hass=hass)

        assert vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == 2

        # VTherm should have been restarted
        assert vtherm.hvac_mode == VThermHvacMode_HEAT
        # a message should have been sent
        assert mock_send_event.call_count >= 1
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "start",
                        "name": "overClimate",
                        "cause": "Auto start conditions reached",
                        "hvac_mode": VThermHvacMode_HEAT,
                        "saved_hvac_mode": VThermHvacMode_HEAT,  # saved don't change
                        "target_temperature": 21.0,
                        "current_temperature": 17.0,
                        "temperature_slope": -0.087,
                        "accumulated_error": 2,
                        "accumulated_error_threshold": 2,
                    },
                )
            ]
        )

        mock_send_event.assert_has_calls(
            [
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_HEAT,
                    },
                )
            ]
        )

    vtherm.remove_thermostat()


async def test_auto_start_stop_medium_heat_vtherm_preset_change_enable_false(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop restart a VTherm stopped upon preset_change (in fast mode)"""

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in FAST mode and enable should be on
    await wait_for_local_condition(lambda: vtherm._attr_extra_state_attributes["auto_start_stop_manager"].get("auto_start_stop_enable") is True, timeout=3.0, hass=hass)

    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_FAST
    )
    enable_entity = search_entity(
        hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
    )
    assert enable_entity is not None
    assert enable_entity.state == STATE_ON

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"].get("auto_start_stop_enable") is True

    # 2. set enable to false
    enable_entity.turn_off()
    await hass.async_block_till_done()
    assert enable_entity.state == STATE_OFF
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"].get("auto_start_stop_enable") is False

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 3. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 16, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.ECO)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 17.0
    # VTherm should be heating
    assert vtherm.hvac_mode == VThermHvacMode_HEAT

    # 3. Set current temperature to 21 5 min later to auto-stop
    now = now + timedelta(minutes=5)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 19, now, True)
        await hass.async_block_till_done()

        # VTherm should not have been stopped cause enable is false
        assert vtherm.hvac_mode == VThermHvacMode_HEAT

        # Not calculated cause enable = false
        assert (
            vtherm.auto_start_stop_manager._auto_start_stop_algo.accumulated_error == 0
        )

        # a message should have been sent
        assert mock_send_event.call_count == 0

    # Restore enable to True before cleanup to avoid restore_state interference
    enable_entity.turn_on()
    await hass.async_block_till_done()
    vtherm.remove_thermostat()


async def test_auto_start_stop_fast_heat_window(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop works with a real over_climate VTherm in FAST level and check
    interaction with window openess detection"""

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
            CONF_WINDOW_DELAY: 10,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in MEDIUM mode and an enable entity should exists
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_FAST
    )
    enable_entity = search_entity(
        hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
    )
    assert enable_entity is not None
    assert enable_entity.state == STATE_ON

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort and close the window
    await send_window_change_event(vtherm, False, False, now, False)
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == VThermHvacMode_HEAT
    # VTherm window_state should be off
    assert vtherm.window_state == STATE_UNKNOWN  # cause condition is not evaluated

    # 3. Set current temperature to 21 5 min later -> should turn off VTherm
    now = now + timedelta(minutes=5)
    # reset accumulated error (only for testing)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 21, now, False)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should no more be heating
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT
        assert mock_send_event.call_count == 2

    # 4. Open the window and wait for the delay
    now = now + timedelta(minutes=2)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        vtherm._set_now(now)
        try_function = await send_window_change_event(
            vtherm, True, False, now, sleep=False
        )

        await try_function(None)

        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # Window takes precedence in the the hvac_off_reason
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT

        mock_send_event.assert_not_called()

        assert vtherm.window_state == STATE_ON

    # 5. close the window
    now = now + timedelta(minutes=2)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        vtherm._set_now(now)
        try_function = await send_window_change_event(
            vtherm, False, True, now, sleep=False
        )

        await try_function(None)

        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # The VTherm should stay off because the reason of off is auto-start-stop
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT

        assert mock_send_event.call_count == 0

        assert vtherm.window_state == STATE_OFF

    vtherm.remove_thermostat()


async def test_auto_start_stop_fast_heat_window_mixed(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than auto-start/stop works with a real over_climate VTherm in FAST level and check
    interaction with window openess detection
    The case is when first window on, then auto-stop, then window off and then auto-start
    """

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
            CONF_WINDOW_DELAY: 10,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in MEDIUM mode and an enable entity should exists
    assert (
        vtherm.auto_start_stop_manager.auto_start_stop_level
        == AUTO_START_STOP_LEVEL_FAST
    )
    enable_entity = search_entity(
        hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
    )
    assert enable_entity is not None
    assert enable_entity.state == STATE_ON

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort and close the window
    await send_window_change_event(vtherm, False, False, now, False)
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == VThermHvacMode_HEAT
    # VTherm window_state should be off
    assert vtherm.window_state == STATE_UNKNOWN  # cause try_condition is not evaluated

    # 3. Open the window and wait for the delay
    now = now + timedelta(minutes=2)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        vtherm._set_now(now)
        try_function = await send_window_change_event(
            vtherm, True, False, now, sleep=False
        )

        await try_function(None)

        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # Nothing should have change (window event is ignoed as we are already OFF)
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT

        assert mock_send_event.call_count == 1

        assert vtherm.window_state == STATE_ON

    # 4. Set current temperature to 21 7 min later -> should turn off VTherm due to Auto-start/stop but window takes precedence
    now = now + timedelta(minutes=7)
    # reset accumulated error (only for testing)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 21, now, True)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should no more be heating
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION  # No change cause window is in priority
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT
        assert mock_send_event.call_count == 1  # Start/stop event only
        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "stop",
                        "name": "overClimate",
                        "cause": "Auto stop conditions reached",
                        "hvac_mode": VThermHvacMode_OFF,
                        "saved_hvac_mode": VThermHvacMode_HEAT,
                        "target_temperature": 19.0,
                        "current_temperature": 21.0,
                        "temperature_slope": 0.167,
                        "accumulated_error": -2,
                        "accumulated_error_threshold": 2,
                    },
                ),
            ]
        )
        assert vtherm.auto_start_stop_manager.is_auto_stop_detected is True

    # 5. close the window
    now = now + timedelta(minutes=2)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        vtherm._set_now(now)
        try_function = await send_window_change_event(
            vtherm, False, True, now, sleep=False
        )

        await try_function(None)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # The VTherm should turn on and off again due to auto-start-stop
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason is HVAC_OFF_REASON_AUTO_START_STOP
        # assert vtherm._saved_hvac_mode == VThermHvacMode_HEAT

        assert vtherm.window_state == STATE_OFF
        assert mock_send_event.call_count == 0

    vtherm.remove_thermostat()


async def test_auto_start_stop_disable_vtherm_off(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that if auto-start-stop is disabled while VTherm is off, the VTherms turns on
    This is in the issue #662"""

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
    }

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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: False,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await create_and_register_mock_climate(hass, "mock_climate", "mock_climate", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT])

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )

    assert vtherm is not None

    # Initialize all temps
    await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

    # Check correct initialization of auto_start_stop attributes
    assert (
        vtherm._attr_extra_state_attributes["is_auto_start_stop_configured"] is True
    )
    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_FAST

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == 7

    # 1. Vtherm auto-start/stop should be in FAST mode and enable should be on
    vtherm._set_now(now)

    assert vtherm.auto_start_stop_manager.auto_start_stop_level == AUTO_START_STOP_LEVEL_FAST
    enable_entity = search_entity(hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN)
    assert enable_entity is not None
    assert enable_entity.state == STATE_ON

    assert vtherm._attr_extra_state_attributes["auto_start_stop_manager"].get("auto_start_stop_enable") is True

    # 2. turn off the VTherm with auto-start/stop
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 25, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.ECO)
    await hass.async_block_till_done()

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        now = now + timedelta(minutes=10)
        vtherm._set_now(now)
        await send_temperature_change_event(vtherm, 26, now, False)

        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)

        # VTherm should have been stopped
        assert vtherm.hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

    # 3. set enable to false
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)

    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
        enable_entity.turn_off()
        await wait_for_local_condition(lambda: enable_entity.state == STATE_OFF, timeout=3.0, hass=hass)

        # VTherm should be heating
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
        # In Eco
        assert vtherm.target_temperature == 17.0
        # We should have a message
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "start",
                        "name": vtherm.name,
                        "cause": "Auto start stop disabled",
                        "hvac_mode": VThermHvacMode_HEAT,
                        "saved_hvac_mode": VThermHvacMode_HEAT,
                        "target_temperature": 17,
                        "current_temperature": 26,
                        "temperature_slope": 3.0,
                        "accumulated_error": -2,
                        "accumulated_error_threshold": 2,
                    },
                ),
                call(
                    EventType.HVAC_MODE_EVENT,
                    {
                        "hvac_mode": VThermHvacMode_HEAT,
                    },
                ),
            ],
            any_order=True,
        )

    vtherm.remove_thermostat()
