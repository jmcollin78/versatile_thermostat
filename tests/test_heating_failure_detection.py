# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the Heating Failure Detection feature """
from unittest.mock import patch, PropertyMock, MagicMock
from datetime import timedelta, datetime
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_heating_failure_detection_manager import (
    FeatureHeatingFailureDetectionManager,
)
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


# ========================================================================
# PART 1: Unit tests for the manager alone
# ========================================================================


async def test_heating_failure_manager_create(hass: HomeAssistant):
    """Test the FeatureHeatingFailureDetectionManager class creation"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)

    assert manager is not None
    assert manager.is_configured is False
    assert manager.is_failure_detected is False
    assert manager.heating_failure_state is STATE_UNAVAILABLE
    assert manager.cooling_failure_state is STATE_UNAVAILABLE
    assert manager.name == "the name"

    custom_attributes = {}
    manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_heating_failure_detection_configured"] is False
    assert custom_attributes.get("heating_failure_detection_manager") is None


@pytest.mark.parametrize(
    "use_feature, heating_threshold, cooling_threshold, delay, tolerance, is_configured, heating_state, cooling_state",
    [
        # fmt: off
        (True, 0.9, 0.0, 15, 0.5, True, STATE_UNKNOWN, STATE_UNKNOWN),
        (False, 0.9, 0.0, 15, 0.5, False, STATE_UNAVAILABLE, STATE_UNAVAILABLE),
        (True, None, 0.0, 15, 0.5, True, STATE_UNKNOWN, STATE_UNKNOWN),  # Uses default
        (True, 0.9, None, 15, 0.5, True, STATE_UNKNOWN, STATE_UNKNOWN),  # Uses default
        (True, 0.9, 0.0, None, 0.5, True, STATE_UNKNOWN, STATE_UNKNOWN),  # Uses default
        (True, 0.9, 0.0, 15, None, True, STATE_UNKNOWN, STATE_UNKNOWN),  # Uses default
        # fmt: on
    ],
)
async def test_heating_failure_manager_post_init(
    hass: HomeAssistant,
    use_feature,
    heating_threshold,
    cooling_threshold,
    delay,
    tolerance,
    is_configured,
    heating_state,
    cooling_state,
):
    """Test the FeatureHeatingFailureDetectionManager post_init"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    assert manager is not None

    config = {CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: use_feature}
    if heating_threshold is not None:
        config[CONF_HEATING_FAILURE_THRESHOLD] = heating_threshold
    if cooling_threshold is not None:
        config[CONF_COOLING_FAILURE_THRESHOLD] = cooling_threshold
    if delay is not None:
        config[CONF_HEATING_FAILURE_DETECTION_DELAY] = delay
    if tolerance is not None:
        config[CONF_TEMPERATURE_CHANGE_TOLERANCE] = tolerance

    manager.post_init(config)

    assert manager.is_configured is is_configured
    assert manager.heating_failure_state is heating_state
    assert manager.cooling_failure_state is cooling_state

    if is_configured:
        assert manager.heating_failure_threshold == (heating_threshold or DEFAULT_HEATING_FAILURE_THRESHOLD)
        assert manager.cooling_failure_threshold == (cooling_threshold or DEFAULT_COOLING_FAILURE_THRESHOLD)
        assert manager.detection_delay_min == (delay or DEFAULT_HEATING_FAILURE_DETECTION_DELAY)
        assert manager.temperature_change_tolerance == (tolerance or DEFAULT_TEMPERATURE_CHANGE_TOLERANCE)

    custom_attributes = {}
    manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_heating_failure_detection_configured"] is is_configured

    if is_configured:
        mgr_attrs = custom_attributes["heating_failure_detection_manager"]
        assert mgr_attrs["heating_failure_state"] is heating_state
        assert mgr_attrs["cooling_failure_state"] is cooling_state


async def test_refresh_state_not_configured(hass: HomeAssistant):
    """Test refresh_state when not configured"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: False})

    result = await manager.refresh_state()
    assert result is False
    assert manager.is_failure_detected is False


async def test_refresh_state_no_prop(hass: HomeAssistant):
    """Test refresh_state when VTherm has no proportional algorithm"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_prop = PropertyMock(return_value=False)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True})

    result = await manager.refresh_state()
    assert result is False


