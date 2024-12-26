# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import asyncio
import logging
from unittest.mock import patch, call, PropertyMock, AsyncMock, MagicMock
from datetime import datetime, timedelta

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from custom_components.versatile_thermostat.feature_window_manager import (
    FeatureWindowManager,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_window_feature_manager_create(
    hass: HomeAssistant,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    assert window_manager is not None
    assert window_manager.is_configured is False
    assert window_manager.is_window_auto_configured is False
    assert window_manager.is_window_detected is False
    assert window_manager.window_state == STATE_UNAVAILABLE
    assert window_manager.name == "the name"

    assert len(window_manager._active_listener) == 0

    custom_attributes = {}
    window_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["window_sensor_entity_id"] is None
    assert custom_attributes["window_state"] == STATE_UNAVAILABLE
    assert custom_attributes["window_auto_state"] == STATE_UNAVAILABLE
    assert custom_attributes["is_window_configured"] is False
    assert custom_attributes["is_window_auto_configured"] is False
    assert custom_attributes["window_delay_sec"] == 0
    assert custom_attributes["window_auto_open_threshold"] == 0
    assert custom_attributes["window_auto_close_threshold"] == 0
    assert custom_attributes["window_auto_max_duration"] == 0
    assert custom_attributes["window_action"] is None


@pytest.mark.parametrize(
    "use_window_feature, window_sensor_entity_id, window_delay_sec, window_auto_open_threshold, window_auto_close_threshold, window_auto_max_duration, window_action, is_configured, is_auto_configured, window_state, window_auto_state",
    [
        # fmt: off
        ( True, "sensor.the_window_sensor", 10, None, None, None, CONF_WINDOW_TURN_OFF, True, False, STATE_UNKNOWN, STATE_UNAVAILABLE  ),
        ( False, "sensor.the_window_sensor", 10, None, None, None, CONF_WINDOW_TURN_OFF, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        ( True, "sensor.the_window_sensor", 10, None, None, None, CONF_WINDOW_TURN_OFF, True, False, STATE_UNKNOWN, STATE_UNAVAILABLE  ),
        # delay is missing
        ( True, "sensor.the_window_sensor", None, None, None, None, CONF_WINDOW_TURN_OFF, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # action is missing -> defaults to TURN_OFF
        ( True, "sensor.the_window_sensor", 10, None, None, None, None, True, False, STATE_UNKNOWN, STATE_UNAVAILABLE  ),
        # With Window auto config complete
        ( True, None, None, 1, 2, 3, CONF_WINDOW_TURN_OFF, True, True, STATE_UNKNOWN, STATE_UNKNOWN  ),
        # With Window auto config not complete -> missing open threshold but defaults to 0
        ( True, None, None, None, 2, 3, CONF_WINDOW_TURN_OFF, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # With Window auto config not complete -> missing close threshold
        ( True, None, None, 1, None, 3, CONF_WINDOW_TURN_OFF, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # With Window auto config not complete -> missing max duration threshold  but defaults to 0
        ( True, None, None, 1, 2, None, CONF_WINDOW_TURN_OFF, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # fmt: on
    ],
)
async def test_window_feature_manager_post_init(
    hass: HomeAssistant,
    use_window_feature,
    window_sensor_entity_id,
    window_delay_sec,
    window_auto_open_threshold,
    window_auto_close_threshold,
    window_auto_max_duration,
    window_action,
    is_configured,
    is_auto_configured,
    window_state,
    window_auto_state,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)
    assert window_manager is not None

    # 2. post_init
    window_manager.post_init(
        {
            CONF_USE_WINDOW_FEATURE: use_window_feature,
            CONF_WINDOW_SENSOR: window_sensor_entity_id,
            CONF_WINDOW_DELAY: window_delay_sec,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: window_auto_open_threshold,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: window_auto_close_threshold,
            CONF_WINDOW_AUTO_MAX_DURATION: window_auto_max_duration,
            CONF_WINDOW_ACTION: window_action,
        }
    )

    assert window_manager.is_configured is is_configured
    assert window_manager.is_window_auto_configured == is_auto_configured
    assert window_manager.window_sensor_entity_id == window_sensor_entity_id
    assert window_manager.window_state == window_state
    assert window_manager.window_auto_state == window_auto_state
    assert window_manager.window_delay_sec == window_delay_sec
    assert window_manager.window_auto_open_threshold == window_auto_open_threshold
    assert window_manager.window_auto_close_threshold == window_auto_close_threshold

    custom_attributes = {}
    window_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["window_sensor_entity_id"] == window_sensor_entity_id
    assert custom_attributes["window_state"] == window_state
    assert custom_attributes["window_auto_state"] == window_auto_state
    assert custom_attributes["is_window_bypass"] is False
    assert custom_attributes["is_window_configured"] is is_configured
    assert custom_attributes["is_window_auto_configured"] is is_auto_configured
    assert custom_attributes["is_window_bypass"] is False
    assert custom_attributes["window_delay_sec"] is window_delay_sec
    assert custom_attributes["window_auto_open_threshold"] is window_auto_open_threshold
    assert (
        custom_attributes["window_auto_close_threshold"] is window_auto_close_threshold
    )
    assert custom_attributes["window_auto_max_duration"] is window_auto_max_duration


@pytest.mark.parametrize(
    "current_state, new_state, nb_call, window_state, is_window_detected, changed",
    [
        (STATE_OFF, STATE_ON, 1, STATE_ON, True, True),
        (STATE_OFF, STATE_OFF, 0, STATE_OFF, False, False),
    ],
)
async def test_window_feature_manager_refresh_sensor(
    hass: HomeAssistant,
    current_state,
    new_state,  # new state of motion event
    nb_call,
    window_state,
    is_window_detected,
    changed,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=PRESET_COMFORT)

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    # 2. post_init
    window_manager.post_init(
        {
            CONF_WINDOW_SENSOR: "sensor.the_window_sensor",
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_DELAY: 10,
        }
    )

    # 3. start listening
    window_manager.start_listening()
    assert window_manager.is_configured is True
    assert window_manager.window_state == STATE_UNKNOWN
    assert window_manager.window_auto_state == STATE_UNAVAILABLE

    assert len(window_manager._active_listener) == 1

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", return_value=State("sensor.the_motion_sensor", new_state)) as mock_get_state:
    # fmt:on
        # Configurer les méthodes mockées
        fake_vtherm.async_set_hvac_mode = AsyncMock()
        fake_vtherm.set_hvac_off_reason = MagicMock()

        # force old state for the test
        window_manager._window_state = current_state

        ret = await window_manager.refresh_state()
        assert ret == changed
        assert window_manager.is_configured is True
        # in the refresh there is no delay
        assert window_manager.window_state == new_state
        assert mock_get_state.call_count == 1

        assert mock_get_state.call_count == 1

        assert fake_vtherm.async_set_hvac_mode.call_count == nb_call

        assert fake_vtherm.set_hvac_off_reason.call_count == nb_call

        if nb_call == 1:
            fake_vtherm.async_set_hvac_mode.assert_has_calls(
                [
                    call.async_set_hvac_mode(HVACMode.OFF),
                ]
            )

            fake_vtherm.set_hvac_off_reason.assert_has_calls(
                [
                    call.set_hvac_off_reason(HVAC_OFF_REASON_WINDOW_DETECTION),
                ]
            )

        fake_vtherm.reset_mock()

    # 5. Check custom_attributes
        custom_attributes = {}
        window_manager.add_custom_attributes(custom_attributes)
        assert custom_attributes["window_sensor_entity_id"] == "sensor.the_window_sensor"
        assert custom_attributes["window_state"] == new_state
        assert custom_attributes["window_auto_state"] == STATE_UNAVAILABLE
        assert custom_attributes["is_window_bypass"] is False
        assert custom_attributes["is_window_configured"] is True
        assert custom_attributes["is_window_auto_configured"] is False
        assert custom_attributes["is_window_bypass"] is False
        assert custom_attributes["window_delay_sec"] is 10
        assert custom_attributes["window_auto_open_threshold"] is None
        assert (
            custom_attributes["window_auto_close_threshold"] is None
        )
        assert custom_attributes["window_auto_max_duration"] is None

    window_manager.stop_listening()
    await hass.async_block_till_done()


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
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
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
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
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
        assert entity._saved_hvac_mode is HVACMode.HEAT
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
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity._saved_hvac_mode is HVACMode.HEAT  # No change
        assert entity.hvac_off_reason is None

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured is True

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
    assert entity.is_window_auto_configured is False

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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured is True

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
        new_callable=PropertyMock,
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
        new_callable=PropertyMock,
        return_value=True,
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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
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
        new_callable=PropertyMock,
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
        assert entity._window_auto_algo.is_window_open_detected() is True
        assert entity._window_auto_algo.is_window_close_detected() is False
        # But the entity is still on
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT

    # Clean the entity
    entity.remove_thermostat()


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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 19

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured is False

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

    # entity._is_window_bypass = True

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
        new_callable=PropertyMock,
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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured

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
        assert entity._window_auto_algo.is_window_open_detected() is False
        assert entity._window_auto_algo.is_window_close_detected() is False
        assert entity.hvac_mode is HVACMode.HEAT

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
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
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
        new_callable=PropertyMock,
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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_CLIMATE: "climate.mock_climate",
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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
        hvac_modes=[HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY],
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
        assert entity.window_action == CONF_WINDOW_FAN_ONLY

        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT
        assert entity.target_temperature == 18

        assert entity.window_state is STATE_OFF

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
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.FAN_ONLY}
                )
            ]
        )

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.FAN_ONLY),
            ]
        )

        assert entity.window_state == STATE_ON
        # The underlying should be in FAN_ONLY hvac_mode
        assert entity.hvac_mode is HVACMode.FAN_ONLY
        assert entity._saved_hvac_mode is HVACMode.HEAT
        assert entity.hvac_off_reason is None  # Hvac is not off
        assert entity.preset_mode is PRESET_COMFORT

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
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
            ],
            any_order=False,
        )

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_COMFORT
        assert entity.hvac_off_reason is None

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_CLIMATE: "climate.mock_climate",
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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
        hvac_modes=[HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO],
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
        assert entity.window_action == CONF_WINDOW_FAN_ONLY

        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT
        assert entity.target_temperature == 18

        assert entity.window_state is STATE_OFF

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
        mock_send_event.assert_has_calls(
            [call.send_event(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF})]
        )

        assert entity.window_state == STATE_ON
        assert entity.hvac_mode is HVACMode.OFF
        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.OFF),
            ]
        )

        assert entity._saved_hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_COMFORT

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
        await asyncio.sleep(0.3)

        assert entity.window_state == STATE_OFF
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.HEAT}
                ),
            ],
            any_order=False,
        )

        # The underlying should be in OFF hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_COMFORT

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_WINDOW_ACTION: CONF_WINDOW_ECO_TEMP,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured is True

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
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.window_state is STATE_OFF
        assert entity.window_auto_state is STATE_OFF

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
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == -6.24
        assert entity.window_auto_state == STATE_ON
        assert entity.window_state == STATE_OFF
        # No change on HVACMode
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
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
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
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
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == 0.42
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
        # The eco temp
        assert entity.target_temperature == 21

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.power_manager.overpowering_state is STATE_UNAVAILABLE
    assert entity.target_temperature == 21

    assert entity.window_state is STATE_OFF
    assert entity.is_window_auto_configured is True

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
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.window_state is STATE_OFF
        assert entity.window_auto_state is STATE_OFF

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
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == -6.24
        assert entity.window_auto_state == STATE_ON
        assert entity.window_state == STATE_OFF
        # No change on HVACMode
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
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
        assert round(entity.last_temperature_slope, 3) == -7.49
        assert entity.window_auto_state == STATE_ON
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
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
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
        assert entity.last_temperature_slope == 0.42
        assert entity.window_auto_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
        # No change on preset
        assert entity.preset_mode is PRESET_BOOST
        # The Boost temp
        assert entity.target_temperature == 21

    # Clean the entity
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.window_state is STATE_OFF

    # Open the window and let the thermostat shut down
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
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_BOOST)
    await hass.async_block_till_done()

    assert vtherm.hvac_mode is HVACMode.HEAT
    assert vtherm.preset_mode is PRESET_BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_OFF
    assert vtherm.is_window_auto_configured is False

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
        assert vtherm.preset_mode is PRESET_BOOST
        assert vtherm.hvac_mode is HVACMode.HEAT

    # 2. Change the preset to comfort
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 7  # frost (window is still open)
    assert vtherm.preset_mode is PRESET_COMFORT
    assert vtherm.hvac_mode is HVACMode.HEAT

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
        assert vtherm.preset_mode is PRESET_COMFORT
        assert vtherm.hvac_mode is HVACMode.HEAT

    # Clean the entity
    vtherm.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
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

    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_BOOST)
    await hass.async_block_till_done()

    assert vtherm.hvac_mode is HVACMode.HEAT
    assert vtherm.preset_mode is PRESET_BOOST
    assert vtherm.target_temperature == 21

    assert vtherm.window_state is STATE_OFF
    assert vtherm.is_window_auto_configured is False

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
        assert vtherm.preset_mode is PRESET_BOOST
        assert vtherm.hvac_mode is HVACMode.HEAT

    # 2. Change the target temperature
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_temperature(temperature=18.5)
    await hass.async_block_till_done()

    # VTherm should have taken the new preset temperature
    assert vtherm.target_temperature == 7  # frost (window is still open)
    assert vtherm.preset_mode is PRESET_NONE
    assert vtherm.hvac_mode is HVACMode.HEAT

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
        assert vtherm.preset_mode is PRESET_NONE
        assert vtherm.hvac_mode is HVACMode.HEAT

    # Clean the entity
    vtherm.remove_thermostat()
