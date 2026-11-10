# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name, wildcard-import, unused-wildcard-import, invalid-name
"""Test the valve write hook offered to the external feature managers: a plugin changes the opening degree of a
valve-regulation underlying before it is written, or writes the valve itself."""

import asyncio
import logging
from datetime import timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from vtherm_api import ValveCommand, ValveCommandCause, ValveWriteDecision, ValveWriteRequest

from .commons import *
from .const import *
from .fake_plugin import FakePluginManager, FaultyConfiguredMixin, register_plugin
from .test_inhibition import CLIMATE, CLOSING, OPENING, heating_climate_valve_vtherm, inhibit, uninhibit
from .test_underlying_hooks import commands, record_services

logging.getLogger().setLevel(logging.DEBUG)


class RecordingManager(FakePluginManager):
    """Records the requests and the after commands. Subclasses define what the decision is"""

    def decision(self, request: ValveWriteRequest):
        """The decision of the manager. None: leave the value unchanged"""
        return None

    async def async_before_valve_write(self, request: ValveWriteRequest):
        if not self.enabled:
            return None
        self.events.append(("before_valve", self.plugin_name, request))
        return self.decision(request)

    async def async_after_valve_command(self, command: ValveCommand):
        if self.enabled:
            self.events.append(("after_valve", command))


class PlusTen(RecordingManager):
    """Adds 10 to the proposed opening"""

    def decision(self, request):
        return ValveWriteDecision(opening_degree=request.opening_degree + 10)


class Doubler(RecordingManager):
    """Doubles the proposed opening"""

    def decision(self, request):
        return ValveWriteDecision(opening_degree=request.opening_degree * 2)


class Handler(RecordingManager):
    """Writes the valve itself"""

    settle = None
    final = None

    def decision(self, request):
        return ValveWriteDecision(opening_degree=self.final, handled=True, settle_sec=self.settle)


class SlowHandler(Handler):
    """Announces a long sequence"""

    settle = 30.0


class FinalHandler(Handler):
    """Writes the valve itself and tells the value the valve will end at"""

    final = 77


class Fixed(RecordingManager):
    """Proposes a fixed value, which can be invalid"""

    value = 55

    def decision(self, request):
        return ValveWriteDecision(opening_degree=self.value)


class Nothing(RecordingManager):
    """Returns an empty decision"""

    def decision(self, request):
        return ValveWriteDecision()


class Raising(RecordingManager):
    """Raises"""

    async def async_before_valve_write(self, request):
        if self.enabled:
            raise RuntimeError("boom write")


class Hanging(RecordingManager):
    """Slower than the timeout"""

    async def async_before_valve_write(self, request):
        if self.enabled:
            await asyncio.sleep(30)


class NotADecision(RecordingManager):
    """Returns something which is not a decision"""

    def decision(self, request):
        return {"opening_degree": 10}


class FaultyPlusTen(FaultyConfiguredMixin, PlusTen):
    """is_configured raises"""


def written(events: list, entity_id: str) -> list:
    """The values written by the core to a number entity"""
    return [e[4]["value"] for e in events if e[0] == "service" and e[3] == entity_id]


def requests(events: list) -> list[ValveWriteRequest]:
    """The valve write requests received by the managers"""
    return [e[2] for e in events if e[0] == "before_valve"]


async def start(hass: HomeAssistant, fake_temp_sensor, events: list):
    """Create the VTherm heating with the plugin still passive, then let the plugin act. Returns what heating_climate_valve_vtherm returns"""
    result = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    for manager in result[0]._external_managers:
        manager.enabled = True
    events.clear()
    return result


async def send(hass: HomeAssistant, under, events: list, value: int = 50, cause: ValveCommandCause = ValveCommandCause.REGULATION):
    """Send a percent open to the valve and record the number writes"""
    events.clear()
    with record_services(events):
        await under.send_percent_open(value, cause=cause)
        await hass.async_block_till_done()


