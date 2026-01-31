# pylint: disable=unused-argument, line-too-long, protected-access
"""Unit tests for UnderlyingStateManager."""
from typing import List

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.versatile_thermostat.underlying_state_manager import UnderlyingStateManager


async def test_manager_initial_empty(hass: HomeAssistant):
    """Manager can be created without entities and reports initialized (empty)."""
    mgr = UnderlyingStateManager(hass)
    assert mgr is not None
    assert mgr._entity_ids == []
    # empty set of states should be considered initialized
    assert mgr.is_all_states_initialized is True


async def test_add_entities_and_state_tracking(hass: HomeAssistant):
    """Adding entities caches initial states and updates on state changes."""
    # Prepare initial HA states
    hass.states.async_set("switch.test_a", "on")
    hass.states.async_set("sensor.test_b", STATE_UNAVAILABLE)

    mgr = UnderlyingStateManager(hass)
    mgr.add_underlying_entities(["switch.test_a", "sensor.test_b"])

    # Allow HA tasks to run (listeners/callbacks)
    await hass.async_block_till_done()

    s_a = mgr.get_state("switch.test_a")
    assert s_a is not None and s_a.state == "on"

    s_b = mgr.get_state("sensor.test_b")
    assert s_b is not None and s_b.state == STATE_UNAVAILABLE

    # Not all states are considered initialized because sensor.test_b is unavailable
    assert mgr.is_all_states_initialized is False

    # Update sensor to a valid state
    hass.states.async_set("sensor.test_b", "42")
    await hass.async_block_till_done()

    assert mgr.get_state("sensor.test_b").state == "42"
    assert mgr.is_all_states_initialized is True


async def test_on_change_callback_and_stop(hass: HomeAssistant):
    """on_change is called for initial cached states, on updates, and stops after stop()."""
    calls: List[tuple] = []

    async def on_change(entity_id: str, state):
        calls.append((entity_id, state.state if state else None))

    # Prepare initial HA state
    hass.states.async_set("switch.cb", "off")

    mgr = UnderlyingStateManager(hass, on_change=on_change)
    mgr.add_underlying_entities(["switch.cb"])
    await hass.async_block_till_done()

    assert mgr.is_all_states_initialized is True

    # initial on_change should have been scheduled for the added entity
    assert calls and calls[-1][0] == "switch.cb"
    assert calls[-1][1] == "off"

    # State change should trigger callback
    hass.states.async_set("switch.cb", "on")
    await hass.async_block_till_done()
    assert any(c for c in calls if c[1] == "on")

    # Add another entity which is not already available
    calls.clear()
    mgr.add_underlying_entities(["number.cb2"])
    await hass.async_block_till_done()
    assert mgr.is_all_states_initialized is False

    # set a set for the new entity, should trigger on_change
    hass.states.async_set("number.cb2", "100")
    await hass.async_block_till_done()

    assert calls and calls[-1][0] == "number.cb2"
    assert calls[-1][1] == "100"

    assert mgr.is_all_states_initialized is True

    # Stopping the manager should prevent further callbacks
    before = len(calls)
    mgr.stop()
    hass.states.async_set("switch.cb", "off")
    await hass.async_block_till_done()
    assert len(calls) == before
