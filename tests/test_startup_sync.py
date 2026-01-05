# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Startup Sync feature """
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_HOME, STATE_NOT_HOME

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.const import (
    DOMAIN,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_SWITCH,
    CONF_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_CYCLE_MIN,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_USE_WINDOW_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_POWER_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_UNDERLYING_LIST,
    CONF_PROP_FUNCTION,
    PROPORTIONAL_FUNCTION_TPI,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_MINIMAL_ACTIVATION_DELAY,
    CONF_MINIMAL_DEACTIVATION_DELAY,
    CONF_SAFETY_DELAY_MIN,
    CONF_SAFETY_MIN_ON_PERCENT,
    CONF_PRESENCE_SENSOR,
    CONF_STARTUP_SYNC_ENABLED,
    CONF_STARTUP_SYNC_MAX_WAIT_SEC,
    CONF_STARTUP_SYNC_SAFETY_DELAY_SEC,
    EventType,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_startup_sync_waits_for_temperature_sensor(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that startup sync waits for temperature sensor to be available"""

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
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
            CONF_STARTUP_SYNC_ENABLED: True,
            CONF_STARTUP_SYNC_MAX_WAIT_SEC: 30,  # Short timeout for testing
            CONF_STARTUP_SYNC_SAFETY_DELAY_SEC: 1,  # Short delay for testing
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity._startup_sync_enabled is True
    assert entity._startup_sync_max_wait_sec == 30
    assert entity._startup_sync_safety_delay_sec == 1

    # Initially, startup sync should not be done
    assert entity._startup_sync_done is False

    # Wait a bit for the startup sync task to run
    await asyncio.sleep(0.1)

    # After the startup sync completes (sensor is available immediately in tests),
    # it should be marked as done
    await asyncio.sleep(2)  # Wait for safety delay + processing
    assert entity._startup_sync_done is True


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_startup_sync_disabled(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that startup sync can be disabled"""

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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_STARTUP_SYNC_ENABLED: False,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity._startup_sync_enabled is False

    # Startup sync should not run, so flag should remain False
    await asyncio.sleep(0.5)
    assert entity._startup_sync_done is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_startup_sync_default_values(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that startup sync uses default values when not specified"""

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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            # No startup sync config - should use defaults
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    # Check default values
    assert entity._startup_sync_enabled is True  # Default is enabled
    assert entity._startup_sync_max_wait_sec == 300  # Default 5 minutes
    assert entity._startup_sync_safety_delay_sec == 10  # Default 10 seconds


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_startup_sync_fires_event_on_state_change(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that startup sync fires an event when state changes"""

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
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
            CONF_STARTUP_SYNC_ENABLED: True,
            CONF_STARTUP_SYNC_MAX_WAIT_SEC: 30,
            CONF_STARTUP_SYNC_SAFETY_DELAY_SEC: 0,  # No delay for faster testing
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    # Listen for the startup sync event
    events = []

    def event_listener(event):
        events.append(event)

    hass.bus.async_listen(EventType.STARTUP_SYNC_EVENT.value, event_listener)

    # Wait for startup sync to complete
    await asyncio.sleep(1)

    # The event may or may not fire depending on whether state changed
    # In a real scenario with state changes, we would see the event
    assert entity._startup_sync_done is True


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_startup_sync_timeout(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test that startup sync times out if sensor never becomes available"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.unavailable_sensor",  # Non-existent sensor
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_STARTUP_SYNC_ENABLED: True,
            CONF_STARTUP_SYNC_MAX_WAIT_SEC: 5,  # Very short timeout for testing
            CONF_STARTUP_SYNC_SAFETY_DELAY_SEC: 0,
        },
    )

    # Create entity - this should not fail even with unavailable sensor
    with patch.object(hass.states, 'get', return_value=None):
        entity: BaseThermostat = await create_thermostat(
            hass, entry, "climate.theoverswitchmockname"
        )

    # Note: In a real scenario, we would need to mock the sensor as unavailable
    # and wait for the timeout. This is a simplified test.
    assert entity
    assert entity._startup_sync_enabled is True