async def test_no_manager_unchanged(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without any plugin the core computes and writes the degrees as before"""
    events: list = []
    vtherm, _, opening, _ = await start(hass, fake_temp_sensor, events)
    assert vtherm._external_managers == []
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    core_opening = written(events, OPENING)
    assert len(core_opening) == 1
    assert written(events, CLOSING) == [100 - core_opening[0]]
    assert under.last_sent_opening_value == core_opening[0]
    assert float(hass.states.get(OPENING).state) == core_opening[0]
    assert under._settle_sec is None


async def test_chain_order_and_modification(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The managers are called in the order they were registered, each one receives the value left by the previous one"""
    events = register_plugin(hass, PlusTen, "a_first")
    register_plugin(hass, Doubler, "b_second", events=events)
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 20, cause=ValveCommandCause.REPAIR)

    first, second = requests(events)
    assert [e[1] for e in events if e[0] == "before_valve"] == ["a_first", "b_second"]
    core_value = first.requested_opening_degree
    assert first.opening_degree == core_value
    assert second.opening_degree == core_value + 10
    assert second.requested_opening_degree == core_value
    assert first.percent_open == 20
    assert first.cause == ValveCommandCause.REPAIR
    assert first.climate_entity_id == CLIMATE
    assert first.opening_degree_entity_id == OPENING
    assert first.closing_degree_entity_id == CLOSING
    assert first.max_opening_degree == 100
    assert first.hvac_mode == "heat"

    final = min(100, (core_value + 10) * 2)
    assert written(events, OPENING) == [final]
    assert written(events, CLOSING) == [100 - final]
    assert under.last_sent_opening_value == final
    assert float(hass.states.get(OPENING).state) == final


