# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name, wildcard-import, unused-wildcard-import
"""Test the VTherm inhibition core (issue #2087, design v2.0).

The plugin side is replaced by direct calls to the VTherm API facade
(``set_inhibition`` / ``unset_inhibition``). The tests count the real service
calls that reach the underlying entities, not only the final state.
"""

import asyncio
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant, ServiceRegistry, State
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.components.climate import ATTR_PRESET_MODE
from homeassistant.exceptions import ServiceNotFound
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_call_later
from pytest_homeassistant_custom_component.common import async_fire_time_changed, mock_restore_cache

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.inhibition_manager import (
    ATTR_INHIBITION,
    CommandGate,
    InhibitionManager,
    InhibitionNotStartedError,
    ERROR_EXIT_RECONCILE_FAILED,
)
from custom_components.versatile_thermostat.state_manager import StateManager
from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch
from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI

from .commons import *
from .const import *

logging.getLogger().setLevel(logging.DEBUG)

SWITCH = "switch.mock_switch"
CLIMATE = "climate.mock_climate"
VALVE = "number.mock_valve"
OPENING = "number.mock_opening_degree"
CLOSING = "number.mock_closing_degree"

PRESETS = {"frost": 7, "eco": 17, "comfort": 19, "boost": 21}


##
## Helpers
##
class ServiceSpy:
    """Record the service calls targeting the given entities. Optionally pause a call."""

    def __init__(self, entity_ids):
        self.entity_ids = set(entity_ids)
        self.calls: list[tuple[str, str, str, dict]] = []
        self.pause_on: tuple[str, str] | None = None
        self.paused = asyncio.Event()
        self.release = asyncio.Event()
        # coroutine function run in the paused call chain (same task and context)
        self.on_pause = None

    def _targets(self, service_data, target) -> list[str]:
        ids = []
        for source in (service_data or {}, target or {}):
            value = source.get(ATTR_ENTITY_ID)
            if isinstance(value, str):
                ids.append(value)
            elif isinstance(value, (list, tuple)):
                ids.extend(value)
        return [entity_id for entity_id in ids if entity_id in self.entity_ids]

    def services(self, entity_id: str | None = None) -> list[tuple[str, str]]:
        """(domain, service) of the recorded calls"""
        return [(domain, service) for domain, service, eid, _ in self.calls if entity_id is None or eid == entity_id]

    def reset(self):
        """Forget the recorded calls"""
        self.calls.clear()


@contextmanager
def spy_services(entity_ids):
    """Wrap the real ServiceRegistry.async_call: the mock entities still change their states"""
    spy = ServiceSpy(entity_ids)
    original = ServiceRegistry.async_call

    async def wrapper(registry, domain, service, service_data=None, blocking=False, context=None, target=None, return_response=False):
        for entity_id in spy._targets(service_data, target):
            spy.calls.append((domain, service, entity_id, dict(service_data or {})))
            if spy.pause_on == (domain, service):
                spy.pause_on = None
                if spy.on_pause:
                    await spy.on_pause()
                spy.paused.set()
                await spy.release.wait()
        return await original(registry, domain, service, service_data, blocking, context, target, return_response)

    with patch.object(ServiceRegistry, "async_call", wrapper):
        yield spy


async def _until(condition):
    """Wait until the condition is true (without waiting for every pending task)"""
    while not condition():
        await asyncio.sleep(0.01)


def api(hass) -> VersatileThermostatAPI:
    """The real VTherm API (facade from vtherm_api >= 0.6.1)"""
    return VersatileThermostatAPI.get_vtherm_api(hass)


async def inhibit(hass, vtherm: BaseThermostat, stop: bool = True):
    """Set the inhibition through the API facade"""
    await api(hass).set_inhibition(vtherm.entity_id, stop)
    await hass.async_block_till_done()


async def uninhibit(hass, vtherm: BaseThermostat):
    """Unset the inhibition through the API facade"""
    await api(hass).unset_inhibition(vtherm.entity_id)
    await hass.async_block_till_done()


async def advance(hass, vtherm: BaseThermostat, minutes: float, steps: int = 1):
    """Move the time forward: fire the HA timers (keep-alive, cycles, delayed commands)
    and run the periodic control cycle"""
    for _ in range(steps):
        now = vtherm.now + timedelta(minutes=minutes)
        vtherm._set_now(now)
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minutes))
        await hass.async_block_till_done()
        await vtherm.async_control_heating(timestamp=now)
        await hass.async_block_till_done()


def snapshot(hass, vtherm: BaseThermostat) -> dict | None:
    """The published inhibition snapshot"""
    return hass.states.get(vtherm.entity_id).attributes["specific_states"].get(ATTR_INHIBITION)


def assert_inhibited(vtherm: BaseThermostat, requested=VThermHvacMode_HEAT):
    """The effective state is OFF with the dedicated reason, the intent is kept"""
    assert vtherm.is_inhibited is True
    assert vtherm.inhibition_manager.command_gate == CommandGate.CLOSED
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_OFF
    assert vtherm.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
    assert vtherm.hvac_mode_reason == HVAC_OFF_REASON_INHIBITION
    assert vtherm.requested_state.hvac_mode == requested


def switch_entry(unique_id="switchInhib", **extra) -> MockConfigEntry:
    """over_switch TPI with keep-alive and the repair feature"""
    data = {
        CONF_NAME: "TheOverSwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        CONF_UNDERLYING_LIST: [SWITCH],
        CONF_HEATER_KEEP_ALIVE: 10,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_MINIMAL_ACTIVATION_DELAY: 0,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_REPAIR_INCORRECT_STATE: True,
    }
    data |= MOCK_DEFAULT_FEATURE_CONFIG | MOCK_DEFAULT_CENTRAL_CONFIG | MOCK_ADVANCED_CONFIG
    data |= extra
    return MockConfigEntry(domain=DOMAIN, title="TheOverSwitchMockName", unique_id=unique_id, data=data)


async def heating_switch_vtherm(hass, fake_temp_sensor, entry=None) -> BaseThermostat:
    """An over_switch VTherm heating at 100% (room 15, comfort 19)"""
    vtherm = await create_thermostat(hass, entry or switch_entry(), "climate.theoverswitchmockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == STATE_ON
    return vtherm


def climate_entry(**extra) -> MockConfigEntry:
    """over_climate with auto-regulation and auto fan"""
    data = {
        CONF_NAME: "TheOverClimateMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        CONF_UNDERLYING_LIST: [CLIMATE],
        CONF_AC_MODE: False,
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
        CONF_AUTO_REGULATION_DTEMP: 0.1,
        CONF_AUTO_REGULATION_PERIOD_MIN: 0,
        CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
        CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        CONF_REPAIR_INCORRECT_STATE: True,
    }
    data |= MOCK_DEFAULT_FEATURE_CONFIG | MOCK_DEFAULT_CENTRAL_CONFIG | MOCK_ADVANCED_CONFIG
    data |= extra
    return MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="climateInhib", data=data)


