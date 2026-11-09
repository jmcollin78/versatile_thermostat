# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name, wildcard-import, unused-wildcard-import, invalid-name
"""Test the underlying hooks offered to the external feature managers (issue #2181).

A fake plugin feature manager records the hook calls and the real service calls
in the same list, so that the tests can check the order of the notifications.
"""

import asyncio
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant, ServiceRegistry

from vtherm_api import CommandReceiptKind, PowerCommandKind, UnderlyingPowerCommand, ValveCommand, ValveCommandCause

from custom_components.versatile_thermostat.base_manager import BaseFeatureManager
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate

from .commons import *
from .const import *
from .test_inhibition import (
    CLIMATE,
    CLOSING,
    OPENING,
    PRESETS,
    SWITCH,
    VALVE,
    advance,
    api,
    heating_climate_valve_vtherm,
    heating_climate_vtherm,
    inhibit,
    switch_entry,
    uninhibit,
    valve_entry,
)

logging.getLogger().setLevel(logging.DEBUG)

SWITCH2 = "switch.mock_switch2"


##
## Fake plugin
##
class _BaseFakeManager(BaseFeatureManager):
    """Feature manager of a fake plugin: records the hook calls in a shared list"""

    def __init__(self, thermostat, events: list, configured: bool = True) -> None:
        super().__init__(thermostat, thermostat.hass, "fake_hooks_fm")
        self.events = events
        self.configured = configured

    def post_init(self, entry_infos) -> None:
        """Nothing to read"""

    async def start_listening(self) -> None:
        """Nothing to listen"""

    async def refresh_state(self) -> bool:
        """Nothing to refresh"""
        return False

    @property
    def is_configured(self) -> bool:
        return self.configured

    @property
    def is_detected(self) -> bool:
        return False


class ModeHookMixin:
    """Implements async_before_underlying_hvac_mode"""

    async def async_before_underlying_hvac_mode(self, climate_entity_id, hvac_mode, current_hvac_mode, command_cause):
        self.events.append(("before_hvac_mode", climate_entity_id, hvac_mode, current_hvac_mode, command_cause))


class ValveHookMixin:
    """Implements async_after_valve_command"""

    async def async_after_valve_command(self, command: ValveCommand):
        self.events.append(("after_valve", command))


class PowerHookMixin:
    """Implements async_on_underlying_power"""

    async def async_on_underlying_power(self, command: UnderlyingPowerCommand):
        self.events.append(("power", command))


class FullManager(ModeHookMixin, ValveHookMixin, PowerHookMixin, _BaseFakeManager):
    """Implements the three hooks"""


class ModeOnlyManager(ModeHookMixin, _BaseFakeManager):
    """Implements one hook only"""


class FailingManager(FullManager):
    """Every hook raises"""

    async def async_before_underlying_hvac_mode(self, *args):
        raise RuntimeError("boom before")

    async def async_after_valve_command(self, command):
        raise RuntimeError("boom valve")

    async def async_on_underlying_power(self, command):
        raise RuntimeError("boom power")


class SlowManager(FullManager):
    """Every hook is slower than the timeout"""

    async def async_before_underlying_hvac_mode(self, *args):
        await asyncio.sleep(30)

    async def async_after_valve_command(self, command):
        await asyncio.sleep(30)

    async def async_on_underlying_power(self, command):
        await asyncio.sleep(30)


class FakeFactory:
    """Factory of the fake plugin"""

    name = "fake_hooks_fm"

    def __init__(self, manager_class, events: list, configured: bool = True) -> None:
        self.manager_class = manager_class
        self.events = events
        self.configured = configured

    def supports(self, thermostat) -> bool:
        return True

    def create(self, thermostat):
        return self.manager_class(thermostat, self.events, self.configured)


def register(hass, manager_class=FullManager, configured: bool = True) -> list:
    """Register the fake plugin. Returns the shared event list"""
    events: list = []
    api(hass).register_feature_manager(FakeFactory(manager_class, events, configured))
    return events


