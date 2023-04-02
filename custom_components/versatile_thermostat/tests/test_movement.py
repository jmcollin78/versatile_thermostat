""" Test the Window management """
import asyncio
from unittest.mock import patch, call, PropertyMock
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from datetime import datetime, timedelta

import logging

logging.getLogger().setLevel(logging.DEBUG)


async def test_movement_management_time_not_enough(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Presence management when time is not enough"""

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
            "eco_away_temp": 17,
            "comfort_away_temp": 18,
            "boost_away_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,  # important to not been obliged to wait
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is None

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state is "on"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=False
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_motion_change_event(entity, True, False, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is "on"

        assert mock_send_event.call_count == 0
        # Change is not confirmed
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ) as mock_device_active, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, False, True, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is "off"
        assert entity.presence_state is "on"

        assert mock_send_event.call_count == 0
        # Change is not confirmed
        assert mock_heater_on.call_count == 0
        # Because device is active
        assert mock_heater_off.call_count == 1
        assert mock_send_event.call_count == 0


async def test_movement_management_time_enough_and_presence(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Presence management when time is not enough"""

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
            "eco_away_temp": 17,
            "comfort_away_temp": 18,
            "boost_away_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,  # important to not been obliged to wait
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is None

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state is "on"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_motion_change_event(entity, True, False, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because motion is detected yet -> switch to Boost mode
        assert entity.target_temperature == 19
        assert entity.motion_state is "on"
        assert entity.presence_state is "on"

        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, False, True, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is "off"
        assert entity.presence_state is "on"

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        # Because heating is no more necessary
        assert mock_heater_off.call_count == 1
        assert mock_send_event.call_count == 0


async def test_movement_management_time_enoughand_not_presence(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Presence management when time is not enough"""

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
            "eco_away_temp": 17.1,
            "comfort_away_temp": 18.1,
            "boost_away_temp": 19.1,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,  # important to not been obliged to wait
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet and presence is unknown
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is None

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state is "off"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_motion_change_event(entity, True, False, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because motion is detected yet -> switch to Boost away mode
        assert entity.target_temperature == 19.1
        assert entity.motion_state is "on"
        assert entity.presence_state is "off"

        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, False, True, event_timestamp)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18.1
        assert entity.motion_state is "off"
        assert entity.presence_state is "off"

        assert mock_send_event.call_count == 0
        # 18.1 starts heating with a low on_percent
        assert mock_heater_on.call_count == 1
        assert entity.proportional_algorithm.on_percent == 0.11
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0