async def test_refresh_state_hvac_off(hass: HomeAssistant):
    """Test refresh_state when VTherm is OFF"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_prop = PropertyMock(return_value=True)
    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_OFF
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True})

    result = await manager.refresh_state()
    assert result is False
    assert manager.heating_failure_state is STATE_OFF
    assert manager.cooling_failure_state is STATE_OFF


async def test_check_heating_failure_detection(hass: HomeAssistant):
    """Test _check_heating_failure method directly"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).target_temperature = PropertyMock(return_value=22.0)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({
        CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
        CONF_HEATING_FAILURE_THRESHOLD: 0.9,
        CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
        CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
    })

    detection_delay_td = timedelta(minutes=15)

    # Test 1: Start tracking when on_percent >= threshold
    manager._check_heating_failure(now, 20.0, 0.95, detection_delay_td)
    assert manager._high_power_start_time == now
    assert manager._last_check_temperature == 20.0
    assert manager.heating_failure_state == STATE_UNKNOWN  # Not detected yet

    # Test 2: After delay, temperature hasn't increased enough -> failure detected
    later = now + timedelta(minutes=16)
    type(fake_vtherm).now = PropertyMock(return_value=later)

    with patch.object(manager, '_send_heating_failure_event') as mock_event:
        manager._check_heating_failure(later, 20.3, 0.95, detection_delay_td)
        assert manager.heating_failure_state == STATE_ON
        # Use ANY for floating point comparison or check call happened
        assert mock_event.call_count == 1
        call_args = mock_event.call_args[0]
        assert call_args[0] == "heating_failure_start"
        assert call_args[1] == 0.95
        assert abs(call_args[2] - 0.3) < 0.01  # Floating point tolerance
        assert call_args[3] == 20.3

    # Test 3: Temperature increases enough -> failure ends
    with patch.object(manager, '_send_heating_failure_event') as mock_event:
        manager._check_heating_failure(later, 21.0, 0.95, detection_delay_td)
        assert manager.heating_failure_state == STATE_OFF
        assert mock_event.call_count == 1
        call_args = mock_event.call_args[0]
        assert call_args[0] == "heating_failure_end"

    # Test 4: on_percent drops below threshold -> reset tracking
    manager._heating_failure_state = STATE_ON  # Simulate failure state
    with patch.object(manager, '_send_heating_failure_event') as mock_event:
        manager._check_heating_failure(later, 21.0, 0.5, detection_delay_td)
        assert manager._high_power_start_time is None
        assert manager.heating_failure_state == STATE_OFF
        mock_event.assert_called_once()