async def test_empty_decision_and_none_leave_the_value(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """None and an empty decision do not change the value"""
    events = register_plugin(hass, RecordingManager, "a_none")
    register_plugin(hass, Nothing, "b_empty", events=events)
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    request = requests(events)[0]
    assert written(events, OPENING) == [request.requested_opening_degree]
    assert commands(events, "after_valve")[0].requested_opening_degree is None


async def test_bounds_and_rounding(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The value of a manager is clamped to 0..max_opening_degree and rounded to an integer"""
    events = register_plugin(hass, Fixed, "fixed")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    under._max_opening_degree = 80

    for proposed, expected in [(150, 80), (-5, 0), (40.6, 41), (79.4, 79), (80, 80)]:
        Fixed.value = proposed
        await send(hass, under, events, 50)
        assert written(events, OPENING) == [expected], proposed
        assert written(events, CLOSING) == [100 - expected], proposed
        assert isinstance(written(events, OPENING)[0], int)
        assert under.last_sent_opening_value == expected
    Fixed.value = 55


async def test_invalid_value_is_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A value which is not a finite number is ignored, the previous value is kept"""
    events = register_plugin(hass, Fixed, "fixed")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    for invalid in (float("nan"), float("inf"), "30", True):
        Fixed.value = invalid
        caplog.clear()
        await send(hass, under, events, 50)
        request = requests(events)[0]
        assert written(events, OPENING) == [request.requested_opening_degree], invalid
        assert "invalid opening degree" in caplog.text
    Fixed.value = 55


async def test_decision_which_is_not_a_decision_is_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """Something else than a ValveWriteDecision is logged and ignored"""
    events = register_plugin(hass, NotADecision, "bad")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    assert written(events, OPENING) == [requests(events)[0].requested_opening_degree]
    assert "invalid valve write decision" in caplog.text


async def test_exception_is_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A failing manager is logged: the next one still receives the value, and the core writes it"""
    events = register_plugin(hass, Raising, "a_raising")
    register_plugin(hass, PlusTen, "b_good", events=events)
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    good_request = [e[2] for e in events if e[0] == "before_valve" and e[1] == "b_good"][0]
    assert good_request.opening_degree == good_request.requested_opening_degree
    assert written(events, OPENING) == [min(100, good_request.requested_opening_degree + 10)]
    assert "boom write" in caplog.text


async def test_timeout_is_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A manager slower than the timeout is cut, logged, and the core writes its value"""
    events = register_plugin(hass, Hanging, "hanging")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    with patch("custom_components.versatile_thermostat.base_thermostat.UNDERLYING_HOOK_TIMEOUT_SEC", 0.05):
        await send(hass, under, events, 50)

    assert len(written(events, OPENING)) == 1
    assert "timed out in async_before_valve_write" in caplog.text
    assert commands(events, "after_valve")[0].written_by_plugin is False


async def test_unconfigured_and_faulty_is_configured_are_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A manager which is not configured, or whose is_configured raises, is not called"""
    events = register_plugin(hass, PlusTen, "a_unconfigured", configured=False)
    register_plugin(hass, FaultyPlusTen, "b_faulty", events=events)
    register_plugin(hass, Nothing, "c_good", events=events)
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    assert [e[1] for e in events if e[0] == "before_valve"] == ["c_good"]
    assert written(events, OPENING) == [requests(events)[0].requested_opening_degree]
    assert "Error while reading is_configured" in caplog.text


async def test_handled_writes_nothing_and_updates_last_sent(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """handled: the core writes neither the opening nor the closing degree but remembers the value, with the time of the command"""
    # the managers are called in the alphabetical order of their names
    events = register_plugin(hass, FinalHandler, "a_handler")
    register_plugin(hass, PlusTen, "b_after", events=events)
    vtherm, _, opening, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    state_before = hass.states.get(OPENING).state
    now = vtherm.now

    await send(hass, under, events, 50)

    assert written(events, OPENING) == []
    assert written(events, CLOSING) == []
    assert hass.states.get(OPENING).state == state_before
    # the chain stops at the handler
    assert [e[1] for e in events if e[0] == "before_valve"] == ["a_handler"]
    assert under.last_sent_opening_value == 77
    assert under._last_command_sent_datetime == now
    command = commands(events, "after_valve")[0]
    assert command.opening_degree == 77
    assert command.written_by_plugin is True
    assert command.requested_opening_degree == requests(events)[0].requested_opening_degree


async def test_handled_without_value_keeps_the_proposed_value(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """handled without opening_degree: the valve ends at the proposed value, here the one left by the previous manager"""
    events = register_plugin(hass, PlusTen, "a_first")
    register_plugin(hass, Handler, "b_handler", events=events)
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    core_value = requests(events)[0].requested_opening_degree
    assert written(events, OPENING) == []
    assert under.last_sent_opening_value == min(100, core_value + 10)
    command = commands(events, "after_valve")[0]
    assert command.opening_degree == min(100, core_value + 10)
    assert command.written_by_plugin is True


async def test_repair_waits_the_default_delay_after_a_handled_write(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without settle_sec the repair waits the resend delay (2 s) after the decision"""
    events = register_plugin(hass, FinalHandler, "handler")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    await send(hass, under, events, 50)
    now = vtherm.now
    # the valve is still where it was: it drifted from the last sent value
    assert under.current_valve_opening != under.last_sent_opening_value

    vtherm._set_now(now + timedelta(seconds=1))
    assert await under.check_and_repair() is False
    vtherm._set_now(now + timedelta(seconds=2, milliseconds=100))
    events.clear()
    assert await under.check_and_repair() is True
    # the repair goes through the hook again
    assert requests(events)[0].cause == ValveCommandCause.REPAIR


async def test_repair_waits_settle_sec(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A long sequence announced by the plugin delays the repair"""
    events = register_plugin(hass, SlowHandler, "handler")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    await send(hass, under, events, 50)
    now = vtherm.now

    vtherm._set_now(now + timedelta(seconds=10))
    assert await under.check_and_repair() is False
    vtherm._set_now(now + timedelta(seconds=29))
    assert await under.check_and_repair() is False
    vtherm._set_now(now + timedelta(seconds=31))
    assert await under.check_and_repair() is True


async def test_settle_sec_also_applies_when_the_core_writes(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The settle time is kept when the manager changes the value but the core writes it"""

    class SettlingPlusTen(PlusTen):
        """Changes the value and announces a settle time"""

        def decision(self, request):
            return ValveWriteDecision(opening_degree=request.opening_degree + 10, settle_sec=20)

    events = register_plugin(hass, SettlingPlusTen, "settling")
    vtherm, _, opening, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    await send(hass, under, events, 50)
    now = vtherm.now
    assert under._settle_sec == 20
    # the valve drifts
    opening.set_native_value(0)
    await hass.async_block_till_done()

    vtherm._set_now(now + timedelta(seconds=10))
    assert await under.check_and_repair() is False
    vtherm._set_now(now + timedelta(seconds=21))
    assert await under.check_and_repair() is True


async def test_settle_sec_is_reset_by_the_next_command(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The settle time of a command does not apply to the next one"""

    class OnceSlow(Handler):
        """Announces a long sequence only the first time"""

        calls = 0

        def decision(self, request):
            OnceSlow.calls += 1
            return ValveWriteDecision(handled=True, settle_sec=30.0 if OnceSlow.calls == 1 else None)

    events = register_plugin(hass, OnceSlow, "once")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    OnceSlow.calls = 0
    await send(hass, under, events, 50)
    assert under._settle_sec == 30.0
    await send(hass, under, events, 60)
    assert under._settle_sec is None


async def test_invalid_settle_sec_is_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A negative or not finite settle_sec is ignored"""

    class BadSettle(PlusTen):
        """Invalid settle_sec"""

        def decision(self, request):
            return ValveWriteDecision(settle_sec=-3.0)

    events = register_plugin(hass, BadSettle, "bad")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    assert under._settle_sec is None
    assert "invalid settle_sec" in caplog.text


async def test_after_valve_command_fields_when_the_core_writes(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """requested_opening_degree holds the value of the core when a manager changed it, written_by_plugin is False"""
    events = register_plugin(hass, PlusTen, "plus")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    # 100 %: the core value is already the maximum and the manager value is clamped back to it
    await send(hass, under, events, 100)
    command = commands(events, "after_valve")[0]
    assert command.opening_degree == 100
    assert command.requested_opening_degree is None
    assert command.written_by_plugin is False

    await send(hass, under, events, 30)
    command = commands(events, "after_valve")[0]
    core_value = requests(events)[0].requested_opening_degree
    assert command.opening_degree == core_value + 10
    assert command.closing_degree == 100 - (core_value + 10)
    assert command.requested_opening_degree == core_value
    assert command.written_by_plugin is False
    assert command.percent_open == 30


async def test_all_causes_call_the_hook(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Startup, repair, regulation and inhibition stop all go through the hook"""
    events = register_plugin(hass, Nothing, "nothing")
    vtherm, _, opening, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    # startup: the valve is closed whereas it should be open
    opening.set_native_value(0)
    await hass.async_block_till_done()
    events.clear()
    await under.check_initial_state()
    await hass.async_block_till_done()
    assert [r.cause for r in requests(events)] == [ValveCommandCause.STARTUP]

    # regulation cycle
    events.clear()
    await vtherm.cycle_scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True)
    await hass.async_block_till_done()
    assert [r.cause for r in requests(events)] == [ValveCommandCause.REGULATION]

    # inhibition stop
    events.clear()
    await inhibit(hass, vtherm, True)
    assert ValveCommandCause.TURN_OFF in [r.cause for r in requests(events)]
    await uninhibit(hass, vtherm)


async def test_not_called_when_the_gate_blocks_the_write(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The inhibition gate blocks everything: no hook, no write"""
    events = register_plugin(hass, Handler, "handler")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    await inhibit(hass, vtherm, True)

    await send(hass, under, events, 70)

    assert events == []
    assert under._settle_sec is None
    await uninhibit(hass, vtherm)


async def test_not_called_for_seed_nor_recalibration(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The seed of unknown degrees and the recalibration write the numbers without the valve write hook"""
    events = register_plugin(hass, PlusTen, "plus")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    events.clear()

    with record_services(events):
        hass.states.async_set(CLOSING, STATE_UNKNOWN, {"min": 0, "max": 100})
        await hass.async_block_till_done()
        await under._seed_unknown_degrees_once()
        await hass.async_block_till_done()
        assert any(e[0] == "service" and e[3] == CLOSING for e in events)

        events.append(("mark",))
        await under.send_value_to_number(OPENING, 100)
        await under.send_value_to_number(CLOSING, 0)
        await hass.async_block_till_done()
        assert any(e[0] == "service" and e[3] == OPENING for e in events)

    assert requests(events) == []
    assert commands(events, "after_valve") == []


async def test_inhibition_resync_compares_with_the_final_value(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """After an inhibition the valve is expected at the final value of the plugin, not at the one of the core"""
    events = register_plugin(hass, PlusTen, "plus")
    vtherm, _, opening, closing = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    under._percent_open = 30
    await send(hass, under, events, 30)
    final = under.last_sent_opening_value
    core_value = requests(events)[0].requested_opening_degree
    assert final == core_value + 10
    assert float(hass.states.get(OPENING).state) == final

    # the valve is where the plugin left it: the percent is kept
    await under.async_inhibition_resync()
    assert under._percent_open == 30

    # the valve is where the core would have put it: it drifted, a resend is forced
    opening.set_native_value(core_value)
    await hass.async_block_till_done()
    await under.async_inhibition_resync()
    assert under._percent_open is None


async def test_inhibition_resync_without_plugin_is_unchanged(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without a plugin the valve is expected at the degrees of the core"""
    events: list = []
    vtherm, _, opening, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]
    under._percent_open = 30
    await send(hass, under, events, 30)

    await under.async_inhibition_resync()
    assert under._percent_open == 30

    opening.set_native_value(5)
    await hass.async_block_till_done()
    await under.async_inhibition_resync()
    assert under._percent_open is None


async def test_manager_without_the_hook_is_not_called(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager which does not implement the valve write hook is not concerned"""
    events = register_plugin(hass, FakePluginManager, "plain")
    vtherm, _, _, _ = await start(hass, fake_temp_sensor, events)
    under = vtherm._underlyings_valve_regulation[0]

    await send(hass, under, events, 50)

    assert len(written(events, OPENING)) == 1
    assert requests(events) == []
