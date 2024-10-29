# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Auto Start Stop algorithm management """
from datetime import datetime, timedelta
import logging
from unittest.mock import patch, call

from homeassistant.components.climate import HVACMode

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.auto_start_stop_algorithm import (
    AutoStartStopDetectionAlgorithm,
    AUTO_START_STOP_ACTION_NOTHING,
    AUTO_START_STOP_ACTION_OFF,
    AUTO_START_STOP_ACTION_ON,
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
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
        now=now,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING
    assert algo.accumulated_error == -1

    # 2. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=5)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING
    assert algo.accumulated_error == -6

    # 3. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=2)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -8
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 4 .No change on accumulated error because the new measure is too near the last one
    now = now + timedelta(minutes=1)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=23,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -8
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 5. should stop now because accumulated_error is > ERROR_THRESHOLD for slow (10)
    now = now + timedelta(minutes=4)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
        now=now,
    )
    assert algo.accumulated_error == -10
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 6. inverse the temperature (target > current) -> accumulated_error should be divided by 2
    now = now + timedelta(minutes=2)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=22,
        current_temp=21,
        slope_min=-0.1,
        now=now,
    )
    assert algo.accumulated_error == -4  # -10/2 + 1
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 7. change level to slow (no real change) -> error_accumulated should not reset to 0
    algo.set_level(AUTO_START_STOP_LEVEL_SLOW)
    assert algo.accumulated_error == -4

    # 8. change level -> error_accumulated should reset to 0
    algo.set_level(AUTO_START_STOP_LEVEL_FAST)
    assert algo.accumulated_error == 0


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
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=22,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING
    assert algo.accumulated_error == 1

    # 2. should not stop (accumulated_error too low)
    now = now + timedelta(minutes=3)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=23,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING
    assert algo.accumulated_error == 4

    # 2. should stop
    now = now + timedelta(minutes=5)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=23,
        current_temp=21,
        slope_min=0.1,
        now=now,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF
    assert algo.accumulated_error == 5  # should be 9 but is capped at error threshold

    # 6. inverse the temperature (target > current) -> accumulated_error should be divided by 2
    now = now + timedelta(minutes=2)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
        now=now,
    )
    assert algo.accumulated_error == 1.5  # 5/2 - 1
    assert ret == AUTO_START_STOP_ACTION_NOTHING


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mock_climate",
        name="mock_climate",
        hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm: ThermostatOverClimate = await create_thermostat(
            hass, config_entry, "climate.overclimate"
        )

        assert vtherm is not None

        # Initialize all temps
        await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")
        # Check correct initialization of auto_start_stop attributes
        assert (
            vtherm._attr_extra_state_attributes["auto_start_stop_level"]
            == AUTO_START_STOP_LEVEL_NONE
        )

        assert vtherm._attr_extra_state_attributes["auto_start_stop_dtmin"] is None

    # 1. Vtherm auto-start/stop should be in NONE mode
    assert vtherm.auto_start_stop_level == AUTO_START_STOP_LEVEL_NONE


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_auto_start_stop_medium_vtherm(
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
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mock_climate",
        name="mock_climate",
        hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm: ThermostatOverClimate = await create_thermostat(
            hass, config_entry, "climate.overclimate"
        )

        assert vtherm is not None

        # Initialize all temps
        await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

        # Check correct initialization of auto_start_stop attributes
        assert (
            vtherm._attr_extra_state_attributes["auto_start_stop_level"]
            == AUTO_START_STOP_LEVEL_MEDIUM
        )

        assert vtherm._attr_extra_state_attributes["auto_start_stop_dtmin"] == 15

    # 1. Vtherm auto-start/stop should be in MEDIUM mode
    assert vtherm.auto_start_stop_level == AUTO_START_STOP_LEVEL_MEDIUM

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == HVACMode.HEAT

    # 3. Set current temperature to 19 5 min later
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(vtherm, 19, now, True)
        await hass.async_block_till_done()

        # VTherm should still be heating
        assert vtherm.hvac_mode == HVACMode.HEAT
        assert mock_send_event.call_count == 0

    # 4. Set current temperature to 20 5 min later
    now = now + timedelta(minutes=5)
    with patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        await send_temperature_change_event(vtherm, 20, now, True)
        await hass.async_block_till_done()

        # VTherm should still be heating
        assert vtherm.hvac_mode == HVACMode.HEAT
        assert mock_send_event.call_count == 0

    # 5. Set current temperature to 21 5 min later
    with patch(
        "custom_components.versatile_thermostat.binary_sensor.send_vtherm_event"
    ) as mock_send_event:
        now = now + timedelta(minutes=5)
        await send_temperature_change_event(vtherm, 21, now, True)
        await hass.async_block_till_done()

        # VTherm should have been stopped
        assert vtherm.hvac_mode == HVACMode.OFF

        # a message should have been sent
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_vtherm_event(
                    hass=hass,
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    entity=vtherm.entity_id,
                    data={},
                )
            ]
        )
