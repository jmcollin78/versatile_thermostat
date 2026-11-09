# pylint: disable=protected-access, unused-argument, redefined-outer-name
"""Regression tests for #2185: a setpoint the device moves itself after VTherm turns it OFF
(e.g. a Sonoff TRVZB dropping to its minimum) must not be followed as a user gesture."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import State
from homeassistant.components.climate import HVACAction

from custom_components.versatile_thermostat.underlyings import off_settle_delay_sec
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT, VThermHvacMode_OFF
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import (
    DOMAIN,
    MockConfigEntry,
    PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    create_and_register_mock_climate,
    create_thermostat,
)

NOW_TZ = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
ECO_TEMP = 20
# The setpoint a device parks at when turned OFF, like a TRVZB at 7 °C. Set to the configured min_temp,
# as UnderlyingClimate ignores setpoints outside min/max.
DEVICE_OFF_TEMP = 15


@pytest.fixture
async def tracking_thermostat(hass, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """A heating VTherm in ECO following its heating underlying."""
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
    entity._set_now(NOW_TZ)
    entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    entity.requested_state.set_preset(VThermPreset.ECO)
    entity.requested_state.set_target_temperature(ECO_TEMP)
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    under = entity.underlying_entity(0)
    under._hvac_mode = VThermHvacMode_HEAT
    under._last_sent_temperature = ECO_TEMP
    # The fixture models a heating VTherm: the OFF sent while creating it is not a recent VTherm OFF.
    under._last_off_sent_datetime = None
    yield entity
    entity.remove_thermostat()


def _climate_state(under, hvac_mode, temperature):
    return State(under.entity_id, hvac_mode, {"hvac_action": HVACAction.OFF, "temperature": temperature})


async def _vtherm_turns_off(entity, under):
    """VTherm is turned OFF while still requested in HEAT (e.g. by an open window) and sends OFF to its underlying."""
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)
    with (
        patch.object(under._state_manager, "get_state", return_value=_climate_state(under, "heat", ECO_TEMP)),
        patch.object(under, "hass_services_async_call", new=AsyncMock()),
    ):
        assert await under.set_hvac_mode(VThermHvacMode_OFF)


async def _report(entity, under, old_state, new_state):
    """The underlying reports a state change through UnderlyingClimate. Returns the debounce delays started."""
    timers = []
    with (
        patch.object(entity, "update_states", new=AsyncMock()),
        patch(
            "custom_components.versatile_thermostat.thermostat_climate.async_call_later",
            side_effect=lambda h, delay, cb: (timers.append(delay), lambda: None)[1],
        ),
    ):
        await under._underlying_changed(under.entity_id, new_state, old_state)
    return timers


def _assert_eco_is_kept(entity, under, timers):
    assert timers == []
    assert not entity._underlying_temperature_candidates
    assert entity._underlying_temperature_status[under.entity_id] == "device_settling"
    assert entity._underlying_temperature_observed[under.entity_id] == DEVICE_OFF_TEMP
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.requested_state.preset == VThermPreset.ECO
    assert entity.requested_state.target_temperature == ECO_TEMP
    assert entity._underlying_tracking_attempts == 0


async def test_device_setpoint_after_vtherm_off_is_not_followed(tracking_thermostat):
    """VTherm turns the TRV OFF, then the TRV reports its own setpoint: ECO is kept."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    await _vtherm_turns_off(entity, under)
    entity._set_now(NOW_TZ + timedelta(seconds=1))

    timers = await _report(entity, under, _climate_state(under, "heat", ECO_TEMP), _climate_state(under, "off", ECO_TEMP))
    timers += await _report(entity, under, _climate_state(under, "off", ECO_TEMP), _climate_state(under, "off", DEVICE_OFF_TEMP))

    _assert_eco_is_kept(entity, under, timers)


async def test_off_and_device_setpoint_in_one_report_is_not_followed(tracking_thermostat):
    """The OFF transition and the device setpoint delivered together. Same report as
    test_filtered_mode_keeps_action_fan_and_temperature_tracking, but just after VTherm sent OFF."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    await _vtherm_turns_off(entity, under)
    entity._set_now(NOW_TZ + timedelta(seconds=1))

    timers = await _report(entity, under, _climate_state(under, "heat", ECO_TEMP), _climate_state(under, "off", DEVICE_OFF_TEMP))

    _assert_eco_is_kept(entity, under, timers)


async def test_device_setpoint_before_off_report_is_not_followed(tracking_thermostat):
    """The device may report its new setpoint before reporting OFF."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    await _vtherm_turns_off(entity, under)
    entity._set_now(NOW_TZ + timedelta(seconds=1))

    timers = await _report(entity, under, _climate_state(under, "heat", ECO_TEMP), _climate_state(under, "heat", DEVICE_OFF_TEMP))
    timers += await _report(entity, under, _climate_state(under, "heat", DEVICE_OFF_TEMP), _climate_state(under, "off", DEVICE_OFF_TEMP))

    _assert_eco_is_kept(entity, under, timers)


