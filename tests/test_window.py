# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import asyncio
import logging
from unittest.mock import patch, call, PropertyMock
from datetime import datetime, timedelta

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_OFF

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
        await send_window_change_event(entity, True, False, datetime.now())
        # simulate the call to try_window_condition. No need due to 0 WINDOW_DELAY and sleep after event is sent
        # await try_window_condition(None)

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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_OFF

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
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
        return_value=True,
    ):
        await send_window_change_event(entity, True, False, datetime.now())

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF})]
        )

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 2
        assert mock_condition.call_count == 1
        assert entity.hvac_mode is HVACMode.OFF
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
        return_value=False,
    ):
        try_function = await send_window_change_event(
            entity, False, True, datetime.now(), sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await asyncio.sleep(0.3)

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 1
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
            ],
            any_order=False,
        )
        assert entity.preset_mode is PRESET_BOOST

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_window_auto_fast(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Window management"""

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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_enabled is True

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
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1
        assert entity.last_temperature_slope == -6.24
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
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
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF

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
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
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
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is True
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.fake_window_sensor",
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_enabled is False

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
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater don't turns on
        assert mock_send_event.call_count == 0
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
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
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_enabled is True

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
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # 3. send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp, sleep=False)

        assert entity.last_temperature_slope == -6.24
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False

        assert mock_send_event.call_count == 2
        # The heater turns off
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
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
        assert entity.hvac_mode is HVACMode.OFF

    # 4. This is to avoid that the slope stay under 6, else we will reactivate the window immediatly
    event_timestamp = event_timestamp + timedelta(minutes=1)
    dearm_window_auto = await send_temperature_change_event(
        entity, 19, event_timestamp, sleep=False
    )
    assert entity.last_temperature_slope > -6.0

    # 5. Waits for automatic disable
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ):
        # simulate the expiration of the delay
        await dearm_window_auto(None)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.window_auto_state == STATE_OFF

        assert mock_set_hvac_mode.call_count == 1
        assert round(entity.last_temperature_slope, 3) == -0.29
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 6,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 6,
            CONF_WINDOW_AUTO_MAX_DURATION: 0,  # Should be 0 for test
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 20

    assert entity.window_state is STATE_OFF

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
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 21, event_timestamp)

        # The heater don't turns on
        assert mock_heater_on.call_count == 0
        assert entity.last_temperature_slope == 0.0
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT
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
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        # But the entity is still on
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT

    # Clean the entity
    entity.remove_thermostat()


# PR - Adding Window Bypass
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_enabled is False

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())

        # Heater shoud turn-on
        assert mock_heater_on.call_count >= 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # Set Window ByPass to true
    await entity.service_set_window_bypass_state(True)
    assert entity.window_bypass_state is True

    # entity._window_bypass_state = True

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
        return_value=True,
    ):
        await send_window_change_event(entity, True, False, datetime.now())

        assert mock_send_event.call_count == 0

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 0
        assert mock_condition.call_count == 1
        assert entity.hvac_mode is HVACMode.HEAT
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
        return_value=False,
    ):
        try_function = await send_window_change_event(
            entity, False, True, datetime.now(), sleep=False
        )

        await try_function(None)

        # Wait for initial delay of heater
        await asyncio.sleep(0.3)

        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 0
        assert mock_send_event.call_count == 0
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST

    # Clean the entity
    entity.remove_thermostat()


# PR - Adding Window bypass for window auto algorithm
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_enabled

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
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert entity.is_device_active is True
        assert entity.last_temperature_slope == 0.0
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # send one degre down in one minute with window bypass on
    await entity.service_set_window_bypass_state(True)
    assert entity.window_bypass_state is True

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ):
        event_timestamp = event_timestamp + timedelta(minutes=1)
        await send_temperature_change_event(entity, 18, event_timestamp, sleep=False)

        # No change should have been done
        assert mock_send_event.call_count == 0

        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == -6.24
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT

    # Clean the entity
    entity.remove_thermostat()


# PR - Adding Window bypass AFTER detection have been done should reactivate the heater
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_OFF

    # change temperature to force turning on the heater
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
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
        return_value=True,
    ):
        await send_window_change_event(entity, True, False, datetime.now())

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF})]
        )

        # Heater should not be on
        assert mock_heater_on.call_count == 0
        # One call in set_hvac_mode turn_off and one call in the control_heating for security
        assert mock_heater_off.call_count == 2
        assert mock_condition.call_count == 1
        assert entity.hvac_mode is HVACMode.OFF
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
        return_value=False,
    ):
        await entity.service_set_window_bypass_state(True)

        assert entity.window_state == STATE_ON
        assert entity.preset_mode is PRESET_BOOST
        assert entity.hvac_mode is HVACMode.HEAT
        # assert mock_heater_on.call_count == 1
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
            ],
            any_order=False,
        )

    # Clean the entity
    entity.remove_thermostat()
