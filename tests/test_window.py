# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import asyncio
import logging
from unittest.mock import patch, call, PropertyMock
from datetime import datetime, timedelta

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

async def test_window_management_time_not_enough(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Window management when time is not enough"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_UNKNOWN

    # Open the window, but condition of time is not satisfied and check the thermostat don't turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition:
        await send_temperature_change_event(entity, 15, datetime.now())
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)

        await try_function(None)
        await wait_for_local_condition(lambda: entity.window_state == STATE_OFF)

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_condition.call_count == 1

        assert entity.window_state == STATE_OFF

        # Close the window
        try_window_condition = await send_window_change_event(
            entity, False, False, datetime.now()
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)
        assert entity.window_state == STATE_OFF

    entity.remove_thermostat()


async def test_window_management_time_enough(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Window management when time is enough"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_UNKNOWN

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)

        await try_function(None)
        await wait_for_local_condition(lambda: entity.window_state == STATE_ON)

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls([call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF})])

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 2
        assert mock_condition.call_count == 1
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        assert entity.window_state == STATE_ON

    # Close the window
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        try_function = await send_window_change_event(
            entity, False, True, datetime.now(), sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await wait_for_local_condition(lambda: entity.window_state == STATE_OFF and mock_heater_on.call_count >= 1)

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 1
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
            ],
            any_order=False,
        )
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT  # No change
        assert entity.hvac_off_reason is None

    # Clean the entity
    entity.remove_thermostat()


async def test_window_auto_fast(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the auto Window management with fast slope down"""

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
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_MAX_DURATION: 10,  # Should be 0 for test
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured is True

    # Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1
        assert entity.last_temperature_slope == -6.24
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.window_auto_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF}),
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {"type": "start", "cause": "slope alert", "curve_slope": -6.24},
                ),
            ],
            any_order=True,
        )

    # send another 0.1 degre in one minute -> no change
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 17.9, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope is not None
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.window_auto_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # send another plus 1.1 degre in one minute -> restore state
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {
                        "type": "end",
                        "cause": "end of slope alert",
                        "curve_slope": 0.42,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == 0.42
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is True
        )
        assert entity.window_auto_state == STATE_OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    entity.remove_thermostat()


async def test_window_auto_fast_and_sensor(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that the auto-window detection algorithm is deactivated if a window sensor is provided"""

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
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_DELAY: 10,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_MAX_DURATION: 10,  # Should be 0 for test
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_auto_state is STATE_UNAVAILABLE
    assert entity.window_manager.is_window_auto_configured is False
    assert entity.window_manager.is_configured is True

    # Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater don't turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp)

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0  # no change in heater
        assert mock_heater_off.call_count == 0  # no change in heater
        assert entity.last_temperature_slope == -6.24
        # The window open should be detected (but not used)
        # because we need to calculate the slope anyway, we have the algorithm running
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.window_auto_state == STATE_UNAVAILABLE
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    entity.remove_thermostat()


async def test_window_auto_auto_stop(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window auto management"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: "switch.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            CONF_WINDOW_AUTO_MAX_DURATION: 1,  # 0 will deactivate window auto detection
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverclimatemockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo is None

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured is True

    # 1. Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # 2. Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.is_device_active",
        return_value=True,
    ):
        # This is the 3rd measurment. Slope is not ready
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The climate turns on but was alredy on
        assert mock_set_hvac_mode.call_count == 0
        assert entity.last_temperature_slope == 0.0
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # 3. send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp, sleep=False)

        assert entity.last_temperature_slope == -6.24
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )

        assert mock_send_event.call_count == 2
        # The heater turns off
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF}),
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {
                        "type": "start",
                        "cause": "slope alert",
                        "curve_slope": -6.24,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_set_hvac_mode.call_count >= 1
        assert entity.window_auto_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # 4. This is to avoid that the slope stay under 6, else we will reactivate the window immediatly
    event_timestamp = event_timestamp + timedelta(minutes=1)
    dearm_window_auto = await send_temperature_change_event(
        entity, 19, event_timestamp, sleep=False
    )
    assert entity.last_temperature_slope is not None
    assert entity.last_temperature_slope > -6.0

    # 5. Waits for automatic disable
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        # simulate the expiration of the delay
        await dearm_window_auto(None)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.window_auto_state == STATE_OFF

        assert mock_set_hvac_mode.call_count == 1
        assert round(entity.last_temperature_slope, 3) == -0.29
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )

    # Clean the entity
    entity.remove_thermostat()


