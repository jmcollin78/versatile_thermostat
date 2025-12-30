# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the over_climate with valve regulation """
from unittest.mock import patch, call
from datetime import datetime, timedelta

import logging

from homeassistant.core import HomeAssistant, State

from custom_components.versatile_thermostat.thermostat_climate_valve import (
    ThermostatOverClimateValve,
)
from custom_components.versatile_thermostat.opening_degree_algorithm import OpeningClosingDegreeCalculation

from .commons import *
from .const import *

logging.getLogger().setLevel(logging.DEBUG)

async def test_over_climate_valve_multi_sync_calibration(
    hass: HomeAssistant, skip_hass_states_get
):
    """Test the temperature calibration synchronization of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=2,
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: [
                "number.mock_opening_degree1",
                "number.mock_opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [
                "number.mock_closing_degree1",
                "number.mock_closing_degree2",
            ],
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_ENTITY_LIST: [
                "number.mock_offset_calibration1",
                "number.mock_offset_calibration2",
            ],
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    fake_underlying_climate1 = MockClimate(
        hass, "mockUniqueId1", "MockClimateName1", {}
    )
    fake_underlying_climate2 = MockClimate(
        hass, "mockUniqueId2", "MockClimateName2", {}
    )

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    mock_get_state_side_effect = SideEffects(
        {
            # Valve 1 is open
            "number.mock_opening_degree1": State("number.mock_opening_degree1", "11", {"min": 0, "max": 100}),
            "number.mock_closing_degree1": State("number.mock_closing_degree1", "89", {"min": 0, "max": 100}),
            "number.mock_offset_calibration1": State("number.mock_offset_calibration1", "0", {"min": -12, "max": 12}),
            # Valve 2 is closed
            "number.mock_opening_degree2": State("number.mock_opening_degree2", "0", {"min": 0, "max": 100}),
            "number.mock_closing_degree2": State("number.mock_closing_degree2", "100", {"min": 0, "max": 100}),
            "number.mock_offset_calibration2": State("number.mock_offset_calibration2", "10", {"min": -12, "max": 12}),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate", side_effect=[fake_underlying_climate1, fake_underlying_climate2]), \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)

        assert vtherm.target_temperature == 19
        assert vtherm.nb_device_actives == 0
        assert vtherm.is_device_active is False
        await send_ext_temperature_change_event(vtherm, 18, now, True)

    # 2. set room temperature -> must see the calibration change
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on
        fake_underlying_climate1.set_current_temperature(15)
        fake_underlying_climate2.set_current_temperature(15)

        await send_temperature_change_event(vtherm, 18, now, True)

        await wait_for_local_condition(lambda: vtherm.current_temperature == 18)

        # Calibration should have changed
        assert mock_service_call.call_count == 2
        mock_service_call.assert_has_calls([
            call(domain='number', service='set_value', service_data={'value': 3.0}, target={'entity_id': 'number.mock_offset_calibration1'}), # 18 - 15 + 0
            call(domain='number', service='set_value', service_data={'value': 12}, target={'entity_id': 'number.mock_offset_calibration2'})   # 18 - 15 + 10 < 12 max
            ]
        )

    # 3. set room temperature lower -> must see the calibration change
    mock_get_state_side_effect.add_or_update_side_effect(
        "number.mock_offset_calibration1", State("number.mock_offset_calibration1", "3", {"min": -12, "max": 12})
    )

    mock_get_state_side_effect.add_or_update_side_effect(
        "number.mock_offset_calibration2", State("number.mock_offset_calibration2", "12", {"min": -12, "max": 12})
    )

    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on
        fake_underlying_climate1.set_current_temperature(13)
        fake_underlying_climate2.set_current_temperature(21)
        await send_temperature_change_event(vtherm, 15, now, True)

        await wait_for_local_condition(lambda: vtherm.current_temperature == 15)

        # Calibration should have changed
        assert mock_service_call.call_count == 2
        mock_service_call.assert_has_calls([
            call(domain='number', service='set_value', service_data={'value': 5.0}, target={'entity_id': 'number.mock_offset_calibration1'}), # 15 - 13 + 3
            call(domain='number', service='set_value', service_data={'value': 6}, target={'entity_id': 'number.mock_offset_calibration2'})   # 15 - 21 + 12
            ]
        )


    vtherm.remove_thermostat()
    await hass.async_block_till_done()

async def test_over_climate_valve_multi_sync_temperature(
    hass: HomeAssistant, skip_hass_states_get
):
    """Test the temperature synchronization of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=2,
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: [
                "number.mock_opening_degree1",
                "number.mock_opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [
                "number.mock_closing_degree1",
                "number.mock_closing_degree2",
            ],
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_SYNC_WITH_CALIBRATION: False,
            CONF_SYNC_ENTITY_LIST: [
                "number.mock_ext_temp1",
                "number.mock_ext_temp2",
            ],
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    fake_underlying_climate1 = MockClimate(
        hass, "mockUniqueId1", "MockClimateName1", {}
    )
    fake_underlying_climate2 = MockClimate(
        hass, "mockUniqueId2", "MockClimateName2", {}
    )

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    mock_get_state_side_effect = SideEffects(
        {
            # Valve 1 is open
            "number.mock_opening_degree1": State("number.mock_opening_degree1", "11", {"min": 0, "max": 100}),
            "number.mock_closing_degree1": State("number.mock_closing_degree1", "89", {"min": 0, "max": 100}),
            "number.mock_ext_temp1": State("number.mock_ext_temp1", "15", {"min": 0, "max": 35}),
            # Valve 2 is closed
            "number.mock_opening_degree2": State("number.mock_opening_degree2", "0", {"min": 0, "max": 100}),
            "number.mock_closing_degree2": State("number.mock_closing_degree2", "100", {"min": 0, "max": 100}),
            "number.mock_ext_temp2": State("number.mock_ext_temp2", "10", {"min": 0, "max": 35}),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate", side_effect=[fake_underlying_climate1, fake_underlying_climate2]), \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps=default_temperatures)
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)

        assert vtherm.target_temperature == 19
        assert vtherm.nb_device_actives == 0
        assert vtherm.is_device_active is False
        await send_ext_temperature_change_event(vtherm, 18, now, True)

    # 2. set room temperature -> must see the calibration change
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on
        fake_underlying_climate1.set_current_temperature(15)
        fake_underlying_climate2.set_current_temperature(15)

        await send_temperature_change_event(vtherm, 18, now, True)

        await wait_for_local_condition(lambda: vtherm.current_temperature == 18)

        # Calibration should have changed
        assert mock_service_call.call_count == 2
        mock_service_call.assert_has_calls([
            call(domain='number', service='set_value', service_data={'value': 18.0}, target={'entity_id': 'number.mock_ext_temp1'}),
            call(domain='number', service='set_value', service_data={'value': 18.0}, target={'entity_id': 'number.mock_ext_temp2'})
            ]
        )

    # 3. set room temperature lower -> must see the calibration change
    mock_get_state_side_effect.add_or_update_side_effect(
        "number.mock_ext_temp1", State("number.mock_ext_temp1", "7", {"min": 0, "max": 35})
    )

    mock_get_state_side_effect.add_or_update_side_effect(
        "number.mock_ext_temp2", State("number.mock_ext_temp2", "9", {"min": 0, "max": 35})
    )

    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()):
    # fmt: on
        fake_underlying_climate1.set_current_temperature(13)
        fake_underlying_climate2.set_current_temperature(21)
        await send_temperature_change_event(vtherm, 15, now, True)

        await wait_for_local_condition(lambda: vtherm.current_temperature == 15)

        # Calibration should have changed
        assert mock_service_call.call_count == 2
        mock_service_call.assert_has_calls([
            call(domain='number', service='set_value', service_data={'value': 15}, target={'entity_id': 'number.mock_ext_temp1'}),
            call(domain='number', service='set_value', service_data={'value': 15}, target={'entity_id': 'number.mock_ext_temp2'})
            ]
        )


    vtherm.remove_thermostat()
    await hass.async_block_till_done()
