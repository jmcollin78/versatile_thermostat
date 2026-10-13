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
        assert spy.services() == [("switch", "turn_on")]


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
        assert spy.calls == []

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
    """A restart during EXIT_RECONCILING is restored inhibited and CLOSED"""
    with spy_services([SWITCH]) as spy:
        vtherm = await start_switch_vtherm_with_restored_state(hass, fake_temp_sensor, inhibited_old_state(gate="EXIT_RECONCILING", inhibited=False), spy)
        assert_inhibited(vtherm)
        await advance(hass, vtherm, 1, steps=3)
        assert spy.calls == []
        assert snapshot(hass, vtherm)["command_gate"] == "CLOSED"
        assert snapshot(hass, vtherm)["inhibited"] is True


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
    """Inhibition resolves OFF with its reason, after central STOPPED and safety, before window"""
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

    # central stopped wins
    vtherm.last_central_mode = CENTRAL_MODE_STOPPED
    await manager.calculate_current_hvac_mode(vtherm)
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_CENTRAL_MODE)

    # safety wins
    vtherm.last_central_mode = None
    vtherm.safety_manager.is_safety_detected = True
    vtherm.is_over_climate = True
    await manager.calculate_current_hvac_mode(vtherm)
    vtherm.set_hvac_off_reason.assert_called_with(HVAC_OFF_REASON_SAFETY)

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
        vtherm.hvac_off_reason = HVAC_OFF_REASON_INHIBITION
        manager = StateManager()
        manager.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
        await manager.calculate_current_hvac_mode(vtherm)
        assert manager.current_state.hvac_mode == VThermHvacMode_HEAT
        vtherm.set_hvac_off_reason.assert_called_with(None)
