# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Window management """
from datetime import datetime, timedelta
import logging
from unittest.mock import patch

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_SECURITY_DELAY_MIN: 10,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 10,  # important to not been obliged to wait
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode, when someone is present. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is None

        event_timestamp = now - timedelta(minutes=5)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == "on"

    # starts detecting motion with time not enough
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=4)
        try_condition = await send_motion_change_event(entity, True, False, event_timestamp)

        # Will return False -> we will stay on movement False
        await try_condition(None)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        # state is not changed if time is not enough
        assert entity.motion_state is STATE_OFF
        assert entity.presence_state == STATE_ON

        assert mock_send_event.call_count == 0
        # Change is not confirmed
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # starts detecting motion with time enough this time
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=3)
        try_condition = await send_motion_change_event(entity, True, False, event_timestamp)

        # Will return True -> we will switch to movement On
        await try_condition(None)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because motion is detected yet
        assert entity.target_temperature == 19
        assert entity.motion_state == STATE_ON
        assert entity.presence_state == STATE_ON

    # stop detecting motion with off delay too low
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ) as mock_device_active, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=2)
        try_condition = await send_motion_change_event(entity, False, True, event_timestamp)

        # Will return False -> we will stay to movement On
        await try_condition(None)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 19
        assert entity.motion_state == STATE_ON
        assert entity.presence_state == STATE_ON

        assert mock_send_event.call_count == 0
        # The heater must heat now
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with off delay enough long
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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
        event_timestamp = now - timedelta(minutes=1)
        try_condition = await send_motion_change_event(entity, False, True, event_timestamp)

        # Will return True -> we will switch to movement Off
        await try_condition(None)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state == STATE_OFF
        assert entity.presence_state == STATE_ON

        assert mock_send_event.call_count == 0
        # The heater must stop heating now
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_movement_management_time_enough_and_presence(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Motion management when time is not enough"""

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

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
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
        assert entity.presence_state == "on"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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
        assert entity.motion_state == "on"
        assert entity.presence_state == "on"

        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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
        assert entity.motion_state == "off"
        assert entity.presence_state == "on"

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        # Because heating is no more necessary
        assert mock_heater_off.call_count == 1
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
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
        assert entity.presence_state == "off"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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
        assert entity.motion_state == "on"
        assert entity.presence_state == "off"

        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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
        assert entity.motion_state == "off"
        assert entity.presence_state == "off"

        assert mock_send_event.call_count == 0
        # 18.1 starts heating with a low on_percent
        assert mock_heater_on.call_count == 1
        assert entity.proportional_algorithm.on_percent == 0.11
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_movement_management_with_stop_during_condition(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Motion management when the movement sensor switch to off and then to on during the test condition"""

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
            CONF_MOTION_DELAY: 10,
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state is None

        event_timestamp = now - timedelta(minutes=6)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state == "off"

    # starts detecting motion
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):  # Not needed for this test
        event_timestamp = now - timedelta(minutes=5)
        try_condition1 = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        assert try_condition1 is not None

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because motion is detected yet -> switch to Boost mode
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state == "off"

        # Send a stop detection
        event_timestamp = now - timedelta(minutes=4)
        try_condition = await send_motion_change_event(
            entity, False, True, event_timestamp
        )
        assert try_condition is None  # The timer should not have been stopped

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state == "off"

        # Resend a start detection
        event_timestamp = now - timedelta(minutes=3)
        try_condition = await send_motion_change_event(
            entity, True, False, event_timestamp
        )
        assert (
            try_condition is None
        )  # The timer should not have been restarted (we keep the first one)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # still no motion detected
        assert entity.target_temperature == 18
        assert entity.motion_state is None
        assert entity.presence_state == "off"

        await try_condition1(None)
        # We should have switch this time
        assert entity.target_temperature == 19  # Boost
        assert entity.motion_state == "on"  # switch to movement on
        assert entity.presence_state == "off"  # Non change


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_movement_management_with_stop_during_condition_last_state_on(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Motion management when the movement sensor switch to off and then to on during the test condition"""

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
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 10,
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "comfort",
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 0. start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_ACTIVITY)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is None

        event_timestamp = now - timedelta(minutes=6)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

    # 1. starts detecting motion but the sensor is off
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch("homeassistant.helpers.condition.state", return_value=False), patch(
        "homeassistant.core.StateMachine.get", return_value=STATE_OFF
    ):
        event_timestamp = now - timedelta(minutes=5)
        try_condition1 = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        assert try_condition1 is not None

        await try_condition1(None)

        # because no motion is detected yet -> condition.state is False and sensor is not active
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_OFF

    # 2. starts detecting motion but the sensor is on
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ), patch("homeassistant.helpers.condition.state", return_value=False), patch(
        "homeassistant.core.StateMachine.get", return_value=STATE_ON
    ):
        event_timestamp = now - timedelta(minutes=5)
        try_condition1 = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        assert try_condition1 is not None

        await try_condition1(None)

        # because no motion is detected yet -> condition.state is False and sensor is not active
        assert entity.target_temperature == 19
        assert entity.motion_state is STATE_ON