async def heating_climate_vtherm(hass, fake_temp_sensor) -> tuple[BaseThermostat, MockClimate]:
    """An over_climate VTherm heating with a fan capable underlying"""
    fake_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, fan_modes=["low", "medium", "high", "auto"])
    vtherm = await create_thermostat(hass, climate_entry(), "climate.theoverclimatemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    assert hass.states.get(CLIMATE).state == HVACMode.HEAT
    return vtherm, fake_climate


def valve_entry(**extra) -> MockConfigEntry:
    """over_valve TPI"""
    data = {
        CONF_NAME: "TheOverValveMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_UNDERLYING_LIST: [VALVE],
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_AUTO_REGULATION_DTEMP: 0,
        CONF_AUTO_REGULATION_PERIOD_MIN: 0,
        CONF_REPAIR_INCORRECT_STATE: True,
    }
    data |= MOCK_DEFAULT_FEATURE_CONFIG | MOCK_DEFAULT_CENTRAL_CONFIG | MOCK_ADVANCED_CONFIG
    data |= extra
    return MockConfigEntry(domain=DOMAIN, title="TheOverValveMockName", unique_id="valveInhib", data=data)


def climate_valve_entry(**extra) -> MockConfigEntry:
    """over_climate with valve regulation (opening and closing degrees)"""
    data = {
        CONF_NAME: "TheOverClimateValveMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        CONF_STEP_TEMPERATURE: 0.1,
        CONF_UNDERLYING_LIST: [CLIMATE],
        CONF_AC_MODE: False,
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
        CONF_AUTO_REGULATION_DTEMP: 0,
        CONF_AUTO_REGULATION_PERIOD_MIN: 0,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.1,
        CONF_OPENING_DEGREE_LIST: [OPENING],
        CONF_CLOSING_DEGREE_LIST: [CLOSING],
        CONF_REPAIR_INCORRECT_STATE: True,
    }
    data |= MOCK_DEFAULT_FEATURE_CONFIG | MOCK_DEFAULT_CENTRAL_CONFIG | MOCK_ADVANCED_CONFIG
    data |= extra
    return MockConfigEntry(domain=DOMAIN, title="TheOverClimateValveMockName", unique_id="climateValveInhib", data=data)


async def heating_climate_valve_vtherm(hass, fake_temp_sensor):
    """An over_climate_valve VTherm heating"""
    fake_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})
    opening = await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=0, min=0, max=100)
    closing = await create_and_register_mock_number(hass, "mock_closing_degree", "MockClosingDegree", value=100, min=0, max=100)
    vtherm = await create_thermostat(hass, climate_valve_entry(), "climate.theoverclimatevalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    assert hass.states.get(CLIMATE).state == HVACMode.HEAT
    assert float(hass.states.get(OPENING).state) > 0
    return vtherm, fake_climate, opening, closing


##
## No plugin: historic behavior
##
async def test_no_inhibition_keeps_historic_behavior(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-011: without any set_inhibition call the gate is open and nothing is published"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    manager = vtherm.inhibition_manager
    assert vtherm.is_inhibited is False
    assert manager.command_gate == CommandGate.OPEN
    assert manager.blocks_command(vtherm.underlying_entity(0), "switch", "turn_on") is False
    assert snapshot(hass, vtherm) is None

    # an unset without inhibition is a no-op
    with spy_services([SWITCH]) as spy:
        await uninhibit(hass, vtherm)
    assert spy.calls == []
    assert snapshot(hass, vtherm) is None


async def test_api_facade_contract(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """The facade targets the VTherm by entity_id and validates its arguments"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with pytest.raises(LookupError):
        await api(hass).set_inhibition("climate.does_not_exist", True)
    with pytest.raises(TypeError):
        await api(hass).set_inhibition(vtherm.entity_id, "yes")
    assert vtherm.is_inhibited is False


##
## over_switch
##
async def test_switch_set_true_single_stop_and_hold(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-001, AC-003, AC-004: one entry stop, then nothing during several cycles
    (TPI, keep-alive, repair), a direct command is not overwritten"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    under: UnderlyingSwitch = vtherm.underlying_entity(0)

    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        assert spy.services() == [("switch", "turn_off")]
        assert hass.states.get(SWITCH).state == STATE_OFF
        assert_inhibited(vtherm)
        assert vtherm.preset_mode == VThermPreset.COMFORT
        assert vtherm.target_temperature == 19
        assert snapshot(hass, vtherm) == {
            "schema_version": 1,
            "inhibited": True,
            "entry_stop_requested": True,
            "entry_stop_completed": True,
            "command_gate": "CLOSED",
            "last_transition_at": snapshot(hass, vtherm)["last_transition_at"],
            "last_error_code": None,
        }

        # repeated set: no second stop (idempotent)
        await inhibit(hass, vtherm, True)
        await inhibit(hass, vtherm, False)
        assert spy.services() == [("switch", "turn_off")]
        spy.reset()

        # another integration turns the switch on
        await fake_underlying_switch.async_turn_on()
        await hass.async_block_till_done()

        # several cycles: TPI, keep-alive (10s), repair, cycle timers
        await advance(hass, vtherm, 1, steps=12)
        await vtherm.async_control_heating(force=True)
        await under.check_and_repair()
        await hass.async_block_till_done()

        assert spy.calls == []
        assert hass.states.get(SWITCH).state == STATE_ON
        assert_inhibited(vtherm)


async def test_switch_set_false_sends_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-002: same withdrawal and gate, but no stop"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy, patch("homeassistant.helpers.restore_state.RestoreStateData.async_dump_states") as dump:
        await inhibit(hass, vtherm, False)
        # the transition is saved now, not at the next 15 min dump
        assert dump.call_count >= 1
        assert_inhibited(vtherm)
        await advance(hass, vtherm, 1, steps=6)
        assert spy.calls == []
    assert hass.states.get(SWITCH).state == STATE_ON
    assert snapshot(hass, vtherm)["entry_stop_requested"] is False
    assert snapshot(hass, vtherm)["entry_stop_completed"] is False


async def test_switch_intent_retained_and_exit_heat(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-005, AC-006: intent changes are retained without command, the exit applies
    the current intent once, then the gate opens and the keep-alive works again"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.reset()

        await vtherm.async_set_preset_mode(VThermPreset.BOOST)
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await vtherm.async_set_temperature(temperature=22)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []
        assert vtherm.requested_state.target_temperature == 22
        assert vtherm.requested_state.preset == VThermPreset.NONE
        assert_inhibited(vtherm)
        assert hass.states.get(SWITCH).state == STATE_OFF

        await uninhibit(hass, vtherm)
        assert spy.services() == [("switch", "turn_on")]
        assert hass.states.get(SWITCH).state == STATE_ON
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert vtherm.hvac_off_reason is None
        assert vtherm.target_temperature == 22
        assert snapshot(hass, vtherm)["command_gate"] == "OPEN"
        assert snapshot(hass, vtherm)["inhibited"] is False

        # repeated unset: no second reconciliation
        spy.reset()
        await uninhibit(hass, vtherm)
        assert spy.calls == []

        # normal operation resumed: the keep-alive sends again
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
        await hass.async_block_till_done()
        assert ("switch", "turn_on") in spy.services()


async def test_switch_exit_off_turns_off_manual_device(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-008: OFF requested during inhibition, the device was turned on by hand:
    the exit turns it off (OFF -> OFF still walks the underlyings) and never on"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, False)
        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        assert_inhibited(vtherm, requested=VThermHvacMode_OFF)
        assert spy.calls == []
        assert hass.states.get(SWITCH).state == STATE_ON

        await uninhibit(hass, vtherm)
        assert spy.services() == [("switch", "turn_off")]
        assert hass.states.get(SWITCH).state == STATE_OFF
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_MANUAL

        spy.reset()
        await advance(hass, vtherm, 1, steps=6)
        assert ("switch", "turn_on") not in spy.services()


async def test_switch_exit_heat_with_device_turned_on_by_hand(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """Exit with HEAT while the switch was turned on by hand: the switch caches follow the
    real state, so the repair does not turn it off and the keep-alive works again"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        await fake_underlying_switch.async_turn_on()
        # a partial power: the first tick keeps the switch on without sending turn_on
        await send_temperature_change_event(vtherm, 18, vtherm.now)
        await hass.async_block_till_done()
        spy.reset()

        await uninhibit(hass, vtherm)
        assert 0 < vtherm.on_percent < 1
        assert spy.calls == []
        await advance(hass, vtherm, 0.5)
        assert ("switch", "turn_off") not in spy.services()
        assert hass.states.get(SWITCH).state == STATE_ON

        spy.reset()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
        await hass.async_block_till_done()
        assert spy.services() == [("switch", "turn_on")]


async def test_switch_command_during_exit_reconciliation_is_blocked(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-007, AC-012: while EXIT_RECONCILING, only the reconciliation passes. A keep-alive,
    a periodic cycle or a timer created before the window are blocked, a concurrent
    unset joins and the gate opens after the reconciliation only"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    under: UnderlyingSwitch = vtherm.underlying_entity(0)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.reset()

        spawned = []

        async def spawn_from_the_transaction():
            # a task and a timer created inside the reconciliation inherit its ContextVar
            spawned.append(hass.async_create_task(under.turn_off()))

            async def later(_):
                spawned.append("timer")
                await under.turn_off()

            async_call_later(hass, 0.01, later)

        spy.on_pause = spawn_from_the_transaction
        spy.pause_on = ("switch", "turn_on")
        exit1 = hass.async_create_task(api(hass).unset_inhibition(vtherm.entity_id))
        await asyncio.wait_for(spy.paused.wait(), 5)
        assert vtherm.inhibition_manager.command_gate == CommandGate.EXIT_RECONCILING
        assert vtherm.is_inhibited is False
        assert spy.services() == [("switch", "turn_on")]

        # ordinary commands from other call chains
        await under._keep_alive_callback()
        await under.turn_on()
        await under.turn_off()
        await under.check_and_repair()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
        await asyncio.sleep(0.05)
        await spawned[0]
        await asyncio.wait_for(_until(lambda: "timer" in spawned), 5)
        await asyncio.sleep(0.05)
        assert spy.services() == [("switch", "turn_on")]

        # a concurrent unset joins the running exit
        exit2 = hass.async_create_task(api(hass).unset_inhibition(vtherm.entity_id))
        await asyncio.sleep(0)
        assert not exit1.done() and not exit2.done()

        spy.release.set()
        await asyncio.wait_for(asyncio.gather(exit1, exit2), 5)
        await hass.async_block_till_done()
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        # the commands dropped during the pause make the reconciliation walk again (turn_on only)
        assert set(spy.services()) == {("switch", "turn_on")}


async def test_switch_exit_failure_returns_to_inhibition(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """An exception in the core exit path: back to inhibited + CLOSED, unset raises, a retry works"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    await inhibit(hass, vtherm, True)
    with spy_services([SWITCH]) as spy:
        with patch.object(UnderlyingSwitch, "async_inhibition_resync", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                await api(hass).unset_inhibition(vtherm.entity_id)
        await hass.async_block_till_done()
        assert_inhibited(vtherm)
        assert snapshot(hass, vtherm)["last_error_code"] == ERROR_EXIT_RECONCILE_FAILED
        assert snapshot(hass, vtherm)["command_gate"] == "CLOSED"
        # the entry stop is sent again by the rollback (stop_underlyings was true)
        assert spy.services() == [("switch", "turn_off")]
        spy.reset()

        await uninhibit(hass, vtherm)
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert spy.services() == [("switch", "turn_on")]
        assert snapshot(hass, vtherm)["last_error_code"] is None


async def test_switch_unavailable_device_does_not_fail_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A service error of one device is logged as today, it is not an exit failure"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    await inhibit(hass, vtherm, True)
    with patch.object(ServiceRegistry, "async_call", side_effect=ServiceNotFound("switch", "turn_on")):
        await uninhibit(hass, vtherm)
    assert vtherm.is_inhibited is False
    assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN


async def test_switch_window_eco_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """Exit with the window open and the eco window action: the requested mode applies
    (not a stale OFF / hvac_off_inhibition) with the eco temperature"""
    entry = switch_entry(
        unique_id="switchInhibWindow",
        **{
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,
            CONF_WINDOW_ACTION: CONF_WINDOW_ECO_TEMP,
        },
    )
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor, entry)
    await inhibit(hass, vtherm, True)

    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_function = await send_window_change_event(vtherm, True, False, datetime.now(), sleep=False)
        await try_function(None)
    await wait_for_local_condition(lambda: vtherm.window_state == STATE_ON)
    assert_inhibited(vtherm)

    await uninhibit(hass, vtherm)
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert vtherm.hvac_off_reason is None
    assert vtherm.hvac_mode_reason == HVAC_OFF_REASON_WINDOW_DETECTION
    assert vtherm.target_temperature == 17


##
## Restart
##
def inhibited_old_state(gate: str = "CLOSED", inhibited: bool = True, completed: bool = True, requested: bool = True) -> State:
    """The previous HA state of an inhibited over_switch VTherm heating in comfort"""
    return State(
        "climate.theoverswitchmockname",
        HVACMode.OFF,
        {
            ATTR_TEMPERATURE: 19,
            ATTR_PRESET_MODE: VThermPreset.COMFORT,
            HVAC_OFF_REASON_NAME: HVAC_OFF_REASON_INHIBITION,
            "requested_state": {"hvac_mode": "heat", "target_temperature": 19, "preset": "comfort"},
            "current_state": {"hvac_mode": "off", "target_temperature": 19, "preset": "comfort"},
            "specific_states": {
                HVAC_MODE_REASON_NAME: HVAC_OFF_REASON_INHIBITION,
                ATTR_INHIBITION: {
                    "schema_version": 1,
                    "inhibited": inhibited,
                    "entry_stop_requested": requested,
                    "entry_stop_completed": completed,
                    "command_gate": gate,
                    "last_transition_at": None,
                    "last_error_code": None,
                },
            },
        },
    )


async def start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, old_state: State, spy) -> BaseThermostat:
    """Start an over_switch VTherm with a previous state while the switch is ON"""
    mock_restore_cache(hass, [old_state])
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    vtherm = await create_thermostat(hass, switch_entry(), "climate.theoverswitchmockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    await hass.async_block_till_done()
    return vtherm


async def test_restart_after_entry_stop(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-010: restored closed before the first command, no second stop, no resumption"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(), spy)
        assert vtherm.is_ready
        assert_inhibited(vtherm)
        await inhibit(hass, vtherm, True)  # the plugin restarts and sets again
        await advance(hass, vtherm, 1, steps=6)
        assert spy.calls == []
        assert hass.states.get(SWITCH).state == STATE_ON
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True

        await uninhibit(hass, vtherm)
        assert spy.services() == [("switch", "turn_on")]
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN


async def test_restart_during_exit_reconciliation_is_restored_closed(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A restart during EXIT_RECONCILING is restored like a failed exit: inhibited, CLOSED,
    and the requested entry stop sent again once (the partial reconciliation may have
    restarted the switch)"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(gate="EXIT_RECONCILING", inhibited=False), spy)
        assert_inhibited(vtherm)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.services() == [("switch", "turn_off")]
        assert snapshot(hass, vtherm)["command_gate"] == "CLOSED"
        assert snapshot(hass, vtherm)["inhibited"] is True
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True


async def test_restart_during_exit_without_requested_stop_sends_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """Interrupted exit of an inhibition set with stop_underlyings=false: nothing is sent"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(
            hass, fake_temp_sensor, inhibited_old_state(gate="EXIT_RECONCILING", inhibited=False, completed=False, requested=False), spy
        )
        await advance(hass, vtherm, 1, steps=3)
        assert_inhibited(vtherm)
        assert spy.calls == []


async def test_second_startup_does_not_restore_again(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A config entry update runs async_startup twice (reload, then init_vtherm_links): the
    snapshot is restored once, a completed entry stop never goes back to pending"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(completed=False), spy)
        await advance(hass, vtherm, 1)
        assert spy.services() == [("switch", "turn_off")]
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True

        await fake_underlying_switch.async_turn_on()
        await hass.async_block_till_done()
        spy.reset()
        await api(hass).init_vtherm_links(vtherm.unique_id)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []
        assert_inhibited(vtherm)
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True
    assert hass.states.get(SWITCH).state == STATE_ON


async def test_restart_with_pending_entry_stop(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A crash between the set and the entry stop: the stop is sent once when ready"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(completed=False), spy)
        assert_inhibited(vtherm)
        assert spy.services() == [("switch", "turn_off")]
        await advance(hass, vtherm, 1, steps=3)
        assert spy.services() == [("switch", "turn_off")]
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True


async def test_restart_without_snapshot_is_historic(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """No snapshot: historic behavior"""
    old_state = inhibited_old_state()
    del old_state.attributes["specific_states"][ATTR_INHIBITION]
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, State(old_state.entity_id, old_state.state, old_state.attributes), spy)
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert snapshot(hass, vtherm) is None
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT


async def test_set_and_unset_before_ready_are_deferred(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Not ready: the entry stop and the exit reconciliation are completed when the VTherm becomes ready"""
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        # restored inhibited, the switch does not exist yet: the VTherm is not ready
        mock_restore_cache(hass, [inhibited_old_state()])
        vtherm = await create_thermostat(hass, switch_entry(), "climate.theoverswitchmockname", temps=PRESETS)
        vtherm._set_now(datetime.now(tz=get_tz(hass)))
        assert vtherm.is_ready is False
        assert vtherm.is_inhibited is True

        await uninhibit(hass, vtherm)
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.EXIT_RECONCILING
        assert spy.calls == []

        # the switch appears (ON, turned on by someone else): the VTherm becomes ready
        switch = MockSwitch(hass, "mock_switch", "theMockedSwitch")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)
        await hass.async_block_till_done()
        assert vtherm.is_ready
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert ("switch", "turn_on") in spy.services()


##
## over_climate
##
async def test_climate_set_true_hold_and_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """over_climate with auto-regulation, auto fan and repair: one set_hvac_mode OFF,
    nothing during the cycles, user fan/swing settings dropped with a warning,
    an external restart is not overwritten, the exit applies the intent"""
    vtherm, fake_climate = await heating_climate_vtherm(hass, fake_temp_sensor)

    with spy_services([CLIMATE]) as spy:
        await inhibit(hass, vtherm, True)
        assert spy.services() == [("climate", "set_hvac_mode")]
        assert spy.calls[0][3]["hvac_mode"] == HVACMode.OFF
        assert hass.states.get(CLIMATE).state == HVACMode.OFF
        assert_inhibited(vtherm)
        spy.reset()

        # another integration restarts the climate with its own fan and setpoint
        fake_climate.set_fan_mode("high")
        fake_climate.set_temperature(temperature=25)
        fake_climate.set_hvac_mode(HVACMode.HEAT)
        await hass.async_block_till_done()

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            await vtherm.async_set_fan_mode("low")
            await advance(hass, vtherm, 1, steps=6)
            await vtherm.async_set_temperature(temperature=21)
        assert spy.calls == []
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "dropped" in r.getMessage()]
        assert len(warnings) == 1
        assert hass.states.get(CLIMATE).state == HVACMode.HEAT
        assert hass.states.get(CLIMATE).attributes["temperature"] == 25
        assert hass.states.get(CLIMATE).attributes["fan_mode"] == "high"
        assert_inhibited(vtherm)

        await uninhibit(hass, vtherm)
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
        # the climate is already heating: only the regulated setpoint is sent
        assert ("climate", "set_hvac_mode") not in spy.services()
        assert ("climate", "set_temperature") in spy.services()
        assert hass.states.get(CLIMATE).attributes["temperature"] != 25


async def test_climate_set_false_and_exit_off(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """set(false) sends nothing; an OFF requested during the inhibition turns off the
    climate left heating at the exit, and nothing reactivates it"""
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    with spy_services([CLIMATE]) as spy:
        await inhibit(hass, vtherm, False)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []
        assert hass.states.get(CLIMATE).state == HVACMode.HEAT

        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        assert spy.calls == []

        await uninhibit(hass, vtherm)
        assert spy.services() == [("climate", "set_hvac_mode")]
        assert hass.states.get(CLIMATE).state == HVACMode.OFF
        spy.reset()
        await advance(hass, vtherm, 1, steps=3)
        assert ("climate", "set_temperature") not in spy.services()
        assert hass.states.get(CLIMATE).state == HVACMode.OFF


async def test_entry_stop_is_sent_even_if_reported_off(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """The entry stop does not rely on the reported state (a turn on may be in flight)"""
    vtherm, fake_climate = await heating_climate_vtherm(hass, fake_temp_sensor)
    fake_climate.set_hvac_mode(HVACMode.OFF)
    await hass.async_block_till_done()
    with spy_services([CLIMATE]) as spy:
        await inhibit(hass, vtherm, True)
        assert spy.services() == [("climate", "set_hvac_mode")]


async def test_valve_entry_stop_is_sent_even_if_reported_closed(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """over_valve: the entry stop closes the valve even if it reports closed"""
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    fake_underlying_valve.set_native_value(0)
    await hass.async_block_till_done()
    with spy_services([VALVE]) as spy:
        await inhibit(hass, vtherm, True)
        assert spy.services() == [("number", "set_value")]


async def test_climate_delayed_resend_timer_is_blocked(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A delayed set_temperature scheduled before the inhibition never passes the gate"""
    vtherm, _ = await heating_climate_vtherm(hass, fake_temp_sensor)
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)  # schedules the resend 2s later
    with spy_services([CLIMATE]) as spy:
        await inhibit(hass, vtherm, False)
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
        await hass.async_block_till_done()
        assert spy.calls == []


##
## over_valve
##
async def test_valve_set_true_hold_and_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """over_valve: one close, nothing while held, a manual opening is kept; the exit
    with an OFF intent closes it again (real state compared with the controlled value)"""
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    assert float(hass.states.get(VALVE).state) > 0

    with spy_services([VALVE]) as spy:
        await inhibit(hass, vtherm, True)
        assert spy.services() == [("number", "set_value")]
        assert float(hass.states.get(VALVE).state) == 0
        assert_inhibited(vtherm)
        spy.reset()

        fake_underlying_valve.set_native_value(50)
        await hass.async_block_till_done()
        await advance(hass, vtherm, 1, steps=6)
        assert spy.calls == []
        assert float(hass.states.get(VALVE).state) == 50

        await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
        assert spy.calls == []
        await uninhibit(hass, vtherm)
        # the reconciliation closes it (the TPI OFF path may resend the same 0 before the state update)
        assert spy.calls
        assert all(call[:2] == ("number", "set_value") and call[3]["value"] == 0 for call in spy.calls)
        assert float(hass.states.get(VALVE).state) == 0


async def test_valve_exit_heat_reopens(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """over_valve: exit with a HEAT intent reopens the valve closed by the entry stop"""
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    opened = float(hass.states.get(VALVE).state)
    assert opened > 0

    await inhibit(hass, vtherm, True)
    await advance(hass, vtherm, 1, steps=3)
    assert float(hass.states.get(VALVE).state) == 0
    await uninhibit(hass, vtherm)
    assert float(hass.states.get(VALVE).state) == opened


async def test_valve_exit_closes_valve_opened_by_hand(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve):
    """over_valve: exit with HEAT and no heating need while the valve was opened by hand:
    the opening cache follows the real state, so the reconciliation closes it"""
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)

    await inhibit(hass, vtherm, True)
    await send_temperature_change_event(vtherm, 25, vtherm.now)
    fake_underlying_valve.set_native_value(50)
    await hass.async_block_till_done()
    await advance(hass, vtherm, 1)
    assert float(hass.states.get(VALVE).state) == 50

    await uninhibit(hass, vtherm)
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert float(hass.states.get(VALVE).state) == 0


##
## over_climate with valve regulation
##
async def test_climate_valve_set_true_hold_seed_and_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """over_climate_valve: the entry stop sets the climate OFF and closes the regulation
    valve; nothing while held; the bootstrap seed runs again at the exit, then the
    regulation is reapplied"""
    vtherm, fake_climate, opening, closing = await heating_climate_valve_vtherm(hass, fake_temp_sensor)

    with spy_services([CLIMATE, OPENING, CLOSING]) as spy:
        await inhibit(hass, vtherm, True)
        assert sorted(spy.services()) == sorted([("climate", "set_hvac_mode"), ("number", "set_value"), ("number", "set_value")])
        assert hass.states.get(CLIMATE).state == HVACMode.OFF
        assert float(hass.states.get(OPENING).state) == 0
        assert float(hass.states.get(CLOSING).state) == 100
        assert_inhibited(vtherm)
        spy.reset()

        # someone changes the TRV setpoint and opens the valve by hand, the closing degree becomes unknown
        fake_climate.set_temperature(temperature=25)
        opening.set_native_value(70)
        await hass.async_block_till_done()
        hass.states.async_set(CLOSING, STATE_UNKNOWN, {"min": 0, "max": 100})
        await hass.async_block_till_done()
        await advance(hass, vtherm, 1, steps=6)
        assert spy.calls == []
        assert float(hass.states.get(OPENING).state) == 70

        await uninhibit(hass, vtherm)
        under_valve = vtherm._underlyings_valve_regulation[0]
        assert under_valve.bootstrap_diagnostics["seed_attempted_targets"] == [CLOSING]
        assert spy.calls[0][:3] == ("number", "set_value", CLOSING)
        assert ("climate", "set_hvac_mode") in spy.services()
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert float(hass.states.get(OPENING).state) == under_valve.last_sent_opening_value
        assert float(hass.states.get(OPENING).state) != 70
        # the setpoint cache followed the real state: the target is sent again
        assert hass.states.get(CLIMATE).attributes["temperature"] == vtherm.target_temperature == 19


async def test_climate_valve_restart_inhibited_unknown_degree_seeded_at_unset(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Restart while inhibited with an unknown closing degree: the gate drops the startup seed,
    so the valve and the VTherm are not ready. unset sends the seed at once (before the
    reconciliation waiting for ready), the degree becomes known, the VTherm becomes ready
    and the deferred reconciliation opens the gate"""
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})
    await create_and_register_mock_number(hass, "mock_opening_degree", "MockOpeningDegree", value=0, min=0, max=100)
    await create_and_register_mock_number(hass, "mock_closing_degree", "MockClosingDegree", value=100, min=0, max=100)
    hass.states.async_set(CLOSING, STATE_UNKNOWN, {"min": 0, "max": 100})
    old = inhibited_old_state()
    mock_restore_cache(hass, [State("climate.theoverclimatevalvemockname", old.state, old.attributes)])
    fake_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()

    with spy_services([CLIMATE, OPENING, CLOSING]) as spy:
        vtherm = await create_thermostat(hass, climate_valve_entry(), "climate.theoverclimatevalvemockname", temps=PRESETS)
        vtherm._set_now(datetime.now(tz=get_tz(hass)))
        await hass.async_block_till_done()
        assert_inhibited(vtherm)
        assert vtherm.is_ready is False
        assert spy.calls == []  # the startup seed was dropped by the closed gate

        await uninhibit(hass, vtherm)
        assert spy.calls[0][:3] == ("number", "set_value", CLOSING)
        assert hass.states.get(CLOSING).state != STATE_UNKNOWN
        assert vtherm.is_ready
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert ("climate", "set_hvac_mode") in spy.services()


async def test_climate_valve_exit_off_closes_valve_opened_by_hand(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """over_climate_valve: an OFF intent at the exit closes the regulation valve opened by hand"""
    vtherm, _, opening, closing = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    await inhibit(hass, vtherm, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    opening.set_native_value(70)
    closing.set_native_value(30)
    await hass.async_block_till_done()
    await advance(hass, vtherm, 1)
    assert float(hass.states.get(OPENING).state) == 70

    await uninhibit(hass, vtherm)
    assert float(hass.states.get(OPENING).state) == 0
    assert float(hass.states.get(CLOSING).state) == 100
    assert hass.states.get(CLIMATE).state == HVACMode.OFF


async def test_climate_valve_set_false_sends_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """over_climate_valve: set(false) sends nothing while held, recalibration is dropped"""
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    with spy_services([CLIMATE, OPENING, CLOSING]) as spy:
        await inhibit(hass, vtherm, False)
        await advance(hass, vtherm, 1, steps=6)
        with patch("custom_components.versatile_thermostat.thermostat_climate_valve.asyncio.sleep"), caplog.at_level(logging.WARNING):
            await vtherm.service_recalibrate_valves(1)
            await hass.async_block_till_done()
        assert spy.calls == []
        assert any("recalibration commands will be dropped" in record.getMessage() for record in caplog.records)
        assert_inhibited(vtherm)


##
## StateManager priorities
##
async def test_state_manager_inhibition_priority():
    """Inhibition resolves OFF with its reason, first: before central STOPPED, safety and window"""
    vtherm = MagicMock()
    vtherm.last_central_mode = None
    vtherm.safety_manager.is_safety_detected = False
    vtherm.window_manager.is_window_detected = True
    vtherm.is_inhibited = True
    manager = StateManager()
    manager.requested_state.set_hvac_mode(VThermHvacMode_HEAT)

    await manager.calculate_current_hvac_mode(vtherm)
    assert manager.current_state.hvac_mode == VThermHvacMode_OFF
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)
    vtherm.set_hvac_mode_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)
    assert manager.requested_state.hvac_mode == VThermHvacMode_HEAT

    # requested OFF stays OFF with the inhibition reason
    manager.requested_state.set_hvac_mode(VThermHvacMode_OFF)
    await manager.calculate_current_hvac_mode(vtherm)
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)

    # inhibition wins over central stopped
    manager.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    vtherm.last_central_mode = CENTRAL_MODE_STOPPED
    await manager.calculate_current_hvac_mode(vtherm)
    assert manager.current_state.hvac_mode == VThermHvacMode_OFF
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)
    vtherm.set_hvac_mode_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)

    # and over safety
    vtherm.last_central_mode = None
    vtherm.safety_manager.is_safety_detected = True
    vtherm.is_over_climate = True
    await manager.calculate_current_hvac_mode(vtherm)
    assert manager.current_state.hvac_mode == VThermHvacMode_OFF
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)

    # once not inhibited, safety and central stopped apply again
    vtherm.is_inhibited = False
    await manager.calculate_current_hvac_mode(vtherm)
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_SAFETY)
    vtherm.last_central_mode = CENTRAL_MODE_STOPPED
    await manager.calculate_current_hvac_mode(vtherm)
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_CENTRAL_MODE)
    vtherm.is_inhibited = True

    # a MagicMock attribute is not an inhibition
    other = MagicMock()
    other.last_central_mode = None
    other.safety_manager.is_safety_detected = False
    other.window_manager.is_window_detected = False
    other.auto_start_stop_manager = None
    manager2 = StateManager()
    manager2.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    await manager2.calculate_current_hvac_mode(other)
    assert manager2.current_state.hvac_mode == VThermHvacMode_HEAT


async def test_state_manager_window_eco_applies_requested_mode():
    """Window eco/frost: the current mode follows the requested one (was left unchanged)"""
    for action in (CONF_WINDOW_ECO_TEMP, CONF_WINDOW_FROST_TEMP):
        vtherm = MagicMock()
        vtherm.last_central_mode = None
        vtherm.safety_manager.is_safety_detected = False
        vtherm.is_inhibited = False
        vtherm.window_manager.is_window_detected = True
        vtherm.window_manager.window_action = action
        vtherm.auto_start_stop_manager = None
        vtherm.hvac_off_reason = HVAC_OFF_REASON_INHIBITION
        manager = StateManager()
        manager.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
        await manager.calculate_current_hvac_mode(vtherm)
        assert manager.current_state.hvac_mode == VThermHvacMode_HEAT
        vtherm.set_hvac_off_reason.assert_called_with(None)


def _window_vtherm(action, central=None, auto_stop=False):
    """A MagicMock VTherm (heat only) with an open window"""
    vtherm = MagicMock()
    vtherm.last_central_mode = central
    vtherm.safety_manager.is_safety_detected = False
    vtherm.is_inhibited = False
    vtherm.is_sleeping = False
    vtherm.window_manager.is_window_detected = True
    vtherm.window_manager.window_action = action
    vtherm.vtherm_hvac_modes = [VThermHvacMode_HEAT, VThermHvacMode_OFF]
    vtherm.vtherm_preset_modes = None
    if auto_stop:
        vtherm.auto_start_stop_manager.is_auto_stop_detected = True
        vtherm.auto_start_stop_manager.stop_mode = VThermHvacMode_OFF
    else:
        vtherm.auto_start_stop_manager = None
    return vtherm


@pytest.mark.parametrize("action", [CONF_WINDOW_ECO_TEMP, CONF_WINDOW_FROST_TEMP])
@pytest.mark.parametrize(
    "central, auto_stop, expected_mode, expected_reason",
    [
        # the window only changes the temperature: the lower constraints still apply (as on main)
        (None, True, VThermHvacMode_OFF, HVAC_OFF_REASON_AUTO_START_STOP),
        (CENTRAL_MODE_COOL_ONLY, False, VThermHvacMode_OFF, HVAC_OFF_REASON_CENTRAL_MODE),
        (CENTRAL_MODE_FROST_PROTECTION, False, VThermHvacMode_OFF, HVAC_OFF_REASON_CENTRAL_MODE),
        (None, False, VThermHvacMode_HEAT, HVAC_OFF_REASON_WINDOW_DETECTION),
    ],
)
async def test_state_manager_window_eco_frost_keeps_lower_constraints(action, central, auto_stop, expected_mode, expected_reason):
    """Window eco/frost does not end the constraint chain: auto-start/stop and the central
    modes still apply, else the requested mode applies with the window reason"""
    vtherm = _window_vtherm(action, central, auto_stop)
    manager = StateManager()
    manager.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    await manager.calculate_current_hvac_mode(vtherm)
    assert manager.current_state.hvac_mode == expected_mode
    vtherm.set_hvac_mode_reason.assert_called_with(expected_reason)


##
## Robustness: readiness, cancellation, ordering, restore, power, persistence
##
async def test_set_before_ready_defers_the_entry_stop(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A set before the VTherm is ready resolves OFF at once and sends the entry stop when ready"""
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await create_thermostat(hass, switch_entry(), "climate.theoverswitchmockname", temps=PRESETS)
        vtherm._set_now(datetime.now(tz=get_tz(hass)))
        assert vtherm.is_ready is False
        await inhibit(hass, vtherm, True)
        assert vtherm.is_inhibited is True
        assert snapshot(hass, vtherm)["entry_stop_completed"] is False
        assert spy.calls == []

        switch = MockSwitch(hass, "mock_switch", "theMockedSwitch")
        switch._attr_is_on = True
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)
        await hass.async_block_till_done()
        assert vtherm.is_ready
        assert spy.services() == [("switch", "turn_off")]
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True
        assert_inhibited(vtherm, requested=vtherm.requested_state.hvac_mode)


async def test_climate_swing_and_humidity_dropped_with_warning(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """User settings outside the requested state are dropped with one warning per service"""
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, swing_mode="on", swing_modes=["on", "off"], swing_horizontal_mode="on", swing_horizontal_modes=["on", "off"])
    vtherm = await create_thermostat(hass, climate_entry(**{CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_NONE}), "climate.theoverclimatemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    with spy_services([CLIMATE]) as spy:
        await inhibit(hass, vtherm, False)
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            for _ in range(2):
                await vtherm.async_set_swing_mode("off")
                await vtherm.async_set_swing_horizontal_mode("off")
                await vtherm.async_set_humidity(40)
        assert spy.calls == []
        dropped = sorted(r.getMessage().split(" for ")[0].split(" - ")[-1] for r in caplog.records if r.levelno == logging.WARNING and "dropped" in r.getMessage())
        assert dropped == ["climate.set_humidity", "climate.set_swing_horizontal_mode", "climate.set_swing_mode"]


async def test_cancelled_exit_rolls_back_to_inhibition(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A cancellation during the reconciliation restores inhibited + CLOSED (entry stop sent
    again), it never leaves the gate EXIT_RECONCILING; a later unset works"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.reset()
        spy.pause_on = ("switch", "turn_on")
        task = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await hass.async_block_till_done()
        assert_inhibited(vtherm)
        assert snapshot(hass, vtherm)["last_error_code"] == "exit_reconcile_cancelled"
        assert spy.services() == [("switch", "turn_on"), ("switch", "turn_off")]
        assert hass.states.get(SWITCH).state == STATE_OFF
        spy.reset()

        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []

        await uninhibit(hass, vtherm)
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert hass.states.get(SWITCH).state == STATE_ON


async def test_joiner_of_a_cancelled_exit_runs_its_own_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A joiner does not get the CancelledError of the leader: it gets the real outcome"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.pause_on = ("switch", "turn_on")
        leader = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        joiner = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.sleep(0)
        leader.cancel()
        with pytest.raises(asyncio.CancelledError):
            await leader
        await asyncio.wait_for(joiner, 5)
        await hass.async_block_till_done()
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN


async def test_cancelled_set_is_completed(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A set cancelled after the gate is closed completes its entry (OFF, single stop,
    persistence) before the CancelledError is raised"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    original = vtherm.update_states
    entered = asyncio.Event()

    async def slow_update_states(force=False):
        entered.set()
        await asyncio.sleep(10)
        return await original(force)

    with spy_services([SWITCH]) as spy:
        with patch.object(vtherm, "update_states", side_effect=slow_update_states):
            task = hass.async_create_task(vtherm.async_set_inhibition(True))
            await asyncio.wait_for(entered.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        await hass.async_block_till_done()
        assert vtherm.is_inhibited is True
        assert vtherm.inhibition_manager.command_gate == CommandGate.CLOSED
        assert spy.services() == [("switch", "turn_off")]
        assert snapshot(hass, vtherm)["entry_stop_completed"] is True


async def test_last_call_wins_when_set_is_queued_during_exit(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """unset A (running), set B (queued), unset C: C must not join A, the result is not inhibited"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.reset()
        spy.pause_on = ("switch", "turn_on")
        task_a = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        task_b = hass.async_create_task(vtherm.async_set_inhibition(True))
        await asyncio.sleep(0)
        task_c = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.sleep(0)
        assert not task_c.done()
        spy.release.set()
        await asyncio.wait_for(asyncio.gather(task_a, task_b, task_c), 5)
        await hass.async_block_till_done()
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        # A reconciled, B stopped, C reconciled again
        assert spy.services()[:2] == [("switch", "turn_on"), ("switch", "turn_off")]
        assert ("switch", "turn_on") in spy.services()[2:]


def _call_before_restore(call, results: list):
    """Patch async_startup so that the plugin calls the API before anything else.
    The outcome of the call (None or the exception) is appended to results."""
    original = BaseThermostat.async_startup

    async def patched(self, central_configuration):
        assert api(self.hass).is_inhibition_started(self.entity_id) is False
        try:
            await call(self)
            results.append(None)
        except Exception as err:  # pylint: disable=broad-except
            results.append(err)
        await original(self, central_configuration)

    return patch.object(BaseThermostat, "async_startup", patched)


@pytest.mark.parametrize("call", ["set", "unset"])
async def test_call_before_restore_is_refused(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch, call):
    """set / unset before the startup restore raise InhibitionNotStartedError and change
    nothing: the inhibited snapshot is restored as is, no command is sent"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    results: list = []
    api_call = (lambda vtherm: vtherm.async_set_inhibition(False)) if call == "set" else (lambda vtherm: vtherm.async_unset_inhibition())
    with spy_services([SWITCH]) as spy, _call_before_restore(api_call, results):
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(), spy)
        await advance(hass, vtherm, 1, steps=3)
        assert vtherm.is_ready
        assert spy.calls == []
    assert len(results) == 1 and isinstance(results[0], InhibitionNotStartedError)
    assert vtherm.inhibition_manager.is_restored
    assert api(hass).is_inhibition_started(vtherm.entity_id) is True
    assert_inhibited(vtherm)
    assert snapshot(hass, vtherm)["entry_stop_completed"] is True
    assert hass.states.get(SWITCH).state == STATE_ON


@pytest.mark.parametrize("with_snapshot", [True, False])
async def test_call_before_restore_on_non_inhibited_snapshot(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch, with_snapshot):
    """A refused set before the restore of a non inhibited VTherm (a non inhibited snapshot, or a
    previous state without any inhibition snapshot) leaves it not inhibited; a non inhibited
    snapshot keeps its diagnostics; the set made after the startup applies normally (one entry stop)"""
    old_state = inhibited_old_state(gate="OPEN", inhibited=False, completed=False, requested=False)
    old_state.attributes["specific_states"][ATTR_INHIBITION]["last_transition_at"] = "2026-10-01T10:00:00+02:00"
    if not with_snapshot:
        del old_state.attributes["specific_states"][ATTR_INHIBITION]
    results: list = []
    with spy_services([SWITCH]) as spy, _call_before_restore(lambda vtherm: vtherm.async_set_inhibition(True), results):
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, old_state, spy)
        await advance(hass, vtherm, 1)
        assert isinstance(results[0], InhibitionNotStartedError)
        assert vtherm.inhibition_manager.is_restored
        assert vtherm.is_inhibited is False
        assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN
        assert vtherm.inhibition_manager.is_used is with_snapshot
        if with_snapshot:
            assert snapshot(hass, vtherm)["last_transition_at"] == "2026-10-01T10:00:00+02:00"
        else:
            assert snapshot(hass, vtherm) is None

        await fake_underlying_switch.async_turn_on()
        await hass.async_block_till_done()
        spy.reset()
        await vtherm.async_set_inhibition(True)
        await advance(hass, vtherm, 1, steps=3)
        assert_inhibited(vtherm)
        assert spy.services() == [("switch", "turn_off")]


async def test_restore_happens_before_the_managers_start(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """An unset arriving while the managers start (before get_my_previous_state) is not lost"""
    original = BaseThermostat.get_my_previous_state

    async def patched(self):
        await self.async_unset_inhibition()
        await original(self)

    with patch.object(BaseThermostat, "get_my_previous_state", patched), spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(), spy)
    assert vtherm.is_inhibited is False
    assert vtherm.inhibition_manager.command_gate == CommandGate.OPEN


# Two call chains run update_states concurrently here: the cycle scheduler / delayed
# resend handles of one chain are overwritten by the other (existing behavior, not
# related to the inhibition), which leaves a timer at the end of the test.
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_valve_change_during_exit_is_reconciled(hass: HomeAssistant, expected_lingering_timers, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_valve, caplog):
    """Another call chain changes the target during EXIT_RECONCILING: its valve command is
    dropped (but updated the cache). The reconciliation walks again before opening the gate,
    so the valve gets the opening of the new target"""
    vtherm = await create_thermostat(hass, valve_entry(), "climate.theovervalvemockname", temps=PRESETS)
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_temp_sensor.set_native_value(17)
    await hass.async_block_till_done()
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await advance(hass, vtherm, 1)
    await inhibit(hass, vtherm, True)
    under = vtherm.underlying_entity(0)
    with spy_services([VALVE]) as spy:
        spy.pause_on = ("number", "set_value")
        exit_task = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        other = hass.async_create_task(vtherm.async_set_temperature(temperature=25))
        await asyncio.sleep(0.05)
        assert vtherm.inhibition_manager.command_gate == CommandGate.EXIT_RECONCILING
        with caplog.at_level(logging.INFO):
            spy.release.set()
            await asyncio.wait_for(asyncio.gather(exit_task, other), 5)
            await hass.async_block_till_done()
    assert any("Reconciling again" in r.getMessage() for r in caplog.records)
    assert vtherm.target_temperature == 25
    assert under.percent_open == under.last_sent_opening_value
    assert float(hass.states.get(VALVE).state) == under.percent_open
    assert under.percent_open > 59


# Two call chains run update_states concurrently here: the cycle scheduler / delayed
# resend handles of one chain are overwritten by the other (existing behavior, not
# related to the inhibition), which leaves a timer at the end of the test.
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_climate_valve_change_during_exit_is_reconciled(hass: HomeAssistant, expected_lingering_timers, fake_temp_sensor, fake_ext_temp_sensor):
    """over_climate_valve: a setpoint change from another chain during EXIT_RECONCILING
    (dropped, but it updated the last sent temperature) reaches the TRV before the gate opens"""
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)
    await inhibit(hass, vtherm, True)
    with spy_services([CLIMATE, OPENING, CLOSING]) as spy:
        spy.pause_on = ("climate", "set_hvac_mode")
        exit_task = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        other = hass.async_create_task(vtherm.async_set_temperature(temperature=25))
        await asyncio.sleep(0.05)
        spy.release.set()
        await asyncio.wait_for(asyncio.gather(exit_task, other), 5)
        await hass.async_block_till_done()
    assert vtherm.target_temperature == 25
    assert hass.states.get(CLIMATE).attributes["temperature"] == 25
    assert hass.states.get(CLIMATE).state == HVACMode.HEAT


async def test_switch_keep_alive_rearmed_after_exit_with_dropped_command(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A turn_off dropped during EXIT_RECONCILING cancelled the keep-alive: it is re-armed"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    under: UnderlyingSwitch = vtherm.underlying_entity(0)
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.pause_on = ("switch", "turn_on")
        task = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        await under.turn_off()  # dropped, and cancels the keep-alive
        spy.release.set()
        await asyncio.wait_for(task, 5)
        await hass.async_block_till_done()
        assert under._keep_alive._remove_handle is not None
        assert hass.states.get(SWITCH).state == STATE_ON
        spy.reset()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
        await hass.async_block_till_done()
        assert ("switch", "turn_on") in spy.services()


async def test_dropped_turn_off_during_exit_keeps_the_power_reservation(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """While EXIT_RECONCILING, a dropped turn_off does not release the reservation the
    reconciliation may have made"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    under: UnderlyingSwitch = vtherm.underlying_entity(0)
    power = vtherm.power_manager
    with spy_services([SWITCH]) as spy:
        await inhibit(hass, vtherm, True)
        spy.pause_on = ("switch", "turn_on")
        task = hass.async_create_task(vtherm.async_unset_inhibition())
        await asyncio.wait_for(spy.paused.wait(), 5)
        with patch.object(type(power), "sub_power_consumption_to_central_power_manager") as sub:
            await under.turn_off()
        sub.assert_not_called()
        spy.release.set()
        await asyncio.wait_for(task, 5)
        await hass.async_block_till_done()


async def test_set_and_unset_return_after_the_dump(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """set and unset return once the restore states are saved"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    await hass.async_block_till_done()
    dumps = []

    async def dump(_self):
        await asyncio.sleep(0.01)
        dumps.append(vtherm.inhibition_manager.as_dict()["command_gate"])

    with patch("homeassistant.helpers.restore_state.RestoreStateData.async_dump_states", dump):
        await vtherm.async_set_inhibition(True)
        assert dumps and dumps[-1] == "CLOSED"
        await vtherm.async_unset_inhibition()
        assert dumps[-1] == "OPEN"
        await hass.async_block_till_done()


async def test_blocked_turn_off_releases_the_power_reservation(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A dropped turn_off still releases the central power reservation; a dropped turn_on adds none"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    under: UnderlyingSwitch = vtherm.underlying_entity(0)
    await inhibit(hass, vtherm, False)
    power = vtherm.power_manager
    with spy_services([SWITCH]) as spy, patch.object(type(power), "sub_power_consumption_to_central_power_manager") as sub, patch.object(
        type(power), "add_power_consumption_to_central_power_manager"
    ) as add:
        await under.turn_off()
        await under.turn_on()
    assert spy.calls == []
    sub.assert_called_once_with(under.power_reservation_key)
    add.assert_not_called()


async def test_dumps_are_coalesced(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """Several transitions in one loop turn share one dump; a later transition dumps again"""
    vtherm = await heating_switch_vtherm(hass, fake_temp_sensor)
    await hass.async_block_till_done()
    manager = vtherm.inhibition_manager
    with patch("homeassistant.helpers.restore_state.RestoreStateData.async_dump_states") as dump:
        manager._persist()
        manager._persist()
        manager._persist()
        await hass.async_block_till_done()
        assert dump.call_count == 1
        manager._persist()
        await hass.async_block_till_done()
        assert dump.call_count == 2


async def test_no_inhibition_same_commands_as_without_the_core(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """AC-011: an unused inhibition core sends exactly the same commands as a VTherm
    built without it (reference), over a full scenario"""

    class NoInhibition:
        """The reference: no inhibition core at all"""

        is_inhibited = False
        is_used = False
        command_gate = CommandGate.OPEN

        def __init__(self, vtherm):
            pass

        def restore_state(self, old_state):
            """No snapshot"""

        async def async_on_vtherm_ready(self):
            """Nothing deferred"""

    switch2 = MockSwitch(hass, "mock_switch2", "theMockedSwitch2")
    await register_mock_entity(hass, switch2, SWITCH_DOMAIN)
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()

    vtherm = await create_thermostat(hass, switch_entry(), "climate.theoverswitchmockname", temps=PRESETS)
    with patch("custom_components.versatile_thermostat.base_thermostat.InhibitionManager", NoInhibition):
        entry = switch_entry(unique_id="switchReference", **{CONF_NAME: "Reference", CONF_UNDERLYING_LIST: ["switch.mock_switch2"]})
        reference = await create_thermostat(hass, entry, "climate.reference", temps=PRESETS)
    assert not isinstance(reference.inhibition_manager, InhibitionManager)

    now = datetime.now(tz=get_tz(hass))
    with spy_services([SWITCH, "switch.mock_switch2"]) as spy:
        for vt in (vtherm, reference):
            vt._set_now(now)
            await vt.async_set_hvac_mode(VThermHvacMode_HEAT)
            await vt.async_set_preset_mode(VThermPreset.COMFORT)
        await hass.async_block_till_done()
        # 0 % / 100 % powers only: partial cycles depend on the wall clock of each tick
        for step, temp in enumerate((15, 25, 15, 25, 15)):
            for vt in (vtherm, reference):
                await send_temperature_change_event(vt, temp, vt.now)
            for vt in (vtherm, reference):
                vt._set_now(vt.now + timedelta(minutes=2))
                await vt.async_control_heating(timestamp=vt.now)
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2 * (step + 1)))
            await hass.async_block_till_done()
        for vt in (vtherm, reference):
            await vt.async_set_hvac_mode(VThermHvacMode_OFF)
            await vt.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert spy.services(SWITCH)
    assert spy.services(SWITCH) == spy.services("switch.mock_switch2")
    assert snapshot(hass, vtherm) is None


async def test_gate_closed_before_the_managers_start(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """The snapshot is restored before the managers start: a command sent while they start
    listening is already blocked"""
    from custom_components.versatile_thermostat.feature_repair_incorrect_state_manager import FeatureRepairIncorrectStateManager

    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    original = FeatureRepairIncorrectStateManager.start_listening

    async def start_listening(self):
        await self._vtherm.async_underlying_entity_turn_off()
        await original(self)

    with patch.object(FeatureRepairIncorrectStateManager, "start_listening", start_listening), spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(), spy)
        assert_inhibited(vtherm)
        assert spy.calls == []
    assert hass.states.get(SWITCH).state == STATE_ON


async def test_second_startup_without_api_call_does_not_restore_again(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """Plain restore of a pending entry stop: sent once when ready; a second async_startup
    (config entry update) does not restore the old snapshot again and does not resend it"""
    await fake_underlying_switch.async_turn_on()
    await hass.async_block_till_done()
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(completed=False), spy)
        await advance(hass, vtherm, 1)
        assert spy.services() == [("switch", "turn_off")]

        await fake_underlying_switch.async_turn_on()
        await hass.async_block_till_done()
        spy.reset()
        await api(hass).init_vtherm_links(vtherm.unique_id)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []
        assert_inhibited(vtherm)
