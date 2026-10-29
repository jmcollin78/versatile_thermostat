# pylint: disable=protected-access, unused-argument, redefined-outer-name
"""Additional local regression tests for issue 2159."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import State

from custom_components.versatile_thermostat.const import COMMAND_CAUSE_UNDERLYING_TRACKING
from custom_components.versatile_thermostat.const import (
    CONF_AUTO_REGULATION_MODE, CONF_AUTO_REGULATION_VALVE, CONF_OPENING_DEGREE_LIST,
    CONF_CLOSING_DEGREE_LIST, CONF_PROP_FUNCTION, PROPORTIONAL_FUNCTION_TPI,
    CONF_TPI_COEF_INT, CONF_TPI_COEF_EXT, CONF_UNDERLYING_LIST,
)
from custom_components.versatile_thermostat.thermostat_climate_valve import ThermostatOverClimateValve
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT, VThermHvacMode_OFF
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import DOMAIN, MockConfigEntry, PARTIAL_CLIMATE_NOT_REGULATED_CONFIG, create_and_register_mock_climate, create_and_register_mock_number, create_thermostat
from .test_issue_2159 import tracking_thermostat  # pylint: disable=unused-import


@pytest.mark.parametrize("old,new,identity,expected", [
    (None, "off", True, False),
    ("unknown", "off", True, False),
    ("unavailable", "off", True, False),
    ("heat", "unknown", True, False),
    ("heat", "heat", True, False),
    ("heat", "off", False, False),
    ("heat", "off", True, True),
])
async def test_transition_qualification(tracking_thermostat, old, new, identity, expected):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    old_state = State(under.entity_id if identity else "climate.other", old) if old else None
    new_state = State(under.entity_id, new)
    with patch.object(entity, "update_states", new=AsyncMock()) as update:
        await entity.underlying_changed(under, None, None, None, None, new_state, old_state)
    assert entity._underlying_tracking_attempts == int(expected)
    assert entity.requested_state.hvac_mode == (VThermHvacMode_OFF if expected else VThermHvacMode_HEAT)
    assert update.await_count == int(expected)


@pytest.mark.parametrize("attempts,suspended,expected", [(0, False, 1), (2, False, 3), (2, True, 2), (3, False, 3)])
async def test_admission_and_third_debit(tracking_thermostat, attempts, suspended, expected):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._underlying_tracking_attempts = attempts
    entity._underlying_tracking_suspended = suspended
    with patch.object(entity, "update_states", new=AsyncMock()) as update:
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity._underlying_tracking_attempts == expected
    if attempts == 2 and not suspended:
        assert entity._underlying_tracking_suspended
        assert not entity._can_send_underlying_tracking_command()
        update.assert_awaited_once_with(_command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)


@pytest.mark.parametrize("assign", [False, True])
async def test_mode_setter_failure_debits_only_retained_mutation(tracking_thermostat, assign):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    state = entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    original = state.set_hvac_mode

    def failing(value):
        if assign:
            original(value)
        raise ValueError("setter failure")

    with patch.object(state, "set_hvac_mode", side_effect=failing), patch.object(entity, "update_states", new=AsyncMock()) as update:
        with pytest.raises(ValueError, match="setter failure"):
            await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity._underlying_tracking_attempts == int(assign)
    assert state.hvac_mode == (VThermHvacMode_OFF if assign else VThermHvacMode_HEAT)
    update.assert_not_awaited()


@pytest.mark.parametrize("initial", [0, 1, 2])
async def test_setter_and_post_debit_failure_preserve_primary_and_clean_once(tracking_thermostat, initial):
    """A secondary hook error never retries the debit or invalidation."""
    entity = tracking_thermostat
    under, state = entity.underlying_entity(0), entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._underlying_tracking_attempts = initial
    cancel = MagicMock()
    entity._underlying_temperature_candidates[under.entity_id] = {"cancel": cancel, "version": 1}
    original_setter = state.set_hvac_mode
    original_record = entity._record_underlying_tracking_command

    def failing_setter(value):
        original_setter(value)
        raise ValueError("primary setter")

    def failing_record(entity_id, command):
        original_record(entity_id, command)
        raise RuntimeError("secondary hook")

    with (
        patch.object(state, "set_hvac_mode", side_effect=failing_setter),
        patch.object(entity, "_record_underlying_tracking_command", side_effect=failing_record) as record,
        patch.object(entity, "update_states", new=AsyncMock()) as update,
    ):
        with pytest.raises(ValueError, match="primary setter"):
            await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
        record.assert_called_once()
        cancel.assert_called_once()
        update.assert_not_awaited()
    assert state.hvac_mode == VThermHvacMode_OFF
    assert entity._underlying_tracking_attempts == initial + 1
    assert entity._underlying_tracking_suspended == (initial == 2)
    assert not entity._underlying_temperature_candidates


async def test_mixed_event_waits_for_mode_application_and_preserves_source(tracking_thermostat):
    entity = tracking_thermostat
    source = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    other = MagicMock(entity_id="climate.other")
    other.hvac_mode = entity.vtherm_hvac_mode
    entity._underlyings.append(other)
    entered, release = asyncio.Event(), asyncio.Event()

    async def apply(**kwargs):
        assert kwargs["_command_cause"] == COMMAND_CAUSE_UNDERLYING_TRACKING
        entered.set()
        await release.wait()

    try:
        with patch.object(entity, "update_states", side_effect=apply), patch.object(entity, "_consider_underlying_temperature_candidate") as consider:
            task = asyncio.create_task(entity.underlying_changed(source, None, None, 23, None, State(source.entity_id, "off"), State(source.entity_id, "heat")))
            await entered.wait()
            consider.assert_not_called()
            release.set()
            await task
            consider.assert_called_once_with(source, 23)
            assert entity._underlying_temperature_observed[source.entity_id] == 23
            assert other.entity_id not in entity._underlying_temperature_observed
    finally:
        entity._underlyings.remove(other)


@pytest.mark.parametrize("source_first,aligned", [(True, True), (False, True), (True, False), (False, False)])
async def test_temperature_source_survives_alignment_loop(hass, tracking_thermostat, source_first, aligned):
    """The real candidate and reference belong to the source even on alignment refusal."""
    entity = tracking_thermostat
    source = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    source._last_sent_temperature = None
    other = MagicMock(entity_id="climate.other", last_sent_temperature=27, target_temperature_step=None)
    other.hvac_mode = entity.vtherm_hvac_mode if aligned else (
        VThermHvacMode_HEAT if entity.vtherm_hvac_mode == VThermHvacMode_OFF else VThermHvacMode_OFF
    )
    if source_first:
        entity._underlyings.append(other)
    else:
        entity._underlyings.insert(0, other)
    try:
        with (
            patch.object(entity, "update_states", new=AsyncMock()),
            patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", return_value=lambda: None),
        ):
            await entity.underlying_changed(source, None, None, 27, None, State(source.entity_id, "off"), State(source.entity_id, "heat"))
        assert entity._underlying_tracking_attempts == int(aligned)
        assert list(entity._underlying_temperature_candidates) == [source.entity_id]
        assert entity._underlying_temperature_observed[source.entity_id] == 27
        assert other.entity_id not in entity._underlying_temperature_observed
    finally:
        entity._underlyings.remove(other)


@pytest.mark.parametrize("initial", [0, 1, 2])
async def test_mixed_candidate_timer_starts_after_application(hass, tracking_thermostat, initial):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    hass.states.async_set(under.entity_id, "off", {"temperature": 27})
    await hass.async_block_till_done()
    entity._on_external_command_received()
    entity._underlying_tracking_attempts = initial
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity.requested_state.set_target_temperature(20)
    under._last_sent_temperature = None
    clock = [0]
    timers = []

    async def apply(**kwargs):
        assert not timers
        clock[0] = 8  # mode application took eight seconds

    def register(_hass, delay, cb):
        timers.append((clock[0], delay, cb))
        return lambda: None

    with patch.object(entity, "update_states", side_effect=apply), patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=register):
        await entity.underlying_changed(under, None, None, 27, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    if initial == 2:
        assert not timers
        assert entity._underlying_tracking_suspended
    else:
        assert [(when, delay) for when, delay, _ in timers] == [(8, 5)]
        assert entity._underlying_tracking_attempts == initial + 1
        assert entity.requested_state.target_temperature == 20
        with patch.object(entity, "update_states", new=AsyncMock()):
            await timers[0][2](None)
        assert entity.requested_state.target_temperature == 27
        assert entity._underlying_tracking_attempts == initial + 2


async def test_refused_mode_keeps_action_fan_and_temperature_source(tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._underlying_tracking_suspended = True
    with patch.object(entity, "update_states", new=AsyncMock()) as update, patch.object(entity, "_consider_underlying_temperature_candidate") as consider:
        await entity.underlying_changed(under, None, None, 23, "low", State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity._attr_fan_mode == "low"
    assert entity._underlying_tracking_attempts == 0
    update.assert_awaited_once_with(_preserve_underlying_temperature_candidates=True)
    consider.assert_called_once_with(under, 23)


@pytest.mark.parametrize("error", [RuntimeError("apply"), asyncio.CancelledError()])
async def test_failed_or_cancelled_mode_application_has_no_fictitious_candidate(tracking_thermostat, error):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    with patch.object(entity, "update_states", new=AsyncMock(side_effect=error)), patch.object(entity, "_consider_underlying_temperature_candidate") as consider:
        with pytest.raises(type(error)):
            await entity.underlying_changed(under, None, None, 27, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity._underlying_tracking_attempts == 1
    consider.assert_not_called()


async def test_cancelled_candidate_is_inert_even_if_a_cancel_handle_fails(hass, tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    callbacks = []
    under._last_sent_temperature = None
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), MagicMock(side_effect=ValueError("cancel")))[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
    entity._underlying_tracking_attempts = 2
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    with pytest.raises(ValueError, match="cancel"):
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity._underlying_tracking_attempts == 3
    assert entity._underlying_tracking_suspended
    assert not entity._underlying_temperature_candidates
    old_temperature = entity.requested_state.target_temperature
    await callbacks[0](None)
    assert entity.requested_state.target_temperature == old_temperature


@pytest.mark.parametrize("sequence", ["MMT", "MTM", "TMM"])
async def test_mixed_adoptions_share_one_budget_without_service(hass, tracking_thermostat, sequence):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    with patch.object(under, "_underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"temperature": 27})
        await hass.async_block_till_done()
    entity._on_external_command_received()
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity.requested_state.set_target_temperature(20)
    under._last_sent_temperature = None
    callbacks = []
    with (
        patch.object(entity, "update_states", new=AsyncMock()),
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
    ):
        for index, kind in enumerate(sequence, 1):
            if kind == "M":
                current = str(entity.requested_state.hvac_mode)
                target = "off" if current == "heat" else "heat"
                await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, target), State(under.entity_id, current))
            else:
                entity._consider_underlying_temperature_candidate(under, 27)
                await callbacks[-1](None)
            assert entity._underlying_tracking_attempts == index
        assert entity._underlying_tracking_suspended
        current = str(entity.requested_state.hvac_mode)
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off" if current == "heat" else "heat"), State(under.entity_id, current))
        assert entity._underlying_tracking_attempts == 3


async def test_reentrant_external_rearm_during_invalidation_does_not_redebit(tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._underlying_tracking_attempts = 2
    entity._underlying_temperature_candidates[under.entity_id] = {
        "cancel": entity._on_external_command_received,
        "version": 1,
        "temperature": 27,
    }
    with patch.object(entity, "update_states", new=AsyncMock()):
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity._underlying_tracking_attempts == 0
    assert not entity._underlying_tracking_suspended
    assert not entity._underlying_temperature_candidates


@pytest.mark.parametrize("initial", [0, 2])
async def test_real_eager_expiration_before_tracked_finalization(hass, tracking_thermostat, initial):
    """The real manager resumes immediately; an eager task may reset flags first."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    manager = entity.timed_preset_manager
    state = entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    state.set_preset(VThermPreset.NONE)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now - timedelta(seconds=1)
    callbacks = []
    under._last_sent_temperature = None
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
    assert manager._expiration_paused
    entity._underlying_tracking_attempts = initial
    trace = []

    async def update(*args, **kwargs):
        trace.append((kwargs.get("_command_cause"), str(state.hvac_mode), state.preset, state.is_changed, entity._underlying_tracking_attempts))
        state.reset_changed()

    with patch.object(entity, "update_states", side_effect=update):
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
        await hass.async_block_till_done()
    assert [item[0] for item in trace] == [None, COMMAND_CAUSE_UNDERLYING_TRACKING]
    assert all(item[1] == "off" and item[2] == VThermPreset.COMFORT and item[3] and item[4] == initial + 1 for item in trace)
    assert not manager.is_timed_preset_active
    assert not entity._underlying_temperature_candidates
    await callbacks[0](None)
    assert entity._underlying_tracking_attempts == initial + 1


