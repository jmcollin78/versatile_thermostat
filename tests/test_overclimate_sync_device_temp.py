# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the over_climate with valve regulation """
from unittest.mock import patch, call
from datetime import datetime, timedelta

import logging

from homeassistant.core import HomeAssistant, State
from homeassistant.components.number import SERVICE_SET_VALUE

from custom_components.versatile_thermostat.thermostat_climate_valve import (
    ThermostatOverClimateValve,
)

from .commons import *
from .const import *

logging.getLogger().setLevel(logging.DEBUG)


async def test_over_climate_valve_multi_sync_calibration(hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor):
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

    # Create underlying climates
    fake_underlying_climate1 = await create_and_register_mock_climate(hass, "mock_climate1", "MockClimateName1", {})
    fake_underlying_climate2 = await create_and_register_mock_climate(hass, "mock_climate2", "MockClimateName2", {})

    # Create mock number entities for valves and calibration
    # Valve 1 is open
    mock_opening_degree1 = await create_and_register_mock_number(hass, "mock_opening_degree1", "MockOpeningDegree1", 11, 0, 100)
    mock_closing_degree1 = await create_and_register_mock_number(hass, "mock_closing_degree1", "MockClosingDegree1", 89, 0, 100)
    mock_offset_calibration1 = await create_and_register_mock_number(hass, "mock_offset_calibration1", "MockOffsetCalibration1", 0, -12, 12)
    # Valve 2 is closed
    mock_opening_degree2 = await create_and_register_mock_number(hass, "mock_opening_degree2", "MockOpeningDegree2", 0, 0, 100)
    mock_closing_degree2 = await create_and_register_mock_number(hass, "mock_closing_degree2", "MockClosingDegree2", 100, 0, 100)
    mock_offset_calibration2 = await create_and_register_mock_number(hass, "mock_offset_calibration2", "MockOffsetCalibration2", 10, -12, 12)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

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

    fake_ext_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()

    # 2. set room temperature -> must see the calibration change
    fake_underlying_climate1.set_current_temperature(15)
    fake_underlying_climate2.set_current_temperature(15)

    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()

    await wait_for_local_condition(lambda: vtherm.current_temperature == 18)

    # Calibration should have changed
    await wait_for_local_condition(lambda: mock_offset_calibration1.state == 3.0)  # 18 - 15 + 0
    await wait_for_local_condition(lambda: mock_offset_calibration2.state == 12.0)  # 18 - 15 + 10 < 12 max

    # 3. set room temperature lower -> must see the calibration change
    mock_offset_calibration1.set_native_value(3)
    mock_offset_calibration2.set_native_value(12)

    fake_underlying_climate1.set_current_temperature(13)
    fake_underlying_climate2.set_current_temperature(21)

    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()

    await wait_for_local_condition(lambda: vtherm.current_temperature == 15)

    # Calibration should have changed
    await wait_for_local_condition(lambda: mock_offset_calibration1.state == 5.0)  # 15 - 13 + 3
    await wait_for_local_condition(lambda: mock_offset_calibration2.state == 6.0)  # 15 - 21

    vtherm.remove_thermostat()
    await hass.async_block_till_done()


async def test_over_climate_valve_multi_sync_temperature(hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor):
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

    # Create underlying climates
    fake_underlying_climate1 = await create_and_register_mock_climate(hass, "mock_climate1", "MockClimateName1", {})
    fake_underlying_climate2 = await create_and_register_mock_climate(hass, "mock_climate2", "MockClimateName2", {})

    # Create mock number entities for valves and external temperature
    # Valve 1 is open
    mock_opening_degree1 = await create_and_register_mock_number(hass, "mock_opening_degree1", "MockOpeningDegree1", 11, 0, 100)
    mock_closing_degree1 = await create_and_register_mock_number(hass, "mock_closing_degree1", "MockClosingDegree1", 89, 0, 100)
    mock_ext_temp1 = await create_and_register_mock_number(hass, "mock_ext_temp1", "MockExtTemp1", 15, 0, 35)
    # Valve 2 is closed
    mock_opening_degree2 = await create_and_register_mock_number(hass, "mock_opening_degree2", "MockOpeningDegree2", 0, 0, 100)
    mock_closing_degree2 = await create_and_register_mock_number(hass, "mock_closing_degree2", "MockClosingDegree2", 100, 0, 100)
    mock_ext_temp2 = await create_and_register_mock_number(hass, "mock_ext_temp2", "MockExtTemp2", 10, 0, 35)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

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
    fake_ext_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    # await send_ext_temperature_change_event(vtherm, 18, now, True)

    # 2. set room temperature -> must see the calibration change
    fake_underlying_climate1.set_current_temperature(15)
    fake_underlying_climate2.set_current_temperature(15)

    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    # await send_temperature_change_event(vtherm, 18, now, True)

    await wait_for_local_condition(lambda: vtherm.current_temperature == 18)

    # Calibration should have changed
    await wait_for_local_condition(lambda: mock_ext_temp1.state == 18)
    await wait_for_local_condition(lambda: mock_ext_temp2.state == 18)
    # assert mock_service_call.call_count == 2
    # mock_service_call.assert_has_calls([
    #     call('number', SERVICE_SET_VALUE, {'value': 18.0}, False, None, {'entity_id': 'number.mock_ext_temp1'}, False),
    #     call('number', SERVICE_SET_VALUE, {'value': 18.0}, False, None, {'entity_id': 'number.mock_ext_temp2'}, False)
    #     ]
    # )

    # 3. set room temperature lower -> must see the calibration change
    mock_ext_temp1.set_native_value(7)
    mock_ext_temp2.set_native_value(9)

    fake_underlying_climate1.set_current_temperature(13)
    fake_underlying_climate2.set_current_temperature(21)

    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    # await send_temperature_change_event(vtherm, 15, now, True)

    await wait_for_local_condition(lambda: vtherm.current_temperature == 15)

    # Calibration should have changed
    await wait_for_local_condition(lambda: mock_ext_temp1.state == 15)
    await wait_for_local_condition(lambda: mock_ext_temp2.state == 15)
    # assert mock_service_call.call_count == 2
    # mock_service_call.assert_has_calls(
    #     [
    #         call("number", SERVICE_SET_VALUE, {"value": 15}, False, None, {"entity_id": "number.mock_ext_temp1"}, False),
    #         call("number", SERVICE_SET_VALUE, {"value": 15}, False, None, {"entity_id": "number.mock_ext_temp2"}, False),
    #     ]
    # )

    vtherm.remove_thermostat()
    await hass.async_block_till_done()