async def test_check_cooling_failure_detection(hass: HomeAssistant):
    """Test _check_cooling_failure method directly"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=22.0)
    type(fake_vtherm).target_temperature = PropertyMock(return_value=20.0)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({
        CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
        CONF_COOLING_FAILURE_THRESHOLD: 0.0,
        CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
        CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
    })

    detection_delay_td = timedelta(minutes=15)

    # Test 1: Start tracking when on_percent <= threshold (0)
    manager._check_cooling_failure(now, 22.0, 0.0, detection_delay_td)
    assert manager._zero_power_start_time == now
    assert manager._last_check_temperature == 22.0
    assert manager.cooling_failure_state == STATE_UNKNOWN  # Not detected yet

    # Test 2: After delay, temperature keeps increasing -> failure detected
    later = now + timedelta(minutes=16)
    type(fake_vtherm).now = PropertyMock(return_value=later)

    with patch.object(manager, '_send_cooling_failure_event') as mock_event:
        manager._check_cooling_failure(later, 23.0, 0.0, detection_delay_td)
        assert manager.cooling_failure_state == STATE_ON
        mock_event.assert_called_once_with("cooling_failure_start", 0.0, 1.0, 23.0)

    # Note: After detecting cooling failure, _last_check_temperature remains at 22.0
    # because the code only updates it when temp_diff <= tolerance (stabilization)
    assert manager._last_check_temperature == 22.0

    # Test 3: on_percent increases above threshold -> reset tracking and end failure
    # This is the most common way to end a cooling failure (system starts heating again)
    with patch.object(manager, '_send_cooling_failure_event') as mock_event:
        manager._check_cooling_failure(later, 23.0, 0.5, detection_delay_td)
        assert manager._zero_power_start_time is None
        assert manager.cooling_failure_state == STATE_OFF
        mock_event.assert_called_once()
        call_args = mock_event.call_args[0]
        assert call_args[0] == "cooling_failure_end"

    # Test 4: Test stabilization scenario from scratch
    # Reset manager state
    manager._cooling_failure_state = STATE_UNKNOWN
    manager._zero_power_start_time = None
    manager._last_check_temperature = None

    # Start tracking at 22.0
    later2 = later + timedelta(minutes=1)
    manager._check_cooling_failure(later2, 22.0, 0.0, detection_delay_td)
    assert manager._zero_power_start_time == later2
    assert manager._last_check_temperature == 22.0

    # Wait for delay, temperature increased significantly -> failure detected
    later3 = later2 + timedelta(minutes=16)
    with patch.object(manager, '_send_cooling_failure_event') as mock_event:
        manager._check_cooling_failure(later3, 23.0, 0.0, detection_delay_td)
        assert manager.cooling_failure_state == STATE_ON
        mock_event.assert_called_once()

    # Now manually update last_check_temperature to simulate time passing
    # In real usage, after a failure is detected, a subsequent check with stable temp
    # will end the failure. We need to simulate this:
    # Set last_check to current temp as if stabilization check
    manager._last_check_temperature = 23.0
    manager._zero_power_start_time = later3  # Reset start time for next check

    # Temperature stabilizes (small change within tolerance)
    later4 = later3 + timedelta(minutes=16)
    with patch.object(manager, '_send_cooling_failure_event') as mock_event:
        manager._check_cooling_failure(later4, 23.2, 0.0, detection_delay_td)
        # temp_diff = 23.2 - 23.0 = 0.2 < 0.5 -> stabilized
        assert manager.cooling_failure_state == STATE_OFF
        mock_event.assert_called_once()
        call_args = mock_event.call_args[0]
        assert call_args[0] == "cooling_failure_end"


async def test_refresh_state_full_cycle(hass: HomeAssistant):
    """Test full refresh_state cycle"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_prop = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({
        CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
        CONF_HEATING_FAILURE_THRESHOLD: 0.9,
        CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
        CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
    })

    # First call initializes tracking
    result = await manager.refresh_state()
    assert result is False
    assert manager._last_check_time == now
    assert manager._last_check_temperature == 20.0

    # Second call starts high power tracking
    later1 = now + timedelta(minutes=1)
    type(fake_vtherm).now = PropertyMock(return_value=later1)

    result = await manager.refresh_state()
    assert result is False
    assert manager._high_power_start_time == later1
    assert manager.heating_failure_state == STATE_OFF

    # After delay without temp increase -> failure detected
    later2 = now + timedelta(minutes=17)
    type(fake_vtherm).now = PropertyMock(return_value=later2)

    with patch.object(manager, '_send_heating_failure_event'):
        result = await manager.refresh_state()
        assert result is True
        assert manager.is_heating_failure_detected is True