async def test_window_auto_no_on_percent(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Power management"""

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
            "boost_temp": 20,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            CONF_WINDOW_AUTO_MAX_DURATION: 1,  # Should be 0 for test but 0 is not possible
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 20

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_auto_state is STATE_UNKNOWN

    # Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 21, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 21, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 21, event_timestamp)

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 21, event_timestamp)

        # The heater don't turns on
        assert mock_heater_on.call_count == 0
        assert entity.last_temperature_slope == 0.0
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.proportional_algorithm.on_percent == 0.0

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 20, event_timestamp)

        # The heater turns on but no alert because the heater was not heating
        assert entity.proportional_algorithm.on_percent == 0.0
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1
        assert entity.last_temperature_slope == -6.24
        # The algo calculate open ...
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        # But the entity is still on and window_auto is not detected
        assert entity.window_auto_state == STATE_UNKNOWN
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    entity.remove_thermostat()


async def test_window_bypass(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management when bypass enabled"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured is False

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Set Window ByPass to true
    await entity.service_set_window_bypass_state(True)
    assert entity.is_window_bypass is True

    # Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        try_function = await send_window_change_event(
            entity, True, False, datetime.now()
        )
        await try_function(None)

        assert mock_send_event.call_count == 0

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 0
        assert mock_condition.call_count > 0
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.window_state == STATE_ON

    # Close the window
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        try_function = await send_window_change_event(
            entity, False, True, datetime.now(), sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await wait_for_local_condition(lambda: entity.window_state == STATE_OFF)

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 0
        assert mock_send_event.call_count == 0
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST

    # Clean the entity
    entity.remove_thermostat()


# PR - Adding Window bypass for window auto algorithm
async def test_window_auto_bypass(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window auto management"""

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
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            CONF_WINDOW_AUTO_MAX_DURATION: 1,  # Should be > 0 to activate window_auto
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured

    # Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert (
            entity.window_manager._window_auto_algo.is_window_open_detected() is False
        )
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # send one degre down in one minute with window bypass on
    await entity.service_set_window_bypass_state(True)
    assert entity.is_window_bypass is True

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp, sleep=False)

        # No change should have been done
        assert mock_send_event.call_count == 0

        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == -6.24
        assert entity.window_manager._window_auto_algo.is_window_open_detected() is True
        assert (
            entity.window_manager._window_auto_algo.is_window_close_detected() is False
        )
        assert entity.window_auto_state == STATE_UNKNOWN
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    entity.remove_thermostat()


# PR - Adding Window bypass AFTER detection have been done should reactivate the heater
async def test_window_bypass_reactivate(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management when window is open and then bypass is set to on"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_UNKNOWN

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)

        await try_function(None)
        await wait_for_local_condition(lambda: entity.window_state == STATE_ON)

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls([call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF})])

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 2
        assert mock_condition.call_count == 1
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.window_state == STATE_ON

    # Call the set bypass service to set bypass ON
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await entity.service_set_window_bypass_state(True)

        assert entity.window_state == STATE_ON
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # assert mock_heater_on.call_count == 1
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
            ],
            any_order=False,
        )

    # Clean the entity
    entity.remove_thermostat()


