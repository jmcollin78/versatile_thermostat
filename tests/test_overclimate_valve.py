# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the over_climate with valve regulation """
from unittest.mock import patch, call
from datetime import datetime, timedelta

import logging

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import SERVICE_SET_TEMPERATURE
from homeassistant.components.number import SERVICE_SET_VALUE

from custom_components.versatile_thermostat.thermostat_climate_valve import (
    ThermostatOverClimateValve,
)
from custom_components.versatile_thermostat.opening_degree_algorithm import OpeningClosingDegreeCalculation

from .commons import *
from .const import *

logging.getLogger().setLevel(logging.DEBUG)


async def test_over_climate_valve_mono(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate: MockClimate):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    fake_temp_sensor.set_native_value(20)
    fake_ext_temp_sensor.set_native_value(20)
    fake_underlying_climate.set_current_temperature(15)

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_SYNC_ENTITY_LIST: ["number.mock_offset_calibration"],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
        }
        | MOCK_DEFAULT_FEATURE_CONFIG
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})
    fake_opening_degree = await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=10, min=0, max=100)
    fake_closing_degree = await create_and_register_mock_number(hass, "mock_closing_degree", "MockClosingDegree", value=90, min=0, max=100)
    fake_offset_calibration = await create_and_register_mock_number(hass, "mock_offset_calibration", "MockOffsetCalibration", value=0, min=-12, max=12, step=0.1)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert vtherm
        vtherm._set_now(now)
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        assert vtherm.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]

        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF
        assert vtherm.target_temperature == vtherm.min_temp
        assert vtherm.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
        ]
        assert vtherm.preset_mode is VThermPreset.NONE
        assert vtherm.safety_manager.is_safety_detected is False
        assert vtherm.window_state is STATE_UNAVAILABLE
        assert vtherm.motion_state is STATE_UNAVAILABLE
        assert vtherm.presence_state is STATE_UNAVAILABLE

        assert vtherm.is_device_active is False
        assert vtherm.valve_open_percent == 0

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

        # the underlying valve should be closed
        assert fake_opening_degree.native_value == 0
        assert fake_closing_degree.native_value == 100

        # room temperature is set to 20
        assert vtherm.current_temperature == 20

        assert fake_offset_calibration.native_value == 0 # no change because no temperature has been sent yet

        # assert mock_get_state.call_count >= 6  # each temp sensor (2) + each valve (2) + temp synchro (2) + all getState in custom_attributes
        assert vtherm.nb_device_actives == 0

        # initialize the temps with the defaults
        await set_all_climate_preset_temp(hass, vtherm, None, "theoverclimatemockname")

        await send_temperature_change_event(vtherm, 18, now, True)
        await send_ext_temperature_change_event(vtherm, 18, now, True)

        await wait_for_local_condition(lambda: fake_offset_calibration.native_value == 3) # 18 - 15 + 0

    # 2. Starts heating slowly (18 vs 19)
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        now = now + timedelta(minutes=3) # avoid temporal filter
        vtherm._set_now(now)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await hass.async_block_till_done()

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 18
        assert vtherm.valve_open_percent == 40 # 0.3*1 + 0.1*1


        assert fake_underlying_climate.target_temperature == 19
        assert fake_opening_degree.native_value == 40
        assert fake_closing_degree.native_value == 60

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True
        assert vtherm.nb_device_actives == 1

    # 3. Starts heating very slowly (18.9 vs 19)
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        await send_temperature_change_event(vtherm, 18.9, now, True)
        await hass.async_block_till_done()

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 18.9
        assert vtherm.valve_open_percent == 13 # 0.3*0.1 + 0.1*1


        assert fake_opening_degree.native_value == 13
        assert fake_closing_degree.native_value == 87
        assert fake_offset_calibration.native_value == 6.9

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True
        assert vtherm.nb_device_actives == 1

    # 4. Stop heating 21 > 19
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        # set the offset to 3
        fake_offset_calibration.set_native_value(3)
        await hass.async_block_till_done()

        await send_temperature_change_event(vtherm, 21, now, True)
        await hass.async_block_till_done()

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 21
        assert vtherm.valve_open_percent == 0 # 0.3* (-2) + 0.1*1

        assert fake_opening_degree.native_value == 0
        assert fake_closing_degree.native_value == 100
        assert fake_offset_calibration.native_value == 9.0 # 6 = 18 (room) - 15 (current of underlying) + 3 (current offset)

        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.is_device_active is False
        assert vtherm.nb_device_actives == 0

    await hass.async_block_till_done()
    vtherm.remove_thermostat()