async def test_real_eager_expiration_and_real_state_application(hass, tracking_thermostat):
    """Exercise the manager and both real state applications, with service boundaries mocked."""
    entity = tracking_thermostat
    under, manager, state = entity.underlying_entity(0), entity.timed_preset_manager, entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    state.set_preset(VThermPreset.NONE)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now - timedelta(seconds=1)
    under._last_sent_temperature = None
    callbacks = []
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
    entity._underlying_tracking_attempts = 2
    original_update = entity.update_states
    trace = []

    async def traced_update(*args, **kwargs):
        trace.append(("start", kwargs.get("_command_cause"), str(state.hvac_mode), state.preset, entity._underlying_tracking_attempts))
        result = await original_update(*args, **kwargs)
        trace.append(("end", kwargs.get("_command_cause"), str(state.hvac_mode), state.preset, entity._underlying_tracking_attempts))
        return result

    with (
        patch.object(entity, "update_states", side_effect=traced_update),
        patch.object(entity, "async_control_heating", new=AsyncMock(return_value=True)),
        patch.object(under, "hass_services_async_call", new=AsyncMock()),
    ):
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
        await hass.async_block_till_done()
    starts = [item for item in trace if item[0] == "start"]
    assert [item[1] for item in starts] == [None, COMMAND_CAUSE_UNDERLYING_TRACKING]
    assert all(item[2] == "off" and item[3] == VThermPreset.COMFORT and item[4] == 3 for item in starts)
    assert state.hvac_mode == VThermHvacMode_OFF
    assert state.preset == VThermPreset.COMFORT
    assert not manager.is_timed_preset_active
    assert not entity._underlying_temperature_candidates
    await callbacks[0](None)
    assert entity._underlying_tracking_attempts == 3


