# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test the race condition during thermostat reload.

This test verifies that timer callbacks (_turn_on_later, _turn_off_later)
do not perform any actions after remove_entity() has been called.
This prevents "ghost sessions" where old thermostat instances continue
to control heating after a reload.
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
async def test_underlying_switch_turn_on_after_remove(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):
    """Test that _turn_on_later does nothing after remove_entity() is called.
    
    This simulates the race condition where a timer callback fires
    after the entity has been removed during a reload.
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
            CONF_HEATER: "switch.mock_switch1",
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
    assert entity.is_over_climate is False

    # Start heating to create an active cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

    # Get the underlying switch
    underlying = entity.underlying_entity(0)
    assert underlying is not None

    # Setup the underlying with a simulated cycle in progress
    underlying._on_time_sec = 120
    underlying._off_time_sec = 180
    underlying._hvac_mode = VThermHvacMode_HEAT

    # Now simulate what happens during a reload:
    # 1. remove_entity() is called
    underlying.remove_entity()

    # 2. But the timer callback fires AFTER removal (race condition)
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_turn_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.call_later",
        return_value=MagicMock(),
    ) as mock_call_later:
        # Simulate the timer callback firing after removal
        await underlying._turn_on_later(None)

        # EXPECTED BEHAVIOR: No action should be taken
        # This test will FAIL initially because there's no guard in _turn_on_later
        assert mock_turn_on.call_count == 0, (
            "turn_on() should NOT be called after remove_entity(). "
            "This is the race condition bug!"
        )

        # Also verify no new timer was scheduled
        assert mock_call_later.call_count == 0, (
            "No new timer should be scheduled after remove_entity(). "
            "This would create a ghost session!"
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_underlying_switch_turn_off_after_remove(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):
    """Test that _turn_off_later does nothing after remove_entity() is called."""
    tz = get_tz(hass)
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId2",
        data={
            CONF_NAME: "TheOverSwitchMockName2",
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
            CONF_HEATER: "switch.mock_switch1",
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
        hass, entry, "climate.theoverswitchmockname2"
    )
    assert entity

    # Start heating
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

    underlying = entity.underlying_entity(0)
    assert underlying is not None

    # Setup the underlying with a simulated cycle
    underlying._on_time_sec = 120
    underlying._off_time_sec = 180
    underlying._hvac_mode = VThermHvacMode_HEAT

    # Simulate reload: remove_entity() is called
    underlying.remove_entity()

    # Timer callback fires after removal
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.call_later",
        return_value=MagicMock(),
    ) as mock_call_later:
        await underlying._turn_off_later(None)

        # EXPECTED: No action after removal
        assert mock_turn_off.call_count == 0, (
            "turn_off() should NOT be called after remove_entity(). "
            "This is the race condition bug!"
        )

        assert mock_call_later.call_count == 0, (
            "No new timer should be scheduled after remove_entity()."
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_underlying_switch_callbacks_cleared_after_remove(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
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
            CONF_HEATER: "switch.mock_switch1",
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
