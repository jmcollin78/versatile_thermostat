# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test the race condition during thermostat reload.

With CycleScheduler, cycle timers are centralized. This test verifies
that cancel_cycle() properly cancels all scheduled actions, preventing
ghost sessions after a reload.
"""

import asyncio
from unittest.mock import patch, PropertyMock, MagicMock
from datetime import datetime, timedelta
import logging

import pytest
from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_cycle_scheduler_cancel_on_remove(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
    fake_underlying_switch: MockSwitch,
):
    """Test that CycleScheduler.cancel_cycle() is effective.

    When a thermostat is removed during reload, the scheduler's
    cancel_cycle should cancel all pending timers to prevent
    ghost sessions.
    """
    tz = get_tz(hass)
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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_MINIMAL_ACTIVATION_DELAY: 0,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity.cycle_scheduler is not None

    scheduler = entity.cycle_scheduler

    # Start a cycle via mock
    mock_cancel_1 = MagicMock()
    mock_cancel_2 = MagicMock()
    scheduler._scheduled_actions = [mock_cancel_1, mock_cancel_2]
    assert scheduler.is_cycle_running is True

    # Cancel cycle (as would happen during remove/reload)
    scheduler.cancel_cycle()

    # All cancel functions should have been called
    mock_cancel_1.assert_called_once()
    mock_cancel_2.assert_called_once()
    assert scheduler.is_cycle_running is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_underlying_switch_callbacks_cleared_after_remove(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
    fake_underlying_switch: MockSwitch,
):
    """Test that cycle callbacks are cleared after remove_entity()."""
    tz = get_tz(hass)
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId3",
        data={
            CONF_NAME: "TheOverSwitchMockName3",
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
            CONF_MINIMAL_ACTIVATION_DELAY: 0,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname3"
    )
    assert entity

    underlying = entity.underlying_entity(0)
    assert underlying is not None

    # Register a callback
    callback_called = False

    async def test_callback(**kwargs):
        nonlocal callback_called
        callback_called = True

    underlying.register_cycle_callback(test_callback)
    assert len(underlying._on_cycle_start_callbacks) == 1

    # Remove entity
    underlying.remove_entity()

    # Callbacks should be cleared
    assert len(underlying._on_cycle_start_callbacks) == 0, (
        "Callbacks should be cleared after remove_entity()"
    )