async def test_tracking_info_attributes(hass: HomeAssistant):
    """Test that tracking info is correctly exposed in attributes"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init({
        CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
        CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
    })

    # No tracking yet
    custom_attrs = {}
    manager.add_custom_attributes(custom_attrs)
    heating_tracking = custom_attrs["heating_failure_detection_manager"]["heating_tracking"]
    assert heating_tracking["is_tracking"] is False
    assert heating_tracking["remaining_time_min"] is None

    # Start tracking
    manager._high_power_start_time = now
    manager._last_check_temperature = 19.5

    # 5 minutes later
    later = now + timedelta(minutes=5)
    type(fake_vtherm).now = PropertyMock(return_value=later)

    custom_attrs = {}
    manager.add_custom_attributes(custom_attrs)
    heating_tracking = custom_attrs["heating_failure_detection_manager"]["heating_tracking"]
    assert heating_tracking["is_tracking"] is True
    assert heating_tracking["initial_temperature"] == 19.5
    assert heating_tracking["current_temperature"] == 20.0
    assert heating_tracking["elapsed_time_min"] == 5.0
    assert heating_tracking["remaining_time_min"] == 10.0


# ========================================================================
# PART 2: Integration tests with a full VTherm
# ========================================================================


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heating_failure_detection_integrated(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Test the heating failure detection with a full VTherm instance
    1. creates a thermostat with heating failure detection enabled
    2. simulate high on_percent with temperature not increasing
    3. verify failure is detected
    4. simulate temperature increase
    5. verify failure ends
    """

    tz = get_tz(hass)
    now: datetime = datetime.now(tz=tz)

    temps = {
        "frost": 7,
        "eco": 17,
        "comfort": 19,
        "boost": 21,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "external_temperature_sensor_entity_id": "sensor.mock_ext_temp_sensor",
            "cycle_min": 5,
            "temp_min": 15,
            "temp_max": 30,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            "use_heating_failure_detection_feature": True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "minimal_deactivation_delay": 0,
            "security_delay_min": 60,  # Long delay to avoid interference
            "security_min_on_percent": 0.2,
            "security_default_on_percent": 0.1,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_COOLING_FAILURE_THRESHOLD: 0.0,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
        },
    )

    # 1. Create the thermostat
    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    # Verify heating failure detection is configured
    assert entity.heating_failure_detection_manager.is_configured is True
    assert entity.heating_failure_detection_manager.is_failure_detected is False

    # Turn on the thermostat and set comfort preset
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.target_temperature == 19

    # 2. Set low temperature to trigger high on_percent
    event_timestamp = now
    entity._set_now(event_timestamp)
    await send_temperature_change_event(entity, 15, event_timestamp)

    # Verify on_percent is high (heating required)
    assert entity.on_percent >= 0.9

    # Initialize tracking by calling refresh_state
    await entity.heating_failure_detection_manager.refresh_state()

    # At this point, tracking should have started but no failure yet
    assert entity.heating_failure_detection_manager.is_heating_failure_detected is False

    # 3. Simulate time passing without temperature increase
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        # Simulate 16 minutes passing with same low temperature
        event_timestamp = now + timedelta(minutes=16)
        entity._set_now(event_timestamp)

        await send_temperature_change_event(entity, 15.2, event_timestamp)  # Only +0.2° (below tolerance of 0.5°)

        # Force refresh of heating failure detection
        await entity.heating_failure_detection_manager.refresh_state()

        # Now failure should be detected
        assert entity.heating_failure_detection_manager.is_heating_failure_detected is True
        assert entity.heating_failure_detection_manager.heating_failure_state == STATE_ON

        # Check event was sent
        heating_failure_calls = [
            c for c in mock_send_event.call_args_list
            if c[0][0] == EventType.HEATING_FAILURE_EVENT
        ]
        assert len(heating_failure_calls) >= 1

    # 4. Simulate temperature increase to resolve failure
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        event_timestamp = now + timedelta(minutes=20)
        entity._set_now(event_timestamp)

        # Temperature increases significantly
        await send_temperature_change_event(entity, 16.5, event_timestamp)

        # Force refresh
        await entity.heating_failure_detection_manager.refresh_state()

        # 5. Verify failure ended
        assert entity.heating_failure_detection_manager.is_heating_failure_detected is False
        assert entity.heating_failure_detection_manager.heating_failure_state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_cooling_failure_detection_integrated(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Test the cooling failure detection with a full VTherm instance
    1. creates a thermostat with heating failure detection enabled
    2. simulate on_percent at 0 with temperature increasing
    3. verify cooling failure is detected
    4. simulate temperature stabilization
    5. verify failure ends
    """

    tz = get_tz(hass)
    now: datetime = datetime.now(tz=tz)

    temps = {
        "frost": 7,
        "eco": 17,
        "comfort": 19,
        "boost": 21,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId2",
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "external_temperature_sensor_entity_id": "sensor.mock_ext_temp_sensor",
            "cycle_min": 5,
            "temp_min": 15,
            "temp_max": 30,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            "use_heating_failure_detection_feature": True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "minimal_deactivation_delay": 0,
            "security_delay_min": 60,
            "security_min_on_percent": 0.2,
            "security_default_on_percent": 0.1,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_COOLING_FAILURE_THRESHOLD: 0.0,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
        },
    )

    # 1. Create the thermostat
    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    # Verify heating failure detection is configured
    assert entity.heating_failure_detection_manager.is_configured is True

    # Turn on the thermostat
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    assert entity.target_temperature == 19

    # 2. Set temperature above target to get on_percent = 0
    event_timestamp = now
    entity._set_now(event_timestamp)
    await send_temperature_change_event(entity, 22, event_timestamp)

    # Verify on_percent is 0 (no heating needed)
    assert entity.on_percent == 0

    # Initialize tracking by calling refresh_state
    await entity.heating_failure_detection_manager.refresh_state()

    # At this point, zero power tracking should start but no failure yet
    assert entity.heating_failure_detection_manager.is_cooling_failure_detected is False

    # 3. Simulate time passing with temperature still increasing (anomaly)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ):
        event_timestamp = now + timedelta(minutes=16)
        entity._set_now(event_timestamp)

        # Temperature increases despite no heating (cooling failure)
        await send_temperature_change_event(entity, 23.5, event_timestamp)

        # Force refresh
        await entity.heating_failure_detection_manager.refresh_state()

        # Cooling failure should be detected
        assert entity.heating_failure_detection_manager.is_cooling_failure_detected is True
        assert entity.heating_failure_detection_manager.cooling_failure_state == STATE_ON

    # 4. Simulate temperature stabilization
    # After cooling failure is detected, we need to reset the tracking
    # to properly test stabilization. The real scenario would involve
    # the on_percent going up (heating restarts) to end the failure.
    # Let's test that scenario instead:
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ):
        event_timestamp = now + timedelta(minutes=20)
        entity._set_now(event_timestamp)

        # Temperature drops, triggering heating to restart (on_percent > 0)
        # This will end the cooling failure
        await send_temperature_change_event(entity, 18, event_timestamp)

        # Force refresh - now on_percent should be > 0 since temp < target
        await entity.heating_failure_detection_manager.refresh_state()

        # 5. Failure should end because on_percent is no longer 0
        assert entity.on_percent > 0  # Heating is active
        assert entity.heating_failure_detection_manager.is_cooling_failure_detected is False
        assert entity.heating_failure_detection_manager.cooling_failure_state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heating_failure_detection_hvac_off_resets(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Test that switching to HVAC OFF resets the failure detection"""

    tz = get_tz(hass)
    now: datetime = datetime.now(tz=tz)

    temps = {
        "frost": 7,
        "eco": 17,
        "comfort": 19,
        "boost": 21,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId3",
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "external_temperature_sensor_entity_id": "sensor.mock_ext_temp_sensor",
            "cycle_min": 5,
            "temp_min": 15,
            "temp_max": 30,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            "use_heating_failure_detection_feature": True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "minimal_deactivation_delay": 0,
            "security_delay_min": 60,
            "security_min_on_percent": 0.2,
            "security_default_on_percent": 0.1,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_COOLING_FAILURE_THRESHOLD: 0.0,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    # Turn on and set preset
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)

    # Trigger failure detection start
    event_timestamp = now
    await send_temperature_change_event(entity, 15, event_timestamp)

    # Verify tracking started
    await entity.heating_failure_detection_manager.refresh_state()
    assert entity.heating_failure_detection_manager._high_power_start_time is not None

    # Switch to OFF
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)

    # Refresh state
    await entity.heating_failure_detection_manager.refresh_state()

    # Verify tracking was reset
    assert entity.heating_failure_detection_manager._high_power_start_time is None
    assert entity.heating_failure_detection_manager._zero_power_start_time is None
    assert entity.heating_failure_detection_manager.heating_failure_state == STATE_OFF
    assert entity.heating_failure_detection_manager.cooling_failure_state == STATE_OFF


