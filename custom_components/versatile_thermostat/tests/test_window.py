""" Test the Window management """
import asyncio
from unittest.mock import patch, call, PropertyMock
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from datetime import datetime, timedelta

import logging

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

    entity: VersatileThermostat = await create_thermostat(
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

    assert entity.window_state is None

    # Open the window, but condition of time is not satisfied and check the thermostat don't turns off
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
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

    entity: VersatileThermostat = await create_thermostat(
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

    assert entity.window_state is None

    # Open the window, but condition of time is not satisfied and check the thermostat don't turns off
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        await send_temperature_change_event(entity, 15, datetime.now())
        await send_window_change_event(entity, True, False, datetime.now())

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF})]
        )

        # TODO should be == 1
        assert mock_heater_on.call_count >= 1
        # One call in turn_oiff and one call in the control_heating
        assert mock_heater_off.call_count == 1
        assert mock_condition.call_count == 1

        assert entity.window_state == STATE_ON

        # Close the window
        try_window_condition = await send_window_change_event(
            entity, False, True, datetime.now()
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)
        assert entity.window_state == STATE_OFF
        assert mock_heater_on.call_count == 2
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
            ],
            any_order=False,
        )
        assert entity.preset_mode is PRESET_BOOST


async def test_window_auto_fast(hass: HomeAssistant, skip_hass_states_is_state):
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

    entity: VersatileThermostat = await create_thermostat(
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

    assert entity.window_state is None

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 1
        assert entity.last_temperature_slope is None
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_temperature_change_event(entity, 18, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1
        assert entity.last_temperature_slope == -1
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
                call.send_event(
                    EventType.WINDOW_AUTO_EVENT,
                    {"type": "start", "cause": "slope alert", "curve_slope": -1.0},
                ),
            ],
            any_order=True,
        )

    # send another 0.1 degre in one minute -> no change
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_temperature_change_event(entity, 17.9, event_timestamp)

        # The heater turns on
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert round(entity.last_temperature_slope, 3) == -0.1 * 0.5 - 1 * 0.5
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF

    # send another plus 1.1 degre in one minute -> restore state
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        event_timestamp = now - timedelta(minutes=1)
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
                        "curve_slope": 0.27500000000000036,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert round(entity.last_temperature_slope, 3) == 0.275
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is True
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT


async def test_window_auto_auto_stop(hass: HomeAssistant, skip_hass_states_is_state):
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
            CONF_WINDOW_AUTO_MAX_DURATION: 0,  # Should be 0 for test
        },
    )

    entity: VersatileThermostat = await create_thermostat(
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

    assert entity.window_state is None

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 19, event_timestamp)

        # The heater turns on
        assert mock_heater_on.call_count == 1
        assert entity.last_temperature_slope is None
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_temperature_change_event(entity, 18, event_timestamp, sleep=False)

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
                        "curve_slope": -1.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1
        assert entity.last_temperature_slope == -1
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF

        # Waits for automatic disable
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=False,
    ):
        await asyncio.sleep(0.3)

        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert round(entity.last_temperature_slope, 3) == -1
        # Because the algorithm is not aware of the expiration, for the algo we are still in alert
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST


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
            CONF_WINDOW_AUTO_MAX_DURATION: 0,  # Should be 0 for test
        },
    )

    entity: VersatileThermostat = await create_thermostat(
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

    assert entity.window_state is None

    # Make the temperature down
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 21.5, event_timestamp)

        # The heater turns on
        assert mock_heater_on.call_count == 0
        assert entity.last_temperature_slope is None
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.proportional_algorithm.on_percent == 0.0

    # send one degre down in one minute
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._is_device_active",
        return_value=True,
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_temperature_change_event(entity, 20, event_timestamp)

        # The heater turns on but no alert because the heater was not heating
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == -1.5
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
