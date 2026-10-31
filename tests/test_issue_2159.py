# pylint: disable=protected-access, unused-argument, redefined-outer-name
"""Regression tests for the shared underlying tracking budget."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import State
from homeassistant.components.climate import HVACAction

from custom_components.versatile_thermostat.const import COMMAND_CAUSE_UNDERLYING_TRACKING
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT, VThermHvacMode_OFF
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import (
    DOMAIN,
    MockConfigEntry,
    PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    create_and_register_mock_climate,
    create_thermostat,
)


@pytest.fixture
async def tracking_thermostat(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """An initialized climate with no downstream sends in the callback tests."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_mode=VThermHvacMode_HEAT,
        hvac_action=HVACAction.OFF,
    )
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG)
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    entity.set_follow_underlying_temp_change(True)
    await hass.async_block_till_done()
    entity._on_external_command_received()
    # Most isolated tests adopt HEAT -> OFF while application is mocked.
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    yield entity
    entity.remove_thermostat()


async def test_effective_off_report_does_not_replace_heat_request(tracking_thermostat):
    """An action change must not turn an imposed OFF into a user request."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)
    assert entity._follow_underlying_temp_change
    assert under.is_initialized
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.hvac_mode == "off"
    assert entity._underlying_tracking_attempts == 0
    old = State(under.entity_id, "heat", {"hvac_action": HVACAction.HEATING})
    new = State(under.entity_id, "off", {"hvac_action": HVACAction.OFF})

    with (
        patch.object(entity, "underlying_changed", wraps=entity.underlying_changed) as callback,
        patch.object(entity, "update_states", new=AsyncMock()),
    ):
        await under._underlying_changed(under.entity_id, new, old)

    callback.assert_awaited_once_with(under, None, HVACAction.OFF, None, None, new, old)
    assert (entity.requested_state.hvac_mode, entity._underlying_tracking_attempts) == (
        VThermHvacMode_HEAT,
        0,
    )


async def test_parent_suppresses_fully_filtered_effective_mode_report(tracking_thermostat):
    """Without another changed field the parent must not deliver a callback."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)
    old = State(under.entity_id, "heat", {"hvac_action": HVACAction.OFF})
    new = State(under.entity_id, "off", {"hvac_action": HVACAction.OFF})

    with patch.object(entity, "underlying_changed", wraps=entity.underlying_changed) as callback:
        await under._underlying_changed(under.entity_id, new, old)

    callback.assert_not_awaited()
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity._underlying_tracking_attempts == 0


async def test_parent_tracks_transition_different_from_effective_mode(tracking_thermostat):
    """A genuine different mode remains eligible and uses the shared budget."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    old = State(under.entity_id, "heat", {"hvac_action": HVACAction.HEATING})
    new = State(under.entity_id, "off", {"hvac_action": HVACAction.OFF})

    with (
        patch.object(entity, "underlying_changed", wraps=entity.underlying_changed) as callback,
        patch.object(entity, "update_states", new=AsyncMock()) as update,
    ):
        await under._underlying_changed(under.entity_id, new, old)

    callback.assert_awaited_once_with(under, VThermHvacMode_OFF, HVACAction.OFF, None, None, new, old)
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity._underlying_tracking_attempts == 1
    update.assert_awaited_once_with(_command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)


async def test_null_parameter_still_tracks_transition_different_from_effective_mode(tracking_thermostat):
    """The guard concerns the reported value, not just the callback parameter."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    old, new = State(under.entity_id, "heat"), State(under.entity_id, "off")

    with patch.object(entity, "update_states", new=AsyncMock()) as update:
        await entity.underlying_changed(under, None, None, None, None, new, old)

    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity._underlying_tracking_attempts == 1
    update.assert_awaited_once_with(_command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)


@pytest.mark.parametrize("attempts", [0, 1, 2])
@pytest.mark.parametrize(
    "requested,effective,old_mode,new_mode",
    [
        (VThermHvacMode_HEAT, VThermHvacMode_OFF, "heat", "off"),
        (VThermHvacMode_OFF, VThermHvacMode_HEAT, "off", "heat"),
    ],
)
async def test_effective_mode_echo_preserves_pending_candidate(tracking_thermostat, attempts, requested, effective, old_mode, new_mode):
    """The value guard is symmetric and must not cancel an existing candidate."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(requested)
    entity._state_manager.current_state.set_hvac_mode(effective)
    entity._underlying_tracking_attempts = attempts
    cancel = MagicMock()
    candidate = {"cancel": cancel, "version": 1, "temperature": 27}
    entity._underlying_temperature_candidates[under.entity_id] = candidate

    with patch.object(entity, "update_states", new=AsyncMock()) as update:
        await entity.underlying_changed(
            under,
            effective,
            None,
            None,
            "low",
            State(under.entity_id, new_mode),
            State(under.entity_id, old_mode),
        )

    assert entity.requested_state.hvac_mode == requested
    assert entity._underlying_tracking_attempts == attempts
    assert not entity._underlying_tracking_suspended
    assert entity._underlying_temperature_candidates[under.entity_id] is candidate
    cancel.assert_not_called()
    assert entity._attr_fan_mode == "low"
    update.assert_awaited_once_with(_preserve_underlying_temperature_candidates=True)


async def test_filtered_mode_keeps_action_fan_and_temperature_tracking(hass, tracking_thermostat):
    """Rejecting an effective-mode echo must not discard other delivered fields."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    with patch.object(entity, "underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"hvac_action": HVACAction.OFF, "temperature": 27, "fan_mode": "low"})
        await hass.async_block_till_done()
    new = hass.states.get(under.entity_id)
    old = State(under.entity_id, "heat", {"hvac_action": HVACAction.HEATING, "temperature": 20})
    entity._on_external_command_received()
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity.requested_state.set_target_temperature(20)
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)
    under._last_sent_temperature = None
    timers = []

    with (
        patch.object(entity, "underlying_changed", wraps=entity.underlying_changed) as callback,
        patch.object(entity, "update_states", new=AsyncMock()) as update,
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, delay, cb: (timers.append((delay, cb)), lambda: None)[1]),
    ):
        await under._underlying_changed(under.entity_id, new, old)
        callback.assert_awaited_once_with(under, None, HVACAction.OFF, 27, "low", new, old)
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.requested_state.target_temperature == 20
        assert entity._attr_fan_mode == "low"
        assert entity._underlying_temperature_observed[under.entity_id] == 27
        assert entity._underlying_tracking_attempts == 0
        assert [delay for delay, _ in timers] == [5]
        update.assert_awaited_once_with(_preserve_underlying_temperature_candidates=True)
        await timers[0][1](None)

    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.requested_state.target_temperature == 27
    assert entity._underlying_tracking_attempts == 1  # temperature adoption only
    update.assert_awaited_with(force=True, _command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)


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
        # Simulate the effective state advancing after the mocked application.
        entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)
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