async def test_over_climate_valve_multi_presence(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_presence_sensor):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    fake_temp_sensor.set_native_value(20)
    fake_ext_temp_sensor.set_native_value(20)
    fake_presence_sensor.turn_off()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=1,
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
            CONF_OFFSET_CALIBRATION_LIST: [
                "number.mock_offset_calibration1",
                "number.mock_offset_calibration2",
            ],
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.fake_presence_sensor",
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # Create the underlying climate entities
    fake_underlying_climate1: MockClimate = await create_and_register_mock_climate(hass, "mock_climate1", "MockClimateName1")
    fake_underlying_climate2: MockClimate = await create_and_register_mock_climate(hass, "mock_climate2", "MockClimateName2")

    fake_underlying_climate1.set_current_temperature(15)
    fake_underlying_climate2.set_current_temperature(15)

    # Create all the number entities needed for the test
    # Valve 1 is initially open at 11%
    fake_opening_degree1 = await create_and_register_mock_number(hass, "mock_opening_degree1", "MockOpeningDegree1", value=11, min=0, max=100)
    fake_closing_degree1 = await create_and_register_mock_number(hass, "mock_closing_degree1", "MockClosingDegree1", value=89, min=0, max=100)
    fake_offset_calibration1 = await create_and_register_mock_number(hass, "mock_offset_calibration1", "MockOffsetCalibration1", value=0, min=-12, max=12, step=0.1)

    # Valve 2 is initially closed
    fake_opening_degree2 = await create_and_register_mock_number(hass, "mock_opening_degree2", "MockOpeningDegree2", value=0, min=0, max=100)
    fake_closing_degree2 = await create_and_register_mock_number(hass, "mock_closing_degree2", "MockClosingDegree2", value=100, min=0, max=100)
    fake_offset_calibration2 = await create_and_register_mock_number(hass, "mock_offset_calibration2", "MockOffsetCalibration2", value=10, min=-12, max=12, step=0.1)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, default_temperatures_away, "theoverclimatemockname")

        await send_temperature_change_event(vtherm, 18, now, True)
        await send_ext_temperature_change_event(vtherm, 18, now, True)
        await send_presence_change_event(vtherm, False, True, now)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)

        assert vtherm.target_temperature == 17.2
        assert vtherm.nb_device_actives == 0

    # 2: set presence on -> should activate the valve and change target
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        await send_presence_change_event(vtherm, True, False, now)
        await hass.async_block_till_done()

        assert vtherm.is_device_active is True
        assert vtherm.valve_open_percent == 40

        # Check the underlying entities have been updated
        assert fake_underlying_climate1.target_temperature == 19.0
        assert fake_underlying_climate2.target_temperature == 19.0
        assert fake_opening_degree1.native_value == 40
        assert fake_closing_degree1.native_value == 60
        assert fake_opening_degree2.native_value == 40
        assert fake_closing_degree2.native_value == 60

        assert vtherm.nb_device_actives >= 2 # should be 2 but when run in // with the first test it give 3

    # 3: set presence off -> should deactivate the valve and change target
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        await send_presence_change_event(vtherm, False, True, now)
        await hass.async_block_till_done()

        assert vtherm.is_device_active is False
        assert vtherm.valve_open_percent == 0

        # Check the underlying entities have been updated
        assert fake_underlying_climate1.target_temperature == 17.2
        assert fake_underlying_climate2.target_temperature == 17.2
        assert fake_opening_degree1.native_value == 0
        assert fake_closing_degree1.native_value == 100
        assert fake_opening_degree2.native_value == 0
        assert fake_closing_degree2.native_value == 100

        assert vtherm.nb_device_actives == 0

    await hass.async_block_till_done()
    vtherm.remove_thermostat()