@contextmanager
def record_services(events: list):
    """Record the real set_hvac_mode and set_value calls in the shared event list"""
    original = ServiceRegistry.async_call

    async def wrapper(registry, domain, service, service_data=None, blocking=False, context=None, target=None, return_response=False):
        if (domain, service) in (("climate", "set_hvac_mode"), ("number", "set_value")):
            ids = (target or {}).get("entity_id") or (service_data or {}).get("entity_id")
            events.append(("service", domain, service, ids, dict(service_data or {})))
        return await original(registry, domain, service, service_data, blocking, context, target, return_response)

    with patch.object(ServiceRegistry, "async_call", wrapper):
        yield


def names(events: list, kind: str | None = None) -> list:
    """The event kinds, optionally filtered"""
    return [e[0] for e in events if kind is None or e[0] == kind]


def commands(events: list, kind: str) -> list:
    """The command objects of an event kind"""
    return [e[1] for e in events if e[0] == kind]


def position(events: list, predicate) -> int:
    """Index of the first event matching the predicate"""
    for i, event in enumerate(events):
        if predicate(event):
            return i
    raise AssertionError(f"event not found in {events}")


async def two_switches_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor):
    """An over_switch VTherm with two underlyings heating at about 30%"""
    await register_mock_entity(hass, MockSwitch(hass, "mock_switch", "theMockedSwitch"), SWITCH_DOMAIN)
    await register_mock_entity(hass, MockSwitch(hass, "mock_switch2", "theMockedSwitch2"), SWITCH_DOMAIN)
    entry = switch_entry(unique_id="twoSwitchHooks", **{CONF_UNDERLYING_LIST: [SWITCH, SWITCH2]})
    vtherm = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_ext_temp_sensor.set_native_value(20)
    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    return vtherm