async def test_window_action_fan_only(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with the fan_only option"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 1,
            CONF_WINDOW_ACTION: CONF_WINDOW_FAN_ONLY,
            # CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            # CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            # CONF_WINDOW_AUTO_MAX_DURATION: 1,  # 0 will deactivate window auto detection
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        hvac_modes=[VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_FAN_ONLY],
    )

    # 1. intialize climate entity
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )

        assert entity

        assert entity.is_over_climate is True
        assert entity.window_manager.window_action == CONF_WINDOW_FAN_ONLY

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.hvac_mode == VThermHvacMode_HEAT
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 18

        assert entity.window_state is STATE_UNKNOWN

    # 2. Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        event_timestamp = now - timedelta(minutes=2)
        try_window_condition = await send_window_change_event(
            entity, True, False, event_timestamp
        )
        await try_window_condition(None)

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls([call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_FAN_ONLY})])

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_FAN_ONLY),
            ]
        )

        assert entity.window_state == STATE_ON
        # The underlying should be in FAN_ONLY hvac_mode
        assert entity.vtherm_hvac_mode is VThermHvacMode_FAN_ONLY
        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT
        assert entity.hvac_off_reason is None  # Hvac is not off
        assert entity.preset_mode == VThermPreset.COMFORT

    # 3. Close the window
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        event_timestamp = now - timedelta(minutes=1)
        try_function = await send_window_change_event(
            entity, False, True, event_timestamp, sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await hass.async_block_till_done()

        assert entity.window_state == STATE_OFF
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
            ],
            any_order=False,
        )

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.hvac_off_reason is None

    # Clean the entity
    entity.remove_thermostat()


async def test_window_action_fan_only_ko(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Window management with the fan_only option but the underlyings doesn't have the FAN_ONLY mode
    So the VTherm switch to OFF which is the fallback mode"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 1,
            CONF_WINDOW_ACTION: CONF_WINDOW_FAN_ONLY,
            # CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            # CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            # CONF_WINDOW_AUTO_MAX_DURATION: 1,  # 0 will deactivate window auto detection
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        hvac_modes=[VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_AUTO],
    )

    # 1. intialize climate entity
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )

        assert entity

        assert entity.is_over_climate is True
        assert entity.window_manager.window_action == CONF_WINDOW_FAN_ONLY

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.hvac_mode == VThermHvacMode_HEAT
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 18

        assert entity.window_state is STATE_UNKNOWN

    # 2. Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        event_timestamp = now - timedelta(minutes=2)
        try_window_condition = await send_window_change_event(
            entity, True, False, event_timestamp
        )
        await try_window_condition(None)

        await wait_for_local_condition(lambda: entity.window_state == STATE_ON)

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls([call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF})])

        assert entity.window_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_OFF),
            ]
        )

        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.COMFORT

    # 3. Close the window
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        event_timestamp = now - timedelta(minutes=1)
        try_function = await send_window_change_event(
            entity, False, True, event_timestamp, sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await wait_for_local_condition(lambda: entity.window_state == STATE_OFF)

        assert entity.window_state == STATE_OFF
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
            ],
            any_order=False,
        )

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.COMFORT

    # Clean the entity
    entity.remove_thermostat()