async def test_over_climate_valve_multi_min_opening_degrees(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Test the normal full start of a thermostat in thermostat_over_climate type
    with valve_regulation and min_opening_degreess set"""

    fake_temp_sensor.set_native_value(20)
    fake_ext_temp_sensor.set_native_value(20)

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
            CONF_AUTO_REGULATION_DTEMP: 0,
            CONF_AUTO_REGULATION_PERIOD_MIN: 0,
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
            CONF_SYNC_ENTITY_LIST: [
                "number.mock_offset_calibration1",
                "number.mock_offset_calibration2",
            ],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_MIN_OPENING_DEGREES: "60,70",
            CONF_MAX_CLOSING_DEGREE: 90,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # Create the underlying climate entities
    fake_underlying_climate1: MockClimate = await create_and_register_mock_climate(hass, "mock_climate1", "MockClimateName1")
    fake_underlying_climate2: MockClimate = await create_and_register_mock_climate(hass, "mock_climate2", "MockClimateName2")

    # Create all the number entities needed for the test
    # Valve 1 is initially open at 10%
    fake_opening_degree1 = await create_and_register_mock_number(hass, "mock_opening_degree1", "MockOpeningDegree1", value=10, min=0, max=100)
    fake_closing_degree1 = await create_and_register_mock_number(hass, "mock_closing_degree1", "MockClosingDegree1", value=90, min=0, max=100)
    fake_offset_calibration1 = await create_and_register_mock_number(hass, "mock_offset_calibration1", "MockOffsetCalibration1", value=0, min=-12, max=12, step=0.1)

    # Valve 2 is initially closed
    fake_opening_degree2 = await create_and_register_mock_number(hass, "mock_opening_degree2", "MockOpeningDegree2", value=0, min=0, max=100)
    fake_closing_degree2 = await create_and_register_mock_number(hass, "mock_closing_degree2", "MockClosingDegree2", value=100, min=0, max=100)
    fake_offset_calibration2 = await create_and_register_mock_number(hass, "mock_offset_calibration2", "MockOffsetCalibration2", value=10, min=-12, max=12, step=0.1)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, default_temperatures, "theoverclimatemockname")

        # await send_temperature_change_event(vtherm, 20, now, True)
        # await send_ext_temperature_change_event(vtherm, 20, now, True)
        fake_underlying_climate1.set_current_temperature(20)
        fake_underlying_climate2.set_current_temperature(20)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)

        await hass.async_block_till_done()

        await wait_for_local_condition(lambda: vtherm.is_device_active is False)

        assert vtherm.target_temperature == 19
        assert vtherm.nb_device_actives == 0
        assert vtherm.hvac_action == HVACAction.IDLE # max closing=90 so valve is not at 0

    # 2: set temperature -> should activate the valve and change target
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await send_temperature_change_event(vtherm, 18, now, True)
    await hass.async_block_till_done()

    assert vtherm.is_device_active is True
    assert vtherm.valve_open_percent == 20

    # Check the valve values - min opening is 60 for valve1, 70 for valve2
    # With 20% opening: valve1 = 60 + 20*0.4 = 68, valve2 = 70 + 20*0.3 = 76
    assert fake_opening_degree1.native_value == 68
    assert fake_closing_degree1.native_value == 32
    assert fake_offset_calibration1.native_value == 3.0
    assert fake_opening_degree2.native_value == 76
    assert fake_closing_degree2.native_value == 24
    assert fake_offset_calibration2.native_value == 12

    assert vtherm.nb_device_actives >= 2 # should be 2 but when run in // with the first test it give 3

    # 3: set high temperature -> should deactivate the valve and change target
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await send_temperature_change_event(vtherm, 22, now, True)
    await hass.async_block_till_done()

    assert vtherm.is_device_active is False
    assert vtherm.valve_open_percent == 0

    # The valves should be closed to max_closing_degree=90
    assert fake_opening_degree1.native_value == 10  # 100 - 90
    assert fake_closing_degree1.native_value == 90
    assert fake_offset_calibration1.native_value == 7.0
    assert fake_opening_degree2.native_value == 10  # 100 - 90
    assert fake_closing_degree2.native_value == 90
    assert fake_offset_calibration2.native_value == 12

    assert vtherm.nb_device_actives == 0

    # 4. restart the VTherm
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await send_temperature_change_event(vtherm, 18, now, True)
    await hass.async_block_till_done()
    assert vtherm.is_device_active is True
    assert vtherm.valve_open_percent == 20

    # Check the valve values again
    assert fake_opening_degree1.native_value == 68
    assert fake_closing_degree1.native_value == 32
    assert fake_offset_calibration1.native_value == 3.0
    assert fake_opening_degree2.native_value == 76
    assert fake_closing_degree2.native_value == 24
    assert fake_offset_calibration2.native_value == 12

    assert vtherm.nb_device_actives >= 2

    # 5. Stop the Vtherm -> should set the opening degree to the min value
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    assert vtherm.is_device_active is False
    assert vtherm.valve_open_percent == 0

    # The valves should be closed to max_closing_degree=90
    assert fake_opening_degree1.native_value == 10  # 100 - 90
    assert fake_closing_degree1.native_value == 90
    assert fake_opening_degree2.native_value == 10  # 100 - 90
    assert fake_closing_degree2.native_value == 90

    assert vtherm.nb_device_actives == 0

    await hass.async_block_till_done()
    vtherm.remove_thermostat()


async def test_over_climate_valve_vtherm_hvac_mode_sleep(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Test the HVAMODE_SLEEP of a thermostat_over_climate type"""

    fake_temp_sensor.set_native_value(18)
    fake_ext_temp_sensor.set_native_value(18)

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_TPI_THRESHOLD_LOW: 0.0,
            CONF_TPI_THRESHOLD_HIGH: 0.0,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_SYNC_ENTITY_LIST: ["number.mock_offset_calibration"],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # Create the underlying climate entity
    fake_underlying_climate: MockClimate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName")

    # Create all the number entities needed for the test
    # Valve is initially open at 11%
    fake_opening_degree = await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=11, min=0, max=100)
    fake_closing_degree = await create_and_register_mock_number(hass, "mock_closing_degree", "MockClosingDegree", value=89, min=0, max=100)
    fake_offset_calibration = await create_and_register_mock_number(hass, "mock_offset_calibration", "MockOffsetCalibration", value=0, min=-12, max=12, step=0.1)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True
        assert vtherm.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]
        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF
        assert vtherm.valve_open_percent == 0
        assert vtherm.is_sleeping is False

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, None, "theoverclimatemockname")

        fake_underlying_climate.set_current_temperature(18)

        # 2. Starts heating slowly (18 vs 19)
        now = now + timedelta(minutes=2)  # avoid temporal filter
        vtherm._set_now(now)

        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        now = now + timedelta(minutes=2)  # avoid temporal filter
        vtherm._set_now(now)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_HEAT)

        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 18
        assert vtherm.valve_open_percent == 40 # 0.3*1 + 0.1*1
        assert vtherm.is_sleeping is False

        # Check the valve values
        assert fake_opening_degree.native_value == 40
        assert fake_closing_degree.native_value == 60

    # 3. set hvac_mode to SLEEP -> should turn off the VTherm and set the valve opening to 100%
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        await vtherm.async_set_hvac_mode(VThermHvacMode_SLEEP)
        await hass.async_block_till_done()
        await wait_for_local_condition(lambda: vtherm._underlyings[0].state_manager.get_state('climate.mock_climate').state == HVACMode.OFF)
        assert vtherm.hvac_mode == VThermHvacMode_OFF

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_SLEEP
        assert vtherm.preset_mode == VThermPreset.COMFORT # no change
        assert vtherm.target_temperature == 19 # no change
        assert vtherm.current_temperature == 18
        assert vtherm.valve_open_percent == 100 # should be 100%
        assert vtherm.is_sleeping is True
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_SLEEP_MODE

        # Check the valve values
        assert fake_opening_degree.native_value == 100
        assert fake_closing_degree.native_value == 0

        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.is_device_active is False
        assert vtherm.nb_device_actives == 0

    # 4. set hvac_mode to HEAT -> should turn on the VTherm and set the valve opening to something < 100%
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        # underlying and vtherm should ne in HEAT mode
        await wait_for_local_condition(lambda: vtherm._underlyings[0].state_manager.get_state('climate.mock_climate').state == HVACMode.HEAT)
        assert vtherm.hvac_mode == VThermHvacMode_HEAT

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT # no change
        assert vtherm.target_temperature == 19 # no change
        assert vtherm.current_temperature == 18
        assert vtherm.valve_open_percent == 40 # should be 40% (as before)
        assert vtherm.is_sleeping is False
        assert vtherm.hvac_off_reason is None

        # Check the valve values
        assert fake_opening_degree.native_value == 40
        assert fake_closing_degree.native_value == 60

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True
        assert vtherm.nb_device_actives == 1

    await hass.async_block_till_done()
    vtherm.remove_thermostat()


