# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Auto Start Stop algorithm management """
from datetime import datetime, timedelta
import logging
from unittest.mock import patch

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


async def test_auto_start_stop_algo_slow(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_SLOW, "testu"
    )

    assert algo._dtemp == 3
    assert algo._dt == 30
    assert algo._vtherm_name == "testu"

    # 1. In heating we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=18,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 2. In heating we should do nothing
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=20,
        target_temp=21,
        current_temp=21,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 3. In Cooling we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=24,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 4. In Colling we should do nothing
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 5. In Off, we should start heating
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 6. In Off we should not heat
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=23,
        target_temp=21,
        current_temp=24,
        slope_min=0.5,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 7. In Off we still should not heat (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 8. In Off, we should start cooling
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=25,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 9. In Off we should not cool
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=20,
        target_temp=24,
        current_temp=21,
        slope_min=0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING
    # 9.1 In Off and slow we should cool
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=20,
        target_temp=24,
        current_temp=21,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 10. In Off we still should not cool (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=23,
        slope_min=0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING


async def test_auto_start_stop_algo_medium(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_MEDIUM, "testu"
    )

    assert algo._dtemp == 2
    assert algo._dt == 15
    assert algo._vtherm_name == "testu"

    # 1. In heating we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=18,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 2. In heating we should do nothing
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=20,
        target_temp=21,
        current_temp=21,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 3. In Cooling we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=24,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 4. In Colling we should do nothing
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 5. In Off, we should start heating
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 6. In Off we should not heat
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=23,
        target_temp=21,
        current_temp=24,
        slope_min=0.5,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 7. In Off we still should not heat (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 8. In Off, we should start cooling
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=25,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 9. In Off we should not cool
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=20,
        target_temp=24,
        current_temp=21,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 10. In Off we still should not cool (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=23,
        slope_min=0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING


async def test_auto_start_stop_algo_high(hass: HomeAssistant):
    """Testing directly the algorithm in Slow level"""
    algo: AutoStartStopDetectionAlgorithm = AutoStartStopDetectionAlgorithm(
        AUTO_START_STOP_LEVEL_FAST, "testu"
    )

    assert algo._dtemp == 1
    assert algo._dt == 7
    assert algo._vtherm_name == "testu"

    # 1. In heating we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=18,
        target_temp=21,
        current_temp=22,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 2. In heating and fast we should turn off
    ret = algo.calculate_action(
        hvac_mode=HVACMode.HEAT,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=20,
        target_temp=21,
        current_temp=21,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 3. In Cooling we should stop
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=24,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 4. In Cooling and fast we should turn off
    ret = algo.calculate_action(
        hvac_mode=HVACMode.COOL,
        saved_hvac_mode=HVACMode.OFF,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=0.0,
    )
    assert ret == AUTO_START_STOP_ACTION_OFF

    # 5. In Off and fast , we should do nothing
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 6. In Off we should not heat
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=23,
        target_temp=21,
        current_temp=24,
        slope_min=0.5,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 7. In Off we still should not heat (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.HEAT,
        regulated_temp=22,
        target_temp=21,
        current_temp=22,
        slope_min=-0.01,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 8. In Off, we should start cooling
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=25,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_ON

    # 9. In Off we should not cool
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=20,
        target_temp=24,
        current_temp=21,
        slope_min=0.1,
    )
    assert ret == AUTO_START_STOP_ACTION_NOTHING

    # 10. In Off we still should not cool (slope too low)
    ret = algo.calculate_action(
        hvac_mode=HVACMode.OFF,
        saved_hvac_mode=HVACMode.COOL,
        regulated_temp=25,
        target_temp=24,
        current_temp=23,
        slope_min=0.01,
    )
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

    # 1. Vtherm auto-start/stop should be in MEDIUM mode
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

    # 1. Vtherm auto-start/stop should be in MEDIUM mode
    assert vtherm.auto_start_stop_level == AUTO_START_STOP_LEVEL_MEDIUM

    # 1. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, datetime.now())
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0

    # 2. Only change the HVAC_MODE (and keep preset to comfort)
    await vtherm.async_set_hvac_mode(HVACMode.COOL)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25.0

    # 3. Only change the HVAC_MODE (and keep preset to comfort)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 19.0

    # 4. Change presence to off
    await send_presence_change_event(vtherm, False, True, datetime.now())
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 19.1

    # 5. Change hvac_mode to AC
    await vtherm.async_set_hvac_mode(HVACMode.COOL)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25.1

    # 6. Change presence to on
    await send_presence_change_event(vtherm, True, False, datetime.now())
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25
