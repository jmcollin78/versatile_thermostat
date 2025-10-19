# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, call, PropertyMock, AsyncMock, MagicMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat

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
        ( False, "sensor.the_window_sensor", 10, None, None, None, CONF_WINDOW_FAN_ONLY, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        ( True, "sensor.the_window_sensor", 10, None, None, None, CONF_WINDOW_FROST_TEMP, True, False, STATE_UNKNOWN, STATE_UNAVAILABLE  ),
        # delay is missing
        ( True, "sensor.the_window_sensor", None, None, None, None, CONF_WINDOW_ECO_TEMP, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # action is missing -> defaults to TURN_OFF
        ( True, "sensor.the_window_sensor", 10, None, None, None, None, True, False, STATE_UNKNOWN, STATE_UNAVAILABLE  ),
        # With Window auto config complete
        ( True, None, None, 1, 2, 3, CONF_WINDOW_FAN_ONLY, True, True, STATE_UNKNOWN, STATE_UNKNOWN  ),
        # With Window auto config not complete -> missing open threshold but defaults to 0
        ( True, None, None, None, 2, 3, CONF_WINDOW_FROST_TEMP, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
        # With Window auto config not complete -> missing close threshold
        ( True, None, None, 1, None, 3, CONF_WINDOW_ECO_TEMP, False, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE  ),
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
        (STATE_ON, STATE_OFF, 1, STATE_OFF, False, True),
        (STATE_ON, STATE_ON, 0, STATE_ON, True, False),
    ],
)
async def test_window_feature_manager_refresh_sensor_action_turn_off(
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
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.COMFORT)
    fake_vtherm.async_get_last_state = AsyncMock(return_value={})

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    # 2. post_init
    window_manager.post_init(
        {
            CONF_WINDOW_SENSOR: "sensor.the_window_sensor",
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_DELAY: 10,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        }
    )

    # 3. start listening
    await window_manager.start_listening()
    assert window_manager.is_configured is True
    assert window_manager.window_state == STATE_UNKNOWN
    assert window_manager.window_auto_state == STATE_UNAVAILABLE

    assert len(window_manager._active_listener) == 1

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", return_value=State("sensor.the_motion_sensor", new_state)) as mock_get_state:
    # fmt:on
        # Configurer les méthodes mockées
        fake_vtherm.update_states = AsyncMock()
        fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

        # force old state for the test
        window_manager._window_state = current_state
        if current_state == STATE_ON:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=HVAC_OFF_REASON_WINDOW_DETECTION)
        else:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)

        ret = await window_manager.refresh_state()
        assert ret == changed
        assert window_manager.is_configured is True
        # in the refresh there is no delay
        assert window_manager.window_state == new_state
        assert mock_get_state.call_count == 1


        if nb_call == 1:
            if new_state == current_state:
                assert fake_vtherm.update_states.call_count == 0
            else:
                assert fake_vtherm.update_states.call_count == 1
                fake_vtherm.update_states.assert_has_calls(
                    [
                        call.update_states(True),
                    ]
                )
        else:
            assert fake_vtherm.update_states.call_count == 0

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


@pytest.mark.parametrize(
    "current_state, new_state, nb_call, window_state, is_window_detected, changed",
    [
        (STATE_OFF, STATE_ON, 1, STATE_ON, True, True),
        (STATE_OFF, STATE_OFF, 0, STATE_OFF, False, False),
        (STATE_ON, STATE_OFF, 1, STATE_OFF, False, True),
        (STATE_ON, STATE_ON, 0, STATE_ON, True, False),
    ],
)
async def test_window_feature_manager_refresh_sensor_action_frost_only(
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
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.COMFORT)
    type(fake_vtherm).last_central_mode = PropertyMock(return_value=None)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    # 2. post_init
    window_manager.post_init(
        {
            CONF_WINDOW_SENSOR: "sensor.the_window_sensor",
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_DELAY: 10,
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
        }
    )

    # 3. start listening
    await window_manager.start_listening()
    assert window_manager.is_configured is True
    assert window_manager.window_state == STATE_UNKNOWN
    assert window_manager.window_auto_state == STATE_UNAVAILABLE

    assert len(window_manager._active_listener) == 1

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", return_value=State("sensor.the_motion_sensor", new_state)) as mock_get_state:
    # fmt:on
        # Configurer les méthodes mockées
        fake_vtherm.set_hvac_off_reason = MagicMock()
        fake_vtherm.update_states = AsyncMock()
        fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

        # force old state for the test
        window_manager._window_state = current_state
        if current_state == STATE_ON:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=HVAC_OFF_REASON_WINDOW_DETECTION)
        else:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)

        ret = await window_manager.refresh_state()
        assert ret == changed
        assert window_manager.is_configured is True
        # in the refresh there is no delay
        assert window_manager.window_state == new_state
        assert mock_get_state.call_count == 1

        assert fake_vtherm.set_hvac_off_reason.call_count == 0

        if nb_call == 1:
            if new_state == current_state:
                assert fake_vtherm.update_states.call_count == 0
            else:
                assert fake_vtherm.update_states.call_count == 1
                fake_vtherm.update_states.assert_has_calls(
                    [
                        call.update_states(True),
                    ]
                )
        else:
            assert fake_vtherm.update_states.call_count == 0

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