async def test_over_climate_valve_period_min(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Test the regulation min parameter for an over climate with direct valve regulation"""

    fake_temp_sensor.set_native_value(18)
    fake_ext_temp_sensor.set_native_value(18)

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,  # The important parameter
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_SYNC_ENTITY_LIST: ["number.mock_offset_calibration"],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # Create the underlying climate entity
    fake_underlying_climate: MockClimate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName")

    # Create all the number entities needed for the test
    # Valve is initially open at 40%
    fake_opening_degree = await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=40, min=0, max=100, step=1)
    fake_closing_degree = await create_and_register_mock_number(hass, "mock_closing_degree", "MockClosingDegree", value=60, min=0, max=100, step=1)
    fake_offset_calibration = await create_and_register_mock_number(hass, "mock_offset_calibration", "MockOffsetCalibration", value=0, min=-12, max=12, step=0.1)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, default_temperatures, "theoverclimatemockname")

        fake_underlying_climate.set_current_temperature(18)

        # 2. Starts heating slowly (18 vs 19)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    now = now + timedelta(minutes=3) # > period min -> regulation will be done
    vtherm._set_now(now)

    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19
    assert vtherm.valve_open_percent == 40 # 0.3*1 + 0.1*1

    # Check the valve values
    assert fake_opening_degree.native_value == 40
    assert fake_closing_degree.native_value == 60

    # 3. Change current temp under one minute -> nothing happens
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        now = now + timedelta(minutes=1) # < period min -> regulation will not be done
        vtherm._set_now(now)

        await send_temperature_change_event(vtherm, 17, now, True)
        await hass.async_block_till_done()

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 17
        assert vtherm.valve_open_percent == 40 # no changes

        # Check the valve values - should not have changed
        assert fake_opening_degree.native_value == 40
        assert fake_closing_degree.native_value == 60

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True
        assert vtherm.nb_device_actives == 1

    # 4. Change current temp above 2 minutes -> changes will happens
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on
        now = now + timedelta(minutes=3) # > period min -> regulation will be done
        vtherm._set_now(now)

        await send_temperature_change_event(vtherm, 16, now, True)
        await hass.async_block_till_done()

        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 16
        assert vtherm.valve_open_percent == 100 # changes !

        # Check the valve values - should have changed
        assert fake_opening_degree.native_value == 100
        assert fake_closing_degree.native_value == 0

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True
        assert vtherm.nb_device_actives == 1

    await hass.async_block_till_done()
    vtherm.remove_thermostat()


@pytest.mark.parametrize(
    "brut_valve_open_percent,min_opening_degree,max_closing_degree,max_opening_degree,opening_threshold,expected_opening",
    # fmt: off
    #    brut_valve_open_percent   min_opening_degree    max_closing_degree    max_opening_degree    opening_threshold    expected_opening
    [
        (0,                        0,                    100,                  100,                  0,                   0),  # full range and 0 -> 0% (no changes)
        (10,                       0,                    100,                  100,                  0,                   10),  # full range and 10 -> 10% (no changes)
        (0,                        10,                   100,                  100,                  10,                  0),  # 10-100 range and 0 -> fully close cause max_close = 100%
        (0,                        10,                   80,                   100,                  10,                  20),   # 10-80 range and 0 -> close -> open to the 1-max_closing
        (5,                        10,                   80,                   100,                  10,                  20),   # 10-80 range and 5 -> close -> open to the 1-max_closing
        (10,                       10,                   80,                   100,                  10,                  10),   # 10-80 range and 10 -> open -> 10% opening
        (20,                       10,                   80,                   100,                  10,                  20),   # 10-80 range and 20 -> open -> 20% opening
        (30,                       10,                   80,                   100,                  10,                  30),   # 10-80 range and 30 -> open -> 30% opening
        (50,                       10,                   80,                   100,                  10,                  50),   # 10-80 range and 50 -> open -> 50% opening
        (80,                       10,                   80,                   100,                  10,                  80),   # 10-80 range and 80 -> open -> 80% opening
        (90,                       10,                   80,                   100,                  10,                  90),   # 10-80 range and 90 -> open -> 90% opening
        (100,                      10,                   80,                   100,                  10,                  100),  # 10-80 range and 100 -> open -> 100% opening
        # With max_opening_degree
        (50,                       10,                   80,                   200,                  10,                  94),   # 10-200 range and 50 -> open -> 94% opening
        (100,                      10,                   80,                   150,                  10,                  150),  # 10-150 range and 100 -> open -> 150% opening
        # With different opening_threshold
        (10,                       15,                   80,                   100,                  20,                  20),   # 10-100 range open at min 15 and brut =10 < threashold (20) -> 20 (100-80)
        (20,                       15,                   80,                   100,                  20,                  15),   # 10-100 range open at min 15 and brut =20 = threashold (20) -> 15 (min_opening)
        (40,                       15,                   80,                   100,                  20,                  36),   # 10-100 range open at min 15 and brut =40 = threashold (20) -> 15 (min_opening + interpolation)
        (80,                       15,                   80,                   100,                  20,                  79),   # 10-100 range open at min 15 and brut =80 = threashold (20) -> 83 (min_opening + interpolation)
        (100,                      15,                   80,                   100,                  20,                  100),  # 10-100 range open at min 15 and brut =100 = threashold (20) -> 100 (min_opening + interpolation = max_opening_degree)
        (100,                      15,                   80,                   150,                  20,                  150),  # 10-100 range open at min 15 and brut =100 = threashold (20) -> 150 (min_opening + interpolation = max_opening_degree)
        # Test of @Tomtom13
        (1,                        10,                   100,                  100,                  0,                   11),   # 10-100 range and 0 -> fully close cause max_close = 100%
        # Error test when min_opening_degree >= max_opening_degree (then threshold is used)
        (40,                       50,                   80,                    40,                  15,                  22),  # use threshold instead of min_opening_degree
    ],
    # fmt: on
)
async def test_min_max_closing_degrees_algo(
    hass: HomeAssistant, skip_hass_states_get, brut_valve_open_percent, min_opening_degree, max_closing_degree, max_opening_degree, opening_threshold, expected_opening
):
    """Test the min and max opening degrees as described here: https://github.com/jmcollin78/versatile_thermostat/issues/1220"""

    # Calculate opening/closing degrees
    opening, closing = OpeningClosingDegreeCalculation.calculate_opening_closing_degree(
        brut_valve_open_percent=brut_valve_open_percent,
        min_opening_degree=min_opening_degree,
        max_closing_degree=max_closing_degree,
        max_opening_degree=max_opening_degree,
        opening_threshold=opening_threshold,
    )

    # Assert expected values
    assert opening == expected_opening, f"Expected opening {expected_opening}%, got {opening}%"
    assert closing == 100 - expected_opening, f"Expected closing {100 - expected_opening}%, got {closing}%"
    assert opening + closing == 100, "Opening + Closing should equal 100%"


# @pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_valve_max_opening_degree(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Test the normal full start of a thermostat in thermostat_over_climate type
    with valve_regulation and max_opening_degree set"""

    fake_temp_sensor.set_native_value(20)
    fake_ext_temp_sensor.set_native_value(20)

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
            CONF_AUTO_REGULATION_DTEMP: 0,
            CONF_AUTO_REGULATION_PERIOD_MIN: 0,
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
            CONF_SYNC_DEVICE_INTERNAL_TEMP: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_MAX_OPENING_DEGREES: "80,85",
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # Create the underlying climate entities
    fake_underlying_climate1: MockClimate = await create_and_register_mock_climate(hass, "mock_climate1", "MockClimateName1")
    fake_underlying_climate2: MockClimate = await create_and_register_mock_climate(hass, "mock_climate2", "MockClimateName2")

    fake_underlying_climate1.set_current_temperature(15)
    fake_underlying_climate2.set_current_temperature(15)

    # Create all the number entities needed for the test
    # Valve 1 is initially open at 10%
    fake_opening_degree1 = await create_and_register_mock_number(hass, "mock_opening_degree1", "MockOpeningDegree1", value=10, min=0, max=100)
    fake_closing_degree1 = await create_and_register_mock_number(hass, "mock_closing_degree1", "MockClosingDegree1", value=90, min=0, max=100)

    # Valve 2 is initially closed
    fake_opening_degree2 = await create_and_register_mock_number(hass, "mock_opening_degree2", "MockOpeningDegree2", value=0, min=0, max=100)
    fake_closing_degree2 = await create_and_register_mock_number(hass, "mock_closing_degree2", "MockClosingDegree2", value=100, min=0, max=100)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, default_temperatures, "theoverclimatemockname")

        await send_temperature_change_event(vtherm, 20, now, True)
        await send_ext_temperature_change_event(vtherm, 20, now, True)

        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)

        await wait_for_local_condition(lambda: fake_underlying_climate1.state == HVACMode.HEAT)
        await wait_for_local_condition(lambda: fake_underlying_climate2.state == HVACMode.HEAT)

        assert vtherm.target_temperature == 19
        assert vtherm.nb_device_actives == 0

    # 2: set temperature to 15°C (far from target 19°C) -> should activate the valve but limit to max_opening_degree (80%)
    # Without max_opening_degree, the valve would open to 100% (0.3 * 4 + 0.1 * 4 = 1.6 -> 100%)
    # With max_opening_degree=80, it should cap at 80%
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await send_temperature_change_event(vtherm, 15, now, True)
    await hass.async_block_till_done()

    await wait_for_local_condition(lambda: fake_underlying_climate1.state == HVACMode.HEAT)
    await wait_for_local_condition(lambda: fake_underlying_climate2.state == HVACMode.HEAT)

    # With dT=4 and coefficients: 0.3*4 + 0.1*4 = 1.6 -> normally 100%, but capped at max_opening_degrees
    assert vtherm.valve_open_percent == 100

    # Check the valve values
    assert fake_opening_degree1.native_value == 80  # max is 80 for valve1
    assert fake_closing_degree1.native_value == 20
    assert fake_opening_degree2.native_value == 85  # max is 85 for valve2
    assert fake_closing_degree2.native_value == 15

    assert vtherm.is_device_active is True
    assert vtherm.nb_device_actives >= 2

    vtherm.remove_thermostat()
    await hass.async_block_till_done()