##
## Hook before the hvac mode
##
async def test_before_hvac_mode_called_before_the_service(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """OFF then HEAT: the hook is called before the service, with the real state of the climate"""
    events = register(hass)
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    events.clear()

    with record_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        await hass.async_block_till_done()

        hooks = [e for e in events if e[0] == "before_hvac_mode"]
        assert hooks == [("before_hvac_mode", CLIMATE, "off", "heat", None)]
        assert position(events, lambda e: e[0] == "before_hvac_mode") < position(events, lambda e: e[:3] == ("service", "climate", "set_hvac_mode"))
        events.clear()

        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

        hooks = [e for e in events if e[0] == "before_hvac_mode"]
        assert hooks == [("before_hvac_mode", CLIMATE, "heat", "off", None)]
        assert position(events, lambda e: e[0] == "before_hvac_mode") < position(events, lambda e: e[:3] == ("service", "climate", "set_hvac_mode"))


async def test_before_hvac_mode_not_called_when_mode_already_set(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The mode is already in place: no command, no hook"""
    events = register(hass)
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings[0]
    events.clear()

    with record_services(events):
        assert await under.set_hvac_mode(VThermHvacMode_HEAT) is False

    assert events == []


async def test_before_hvac_mode_not_called_when_inhibition_blocks(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The inhibition gate drops the command: the hook is not called"""
    events = register(hass)
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    await inhibit(hass, vtherm, True)
    under = vtherm._underlyings[0]
    events.clear()

    with record_services(events):
        await under.set_hvac_mode(VThermHvacMode_HEAT)

    assert events == []


async def test_before_hvac_mode_not_called_when_overpowering_refuses(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The load shedding refuses to turn on: the hook is not called"""
    events = register(hass)
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    under = vtherm._underlyings[0]
    events.clear()

    with record_services(events), patch.object(UnderlyingClimate, "check_overpowering", return_value=False):
        assert await under.set_hvac_mode(VThermHvacMode_HEAT) is False

    assert events == []


async def test_before_hvac_mode_cause_underlying_tracking(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The cause is transmitted when the VTherm follows a change made on the device"""
    events = register(hass)
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings[0]
    events.clear()

    with record_services(events):
        await under.set_hvac_mode(VThermHvacMode_OFF, command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)

    assert ("before_hvac_mode", CLIMATE, "off", "heat", COMMAND_CAUSE_UNDERLYING_TRACKING) in events


##
## Hook after a valve command
##
async def test_valve_hook_order_at_underlying_turn_off(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Valve turn_off: the valves are closed, the valve hook is called, then the mode hook, then the mode is sent"""
    events = register(hass)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings_valve_regulation[0]
    events.clear()

    with record_services(events):
        await under.turn_off()
        await hass.async_block_till_done()

    open_idx = position(events, lambda e: e[0] == "service" and e[2] == "set_value" and e[3] == OPENING)
    valve_idx = position(events, lambda e: e[0] == "after_valve")
    before_idx = position(events, lambda e: e[0] == "before_hvac_mode")
    mode_idx = position(events, lambda e: e[0] == "service" and e[2] == "set_hvac_mode")
    assert open_idx < valve_idx < before_idx < mode_idx
    assert events[open_idx][4] == {"value": 0}
    assert events[before_idx] == ("before_hvac_mode", CLIMATE, "off", "heat", None)

    command: ValveCommand = events[valve_idx][1]
    assert command.cause == ValveCommandCause.TURN_OFF
    assert command.percent_open == 0
    assert command.opening_degree == 0
    assert command.closing_degree == 100
    assert command.climate_entity_id == CLIMATE
    assert command.opening_degree_entity_id == OPENING
    assert command.closing_degree_entity_id == CLOSING


async def test_valve_hook_hvac_mode_off_of_the_vtherm(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """VTherm OFF: the mode hook is called with the real state of the climate and the valves end closed"""
    events = register(hass)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    events.clear()

    with record_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        await hass.async_block_till_done()

    assert ("before_hvac_mode", CLIMATE, "off", "heat", None) in events
    assert position(events, lambda e: e[0] == "before_hvac_mode") < position(events, lambda e: e[:3] == ("service", "climate", "set_hvac_mode"))
    valve_commands = commands(events, "after_valve")
    assert valve_commands and valve_commands[-1].percent_open == 0
    assert valve_commands[-1].hvac_mode == "off"
    assert float(hass.states.get(OPENING).state) == 0


async def test_valve_hook_regulation_and_values(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The regulation cycle sends REGULATION commands carrying the values really sent"""
    events = register(hass)
    vtherm, _, opening, closing = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    events.clear()

    with record_services(events):
        await vtherm.cycle_scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True)
        await hass.async_block_till_done()

    valve_commands = commands(events, "after_valve")
    assert len(valve_commands) == 1
    command = valve_commands[0]
    assert command.cause == ValveCommandCause.REGULATION
    assert command.percent_open == 50
    assert command.hvac_mode == "heat"
    sent_opening = [e[4]["value"] for e in events if e[0] == "service" and e[3] == OPENING]
    sent_closing = [e[4]["value"] for e in events if e[0] == "service" and e[3] == CLOSING]
    assert sent_opening == [command.opening_degree]
    assert sent_closing == [command.closing_degree]
    # sent before the notification
    assert position(events, lambda e: e[0] == "service" and e[3] == CLOSING) < position(events, lambda e: e[0] == "after_valve")


async def test_valve_hook_closing_degree_none_without_closing_entity(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """No closing degree entity: closing_degree is None"""
    events = register(hass)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings_valve_regulation[0]
    events.clear()

    with patch.object(type(under), "has_closing_degree_entity", new_callable=lambda: property(lambda self: False)):
        await under.send_percent_open(40)

    command = commands(events, "after_valve")[0]
    assert command.closing_degree is None
    assert command.closing_degree_entity_id is None
    assert command.opening_degree >= 0


async def test_valve_hook_causes(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Startup, repair and inhibition stop carry their own cause"""
    events = register(hass)
    vtherm, _, opening, closing = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings_valve_regulation[0]

    # startup: the valve is closed whereas it should be open
    opening.set_native_value(0)
    await hass.async_block_till_done()
    events.clear()
    await under.check_initial_state()
    await hass.async_block_till_done()
    assert [c.cause for c in commands(events, "after_valve")] == [ValveCommandCause.STARTUP]

    # repair: the valve drifted from the last sent value
    await under.send_percent_open(60)
    opening.set_native_value(10)
    await hass.async_block_till_done()
    vtherm._set_now(vtherm.now + timedelta(minutes=10))
    events.clear()
    assert await under.check_and_repair() is True
    assert [c.cause for c in commands(events, "after_valve")] == [ValveCommandCause.REPAIR]

    # inhibition stop
    events.clear()
    await inhibit(hass, vtherm, True)
    assert ValveCommandCause.TURN_OFF in [c.cause for c in commands(events, "after_valve")]
    # the gate is closed: no valve command goes out, no hook either
    events.clear()
    await under.send_percent_open(70)
    assert commands(events, "after_valve") == []
    await uninhibit(hass, vtherm)


async def test_valve_hook_not_called_for_seed_nor_recalibration(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The seed of unknown degrees and the recalibration write the numbers without the valve hook"""
    events = register(hass)
    vtherm, _, opening, closing = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    under = vtherm._underlyings_valve_regulation[0]
    events.clear()

    with record_services(events):
        # seed
        hass.states.async_set(CLOSING, STATE_UNKNOWN, {"min": 0, "max": 100})
        await hass.async_block_till_done()
        await under._seed_unknown_degrees_once()
        await hass.async_block_till_done()
        assert any(e[0] == "service" and e[3] == CLOSING for e in events)

        # recalibration
        events.clear()
        await under.send_value_to_number(OPENING, 100)
        await under.send_value_to_number(CLOSING, 0)
        await hass.async_block_till_done()
        assert any(e[0] == "service" and e[3] == OPENING for e in events)

    assert commands(events, "after_valve") == []


##
## Hook of the power
##
async def test_power_hook_two_switches(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Two switches: one CYCLE_START per underlying with its offset, then is_repeat at the next cycle"""
    events = register(hass)
    vtherm = await two_switches_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    scheduler = vtherm.cycle_scheduler
    receipts = []

    async def _on_receipt(receipt):
        receipts.append(receipt)

    scheduler.register_command_receipt_callback(_on_receipt)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    starts = [c for c in commands(events, "power") if c.kind == PowerCommandKind.CYCLE_START]
    first = starts[-2:]
    assert [c.underlying_entity_id for c in first] == [SWITCH, SWITCH2]
    assert first[0].start_offset_sec == 0.0
    assert first[1].start_offset_sec == pytest.approx(scheduler._cycle_duration_sec / 2)
    for command in first:
        assert command.underlying_type == "switch"
        assert command.climate_entity_id is None
        assert command.hvac_mode == "heat"
        assert command.is_repeat is False
        assert command.cycle_duration_sec == scheduler._cycle_duration_sec
        assert 0 < command.applied_on_percent < 1
        assert command.applied_on_percent == pytest.approx(command.on_time_sec / command.cycle_duration_sec)
        assert command.requested_on_percent > 0

    # Same time origin for the two underlyings and as the receipt of the cycle start
    start_receipt = [r for r in receipts if r.kind == CommandReceiptKind.CYCLE_START][-1]
    assert first[0].cycle_start_monotonic is not None
    assert first[0].cycle_start_monotonic == first[1].cycle_start_monotonic == start_receipt.cycle_start_monotonic
    for command in first:
        assert command.monotonic >= command.cycle_start_monotonic

    nb = len(commands(events, "power"))
    scheduler._cycle_start_time -= 300
    await scheduler._on_master_cycle_end(None)
    await hass.async_block_till_done()
    repeats = commands(events, "power")[nb:]
    assert [c.kind for c in repeats] == [PowerCommandKind.CYCLE_START] * 2
    assert all(c.is_repeat for c in repeats)
    # the second cycle has a later time origin, shared by the two underlyings
    assert repeats[0].cycle_start_monotonic == repeats[1].cycle_start_monotonic
    assert repeats[0].cycle_start_monotonic > first[0].cycle_start_monotonic
    # an internal restart is not a STOP
    assert PowerCommandKind.STOP not in [c.kind for c in repeats]


async def test_power_hook_stop_at_turn_off(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """OFF: a STOP per underlying with an applied power of 0"""
    events = register(hass)
    vtherm = await two_switches_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()
    events.clear()

    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    stops = [c for c in commands(events, "power") if c.kind == PowerCommandKind.STOP]
    assert [c.underlying_entity_id for c in stops] == [SWITCH, SWITCH2]
    assert all(c.applied_on_percent == 0 and c.hvac_mode == "off" for c in stops)
    # the cycle is over: there is no time origin
    assert all(c.cycle_start_monotonic is None and c.monotonic > 0 for c in stops)


async def test_power_hook_over_valve(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """over_valve: CYCLE_START, then UPDATE in the running cycle, then STOP"""
    events = register(hass)
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    powers = commands(events, "power")
    assert powers[0].kind == PowerCommandKind.CYCLE_START
    assert powers[0].underlying_type == "valve"
    assert powers[0].underlying_entity_id == VALVE
    assert powers[0].climate_entity_id is None
    assert powers[0].start_offset_sec is None
    assert powers[0].cycle_start_monotonic is not None
    assert powers[0].monotonic >= powers[0].cycle_start_monotonic
    # no valve command hook for over_valve
    assert names(events, "after_valve") == []

    events.clear()
    await vtherm.cycle_scheduler.start_cycle(VThermHvacMode_HEAT, 0.8, force=False)
    await hass.async_block_till_done()
    updates = commands(events, "power")
    assert [c.kind for c in updates] == [PowerCommandKind.UPDATE]
    assert updates[0].requested_on_percent == pytest.approx(0.8)
    # an UPDATE inside the running cycle keeps the origin of that cycle
    assert updates[0].cycle_start_monotonic is not None
    assert updates[0].cycle_start_monotonic == vtherm.cycle_scheduler._cycle_start_monotonic
    assert updates[0].monotonic >= updates[0].cycle_start_monotonic

    events.clear()
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert PowerCommandKind.STOP in [c.kind for c in commands(events, "power")]


async def test_power_hook_over_climate_valve(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """over_climate with valve regulation: CYCLE_START then UPDATE, with the climate entity id"""
    events = register(hass)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    events.clear()

    await vtherm.cycle_scheduler.start_cycle(VThermHvacMode_HEAT, 0.6, force=True)
    await vtherm.cycle_scheduler.start_cycle(VThermHvacMode_HEAT, 0.9, force=False)
    await hass.async_block_till_done()

    powers = commands(events, "power")
    assert [c.kind for c in powers[:2]] == [PowerCommandKind.CYCLE_START, PowerCommandKind.UPDATE]
    assert powers[0].underlying_type == "valve_regulation"
    assert powers[0].climate_entity_id == CLIMATE
    assert powers[0].underlying_entity_id == OPENING
    assert powers[0].start_offset_sec is None


##
## Robustness
##
async def test_unconfigured_manager_receives_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager which is not configured is skipped"""
    events = register(hass, FullManager, configured=False)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    assert len(vtherm._external_managers) == 1
    assert events == []


async def test_failing_hook_is_logged_and_core_command_is_sent(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """An exception in the hooks never blocks the core commands"""
    events = register(hass, FailingManager)
    vtherm, _, opening, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    events.clear()

    with record_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        await hass.async_block_till_done()

    assert hass.states.get(CLIMATE).state == "off"
    assert float(hass.states.get(OPENING).state) == 0
    assert "boom before" in caplog.text
    assert "boom valve" in caplog.text
    assert "boom power" in caplog.text


async def test_slow_hook_times_out_and_core_command_is_sent(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A hook slower than the timeout is cut, logged, and the core command is sent"""
    register(hass, SlowManager)
    with patch("custom_components.versatile_thermostat.base_thermostat.UNDERLYING_HOOK_TIMEOUT_SEC", 0.05):
        vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        await hass.async_block_till_done()

    assert hass.states.get(CLIMATE).state == "off"
    assert float(hass.states.get(OPENING).state) == 0
    assert "timed out in async_before_underlying_hvac_mode" in caplog.text
    assert "timed out in async_after_valve_command" in caplog.text


async def test_manager_with_one_hook_only(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager implementing only one hook receives only that one"""
    events = register(hass, ModeOnlyManager)
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    events.clear()

    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    assert names(events) == ["before_hvac_mode"]


async def test_no_plugin_no_error(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without any external manager the hooks return immediately"""
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    assert vtherm._external_managers == []
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).state == "off"