# ========================================================================
# PART 3: Unit tests for template enable feature
# ========================================================================


async def test_enable_template_disables_detection(hass: HomeAssistant):
    """Test that a template returning False disables detection"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_tpi = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init(
        {
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
            CONF_FAILURE_DETECTION_ENABLE_TEMPLATE: "{{ false }}",
        }
    )

    # Template returns False -> detection should be disabled
    result = await manager.refresh_state()
    assert result is False
    # Tracking should not start because template is False
    assert manager._high_power_start_time is None

    custom_attributes = {}
    manager.add_custom_attributes(custom_attributes)
    mgr_attrs = custom_attributes["heating_failure_detection_manager"]
    assert mgr_attrs["failure_detection_enable_template"] == "{{ false }}"
    assert mgr_attrs["is_detection_enabled_by_template"] is False


async def test_enable_template_enables_detection(hass: HomeAssistant):
    """Test that a template returning True enables detection"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_tpi = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init(
        {
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
            CONF_FAILURE_DETECTION_ENABLE_TEMPLATE: "{{ true }}",
        }
    )

    # First call initializes tracking
    result = await manager.refresh_state()
    assert result is False
    assert manager._last_check_time == now
    assert manager._last_check_temperature == 20.0

    # Second call - template returns True, detection should work
    later1 = now + timedelta(minutes=1)
    type(fake_vtherm).now = PropertyMock(return_value=later1)

    result = await manager.refresh_state()
    assert result is False
    # Tracking should start because template is True
    assert manager._high_power_start_time == later1

    custom_attributes = {}
    manager.add_custom_attributes(custom_attributes)
    mgr_attrs = custom_attributes["heating_failure_detection_manager"]
    assert mgr_attrs["failure_detection_enable_template"] == "{{ true }}"
    assert mgr_attrs["is_detection_enabled_by_template"] is True


