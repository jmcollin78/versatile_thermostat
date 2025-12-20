# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable, too-many-lines

""" Test the Window management """
from datetime import datetime, timedelta
import logging
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_motion_manager import (
    FeatureMotionManager,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "current_state, new_state, temp, nb_call, motion_state, is_motion_detected, preset_refresh, changed",
    [
        (STATE_OFF, STATE_ON, 21, 1, STATE_ON, True, VThermPreset.BOOST, True),
        # motion is ON. So is_motion_detected is true and preset is BOOST
        (STATE_OFF, STATE_ON, 21, 1, STATE_ON, True, VThermPreset.BOOST, True),
        # current_state is ON and motion is OFF. So is_motion_detected is false and preset is ECO
        (STATE_ON, STATE_OFF, 17, 1, STATE_OFF, False, VThermPreset.ECO, True),
    ],
)
async def test_motion_feature_manager_refresh(
    hass: HomeAssistant,
    current_state,
    new_state,  # new state of motion event
    temp,
    nb_call,
    motion_state,
    is_motion_detected,
    preset_refresh,
    changed,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.ACTIVITY)

    # 1. creation
    motion_manager = FeatureMotionManager(fake_vtherm, hass)

    assert motion_manager is not None
    assert motion_manager.is_configured is False
    assert motion_manager.is_motion_detected is False
    assert motion_manager.motion_state == STATE_UNAVAILABLE
    assert motion_manager.name == "the name"

    assert len(motion_manager._active_listener) == 0

    custom_attributes = {}
    motion_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_motion_configured"] is False
    assert custom_attributes.get("motion_manager") is None

    # 2. post_init
    motion_manager.post_init(
        {
            CONF_MOTION_SENSOR: "sensor.the_motion_sensor",
            CONF_USE_MOTION_FEATURE: True,
            CONF_MOTION_DELAY: 10,
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: VThermPreset.BOOST,
            CONF_NO_MOTION_PRESET: VThermPreset.ECO,
        }
    )

    assert motion_manager.is_configured is True
    assert motion_manager.motion_state == STATE_UNKNOWN
    assert motion_manager.is_motion_detected is False

    custom_attributes = {}
    motion_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_motion_configured"] is True
    assert custom_attributes["motion_manager"]["motion_sensor_entity_id"] == "sensor.the_motion_sensor"
    assert custom_attributes["motion_manager"]["motion_state"] == STATE_UNKNOWN
    assert custom_attributes["motion_manager"]["motion_preset"] is VThermPreset.BOOST
    assert custom_attributes["motion_manager"]["no_motion_preset"] is VThermPreset.ECO
    assert custom_attributes["motion_manager"]["motion_delay_sec"] == 10
    assert custom_attributes["motion_manager"]["motion_off_delay_sec"] == 30

    # 3. start listening
    await motion_manager.start_listening()
    assert motion_manager.is_configured is True
    assert motion_manager.motion_state == STATE_UNKNOWN
    assert motion_manager.is_motion_detected is False

    assert len(motion_manager._active_listener) == 1

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", return_value=State("sensor.the_motion_sensor", new_state)) as mock_get_state:
    # fmt:on
        # force old state for the test
        motion_manager._motion_state = current_state

        ret = await motion_manager.refresh_state()
        assert ret == changed
        assert motion_manager.is_configured is True
        # in the refresh there is no delay
        assert motion_manager.motion_state == new_state
        assert motion_manager.is_motion_detected is is_motion_detected

        assert mock_get_state.call_count == 1

        fake_vtherm.reset_mock()

    # 5. Check custom_attributes
        custom_attributes = {}
        motion_manager.add_custom_attributes(custom_attributes)
        assert custom_attributes["is_motion_configured"] is True
        assert custom_attributes["motion_manager"]["motion_sensor_entity_id"] == "sensor.the_motion_sensor"
        assert custom_attributes["motion_manager"]["motion_state"] == new_state
        assert custom_attributes["motion_manager"]["motion_preset"] is VThermPreset.BOOST
        assert custom_attributes["motion_manager"]["no_motion_preset"] is VThermPreset.ECO
        assert custom_attributes["motion_manager"]["motion_delay_sec"] == 10
        assert custom_attributes["motion_manager"]["motion_off_delay_sec"] == 30

    motion_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "current_state, long_enough, new_state, temp, nb_call, motion_state, is_motion_detected, preset_event, changed",
    [
        (STATE_OFF, True, STATE_ON, 21, 1, STATE_ON, True, VThermPreset.BOOST, True),
        # motion is ON but for not enough time but sensor is on at the end. So is_motion_detected is true and preset is BOOST
        (STATE_OFF, False, STATE_ON, 21, 1, STATE_ON, True, VThermPreset.BOOST, True),
        # motion is OFF for enough time. So is_motion_detected is false and preset is ECO
        (STATE_ON, True, STATE_OFF, 17, 1, STATE_OFF, False, VThermPreset.ECO, True),
        # motion is OFF for not enough time. So is_motion_detected is false and preset is ECO
        (STATE_ON, False, STATE_OFF, 21, 1, STATE_ON, True, VThermPreset.BOOST, True),
    ],
)
async def test_motion_feature_manager_event(
    hass: HomeAssistant,
    current_state,
    long_enough,
    new_state,  # new state of motion event
    temp,
    nb_call,
    motion_state,
    is_motion_detected,
    preset_event,
    changed,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.ACTIVITY)

    # 1. iniitialization creation, post_init, start_listening
    motion_manager = FeatureMotionManager(fake_vtherm, hass)
    motion_manager.post_init(
        {
            CONF_MOTION_SENSOR: "sensor.the_motion_sensor",
            CONF_USE_MOTION_FEATURE: True,
            CONF_MOTION_DELAY: 10,
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: VThermPreset.BOOST,
            CONF_NO_MOTION_PRESET: VThermPreset.ECO,
        }
    )
    await motion_manager.start_listening()

    # 2. test _motion_sensor_changed with the parametrized
    # fmt: off
    with patch("homeassistant.helpers.condition.state", return_value=long_enough), \
        patch("homeassistant.core.StateMachine.get", return_value=State("sensor.the_motion_sensor", new_state)):
    # fmt: on

        # force old state for the test
        motion_manager._motion_state = current_state

        delay = await motion_manager._motion_sensor_changed(
            event=Event(
                event_type=EVENT_STATE_CHANGED,
                data={
                    "entity_id": "sensor.the_motion_sensor",
                    "new_state": State("sensor.the_motion_sensor", new_state),
                    "old_state": State("sensor.the_motion_sensor", STATE_UNAVAILABLE),
                }))
        assert delay is not None

        await delay(None)
        assert motion_manager.is_configured is True
        assert motion_manager.motion_state == motion_state
        assert motion_manager.is_motion_detected is is_motion_detected


    fake_vtherm.reset_mock()

    # 3. Check custom_attributes
    custom_attributes = {}
    motion_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_motion_configured"] is True
    assert custom_attributes["motion_manager"]["motion_sensor_entity_id"] == "sensor.the_motion_sensor"
    assert custom_attributes["motion_manager"]["motion_state"] == motion_state
    assert custom_attributes["motion_manager"]["motion_preset"] is VThermPreset.BOOST
    assert custom_attributes["motion_manager"]["no_motion_preset"] is VThermPreset.ECO
    assert custom_attributes["motion_manager"]["motion_delay_sec"] == 10
    assert custom_attributes["motion_manager"]["motion_off_delay_sec"] == 30

    motion_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_motion_management_time_not_enough(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Presence management when time is not enough"""
    temps = {
        "frost": 10,
        "eco": 17,
        "comfort": 18,
        "boost": 19,
        "frost_away": 10,
        "eco_away": 17,
        "comfort_away": 18,
        "boost_away": 19,
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
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 10,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. start heating, in boost mode, when someone is present. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN

        event_timestamp = now - timedelta(minutes=5)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == STATE_ON

    # 2. starts detecting motion with time not enough
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="binary_sensor.mock_motion_sensor", state=STATE_OFF),
    ):
        event_timestamp = now - timedelta(minutes=4)
        try_condition = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        # Will return False -> we will stay on movement False
        await try_condition(None)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
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
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=3)
        try_condition = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        # Will return True -> we will switch to movement On
        await try_condition(None)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because motion is detected yet
        assert entity.target_temperature == 19
        assert entity.motion_state == STATE_ON
        assert entity.presence_state == STATE_ON

    # stop detecting motion with off delay too low
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ) as mock_device_active, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="binary_sensor.mock_motion_sensor", state=STATE_OFF),
    ):
        event_timestamp = now - timedelta(minutes=2)
        try_condition = await send_motion_change_event(
            entity, False, True, event_timestamp
        )

        # Will return False -> we will stay to movement On
        await try_condition(None)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
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
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ) as mock_device_active, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition:
        event_timestamp = now - timedelta(minutes=1)
        try_condition = await send_motion_change_event(
            entity, False, True, event_timestamp
        )

        # Will return True -> we will switch to movement Off
        await try_condition(None)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
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
async def test_motion_management_time_enough_and_presence(
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == "on"

    # starts detecting motion
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_motion_change_event(entity, True, False, event_timestamp)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because motion is detected yet -> switch to Boost mode
        assert entity.target_temperature == 19
        assert entity.motion_state == STATE_ON
        assert entity.presence_state == STATE_ON
        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, False, True, event_timestamp)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state == STATE_OFF
        assert entity.presence_state == STATE_ON

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        # Because heating is no more necessary
        assert mock_heater_off.call_count == 1
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_motion_management_time_enough_and_not_presence(
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet and presence is unknown
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state == STATE_OFF

    # starts detecting motion
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_motion_change_event(entity, True, False, event_timestamp)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because motion is detected yet -> switch to Boost away mode
        assert entity.target_temperature == 19.1
        assert entity.motion_state == STATE_ON
        assert entity.presence_state == STATE_OFF

        assert mock_send_event.call_count == 0
        # Change is confirmed. Heater should be started
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0

    # stop detecting motion with confirmation of stop
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        event_timestamp = now - timedelta(minutes=2)
        await send_motion_change_event(entity, False, True, event_timestamp)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18.1
        assert entity.motion_state == STATE_OFF
        assert entity.presence_state == STATE_OFF
        assert mock_send_event.call_count == 0
        # 18.1 starts heating with a low on_percent
        assert mock_heater_on.call_count == 1
        assert entity.proportional_algorithm.on_percent == 0.11
        assert mock_heater_off.call_count == 0
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_motion_management_with_stop_during_condition(
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN

        event_timestamp = now - timedelta(minutes=6)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state == STATE_OFF

    # starts detecting motion
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):  # Not needed for this test
        event_timestamp = now - timedelta(minutes=5)
        try_condition1 = await send_motion_change_event(
            entity, True, False, event_timestamp
        )

        assert try_condition1 is not None

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because motion is detected yet -> switch to Boost mode
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state == STATE_OFF
        # Send a stop detection
        event_timestamp = now - timedelta(minutes=4)
        try_condition = await send_motion_change_event(
            entity, False, True, event_timestamp
        )
        assert try_condition is None  # The timer should not have been stopped

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state == STATE_OFF

        # Resend a start detection
        event_timestamp = now - timedelta(minutes=3)
        try_condition = await send_motion_change_event(
            entity, True, False, event_timestamp
        )
        assert (
            try_condition is None
        )  # The timer should not have been restarted (we keep the first one)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # still no motion detected
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state == STATE_OFF

        await try_condition1(None)
        # We should have switch this time
        assert entity.target_temperature == 19  # Boost
        assert entity.motion_state == STATE_ON  # switch to movement on
        assert entity.presence_state == STATE_OFF  # Non change


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_motion_management_with_stop_during_condition_last_state_on(
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.ACTIVITY
        # because no motion is detected yet
        assert entity.target_temperature == 18
        assert entity.motion_state is STATE_UNKNOWN

        event_timestamp = now - timedelta(minutes=6)
        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

    # 1. starts detecting motion but the sensor is off
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch("homeassistant.helpers.condition.state", return_value=False), patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="binary_sensor.mock_motion_sensor", state=STATE_OFF),
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
        new_callable=PropertyMock,
        return_value=True,
    ), patch("homeassistant.helpers.condition.state", return_value=False), patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="binary_sensor.mock_motion_sensor", state=STATE_ON),
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
