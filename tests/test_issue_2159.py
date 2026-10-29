# pylint: disable=protected-access, unused-argument, redefined-outer-name
"""Regression tests for the shared underlying tracking budget."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import State
from homeassistant.components.climate import HVACAction

from custom_components.versatile_thermostat.const import COMMAND_CAUSE_UNDERLYING_TRACKING
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT, VThermHvacMode_OFF
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import (
    DOMAIN, MockConfigEntry, PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    create_and_register_mock_climate, create_thermostat,
)


@pytest.fixture
async def tracking_thermostat(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """An initialized climate with no downstream sends in the callback tests."""
    await create_and_register_mock_climate(
        hass, "mock_climate", "MockClimateName", {},
        hvac_mode=VThermHvacMode_HEAT, hvac_action=HVACAction.OFF,
    )
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG)
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    entity.set_follow_underlying_temp_change(True)
    await hass.async_block_till_done()
    entity._on_external_command_received()
    yield entity
    entity.remove_thermostat()


async def test_hvac_transition_uses_shared_budget_and_cause(tracking_thermostat):
    """A genuine delivered transition consumes one unit, then suspension blocks it."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    old = State(under.entity_id, "heat")
    new = State(under.entity_id, "off")
    with patch.object(entity, "update_states", new=AsyncMock()) as update:
        await entity.underlying_changed(under, None, None, None, None, new, old)
        assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
        assert entity._underlying_tracking_attempts == 1
        update.assert_awaited_once_with(_command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)
        entity._underlying_tracking_attempts = 3
        entity._underlying_tracking_suspended = True
        update.reset_mock()
        await entity.underlying_changed(under, VThermHvacMode_HEAT, None, None, None, old, new)
        assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
        assert entity._underlying_tracking_attempts == 3
        update.assert_not_awaited()


async def test_temperature_adoption_counts_but_identical_retains_manual_effects(hass, tracking_thermostat):
    """A request-identical admissible candidate remains a manual action, not an adoption."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    callbacks = []
    value = entity.requested_state.target_temperature
    if value is None:
        value = 20.0
        entity.requested_state.set_target_temperature(value)
    under._last_sent_temperature = None
    entity.requested_state.set_preset(VThermPreset.COMFORT)
    hass.states.async_set(under.entity_id, "off", {"temperature": value})
    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
        patch.object(entity._timed_preset_manager, "cancel_without_revert") as cancel,
        patch.object(entity, "update_states", new=AsyncMock()) as update,
    ):
        entity._consider_underlying_temperature_candidate(under, value)
        await callbacks[-1](None)
        assert entity._underlying_tracking_attempts == 0
        assert entity.requested_state.preset == VThermPreset.NONE
        cancel.assert_called_once()
        update.assert_awaited_once_with(force=True, _command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)

        value += 2
        hass.states.async_set(under.entity_id, "off", {"temperature": value})
        entity._consider_underlying_temperature_candidate(under, value)
        await callbacks[-1](None)
        assert entity.requested_state.target_temperature == value
        assert entity._underlying_tracking_attempts == 1