@pytest.mark.parametrize(
    "current_state, long_enough, new_state, nb_call, window_state, is_window_detected",
    [
        (STATE_OFF, True, STATE_ON, 1, STATE_ON, True),
        (STATE_OFF, True, STATE_OFF, 0, STATE_OFF, False),
        (STATE_ON, True, STATE_OFF, 1, STATE_OFF, False),
        (STATE_ON, True, STATE_ON, 0, STATE_ON, True),
        (STATE_OFF, False, STATE_ON, 0, STATE_OFF, False),
        (STATE_ON, False, STATE_OFF, 0, STATE_ON, True),
    ],
)
async def test_window_feature_manager_sensor_event_action_turn_off(
    hass: HomeAssistant,
    current_state,
    long_enough,
    new_state,  # new state of motion event
    nb_call,
    window_state,
    is_window_detected,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.COMFORT)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    # 2. post_init
    window_manager.post_init(
        {
            CONF_WINDOW_SENSOR: "sensor.the_window_sensor",
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_DELAY: 10,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        }
    )

    # 3. start listening
    await window_manager.start_listening()
    assert len(window_manager._active_listener) == 1

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.helpers.condition.state", return_value=long_enough):
    # fmt:on
        # Configurer les méthodes mockées
        fake_vtherm.update_states = AsyncMock()
        fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

        # force old state for the test
        window_manager._window_state = current_state
        if current_state == STATE_ON:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=HVAC_OFF_REASON_WINDOW_DETECTION)
        else:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)

        try_window_condition = await window_manager._window_sensor_changed(
            event=Event(
                event_type=EVENT_STATE_CHANGED,
                data={
                    "entity_id": "sensor.the_window_sensor",
                    "new_state": State("sensor.the_window_sensor", new_state),
                    "old_state": State("sensor.the_window_sensor", current_state),
                }))
        assert try_window_condition is not None

        await try_window_condition(None)

        # There is change only if long enough
        if long_enough:
            assert window_manager.window_state == new_state
        else:
            assert window_manager.window_state == current_state


        if nb_call == 1:
            if new_state == current_state:
                assert fake_vtherm.update_states.call_count == 0
            else:
                assert fake_vtherm.update_states.call_count == 1
                fake_vtherm.update_states.assert_has_calls(
                    [
                        call.update_states(True),
                    ]
                )
        else:
            assert fake_vtherm.update_states.call_count == 0

        fake_vtherm.reset_mock()

    # 5. Check custom_attributes
        custom_attributes = {}
        window_manager.add_custom_attributes(custom_attributes)
        assert custom_attributes["window_sensor_entity_id"] == "sensor.the_window_sensor"
        assert custom_attributes["window_state"] == new_state if long_enough else current_state
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