async def test_candidate_pending_before_vtherm_off_is_cancelled(tracking_thermostat):
    """A dial change made just before VTherm turns the TRV OFF is superseded by the device setpoint."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    timers = await _report(entity, under, _climate_state(under, "heat", ECO_TEMP), _climate_state(under, "heat", 25))
    assert timers == [5]
    assert list(entity._underlying_temperature_candidates) == [under.entity_id]

    await _vtherm_turns_off(entity, under)
    timers = await _report(entity, under, _climate_state(under, "heat", 25), _climate_state(under, "off", DEVICE_OFF_TEMP))

    _assert_eco_is_kept(entity, under, timers)


async def test_gesture_on_off_trv_after_settle_delay_is_still_followed(tracking_thermostat):
    """A later dial change on an OFF TRV keeps the 10.6.3 behaviour: it becomes a candidate."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    await _vtherm_turns_off(entity, under)
    entity._set_now(NOW_TZ + timedelta(seconds=off_settle_delay_sec + 1))

    timers = await _report(entity, under, _climate_state(under, "off", ECO_TEMP), _climate_state(under, "off", 25))

    assert timers == [5]
    assert entity._underlying_temperature_status[under.entity_id] == "candidate_pending"


async def test_setpoint_on_trv_not_turned_off_by_vtherm_is_followed(tracking_thermostat):
    """Without an OFF sent by VTherm, a setpoint reported by an OFF underlying is followed as in 10.6.3."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    entity._state_manager.current_state.set_hvac_mode(VThermHvacMode_OFF)

    timers = await _report(entity, under, _climate_state(under, "off", ECO_TEMP), _climate_state(under, "off", 25))

    assert timers == [5]
    assert entity._underlying_temperature_status[under.entity_id] == "candidate_pending"


async def test_sending_heat_ends_the_settle_delay(tracking_thermostat):
    """Once VTherm turns the underlying back on, the OFF is no longer recent."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    await _vtherm_turns_off(entity, under)
    with (
        patch.object(under._state_manager, "get_state", return_value=_climate_state(under, "off", DEVICE_OFF_TEMP)),
        patch.object(under, "hass_services_async_call", new=AsyncMock()),
        patch.object(under, "check_overpowering", new=AsyncMock(return_value=True)),
    ):
        assert await under.set_hvac_mode(VThermHvacMode_HEAT)
        under._cancel_delayed_commands()

    assert under.sent_off_recently() is False


async def test_inhibition_stop_starts_the_settle_delay(tracking_thermostat):
    """The OFF sent when a plugin inhibits the VTherm is a VTherm OFF as well."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    with patch.object(under, "hass_services_async_call", new=AsyncMock()):
        await under.async_inhibition_stop()

    assert under.sent_off_recently() is True


async def test_trv_switched_off_by_hand_with_device_setpoint_is_not_followed(tracking_thermostat):
    """The user switches the TRV OFF on the device, which also moves its own setpoint in the same report.
    The OFF is followed and sent by VTherm, so the device setpoint is not."""
    entity = tracking_thermostat
    under = entity.underlying_entity(0)
    timers = []
    with (
        patch.object(under._state_manager, "get_state", return_value=_climate_state(under, "heat", ECO_TEMP)),
        patch.object(under, "hass_services_async_call", new=AsyncMock()),
        patch(
            "custom_components.versatile_thermostat.thermostat_climate.async_call_later",
            side_effect=lambda h, delay, cb: (timers.append(delay), lambda: None)[1],
        ),
    ):
        await under._underlying_changed(under.entity_id, _climate_state(under, "off", DEVICE_OFF_TEMP), _climate_state(under, "heat", ECO_TEMP))

    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert under.sent_off_recently() is True
    assert timers == []
    assert entity._underlying_temperature_status[under.entity_id] == "device_settling"
    assert entity.requested_state.preset == VThermPreset.ECO
    assert entity.requested_state.target_temperature == ECO_TEMP
