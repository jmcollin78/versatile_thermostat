# pylint: disable=protected-access, unused-argument, redefined-outer-name
"""Issue #2141 - follow_underlying_temp_change must follow every manual TRV setpoint change.

- a report in the setpoint grid cell of the last sent setpoint is an echo (19.6 sent, 19.5 reported)
- one knob step (0.5) is a manual change, even when it is equal to the step
- consecutive knob changes are never suspended by the mode tracking budget (#2159)
- one candidate for the whole VTherm: the last change wins, whichever TRV it comes from
- the regulation does not overwrite a knob change while it is debounced
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.components.climate import HVACAction

from custom_components.versatile_thermostat.const import COMMAND_CAUSE_UNDERLYING_TRACKING
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import (
    DOMAIN,
    MockConfigEntry,
    PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    create_and_register_mock_climate,
    create_thermostat,
)


@pytest.fixture
async def knob_thermostat(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """A heating over_climate VTherm following its underlying, with a 0.5 TRV grid"""
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=VThermHvacMode_HEAT, hvac_action=HVACAction.OFF)
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG)
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    entity.set_follow_underlying_temp_change(True)
    await hass.async_block_till_done()
    entity._on_external_command_received()
    entity.underlying_entity(0)._last_off_sent_datetime = None
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity._attr_target_temperature_step = 0.1
    with patch.object(UnderlyingClimate, "target_temperature_step", new_callable=PropertyMock, return_value=0.5):
        yield entity
    entity.remove_thermostat()


async def report(hass, under, temperature):
    """The TRV reports a setpoint, without running the VTherm tracking (the test calls it)"""
    with patch.object(under._thermostat, "underlying_changed", new=AsyncMock()):
        hass.states.async_set(under.entity_id, "heat", {"temperature": temperature})
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    "sent,reported,same",
    [
        (19.6, 19.5, True),  # the TRV rounds the received setpoint
        (21.5, 21.6, True),  # the TRV reports the setpoint with a small offset
        (21.0, 21.0, True),
        (21.0, 21.5, False),  # one knob step
        (21.0, 20.5, False),
        (21.0, 23.0, False),
    ],
)
async def test_setpoint_grid(knob_thermostat, sent, reported, same):
    """A setpoint is compared to the last sent one on the grid of the TRV"""
    under = knob_thermostat.underlying_entity(0)
    under._last_sent_temperature = sent
    assert under.is_vtherm_setpoint(reported) is same


async def test_setpoint_grid_never_sent(knob_thermostat):
    """Nothing sent yet: every report is a manual change"""
    under = knob_thermostat.underlying_entity(0)
    under._last_sent_temperature = None
    assert under.is_vtherm_setpoint(20.0) is False


async def test_rounded_echo_does_not_switch_preset_to_none(hass, knob_thermostat):
    """VTherm sends 19.6, the TRV reports 19.5: an echo, the preset is kept"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    entity.requested_state.set_preset(VThermPreset.ECO)
    under._last_sent_temperature = 19.6
    await report(hass, under, 19.5)
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later") as call_later:
        entity._consider_underlying_temperature_candidate(under, 19.5)
    call_later.assert_not_called()
    assert entity._underlying_temperature_status[under.entity_id] == "echo_possible"
    assert not entity._underlying_temperature_candidates
    assert entity.requested_state.preset == VThermPreset.ECO