async def test_window_action_eco_temp(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with the eco_temp option"""

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
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_MAX_DURATION: 10,  # Should be 0 for test
            CONF_WINDOW_ACTION: CONF_WINDOW_ECO_TEMP,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured is True

    # 1. Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # 2. Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.window_state is STATE_UNKNOWN
        assert entity.window_auto_state is STATE_UNKNOWN

    # 3. send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 1
        assert mock_heater_on.call_count == 0
        # because the turnoff is called by window_auto and by control_heating
        assert mock_heater_off.call_count >= 1
        assert entity.last_temperature_slope == -6.24
        assert entity.window_auto_state == STATE_ON
        assert entity.window_state == STATE_ON
        # No change on VThermHvacMode
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The eco temp
        assert entity.target_temperature == 17

        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {"type": "start", "cause": "slope alert", "curve_slope": -6.24},
                ),
            ],
            any_order=True,
        )

    # 4. send another 0.1 degre in one minute -> no change
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 17.9, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope is not None
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity.window_auto_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The eco temp
        assert entity.target_temperature == 17

    # 5. send another plus 1.1 degre in one minute -> restore state
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {
                        "type": "end",
                        "cause": "end of slope alert",
                        "curve_slope": 0.42,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == 0.42
        assert entity.window_auto_state == STATE_OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The eco temp
        assert entity.target_temperature == 21

    # Clean the entity
    entity.remove_thermostat()


async def test_window_action_frost_temp(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with the frost_temp option"""

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
            "boost_temp": 21,
            "frost_temp": 10,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_MAX_DURATION: 10,  # Should be 0 for test
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN
    assert entity.window_manager.is_window_auto_configured is True

    # 1. Initialize the slope algo with 2 measurements
    event_timestamp = now + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)
    event_timestamp = event_timestamp + timedelta(minutes=1)
    await send_temperature_change_event(entity, 19, event_timestamp)

    # 2. Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.window_state is STATE_UNKNOWN
        assert entity.window_auto_state is STATE_UNKNOWN

    # 3. send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 1
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count > 0
        assert entity.last_temperature_slope == -6.24
        assert entity.window_auto_state == STATE_ON
        assert entity.window_state == STATE_ON
        # No change on VThermHvacMode
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The eco temp
        assert entity.target_temperature == 10

        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {"type": "start", "cause": "slope alert", "curve_slope": -6.24},
                ),
            ],
            any_order=True,
        )

    # 4. send another 0.1 degre in one minute -> no change
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 17.9, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope is not None
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity.window_auto_state == STATE_ON
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The eco temp
        assert entity.target_temperature == 10

    # 5. send another plus 1.1 degre in one minute -> restore state
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {
                        "type": "end",
                        "cause": "end of slope alert",
                        "curve_slope": 0.42,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == 0.42
        assert entity.window_auto_state == STATE_OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # No change on preset
        assert entity.preset_mode == VThermPreset.BOOST
        # The Boost temp
        assert entity.target_temperature == 21

    # Clean the entity
    entity.remove_thermostat()


async def test_bug_66(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to open/close the window rapidly without side effect"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)

    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 19
    assert entity.window_state is STATE_UNKNOWN

    # Open the window and let the thermostat shut down
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await send_temperature_change_event(entity, 15, now)
        try_window_condition = await send_window_change_event(
            entity, True, False, now, False
        )

        # simulate the call to try_window_condition
        await try_window_condition(None)

        assert mock_send_event.call_count == 1
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count >= 1
        assert mock_condition.call_count == 1

        assert entity.window_state == STATE_ON

    # Close the window but too shortly
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = now + timedelta(minutes=1)
        try_window_condition = await send_window_change_event(
            entity, False, True, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # window state should not have change
        assert entity.window_state == STATE_ON

    # Reopen immediatly with sufficient time
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        try_window_condition = await send_window_change_event(
            entity, True, False, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # still no change
        assert entity.window_state == STATE_ON
        assert entity.hvac_mode == VThermHvacMode_OFF

    # Close the window but with sufficient time this time
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = now + timedelta(minutes=2)
        try_window_condition = await send_window_change_event(
            entity, False, True, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # window state should be Off this time and old state should have been restored
        assert entity.window_state == STATE_OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST


async def test_window_action_frost_temp_preset_change(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Window management with the frost_temp option and change the preset during
    the window is open. This should restore the new preset temperature"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_DELAY: 1,
        },
    )

    vtherm: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert vtherm

    await set_all_climate_preset_temp(
        hass, vtherm, default_temperatures, "theoverswitchmockname"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.preset_mode == VThermPreset.BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_UNKNOWN
    assert vtherm.window_manager.is_window_auto_configured is False

    # 1. Turn on the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, True, False, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have taken the window action
        assert vtherm.target_temperature == 7  # Frost
        # No change
        assert vtherm.preset_mode == VThermPreset.BOOST
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # 2. Change the preset to comfort
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 7  # frost (window is still open)
    assert vtherm.preset_mode == VThermPreset.COMFORT
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # 3.Turn off the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, False, True, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have restore the Comfort preset temperature
        assert vtherm.target_temperature == 19  # restore comfort
        # No change
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    vtherm.remove_thermostat()


async def test_window_action_frost_temp_temp_change(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Window management with the frost_temp option and change the target temp during
    the window is open. This should restore the new temperature"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_DELAY: 1,
        },
    )

    vtherm: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert vtherm

    await set_all_climate_preset_temp(
        hass, vtherm, default_temperatures, "theoverswitchmockname"
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.preset_mode == VThermPreset.BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_UNKNOWN
    assert vtherm.window_manager.is_window_auto_configured is False

    # 1. Turn on the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, True, False, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have taken the window action
        assert vtherm.target_temperature == 7  # Frost
        # No change
        assert vtherm.preset_mode == VThermPreset.BOOST
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # 2. Change the target temperature
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_temperature(temperature=18.5)
    await hass.async_block_till_done()

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 7  # frost (window is still open)
    assert vtherm.preset_mode is VThermPreset.NONE
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # 3.Turn off the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, False, True, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have restore the new target temperature
        assert vtherm.target_temperature == 18.5  # restore new target temperature
        # No change
        assert vtherm.preset_mode is VThermPreset.NONE
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    vtherm.remove_thermostat()


async def test_window_bypass_frost(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with window action = FROST when window is open and then bypass is set to on"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps=default_temperatures)
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_UNKNOWN

    # change temperature to force turning on the heater
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Open the window, condition of time is satisfied, check the thermostat and heater turns off
    # fmt:off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("homeassistant.helpers.condition.state", return_value=True), \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",new_callable=PropertyMock,return_value=True
    ):
    # fmt:on
        try_function = await send_window_change_event(entity, True, False, datetime.now())
        await try_function(None)

        await wait_for_local_condition(lambda: entity.target_temperature == 7)

        # The preset is kept to BOOST but target temp is changed to frost
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 7
        assert entity.window_state == STATE_ON

        assert mock_send_event.call_count == 0

        # Heater should be stopped
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1

    # Call the set bypass service to set bypass ON
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.call_later", return_value=None) as mock_call_later, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",new_callable=PropertyMock,return_value=False):
    # fmt: on
        await entity.service_set_window_bypass_state(True)

        await wait_for_local_condition(lambda: entity.target_temperature == 21)

        assert entity.window_state == STATE_ON
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.target_temperature == 21

        assert mock_send_event.call_count == 0
        assert mock_call_later.call_count == 1
        assert mock_call_later.call_count == 1
        mock_call_later.assert_has_calls(
            [
                call.call_later(hass, 0.0, entity.underlying_entity(0)._turn_on_later),
            ],
            any_order=False,
        )

    # Clean the entity
    entity.remove_thermostat()


async def test_window_action_turn_off_preset_change(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with the turn_off option and change the preset during
    the window is open. This should restore the new preset and temperature when the window is closed"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_DELAY: 1,
        },
    )

    vtherm: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert vtherm

    await set_all_climate_preset_temp(hass, vtherm, default_temperatures, "theoverswitchmockname")

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.preset_mode == VThermPreset.BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_UNKNOWN
    assert vtherm.window_manager.is_window_auto_configured is False

    # 1. Turn on the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, True, False, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have taken the window action
        # No change
        assert vtherm.target_temperature == 21
        assert vtherm.preset_mode == VThermPreset.BOOST
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    # 2. Change the preset to comfort
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await wait_for_local_condition(lambda: vtherm.target_temperature == 19)

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 19
    assert vtherm.preset_mode == VThermPreset.COMFORT
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    # 3.Turn off the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, False, True, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have restore the Comfort preset temperature
        assert vtherm.target_temperature == 19  # restore comfort
        # No change
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    vtherm.remove_thermostat()


async def test_window_action_turn_off_temperature_change(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management with the turn_off option and change the temperature during
    the window is open. This should restore the new temperature when the window is closed"""

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
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
            CONF_WINDOW_DELAY: 1,
        },
    )

    vtherm: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert vtherm

    await set_all_climate_preset_temp(hass, vtherm, default_temperatures, "theoverswitchmockname")

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.BOOST)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.preset_mode == VThermPreset.BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_UNKNOWN
    assert vtherm.window_manager.is_window_auto_configured is False

    # 1. Turn on the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, True, False, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have taken the window action
        # No change
        assert vtherm.target_temperature == 21
        assert vtherm.preset_mode == VThermPreset.BOOST
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    # 2. Change the preset to comfort
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_temperature(temperature=18.5)
    await hass.async_block_till_done()

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 18.5
    assert vtherm.preset_mode is VThermPreset.NONE
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    # 3.Turn off the window sensor
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch("homeassistant.helpers.condition.state", return_value=True):

        try_function = await send_window_change_event(vtherm, False, True, now)

        now = now + timedelta(minutes=2)
        vtherm._set_now(now)
        await try_function(None)

        # VTherm should have restore the Comfort preset temperature
        assert vtherm.target_temperature == 18.5  # restore comfort
        # No change
        assert vtherm.preset_mode is VThermPreset.NONE
        assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    vtherm.remove_thermostat()


async def test_window_and_central_mode_heat_only(hass: HomeAssistant, skip_hass_states_is_state, init_central_config):
    """Test the Window management and the central mode with a heat only."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: True,
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
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19
    assert entity.is_controlled_by_central_mode

    assert entity.window_state is STATE_UNKNOWN

    # Find the select entity
    select_entity = search_entity(hass, "select.central_mode", SELECT_DOMAIN)

    assert select_entity

    # set central mode to HEAT_ONLY
    await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)
    await hass.async_block_till_done()
    assert select_entity.current_option == CENTRAL_MODE_HEAT_ONLY
    assert entity.last_central_mode == CENTRAL_MODE_HEAT_ONLY

    # change temperature to force turning on the heater
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Open the window, condition of time is satisfied, check the thermostat and heater turns off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)

        await try_function(None)
        await wait_for_local_condition(lambda: entity.window_state == STATE_ON)

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls([call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF})])

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 2
        assert mock_condition.call_count == 1
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT
        # assert entity._saved_preset_mode is VThermPreset.COMFORT
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        assert entity.window_state == STATE_ON

    # Close the window
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        try_function = await send_window_change_event(entity, False, True, datetime.now(), sleep=False)

        await try_function(None)

        # Wait for initial delay of heater
        await wait_for_local_condition(lambda: entity.window_state == STATE_OFF and mock_heater_on.call_count >= 1)

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 1
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_HEAT}),
            ],
            any_order=False,
        )
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        # assert entity._saved_hvac_mode is VThermHvacMode_HEAT  # No change
        assert entity.hvac_off_reason is None

    # Clean the entity
    entity.remove_thermostat()