async def test_no_template_defaults_to_enabled(hass: HomeAssistant):
    """Test that when no template is provided, detection is enabled by default"""

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_tpi = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init(
        {
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
            # No template provided
        }
    )

    # First call initializes tracking
    await manager.refresh_state()

    # Second call - no template means enabled by default
    later1 = now + timedelta(minutes=1)
    type(fake_vtherm).now = PropertyMock(return_value=later1)

    result = await manager.refresh_state()
    assert result is False
    # Tracking should start because no template means enabled
    assert manager._high_power_start_time == later1

    custom_attributes = {}
    manager.add_custom_attributes(custom_attributes)
    mgr_attrs = custom_attributes["heating_failure_detection_manager"]
    assert mgr_attrs.get("failure_detection_enable_template") is None
    assert mgr_attrs["is_detection_enabled_by_template"] is True


async def test_template_resets_tracking_when_disabled(hass: HomeAssistant):
    """Test that when template switches from True to False, tracking is reset"""
    from homeassistant.helpers.template import Template

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_tpi = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    # Start with template returning True
    manager.post_init(
        {
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
            CONF_FAILURE_DETECTION_ENABLE_TEMPLATE: "{{ true }}",
        }
    )

    # First call initializes tracking
    await manager.refresh_state()

    # Second call - starts tracking
    later1 = now + timedelta(minutes=1)
    type(fake_vtherm).now = PropertyMock(return_value=later1)
    await manager.refresh_state()
    assert manager._high_power_start_time == later1

    # Now change template to return False (simulate external heat source)
    manager._failure_detection_enable_template = Template("{{ false }}", hass)

    later2 = now + timedelta(minutes=2)
    type(fake_vtherm).now = PropertyMock(return_value=later2)
    result = await manager.refresh_state()

    # Tracking should be reset
    assert manager._high_power_start_time is None
    assert manager._zero_power_start_time is None


async def test_template_ends_failure_when_disabled(hass: HomeAssistant):
    """Test that when template switches to False during active failure, failure is ended"""
    from homeassistant.helpers.template import Template

    now = datetime.now()
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).has_tpi = PropertyMock(return_value=True)
    type(fake_vtherm).now = PropertyMock(return_value=now)
    type(fake_vtherm).current_temperature = PropertyMock(return_value=20.0)
    type(fake_vtherm).on_percent = PropertyMock(return_value=0.95)
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)

    fake_requested_state = MagicMock()
    fake_requested_state.hvac_mode = VThermHvacMode_HEAT
    type(fake_vtherm).requested_state = PropertyMock(return_value=fake_requested_state)

    manager = FeatureHeatingFailureDetectionManager(fake_vtherm, hass)
    manager.post_init(
        {
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: True,
            CONF_HEATING_FAILURE_THRESHOLD: 0.9,
            CONF_HEATING_FAILURE_DETECTION_DELAY: 15,
            CONF_TEMPERATURE_CHANGE_TOLERANCE: 0.5,
            CONF_FAILURE_DETECTION_ENABLE_TEMPLATE: "{{ true }}",
        }
    )

    # Simulate an active heating failure
    manager._heating_failure_state = STATE_ON
    manager._high_power_start_time = now

    # Now change template to return False
    manager._failure_detection_enable_template = Template("{{ false }}", hass)

    later = now + timedelta(minutes=1)
    type(fake_vtherm).now = PropertyMock(return_value=later)

    with patch.object(manager, "_send_heating_failure_event") as mock_event:
        result = await manager.refresh_state()

        # Failure should be ended
        assert manager._heating_failure_state == STATE_OFF
        # Event should be sent
        mock_event.assert_called_once()
        call_args = mock_event.call_args[0]
        assert call_args[0] == "heating_failure_end"