async def test_consecutive_knob_steps_are_all_adopted(hass, knob_thermostat):
    """AVATTO / Aqara scenario: every knob change is adopted, the tracking is never suspended"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    under._last_sent_temperature = 23.5
    callbacks = []
    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
        patch.object(entity, "update_states", new=AsyncMock()) as update,
    ):
        for temperature in (24.0, 26.0, 26.5, 27.0, 31.0, 30.5):
            await report(hass, under, temperature)
            entity._consider_underlying_temperature_candidate(under, temperature)
            assert entity._underlying_temperature_status[under.entity_id] == "candidate_pending"
            await callbacks[-1](None)
            assert entity.requested_state.target_temperature == temperature
            assert entity._underlying_temperature_status[under.entity_id] == "accepted"
            assert under.last_sent_temperature == temperature
            update.assert_awaited_with(force=True, _command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)

    assert entity._underlying_tracking_attempts == 0
    assert not entity._underlying_tracking_suspended
    assert entity.requested_state.preset == VThermPreset.NONE


async def test_knob_change_adopted_with_exhausted_mode_budget(hass, knob_thermostat):
    """The mode budget (#2159) does not suspend the temperature tracking"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    entity._underlying_tracking_attempts = 3
    entity._underlying_tracking_suspended = True
    under._last_sent_temperature = 20.0
    callbacks = []
    await report(hass, under, 20.5)
    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
        patch.object(entity, "update_states", new=AsyncMock()),
    ):
        entity._consider_underlying_temperature_candidate(under, 20.5)
        await callbacks[-1](None)
    assert entity.requested_state.target_temperature == 20.5


async def test_off_grid_report_is_snapped_to_vtherm_step(hass, knob_thermostat):
    """A TRV reporting 23.1 for a displayed 23.0 is adopted on the VTherm step"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    entity._attr_target_temperature_step = 0.5
    under._last_sent_temperature = 20.0
    callbacks = []
    await report(hass, under, 23.1)
    with (
        patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=lambda h, d, cb: (callbacks.append(cb), lambda: None)[1]),
        patch.object(entity, "update_states", new=AsyncMock()),
    ):
        entity._consider_underlying_temperature_candidate(under, 23.1)
        await callbacks[-1](None)
    assert entity.requested_state.target_temperature == 23.0
    assert entity._underlying_temperature_status[under.entity_id] == "accepted"
    # The TRV holds the reported value: its next report of it is an echo
    assert under.is_vtherm_setpoint(23.1)


async def test_last_change_wins_across_underlyings(hass, knob_thermostat):
    """One candidate for the whole VTherm: a change on another TRV replaces the pending one"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    under._last_sent_temperature = 20.0
    other = MagicMock(entity_id="climate.other")
    other.is_vtherm_setpoint.return_value = False
    cancels = []

    def register(_hass, _delay, _cb):
        cancel = MagicMock()
        cancels.append(cancel)
        return cancel

    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=register):
        entity._consider_underlying_temperature_candidate(under, 22.0)
        entity._consider_underlying_temperature_candidate(other, 23.0)

    cancels[0].assert_called_once()
    cancels[1].assert_not_called()
    assert list(entity._underlying_temperature_candidates) == ["climate.other"]
    assert entity._underlying_temperature_candidates["climate.other"]["temperature"] == 23.0
    assert entity._underlying_temperature_status[under.entity_id] == "cancelled"
    entity._cancel_all_underlying_temperature_candidates(resume_timed_preset=False)


async def test_echo_cancels_pending_candidate(hass, knob_thermostat):
    """The knob is turned back to the VTherm setpoint before the end of the debounce"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    under._last_sent_temperature = 20.0
    cancel = MagicMock()
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", return_value=cancel):
        entity._consider_underlying_temperature_candidate(under, 21.0)
        entity._consider_underlying_temperature_candidate(under, 20.0)
    cancel.assert_called_once()
    assert not entity._underlying_temperature_candidates
    assert entity._underlying_temperature_status[under.entity_id] == "echo_possible"


async def test_regulation_not_sent_while_debounced(hass, knob_thermostat):
    """A regulation cycle must not overwrite a knob change while it is debounced"""
    entity = knob_thermostat
    under = entity.underlying_entity(0)
    under._last_sent_temperature = 20.0
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", return_value=lambda: None):
        entity._consider_underlying_temperature_candidate(under, 22.0)

    with patch.object(under, "set_temperature", new=AsyncMock()) as set_temperature:
        await entity._send_regulated_temperature(force=True)
        set_temperature.assert_not_awaited()

        # Without pending candidate the regulation is sent again
        entity._cancel_all_underlying_temperature_candidates(resume_timed_preset=False)
        await entity._send_regulated_temperature(force=True)
        set_temperature.assert_awaited()