async def test_eager_expiration_resumes_interrupted_preset(tracking_thermostat):
    """Mode adoption retains immediate resumption of an interrupted timed preset."""
    entity = tracking_thermostat
    under, manager, state = entity.underlying_entity(0), entity.timed_preset_manager, entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    state.set_preset(VThermPreset.NONE)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.ECO
    manager._timed_preset_end_time = entity.now - timedelta(seconds=1)
    manager._resume_preset = VThermPreset.COMFORT
    manager._resume_end_time = entity.now + timedelta(minutes=5)
    resume_end = manager._resume_end_time
    under._last_sent_temperature = None
    trace = []

    async def update(*args, **kwargs):
        trace.append((kwargs.get("_command_cause"), state.preset, str(state.hvac_mode)))
        state.reset_changed()

    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", return_value=lambda: None),
        patch.object(entity, "update_states", side_effect=update),
    ):
        entity._consider_underlying_temperature_candidate(under, 27)
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
    assert trace == [(None, VThermPreset.COMFORT, "off"), (COMMAND_CAUSE_UNDERLYING_TRACKING, VThermPreset.COMFORT, "off")]
    assert manager.is_timed_preset_active
    assert manager._timed_preset == VThermPreset.COMFORT
    assert manager._timed_preset_end_time == resume_end
    assert not manager._expiration_paused
    assert entity._underlying_tracking_attempts == 1