async def test_window_no_motion_absence(hass: HomeAssistant, skip_hass_states_is_state, init_central_config):
    """Test the Window management and a Vtherm in Activity with no motion and absence."""

    temps = {
        "frost": 8,
        "eco": 18,
        "comfort": 19,
        "boost": 20,
        "frost_away": 7,
        "eco_away": 15,
        "comfort_away": 16,
        "boost_away": 17,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: False,
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
            CONF_MOTION_SENSOR: "sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,
            CONF_MOTION_OFF_DELAY: 0,
            CONF_MOTION_PRESET: VThermPreset.COMFORT,
            CONF_NO_MOTION_PRESET: VThermPreset.ECO,
            CONF_PRESENCE_SENSOR: "sensor.mock_presence_sensor",
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps)
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.ACTIVITY)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.ACTIVITY
    # no motion and presence -> ECO temp
    assert entity.target_temperature == 18

    assert entity.window_state is STATE_UNKNOWN

    # 1. Presence detection says no presence and no motion is detected
    # fmt:off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",new_callable=PropertyMock,return_value=False):
    # fmt:on

        await send_presence_change_event(entity, False, True, datetime.now())
        await send_motion_change_event(entity, False, True, datetime.now())

        await wait_for_local_condition(lambda: entity.target_temperature == 15)

        # no motion, no presence -> ECO away temp
        assert entity.target_temperature == 15

        # Heater shoud turn-on
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

        # no changes
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY

    # 2. Open the window, condition of time is satisfied
    # fmt:off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("homeassistant.helpers.condition.state", return_value=True) as mock_condition, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",new_callable=PropertyMock,return_value=False):
    # fmt:on
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)

        await try_function(None)
        await wait_for_local_condition(lambda: entity.window_state == STATE_ON)

        # no motion -> Frost away temp
        assert entity.target_temperature == 7
        # assert entity._saved_target_temp == 15

        # no event due to Window action frost temp
        assert mock_send_event.call_count == 0

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert mock_condition.call_count == 1
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.window_state == STATE_ON

    # 3. Close the window
    # fmt:off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("homeassistant.helpers.condition.state", return_value=True) as mock_condition, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",new_callable=PropertyMock,return_value=False):
    # fmt:on
        try_function = await send_window_change_event(entity, False, True, datetime.now(), sleep=False)

        await try_function(None)

        # no motion, no window -> eco away temp
        assert entity.target_temperature == 15

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 0
        assert mock_send_event.call_count == 0
        assert entity.preset_mode == VThermPreset.ACTIVITY
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

    # Clean the entity
    entity.remove_thermostat()
