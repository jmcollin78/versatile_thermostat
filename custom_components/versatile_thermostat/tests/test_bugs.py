""" Test the Window management """
from unittest.mock import patch
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from datetime import datetime, timedelta

import logging

logging.getLogger().setLevel(logging.DEBUG)


async def test_bug_56(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that in over_climate mode there is no error when underlying climate is not available"""

    the_mock_underlying = MagicMockClimate()
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=None,  # dont find the underlying climate
    ):
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
                CONF_USE_WINDOW_FEATURE: False,
                CONF_USE_MOTION_FEATURE: False,
                CONF_USE_POWER_FEATURE: False,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_CLIMATE: "climate.mock_climate",
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_SECURITY_DELAY_MIN: 5,
                CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            },
        )

        entity: VersatileThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        # cause the underlying climate was not found
        assert entity.is_over_climate is True
        assert entity._underlying_climate is None

        # Should not failed
        entity.update_custom_attributes()

        # try to call _async_control_heating
        try:
            await entity._async_control_heating()
            # an exception should be send
            assert False
        except UnknownEntity:
            pass
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

    # This time the underlying will be found
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=the_mock_underlying,  # dont find the underlying climate
    ):
        # try to call _async_control_heating
        try:
            await entity._async_control_heating()
        except UnknownEntity:
            assert False
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

        # Should not failed
        entity.update_custom_attributes()


async def test_bug_63(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the security_default_on_percent to 0"""

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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.0,  # !! here
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.0,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    assert entity._security_min_on_percent == 0
    assert entity._security_default_on_percent == 0


# Waiting for answer in https://github.com/jmcollin78/versatile_thermostat/issues/64
# Repro case not evident
async def test_bug_64(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the security_default_on_percent to 0"""

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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity


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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,  # !! here
            CONF_DEVICE_POWER: 200,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.window_state is None

    # Open the window and let the thermostat shut down
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
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
        await send_temperature_change_event(entity, 15, now)
        try_window_condition = await send_window_change_event(
            entity, True, False, now, False
        )

        # simulate the call to try_window_condition
        await try_window_condition(None)

        assert mock_send_event.call_count == 1
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 1
        assert mock_condition.call_count == 1

        assert entity.window_state == STATE_ON

    # Close the window but too shortly
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
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
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
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
        try_window_condition = await send_window_change_event(
            entity, True, False, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # still no change
        assert entity.window_state == STATE_ON
        assert entity.hvac_mode == HVACMode.OFF

    # Close the window but with sufficient time this time
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
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
        event_timestamp = now + timedelta(minutes=2)
        try_window_condition = await send_window_change_event(
            entity, False, True, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # window state should be Off this time and old state should have been restored
        assert entity.window_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