@pytest.mark.parametrize("assign", [False, True])
async def test_temperature_setter_failure(hass, tracking_thermostat, assign):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    hass.states.async_set(under.entity_id, "off", {"temperature": 27})
    await hass.async_block_till_done()
    entity._on_external_command_received()
    under._last_sent_temperature = None
    state = entity.requested_state
    state.set_target_temperature(20)
    callbacks = []
    original = state.set_target_temperature

    def failing(value):
        if assign:
            original(value)
        raise ValueError("temperature setter")

    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
    with patch.object(state, "set_target_temperature", side_effect=failing), patch.object(entity, "update_states", new=AsyncMock()) as update:
        with pytest.raises(ValueError, match="temperature setter"):
            await callbacks[0](None)
    assert state.target_temperature == (27 if assign else 20)
    assert entity._underlying_tracking_attempts == int(assign)
    assert not entity._underlying_temperature_candidates
    update.assert_not_awaited()
    await callbacks[0](None)
    assert entity._underlying_tracking_attempts == int(assign)


async def test_temperature_candidate_replaced_during_manual_cleanup(hass, tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    hass.states.async_set(under.entity_id, "off", {"temperature": 27})
    await hass.async_block_till_done()
    entity._on_external_command_received()
    entity.requested_state.set_target_temperature(20)
    under._last_sent_temperature = None
    callbacks = []
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
        with patch.object(entity.timed_preset_manager, "cancel_without_revert", side_effect=lambda: entity._consider_underlying_temperature_candidate(under, 28)):
            await callbacks[0](None)
    assert entity.requested_state.target_temperature == 20
    assert entity._underlying_tracking_attempts == 0
    assert entity._underlying_temperature_candidates[under.entity_id]["temperature"] == 28


async def test_new_candidate_during_other_handle_cleanup_keeps_preset_paused(hass, tracking_thermostat):
    """An older closure must not cancel the preset paused for a newer candidate."""
    entity = tracking_thermostat
    under, manager, state = entity.underlying_entity(0), entity.timed_preset_manager, entity.requested_state
    with patch.object(under, "_underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"temperature": 27})
        await hass.async_block_till_done()
    entity._on_external_command_received()
    state.set_target_temperature(20)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now + timedelta(minutes=5)
    under._last_sent_temperature = None
    callbacks = []
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
        entity._underlying_temperature_candidates["climate.other"] = {
            "temperature": 26,
            "version": 0,
            "cancel": lambda: entity._consider_underlying_temperature_candidate(under, 28),
        }
        await callbacks[0](None)
    assert entity._underlying_temperature_candidates[under.entity_id]["temperature"] == 28
    assert manager.is_timed_preset_active
    assert manager._expiration_paused
    assert state.target_temperature == 20
    assert entity._underlying_tracking_attempts == 0


async def test_new_preset_intention_during_other_handle_cleanup_is_preserved(hass, tracking_thermostat):
    """An obsolete closure must not cancel an override after a newer intention."""
    entity = tracking_thermostat
    under, manager, state = entity.underlying_entity(0), entity.timed_preset_manager, entity.requested_state
    with patch.object(under, "_underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"temperature": 27})
        await hass.async_block_till_done()
    entity._on_external_command_received()
    state.set_target_temperature(20)
    state.set_preset(VThermPreset.NONE)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now + timedelta(minutes=5)
    under._last_sent_temperature = None
    callbacks = []

    def newer_intention():
        state.set_preset(VThermPreset.COMFORT)
        entity._on_external_command_received()

    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
        entity._underlying_temperature_candidates["climate.other"] = {
            "temperature": 26, "version": 0, "cancel": newer_intention,
        }
        await callbacks[0](None)
    assert manager.is_timed_preset_active
    assert not manager._expiration_paused
    assert state.preset == VThermPreset.COMFORT
    assert state.target_temperature == 20
    assert entity._underlying_tracking_attempts == 0


async def test_failed_handle_does_not_cancel_reentrant_replacement(hass, tracking_thermostat):
    """Finish the old batch after an error without resuming the new candidate's pause."""
    entity = tracking_thermostat
    under, manager = entity.underlying_entity(0), entity.timed_preset_manager
    with patch.object(under, "_underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"temperature": 27})
        await hass.async_block_till_done()
    entity._on_external_command_received()
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._timed_preset_end_time = entity.now + timedelta(minutes=5)
    under._last_sent_temperature = None
    callbacks = []
    failed = MagicMock(side_effect=ValueError("first handle"))
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
        entity._underlying_temperature_candidates["climate.first"] = {"cancel": failed, "version": 0}
        entity._underlying_temperature_candidates["climate.second"] = {
            "cancel": lambda: entity._consider_underlying_temperature_candidate(under, 28), "version": 0,
        }
        with pytest.raises(ValueError, match="first handle"):
            await callbacks[0](None)
        failed.assert_called_once()
        assert entity._underlying_temperature_candidates[under.entity_id]["temperature"] == 28
        assert manager.is_timed_preset_active and manager._expiration_paused
        await callbacks[0](None)
        assert entity._underlying_tracking_attempts == 0


async def test_failed_early_resume_is_not_retried(hass, tracking_thermostat):
    """A failing early resume keeps its error and is not invoked twice."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    with patch.object(under, "_underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "off", {"temperature": 27})
        await hass.async_block_till_done()
    entity._on_external_command_received()
    entity.requested_state.set_target_temperature(20)
    under._last_sent_temperature = None
    callbacks = []
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]):
        entity._consider_underlying_temperature_candidate(under, 27)
        entity._underlying_temperature_candidates["climate.other"] = {
            "cancel": lambda: entity.requested_state.set_target_temperature(21), "version": 0,
        }
        with patch.object(entity.timed_preset_manager, "resume_expiration", side_effect=ValueError("resume")) as resume:
            with pytest.raises(ValueError, match="resume"):
                await callbacks[0](None)
            resume.assert_called_once()
    assert entity.requested_state.target_temperature == 21
    assert entity._underlying_tracking_attempts == 0


async def test_identical_temperature_keeps_manual_effects_and_counts_real_attempt(hass, tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    hass.states.async_set(under.entity_id, "off", {"temperature": 22})
    await hass.async_block_till_done()
    entity._on_external_command_received()
    state, manager = entity.requested_state, entity.timed_preset_manager
    state.set_target_temperature(22)
    state.set_preset(VThermPreset.COMFORT)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now + timedelta(minutes=5)
    old_expiration = manager._timed_preset_end_time
    under._last_sent_temperature = 15
    entity._underlying_tracking_attempts = 2
    callbacks = []

    async def apply(**kwargs):
        assert await under.set_temperature(23, None, None, command_cause=kwargs["_command_cause"])

    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
        patch.object(entity, "update_states", side_effect=apply) as update,
        patch.object(under, "hass_services_async_call", new=AsyncMock()) as service,
    ):
        entity._consider_underlying_temperature_candidate(under, 22)
        assert manager._expiration_paused
        await callbacks[0](None)
        update.assert_awaited_once_with(force=True, _command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)
        assert service.await_count == 1
    assert state.target_temperature == 22
    assert state.preset == VThermPreset.NONE
    assert not manager.is_timed_preset_active
    assert entity._underlying_tracking_attempts == 3
    assert entity._underlying_tracking_suspended
    await manager._async_timed_preset_expired(old_expiration)
    assert state.preset == VThermPreset.NONE


async def test_deferred_expiration_keeps_new_mode(hass, tracking_thermostat):
    entity = tracking_thermostat
    under, manager, state = entity.underlying_entity(0), entity.timed_preset_manager, entity.requested_state
    state.set_hvac_mode(VThermHvacMode_HEAT)
    state.set_preset(VThermPreset.NONE)
    manager._is_timed_preset_active = True
    manager._is_manual_override = True
    manager._timed_preset = VThermPreset.NONE
    manager._original_preset = VThermPreset.COMFORT
    manager._timed_preset_end_time = entity.now - timedelta(seconds=1)
    under._last_sent_temperature = None
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", return_value=lambda: None):
        entity._consider_underlying_temperature_candidate(under, 27)
    entity._underlying_tracking_attempts = 2
    trace = []
    original_create = hass.async_create_task

    def create_deferred(coro, *args, **kwargs):
        kwargs["eager_start"] = False
        return original_create(coro, *args, **kwargs)

    async def update(*args, **kwargs):
        trace.append(kwargs.get("_command_cause"))
        state.reset_changed()

    with patch.object(hass, "async_create_task", side_effect=create_deferred), patch.object(entity, "update_states", side_effect=update):
        await entity.underlying_changed(under, None, None, None, None, State(under.entity_id, "off"), State(under.entity_id, "heat"))
        await hass.async_block_till_done()
    assert trace == [COMMAND_CAUSE_UNDERLYING_TRACKING, None]
    assert state.hvac_mode == VThermHvacMode_OFF
    assert state.preset == VThermPreset.COMFORT
    assert entity._underlying_tracking_attempts == 3


async def test_real_tagged_attempt_and_trvzb_resend(tracking_thermostat):
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_hvac_mode(VThermHvacMode_OFF)
    callbacks = []

    async def apply(**kwargs):
        assert await under.set_hvac_mode(VThermHvacMode_HEAT, command_cause=kwargs["_command_cause"])

    with (
        patch.object(entity, "update_states", side_effect=apply),
        patch.object(under, "hass_services_async_call", new=AsyncMock()) as service,
        patch("custom_components.versatile_thermostat.underlyings.async_call_later", side_effect=lambda h, delay, cb: (callbacks.append((delay, cb)), lambda: None)[1]),
    ):
        await under._underlying_changed(under.entity_id, State(under.entity_id, "heat"), State(under.entity_id, "off"))
        assert entity._underlying_tracking_attempts == 2  # mode adoption + actual HVAC attempt
        assert service.await_count == 1
        assert callbacks[0][0] == 2
        under._last_sent_temperature = 23
        await callbacks[0][1](None)
        assert entity._underlying_tracking_attempts == 3
        assert entity._underlying_tracking_suspended
        assert service.await_count == 2
        assert await under.set_temperature(24, None, None, command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING) is False
        assert service.await_count == 2


async def test_valve_inherited_callback_obeys_suspension(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=VThermHvacMode_OFF)
    await create_and_register_mock_number(hass, "mock_opening", "MockOpening", value=0, min=0, max=100)
    await create_and_register_mock_number(hass, "mock_closing", "MockClosing", value=100, min=0, max=100)
    config = PARTIAL_CLIMATE_NOT_REGULATED_CONFIG | {
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
        CONF_OPENING_DEGREE_LIST: ["number.mock_opening"],
        CONF_CLOSING_DEGREE_LIST: ["number.mock_closing"],
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.1,
    }
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="valve2159", data=config)
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    try:
        assert isinstance(entity, ThermostatOverClimateValve)
        entity.set_follow_underlying_temp_change(True)
        await hass.async_block_till_done()
        entity._on_external_command_received()
        source = entity.underlying_entity(0)
        entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
        entity._underlying_tracking_attempts = 3
        entity._underlying_tracking_suspended = True
        with patch.object(entity, "update_states", new=AsyncMock()) as update:
            await entity.underlying_changed(source, None, None, None, None, State(source.entity_id, "off"), State(source.entity_id, "heat"))
            assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
            update.assert_not_awaited()
            entity._on_external_command_received()
            await entity.underlying_changed(source, None, None, None, None, State(source.entity_id, "off"), State(source.entity_id, "heat"))
            assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
            assert entity._underlying_tracking_attempts == 1
            update.assert_awaited_once_with(_command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)
    finally:
        entity.remove_thermostat()


@pytest.mark.parametrize("initial,expected_count,expected_services", [(0, 2, 1), (1, 3, 1), (2, 3, 0)])
async def test_saturating_off_publication_and_other_trv(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event, initial, expected_count, expected_services):
    """AC-039: logical OFF is not evidence that B has received a physical OFF."""
    for name in ("mock_climate", "mock_climate_b"):
        await create_and_register_mock_climate(hass, name, name, {}, hvac_mode=VThermHvacMode_HEAT)
    entry = MockConfigEntry(
        domain=DOMAIN, title="TheOverClimateMockName", unique_id="multi2159",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG | {CONF_UNDERLYING_LIST: ["climate.mock_climate", "climate.mock_climate_b"]},
    )
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    try:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()
        entity.set_follow_underlying_temp_change(True)
        source, other = entity.underlying_entity(0), entity.underlying_entity(1)
        old = hass.states.get(source.entity_id)
        with patch.object(entity, "underlying_changed", new=AsyncMock()):
            hass.states.async_set(source.entity_id, "off", dict(old.attributes))
            await hass.async_block_till_done()
        new = hass.states.get(source.entity_id)
        source._hvac_mode = VThermHvacMode_OFF
        entity._on_external_command_received()
        entity._underlying_tracking_attempts = initial
        with (
            patch.object(source, "hass_services_async_call", new=AsyncMock()) as source_service,
            patch.object(other, "hass_services_async_call", new=AsyncMock()) as other_service,
            patch.object(entity, "async_control_heating", new=AsyncMock(return_value=True)),
        ):
            await source._underlying_changed(source.entity_id, new, old)
            assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
            assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
            assert entity.hvac_mode == "off"
            assert hass.states.get(other.entity_id).state == "heat"
            assert source_service.await_count == 0
            assert other_service.await_count == expected_services
            assert entity._underlying_tracking_attempts == expected_count
            assert entity._underlying_tracking_suspended == (expected_count == 3)
    finally:
        entity.remove_thermostat()