@pytest.mark.parametrize(
    "current_state, long_enough, new_state, nb_call, window_state, is_window_detected",
    [
        (STATE_OFF, True, STATE_ON, 1, STATE_ON, True),
        (STATE_OFF, True, STATE_OFF, 0, STATE_OFF, False),
        (STATE_ON, True, STATE_OFF, 1, STATE_OFF, False),
        (STATE_ON, True, STATE_ON, 0, STATE_ON, True),
        (STATE_OFF, False, STATE_ON, 0, STATE_OFF, False),
        (STATE_ON, False, STATE_OFF, 0, STATE_ON, True),
    ],
)
async def test_window_feature_manager_event_sensor_action_frost_only(
    hass: HomeAssistant,
    current_state,
    long_enough,
    new_state,  # new state of motion event
    nb_call,
    window_state,
    is_window_detected,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.COMFORT)
    type(fake_vtherm).last_central_mode = PropertyMock(return_value=None)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    # 1. creation
    window_manager = FeatureWindowManager(fake_vtherm, hass)

    # 2. post_init
    window_manager.post_init(
        {
            CONF_WINDOW_SENSOR: "sensor.the_window_sensor",
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_DELAY: 10,
            CONF_WINDOW_ACTION: CONF_WINDOW_FROST_TEMP,
        }
    )

    # 3. start listening
    await window_manager.start_listening()

    # 4. test refresh with the parametrized
    # fmt:off
    with patch("homeassistant.helpers.condition.state", return_value=long_enough):
    # fmt:on
        # Configurer les méthodes mockées
        fake_vtherm.set_hvac_off_reason = MagicMock()
        fake_vtherm.update_states = AsyncMock()
        fake_vtherm.async_get_last_state = AsyncMock(return_value={})

        # force old state for the test
        window_manager._window_state = current_state
        if current_state == STATE_ON:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=HVAC_OFF_REASON_WINDOW_DETECTION)
        else:
            type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)

        try_window_condition = await window_manager._window_sensor_changed(
            event=Event(
                event_type=EVENT_STATE_CHANGED,
                data={
                    "entity_id": "sensor.the_window_sensor",
                    "new_state": State("sensor.the_window_sensor", new_state),
                    "old_state": State("sensor.the_window_sensor", current_state),
                }))
        assert try_window_condition is not None

        await try_window_condition(None)

        if long_enough:
            assert window_manager.window_state == new_state
        else:
            assert window_manager.window_state == current_state

        assert fake_vtherm.set_hvac_off_reason.call_count == 0

        if nb_call == 1:
            if new_state == current_state:
                assert fake_vtherm.update_states.call_count == 0
            else:
                assert fake_vtherm.update_states.call_count == 1
                fake_vtherm.update_states.assert_has_calls(
                    [
                        call.update_states(True),
                    ]
                )
        else:
            assert fake_vtherm.update_states.call_count == 0

        fake_vtherm.reset_mock()

    # 5. Check custom_attributes
        custom_attributes = {}
        window_manager.add_custom_attributes(custom_attributes)
        assert custom_attributes["window_sensor_entity_id"] == "sensor.the_window_sensor"
        assert custom_attributes["window_state"] == new_state if long_enough else current_state
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


@pytest.mark.parametrize(
    "current_state, in_cycle, new_temp, new_state, nb_call, window_state, is_window_detected",
    [
        (STATE_OFF, True, 10, STATE_ON, 1, STATE_ON, True),
        (STATE_ON, True, 10, STATE_ON, 0, STATE_ON, True),
        (STATE_ON, True, 20, STATE_OFF, 1, STATE_OFF, False),
        (STATE_OFF, True, 20, STATE_OFF, 0, STATE_OFF, False),
    ],
)
async def test_window_feature_manager_window_auto(
    hass: HomeAssistant,
    current_state,
    in_cycle,
    new_temp,
    new_state,  # new state of motion event
    nb_call,
    window_state,
    is_window_detected,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).preset_mode = PropertyMock(return_value=VThermPreset.COMFORT)
    type(fake_vtherm).hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)
    type(fake_vtherm).last_central_mode = PropertyMock(return_value=None)
    type(fake_vtherm).proportional_algorithm = PropertyMock(return_value=None)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    # 1. creation / post_init / start listening
    window_manager = FeatureWindowManager(fake_vtherm, hass)
    window_manager.post_init(
        {
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 3,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
            CONF_WINDOW_AUTO_MAX_DURATION: 10,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        }
    )
    assert window_manager.is_window_auto_configured is True
    await window_manager.start_listening()

    # 2. Call manage window auto
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # Add a fake temp point for the window_auto_algo. We need at least 4 points
    for i in range(0, 4):
        window_manager._window_auto_algo.add_temp_measurement(
            17 + (i * (new_temp - 17) / 4), now, True
        )
        now = now + timedelta(minutes=5)

    # fmt:off
    with patch("custom_components.versatile_thermostat.feature_window_manager.FeatureWindowManager.update_window_state") as mock_update_window_state:
    #fmt: on
        now = now + timedelta(minutes=10)
        # From 17 to new_temp in 10 minutes
        type(fake_vtherm).ema_temperature = PropertyMock(return_value=new_temp)
        type(fake_vtherm).last_temperature_measure = PropertyMock(return_value=now)
        type(fake_vtherm).now = PropertyMock(return_value=now)
        fake_vtherm.send_event = MagicMock()

        window_manager._window_auto_state = current_state

        dearm_window_auto = await window_manager.manage_window_auto(in_cycle=in_cycle)
        assert dearm_window_auto is not None

        assert mock_update_window_state.call_count == nb_call
        if nb_call > 0:
            mock_update_window_state.assert_has_calls(
                [
                    call.update_window_state(new_state),
                ]
            )
            if new_state == STATE_ON:
                assert window_manager._window_call_cancel is not None

        assert window_manager.window_auto_state == new_state
        # update_window_state is mocked
        # assert window_manager.window_state == new_state

    window_manager.stop_listening()
    await hass.async_block_till_done()
