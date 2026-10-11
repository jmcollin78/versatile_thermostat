# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name
"""Test the extensible VTherm inhibition (issue #2087, controlled withdrawal).

A fake inhibition plugin (factory + provider) is registered through the real
VTherm API. The tests count the commands sent to the underlyings (turn_on,
turn_off, set_hvac_mode, cycle starts, repairs) and not only the final state.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from vtherm_api import (
    InhibitionStatus,
    InhibitionStopPolicy,
    InhibitionTransition,
)

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.feature_repair_incorrect_state_manager import FeatureRepairIncorrectStateManager
from custom_components.versatile_thermostat.inhibition_manager import (
    ATTR_INHIBITION,
    InhibitionErrorCode,
    InhibitionPhysicalStopResult,
    InhibitionProviderStatus,
)
from custom_components.versatile_thermostat.state_manager import StateManager
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate, UnderlyingSwitch, UnderlyingValve
from custom_components.versatile_thermostat.feature_power_manager import FeaturePowerManager
from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

SWITCH_ENTITY_ID = "climate.theoverswitchmockname"


##
## Fake inhibition plugin
##
class FakeInhibitionProvider:
    """A minimal inhibition provider driven by the tests"""

    def __init__(self, name: str, thermostat, status: InhibitionStatus, policy: InhibitionStopPolicy):
        self._name = name
        self._thermostat = thermostat
        self._status = status
        self._policy = policy
        self._callbacks = []
        self._sequence = 0
        self.refresh_error: Exception | None = None
        self.entry_infos = None
        self.post_init_calls = 0
        self.start_listening_calls = 0
        self.stop_listening_calls = 0
        self.refresh_calls = 0
        self.restored_states = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> InhibitionStatus:
        return self._status

    @property
    def physical_stop_policy(self) -> InhibitionStopPolicy:
        return self._policy

    def post_init(self, entry_infos):
        self.post_init_calls += 1
        self.entry_infos = entry_infos

    async def async_start_listening(self):
        self.start_listening_calls += 1

    def stop_listening(self):
        """Report UNKNOWN to the callbacks before detaching them (contract)"""
        self.stop_listening_calls += 1
        old = self._status
        self._status = InhibitionStatus.UNKNOWN
        transition = self._build(InhibitionStatus.UNKNOWN, old, None)
        for callback in list(self._callbacks):
            self._thermostat.hass.async_create_task(callback(transition))
        self._callbacks.clear()

    def restore_state(self, old_state):
        self.restored_states.append(old_state)

    async def async_refresh_state(self) -> InhibitionStatus:
        self.refresh_calls += 1
        if self.refresh_error:
            raise self.refresh_error
        return self._status

    def register_transition_callback(self, callback):
        self._callbacks.append(callback)

        def remove():
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return remove

    def _build(self, new_status, old_status, sequence) -> InhibitionTransition:
        if sequence is None:
            self._sequence += 1
            sequence = self._sequence
        return InhibitionTransition(
            provider_name=self._name,
            new_status=new_status,
            old_status=old_status,
            stop_policy=self._policy,
            timestamp=datetime.now(),
            sequence=sequence,
        )

    async def async_notify(self, status: InhibitionStatus, policy: InhibitionStopPolicy | None = None, sequence: int | None = None) -> InhibitionTransition:
        """Change the confirmed status and notify the core"""
        old = self._status
        self._status = status
        if policy is not None:
            self._policy = policy
        transition = self._build(status, old, sequence)
        await self.async_send(transition)
        return transition

    async def async_send(self, transition: InhibitionTransition):
        """Send (or replay) a transition"""
        for callback in list(self._callbacks):
            await callback(transition)


class FakeInhibitionFactory:
    """A minimal inhibition provider factory"""

    def __init__(
        self,
        name: str = "fake_inhibition",
        status: InhibitionStatus = InhibitionStatus.INACTIVE,
        policy: InhibitionStopPolicy = InhibitionStopPolicy.TURN_OFF,
        supports: bool = True,
        supports_error: Exception | None = None,
        create_error: Exception | None = None,
    ):
        self._name = name
        self.status = status
        self.policy = policy
        self.supports_result = supports
        self.supports_error = supports_error
        self.create_error = create_error
        self.supports_calls = 0
        self.providers: list[FakeInhibitionProvider] = []

    @property
    def name(self) -> str:
        return self._name

    def supports(self, thermostat) -> bool:
        self.supports_calls += 1
        if self.supports_error:
            raise self.supports_error
        return self.supports_result

    def create(self, thermostat) -> FakeInhibitionProvider:
        if self.create_error:
            raise self.create_error
        provider = FakeInhibitionProvider(self._name, thermostat, self.status, self.policy)
        self.providers.append(provider)
        return provider

    @property
    def provider(self) -> FakeInhibitionProvider:
        """The last created provider"""
        return self.providers[-1]


##
## Helpers
##
def switch_entry(**extra) -> MockConfigEntry:
    """An over_switch TPI VTherm with a window sensor and the repair feature"""
    data = {
        CONF_NAME: "TheOverSwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        "eco_temp": 17,
        "comfort_temp": 18,
        "boost_temp": 19,
        CONF_USE_WINDOW_FEATURE: True,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_UNDERLYING_LIST: ["switch.mock_switch"],
        CONF_HEATER_KEEP_ALIVE: 0,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_MINIMAL_ACTIVATION_DELAY: 30,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
        CONF_WINDOW_DELAY: 0,
        CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        CONF_REPAIR_INCORRECT_STATE: True,
    }
    data.update(extra)
    return MockConfigEntry(domain=DOMAIN, title="TheOverSwitchMockName", unique_id="uniqueId", data=data)


@contextmanager
def spy_switch_commands():
    """Count every command that can reach an underlying switch"""
    # fmt: off
    with patch.object(UnderlyingSwitch, "turn_on", new_callable=AsyncMock) as turn_on, \
        patch.object(UnderlyingSwitch, "turn_off", new_callable=AsyncMock) as turn_off, \
        patch.object(UnderlyingSwitch, "set_hvac_mode", autospec=True, side_effect=UnderlyingSwitch.set_hvac_mode) as set_hvac_mode, \
        patch.object(CycleScheduler, "start_cycle", new_callable=AsyncMock) as start_cycle, \
        patch.object(FeatureRepairIncorrectStateManager, "check_and_repair", new_callable=AsyncMock, return_value=False) as check_and_repair:
        # fmt: on
        yield SimpleNamespace(
            turn_on=turn_on,
            turn_off=turn_off,
            set_hvac_mode=set_hvac_mode,
            start_cycle=start_cycle,
            check_and_repair=check_and_repair,
        )


def reset_spies(spies: SimpleNamespace):
    """Reset all the counters"""
    for mock in vars(spies).values():
        mock.reset_mock()


def assert_no_command(spies: SimpleNamespace):
    """No VTherm command reached the underlyings"""
    assert spies.turn_on.call_count == 0
    assert spies.turn_off.call_count == 0
    assert spies.set_hvac_mode.call_count == 0
    assert spies.start_cycle.call_count == 0
    assert spies.check_and_repair.call_count == 0


def register_factories(hass, *factories):
    """Register the fake factories in the real VTherm API"""
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    for factory in factories:
        api.register_inhibition_provider_factory(factory)
    return api


async def create_heating_switch_vtherm(hass, entry=None) -> BaseThermostat:
    """Create the over_switch VTherm and make it heat in comfort"""
    entity = await create_thermostat(hass, entry or switch_entry(), SWITCH_ENTITY_ID)
    assert entity
    now = datetime.now(tz=get_tz(hass))
    entity._set_now(now)
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 5, now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    return entity


async def run_cycles(entity: BaseThermostat, nb: int = 3):
    """Run some periodic control cycles and temperature events"""
    for _ in range(nb):
        await entity.async_control_heating(timestamp=entity.now)
        await send_temperature_change_event(entity, 15, entity.now)


def inhibition_attributes(hass, entity: BaseThermostat) -> dict:
    """The published inhibition attribute block"""
    return hass.states.get(entity.entity_id).attributes["specific_states"][ATTR_INHIBITION]


async def open_window(entity: BaseThermostat):
    """Open the window (window delay is 0)"""
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_function = await send_window_change_event(entity, True, False, datetime.now(), sleep=False)
        await try_function(None)
    await wait_for_local_condition(lambda: entity.window_state == STATE_ON)


async def close_window(entity: BaseThermostat):
    """Close the window"""
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_function = await send_window_change_event(entity, False, True, datetime.now(), sleep=False)
        await try_function(None)
    await wait_for_local_condition(lambda: entity.window_state == STATE_OFF)


##
## StateManager priority (D-2087-04)
##
@pytest.mark.parametrize(
    "inhibited, requested_hvac_mode, last_central_mode, is_safety_detected, is_window_detected, is_auto_stop_detected, expected_hvac_mode, expected_reason",
    # fmt: off
    [
        # no inhibition: historic resolution
        (False, VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, False, False, VThermHvacMode_HEAT, None),
        # inhibition alone
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, False, False, VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        (True,  VThermHvacMode_COOL, CENTRAL_MODE_AUTO,    False, False, False, VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        # inhibition resolves OFF also when the requested hvac_mode is already OFF
        (True,  VThermHvacMode_OFF,  CENTRAL_MODE_AUTO,    False, False, False, VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        # central stop and safety keep the priority
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_STOPPED, False, False, False, VThermHvacMode_OFF,  HVAC_OFF_REASON_CENTRAL_MODE),
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    True,  False, False, VThermHvacMode_OFF,  HVAC_OFF_REASON_SAFETY),
        # inhibition wins over window and auto-start/stop
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, True,  False, VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, False, True,  VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        (True,  VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, True,  True,  VThermHvacMode_OFF,  HVAC_OFF_REASON_INHIBITION),
        # and over the central heat only / frost protection modes
        (True,  VThermHvacMode_COOL, CENTRAL_MODE_HEAT_ONLY, False, False, False, VThermHvacMode_OFF, HVAC_OFF_REASON_INHIBITION),
        # without inhibition the window and auto-start/stop are unchanged
        (False, VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, True,  True,  VThermHvacMode_OFF,  HVAC_OFF_REASON_WINDOW_DETECTION),
        (False, VThermHvacMode_HEAT, CENTRAL_MODE_AUTO,    False, False, True,  VThermHvacMode_OFF,  HVAC_OFF_REASON_AUTO_START_STOP),
    ],
    # fmt: on
)
async def test_state_manager_inhibition_priority(
    hass: HomeAssistant,
    inhibited,
    requested_hvac_mode,
    last_central_mode,
    is_safety_detected,
    is_window_detected,
    is_auto_stop_detected,
    expected_hvac_mode,
    expected_reason,
):
    """Central stop and safety > inhibition > window > auto-start/stop > rest"""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).is_over_climate = PropertyMock(return_value=True)
    type(fake_vtherm).vtherm_hvac_modes = PropertyMock(return_value=[VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF])
    type(fake_vtherm).is_sleeping = PropertyMock(return_value=False)
    type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)
    type(fake_vtherm).last_central_mode = PropertyMock(return_value=last_central_mode)
    type(fake_vtherm).is_inhibition_withdrawn = PropertyMock(return_value=inhibited)
    fake_vtherm.safety_manager = MagicMock()
    type(fake_vtherm.safety_manager).is_safety_detected = PropertyMock(return_value=is_safety_detected)
    type(fake_vtherm.safety_manager).safety_default_on_percent = PropertyMock(return_value=0.0)
    fake_vtherm.window_manager = MagicMock()
    type(fake_vtherm.window_manager).is_window_detected = PropertyMock(return_value=is_window_detected)
    type(fake_vtherm.window_manager).window_action = PropertyMock(return_value=CONF_WINDOW_TURN_OFF)
    fake_vtherm.auto_start_stop_manager = MagicMock()
    type(fake_vtherm.auto_start_stop_manager).is_auto_stop_detected = PropertyMock(return_value=is_auto_stop_detected)
    type(fake_vtherm.auto_start_stop_manager).stop_mode = PropertyMock(return_value=VThermHvacMode_OFF)

    state_manager = StateManager()
    state_manager.requested_state.set_state(hvac_mode=requested_hvac_mode, preset=VThermPreset.ECO, target_temperature=22)
    state_manager.current_state.set_state(hvac_mode=requested_hvac_mode, preset=VThermPreset.ECO, target_temperature=22)

    await state_manager.calculate_current_hvac_mode(fake_vtherm)

    assert state_manager.current_state.hvac_mode == expected_hvac_mode
    # the requested state is never modified by the inhibition
    assert state_manager.requested_state.hvac_mode == requested_hvac_mode
    if expected_reason is not None:
        fake_vtherm.set_hvac_off_reason.assert_called_with(expected_reason)
    if expected_reason == HVAC_OFF_REASON_INHIBITION:
        fake_vtherm.set_hvac_mode_reason.assert_called_with(HVAC_OFF_REASON_INHIBITION)


##
## No eligible provider (ABSENT): historic behavior
##
async def test_no_eligible_provider_is_absent(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """A non eligible factory leaves the VTherm untouched"""
    factory = FakeInhibitionFactory(supports=False)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        assert factory.supports_calls >= 1
        assert not factory.providers
        assert entity.inhibition_manager.provider_name is None
        assert entity.inhibition_manager.state.provider_status == InhibitionProviderStatus.ABSENT
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.start_cycle.call_count >= 1
        # no inhibition block for a VTherm without provider
        assert ATTR_INHIBITION not in hass.states.get(entity.entity_id).attributes["specific_states"]

    entity.remove_thermostat()


##
## Entry, holding, exit over_switch (AC-001, AC-002, AC-003)
##
async def test_entry_turn_off_policy_and_holding(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-001 / AC-002 / AC-003 - one stop, then no order at all, direct commands kept"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        assert provider.post_init_calls == 1
        assert provider.entry_infos is entity.entry_infos
        assert provider.start_listening_calls == 1
        assert provider.refresh_calls == 1
        assert entity.inhibition_manager.state.provider_status == InhibitionProviderStatus.INACTIVE
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert inhibition_attributes(hass, entity)["withdrawal_active"] is False

        reset_spies(spies)

        # 1. the provider confirms the activation
        await provider.async_notify(InhibitionStatus.ACTIVE)

        assert entity.is_inhibition_withdrawn is True
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert entity.hvac_mode_reason == HVAC_OFF_REASON_INHIBITION
        # the intent is untouched
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.requested_state.preset == VThermPreset.COMFORT
        # exactly one physical stop, through turn_off only
        assert spies.turn_off.call_count == 1
        assert spies.turn_on.call_count == 0
        assert spies.set_hvac_mode.call_count == 0
        assert spies.start_cycle.call_count == 0
        assert spies.check_and_repair.call_count == 0
        assert entity.cycle_scheduler.is_cycle_running is False

        state = entity.inhibition_manager.state
        assert state.withdrawal_active is True
        assert state.awaiting_confirmation is False
        assert state.entry_handled is True
        assert state.physical_stop_emitted is True
        assert state.physical_stop_result == InhibitionPhysicalStopResult.SENT
        assert state.effective_stop_policy == InhibitionStopPolicy.TURN_OFF
        assert state.last_transition_at is not None

        attributes = inhibition_attributes(hass, entity)
        assert attributes["schema_version"] == 1
        assert attributes["provider_name"] == "fake_inhibition"
        assert attributes["provider_status"] == "active"
        assert attributes["withdrawal_active"] is True
        assert attributes["effective_stop_policy"] == "turn_off"
        assert attributes["entry_handled"] is True
        assert attributes["physical_stop_emitted"] is True
        assert attributes["physical_stop_result"] == "sent"
        assert attributes["last_error_code"] is None
        assert hass.states.get(entity.entity_id).attributes["specific_states"]["hvac_off_reason"] == HVAC_OFF_REASON_INHIBITION

        # 2. AC-002 - repeated ACTIVE and several cycles: nothing is sent
        reset_spies(spies)
        await provider.async_notify(InhibitionStatus.ACTIVE)
        await run_cycles(entity, 3)
        assert_no_command(spies)

        # 3. AC-003 - the user turns the switch on directly: never overwritten
        hass.states.async_set("switch.mock_switch", STATE_ON)
        await hass.async_block_till_done()
        assert entity.is_device_active is True
        await run_cycles(entity, 3)
        assert_no_command(spies)
        assert hass.states.get("switch.mock_switch").state == STATE_ON

    entity.remove_thermostat()


async def test_entry_do_not_turn_off_policy(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-001b - withdrawal without any turn_off when the plugin disables the stop"""
    factory = FakeInhibitionFactory(policy=InhibitionStopPolicy.DO_NOT_TURN_OFF)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        reset_spies(spies)

        await provider.async_notify(InhibitionStatus.ACTIVE)

        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        state = entity.inhibition_manager.state
        assert state.withdrawal_active is True
        assert state.entry_handled is True
        assert state.physical_stop_emitted is False
        assert state.physical_stop_result == InhibitionPhysicalStopResult.NOT_REQUIRED
        assert state.effective_stop_policy == InhibitionStopPolicy.DO_NOT_TURN_OFF
        # the running cycle is cancelled, but nothing is sent
        assert entity.cycle_scheduler.is_cycle_running is False
        assert_no_command(spies)

        await run_cycles(entity, 3)
        assert_no_command(spies)

    entity.remove_thermostat()


async def test_policy_captured_at_entry(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """A policy change while withdrawn applies to the next entry only"""
    factory = FakeInhibitionFactory(policy=InhibitionStopPolicy.DO_NOT_TURN_OFF)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        reset_spies(spies)

        await provider.async_notify(InhibitionStatus.ACTIVE)
        await provider.async_notify(InhibitionStatus.ACTIVE, policy=InhibitionStopPolicy.TURN_OFF)
        assert entity.inhibition_manager.state.effective_stop_policy == InhibitionStopPolicy.DO_NOT_TURN_OFF
        assert spies.turn_off.call_count == 0

        await provider.async_notify(InhibitionStatus.INACTIVE)
        reset_spies(spies)
        # next activation uses the new policy
        await provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.inhibition_manager.state.effective_stop_policy == InhibitionStopPolicy.TURN_OFF
        assert spies.turn_off.call_count == 1

    entity.remove_thermostat()


##
## Intent and exit (AC-004, AC-005, AC-006, BR-006)
##
async def test_intent_changes_retained_and_applied_once_on_exit(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-004 / AC-006 - hvac, preset and setpoint changes are retained, applied once at exit"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        await provider.async_notify(InhibitionStatus.ACTIVE)
        reset_spies(spies)

        # intent changes during the withdrawal
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert entity.requested_state.preset == VThermPreset.BOOST
        assert entity.target_temperature == 19
        await entity.async_set_temperature(temperature=21)

        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.requested_state.preset == VThermPreset.NONE
        assert entity.requested_state.target_temperature == 21
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert_no_command(spies)

        # exit: the current intent is applied once
        await provider.async_notify(InhibitionStatus.INACTIVE)

        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.target_temperature == 21
        assert entity.hvac_off_reason is None
        assert entity.hvac_mode_reason is None
        assert spies.start_cycle.call_count == 1
        assert spies.turn_off.call_count == 0
        state = entity.inhibition_manager.state
        assert state.withdrawal_active is False
        assert state.entry_handled is False
        assert state.physical_stop_emitted is False
        assert inhibition_attributes(hass, entity)["provider_status"] == "inactive"

        # repeated INACTIVE is idempotent: no second reconciliation
        reset_spies(spies)
        await provider.async_notify(InhibitionStatus.INACTIVE)
        assert_no_command(spies)

    entity.remove_thermostat()


async def test_manual_off_kept_after_exit(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-005 - an OFF request made during the withdrawal stays OFF after exit"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        await provider.async_notify(InhibitionStatus.ACTIVE)

        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        reset_spies(spies)

        await provider.async_notify(InhibitionStatus.INACTIVE)

        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_MANUAL
        assert spies.turn_on.call_count == 0
        assert spies.start_cycle.call_count == 0

    entity.remove_thermostat()


async def test_exit_subject_to_window_and_priority(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-006 / AC-012 - inhibition wins over an open window, the window applies at exit"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        await provider.async_notify(InhibitionStatus.ACTIVE)
        reset_spies(spies)

        await open_window(entity)
        # inhibition keeps the priority, nothing is sent
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert_no_command(spies)

        # exit: the window is still open
        await provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        assert spies.turn_on.call_count == 0

        # the window closes: normal resume
        await close_window(entity)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.start_cycle.call_count >= 1

        # window open first, then inhibition: inhibition reason wins, window kept
        await open_window(entity)
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        reset_spies(spies)
        await provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert entity.window_manager.is_window_detected is True
        assert spies.turn_off.call_count == 1

    entity.remove_thermostat()


async def test_already_off_with_active_underlying(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-011 - VTherm already OFF but an underlying is on: the stop is still sent once"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        hass.states.async_set("switch.mock_switch", STATE_ON)
        await hass.async_block_till_done()
        assert entity.is_device_active is True
        reset_spies(spies)

        await provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert spies.turn_off.call_count == 1
        assert spies.set_hvac_mode.call_count == 0

        await run_cycles(entity, 2)
        assert spies.turn_off.call_count == 1

    entity.remove_thermostat()


async def test_replayed_sequence_and_stale_callbacks(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Replayed transitions and callbacks of a removed VTherm are ignored"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        active = await provider.async_notify(InhibitionStatus.ACTIVE)
        inactive = await provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.is_inhibition_withdrawn is False
        reset_spies(spies)

        # replaying an older transition does nothing
        await provider.async_send(active)
        assert entity.is_inhibition_withdrawn is False
        await provider.async_send(inactive)
        assert_no_command(spies)

        # a transition of another provider is ignored
        await provider.async_send(
            InhibitionTransition("another", InhibitionStatus.ACTIVE, InhibitionStatus.INACTIVE, InhibitionStopPolicy.TURN_OFF, datetime.now(), 1000)
        )
        assert entity.is_inhibition_withdrawn is False

        # an invalid status is treated as unknown
        await provider.async_send(
            InhibitionTransition("fake_inhibition", "bad", InhibitionStatus.INACTIVE, InhibitionStopPolicy.TURN_OFF, datetime.now(), 1001)
        )
        assert entity.inhibition_manager.state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert entity.inhibition_manager.state.last_error_code == InhibitionErrorCode.INVALID_STATUS
        assert entity.is_inhibition_withdrawn is True
        await provider.async_notify(InhibitionStatus.INACTIVE, sequence=1002)
        assert entity.is_inhibition_withdrawn is False
        assert entity.inhibition_manager.state.last_error_code is None

        # removal detaches the provider (stop_listening reports UNKNOWN, ignored)
        entity.remove_thermostat()
        assert provider.stop_listening_calls == 1
        await hass.async_block_till_done()
        reset_spies(spies)
        await provider.async_send(
            InhibitionTransition("fake_inhibition", InhibitionStatus.ACTIVE, InhibitionStatus.INACTIVE, InhibitionStopPolicy.TURN_OFF, datetime.now(), 2000)
        )
        assert_no_command(spies)


async def test_physical_stop_failure_not_resent(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """A failing stop is reported and never resent automatically"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        reset_spies(spies)
        spies.turn_off.side_effect = HomeAssistantError("service failed")

        await provider.async_notify(InhibitionStatus.ACTIVE)

        state = entity.inhibition_manager.state
        assert spies.turn_off.call_count == 1
        assert state.withdrawal_active is True
        assert state.entry_handled is True
        assert state.physical_stop_emitted is True
        assert state.physical_stop_result == InhibitionPhysicalStopResult.FAILED_OR_UNKNOWN
        assert state.last_error_code == InhibitionErrorCode.PHYSICAL_STOP_FAILED

        await run_cycles(entity, 2)
        await provider.async_notify(InhibitionStatus.ACTIVE)
        assert spies.turn_off.call_count == 1

    entity.remove_thermostat()


##
## Conflicts (AC-009, AC-013)
##
async def test_conflict_first_registered_wins(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch, caplog):
    """Two eligible factories: the first registered is retained, the second rejected and named"""
    first = FakeInhibitionFactory(name="first_inhibition")
    second = FakeInhibitionFactory(name="second_inhibition")
    not_eligible = FakeInhibitionFactory(name="other_inhibition", supports=False)
    register_factories(hass, first, not_eligible, second)

    caplog.set_level(logging.ERROR)
    with spy_switch_commands():
        entity = await create_heating_switch_vtherm(hass)

        assert entity.inhibition_manager.provider_name == "first_inhibition"
        assert len(first.providers) == 1
        assert not second.providers
        assert not not_eligible.providers
        conflicts = entity.inhibition_manager.conflicts
        assert len(conflicts) == 1
        assert conflicts[0].as_dict() == {"retained": "first_inhibition", "rejected": "second_inhibition"}
        assert inhibition_attributes(hass, entity)["rejected_providers"] == ["second_inhibition"]

        messages = [record.getMessage() for record in caplog.records if "conflict" in record.getMessage()]
        # reported once, although the discovery runs at post_init and at startup
        assert len(messages) == 1
        assert "first_inhibition" in messages[0] and "second_inhibition" in messages[0]

        # only the retained provider drives the VTherm
        await first.provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.is_inhibition_withdrawn is True

    entity.remove_thermostat()


async def test_api_refuses_duplicate_name(hass: HomeAssistant):
    """The API refuses a second factory with the same name (explicit conflict)"""
    api = register_factories(hass, FakeInhibitionFactory(name="dup"))
    with pytest.raises(ValueError):
        api.register_inhibition_provider_factory(FakeInhibitionFactory(name="dup"))
    assert api.list_inhibition_provider_factories() == ["dup"]


##
## UNKNOWN (AC-010, D-2087-06)
##
async def test_supports_exception_is_unknown_with_safe_stop(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """A failing supports() is a failing candidate: UNKNOWN, withdrawal, one precautionary stop"""
    failing = FakeInhibitionFactory(name="failing", supports_error=RuntimeError("boom"))
    second = FakeInhibitionFactory(name="second")
    register_factories(hass, failing, second)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)

        state = entity.inhibition_manager.state
        assert state.provider_name == "failing"
        assert state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert state.last_error_code == InhibitionErrorCode.SUPPORTS_FAILED
        assert state.withdrawal_active is True
        assert state.awaiting_confirmation is True
        # no usable provider nor known policy: TURN_OFF fallback, one stop
        assert state.effective_stop_policy == InhibitionStopPolicy.TURN_OFF
        assert state.physical_stop_emitted is True
        assert spies.turn_off.call_count == 1
        # the requested heating is not resumed
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert spies.start_cycle.call_count == 0
        # the second eligible factory is rejected
        assert not second.providers
        assert [conflict.rejected for conflict in entity.inhibition_manager.conflicts] == ["second"]

        await run_cycles(entity, 2)
        assert spies.turn_off.call_count == 1
        assert spies.start_cycle.call_count == 0

    entity.remove_thermostat()


async def test_create_exception_is_unknown(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """A failing create() leaves the VTherm UNKNOWN and withdrawn"""
    factory = FakeInhibitionFactory(create_error=RuntimeError("boom"))
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        state = entity.inhibition_manager.state
        assert state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert state.last_error_code == InhibitionErrorCode.CREATE_FAILED
        assert entity.is_inhibition_withdrawn is True
        assert spies.turn_off.call_count == 1
        assert inhibition_attributes(hass, entity)["last_error_code"] == "create_failed"

    entity.remove_thermostat()


@pytest.mark.parametrize("policy, expected_turn_off", [(InhibitionStopPolicy.TURN_OFF, 1), (InhibitionStopPolicy.DO_NOT_TURN_OFF, 0)])
async def test_unknown_at_load(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch, policy, expected_turn_off):
    """AC-010 - UNKNOWN at load: withdrawal, stop only with TURN_OFF, resume only on INACTIVE"""
    factory = FakeInhibitionFactory(status=InhibitionStatus.UNKNOWN, policy=policy)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider

        state = entity.inhibition_manager.state
        assert state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert state.awaiting_confirmation is True
        assert state.withdrawal_active is True
        assert state.entry_handled is True
        assert state.effective_stop_policy == policy
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert spies.turn_off.call_count == expected_turn_off
        assert spies.start_cycle.call_count == 0
        assert inhibition_attributes(hass, entity)["awaiting_confirmation"] is True

        # a confirmed ACTIVE does not duplicate the stop
        await provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.inhibition_manager.state.awaiting_confirmation is False
        assert spies.turn_off.call_count == expected_turn_off

        # UNKNOWN again does not resume either
        await provider.async_notify(InhibitionStatus.UNKNOWN)
        await run_cycles(entity, 2)
        assert spies.start_cycle.call_count == 0
        assert spies.turn_off.call_count == expected_turn_off

        # only a confirmed INACTIVE resumes
        await provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.start_cycle.call_count == 1

    entity.remove_thermostat()


async def test_refresh_error_is_unknown(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """An exception in async_refresh_state() is UNKNOWN with an error code"""
    factory = FakeInhibitionFactory(status=InhibitionStatus.INACTIVE)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        reset_spies(spies)

        provider.refresh_error = RuntimeError("source unavailable")
        await entity.inhibition_manager.async_refresh()
        state = entity.inhibition_manager.state
        assert state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert state.last_error_code == InhibitionErrorCode.REFRESH_FAILED
        assert entity.is_inhibition_withdrawn is True
        assert spies.turn_off.call_count == 1

        provider.refresh_error = None
        await entity.inhibition_manager.async_refresh()
        assert entity.is_inhibition_withdrawn is False
        assert entity.inhibition_manager.state.last_error_code is None
        assert spies.start_cycle.call_count == 1

    entity.remove_thermostat()


@pytest.mark.parametrize("policy, expected_turn_off", [(InhibitionStopPolicy.TURN_OFF, 1), (InhibitionStopPolicy.DO_NOT_TURN_OFF, 0)])
async def test_plugin_reload(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch, policy, expected_turn_off):
    """AC-010 - plugin reload: UNKNOWN, withdrawal kept, resume only on a confirmed INACTIVE"""
    factory = FakeInhibitionFactory(policy=policy)
    api = register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        provider = factory.provider
        reset_spies(spies)

        # 1. plugin unload: the provider reports UNKNOWN, then the factory is unregistered
        provider.stop_listening()
        api.unregister_inhibition_provider_factory("fake_inhibition")
        await hass.async_block_till_done()

        state = entity.inhibition_manager.state
        assert state.provider_status == InhibitionProviderStatus.UNKNOWN
        assert state.provider_name == "fake_inhibition"
        assert state.withdrawal_active is True
        assert state.awaiting_confirmation is True
        assert entity.inhibition_manager.provider is None
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert spies.turn_off.call_count == expected_turn_off
        await run_cycles(entity, 2)
        assert spies.start_cycle.call_count == 0

        # 2. plugin reload: a new factory instance registers again
        new_factory = FakeInhibitionFactory(policy=policy)
        api.register_inhibition_provider_factory(new_factory)
        await hass.async_block_till_done()

        assert len(new_factory.providers) == 1
        assert entity.inhibition_manager.provider is new_factory.provider
        assert entity.inhibition_manager.state.provider_status == InhibitionProviderStatus.INACTIVE
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.turn_off.call_count == expected_turn_off
        assert spies.start_cycle.call_count == 1

        # the old provider instance cannot drive the VTherm anymore
        await provider.async_send(
            InhibitionTransition("fake_inhibition", InhibitionStatus.ACTIVE, InhibitionStatus.INACTIVE, policy, datetime.now(), 1000)
        )
        assert entity.is_inhibition_withdrawn is False

    entity.remove_thermostat()


@pytest.mark.parametrize("late_status, expected_turn_off, expected_hvac_mode", [(InhibitionStatus.INACTIVE, 0, VThermHvacMode_HEAT), (InhibitionStatus.UNKNOWN, 1, VThermHvacMode_OFF), (InhibitionStatus.ACTIVE, 1, VThermHvacMode_OFF)])
async def test_late_provider(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch, late_status, expected_turn_off, expected_hvac_mode):
    """A plugin registered after the VTherm startup attaches with the same path"""
    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass)
        assert entity.inhibition_manager.provider_name is None
        reset_spies(spies)

        factory = FakeInhibitionFactory(status=late_status)
        register_factories(hass, factory)
        await hass.async_block_till_done()

        assert entity.inhibition_manager.provider_name == "fake_inhibition"
        assert factory.provider.start_listening_calls == 1
        assert entity.inhibition_manager.state.provider_status == InhibitionProviderStatus(late_status.value)
        assert entity.vtherm_hvac_mode == expected_hvac_mode
        assert spies.turn_off.call_count == expected_turn_off
        assert spies.turn_on.call_count == 0

    entity.remove_thermostat()


async def test_reload_of_the_last_vtherm_keeps_the_factories(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """The API is rebuilt when the last VTherm entry is unloaded: the inhibition factories
    registered by the plugins are kept and the reloaded VTherm attaches its provider again"""
    factory = FakeInhibitionFactory(status=InhibitionStatus.ACTIVE)
    old_api = register_factories(hass, factory)
    entry = switch_entry()

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass, entry)
        assert entity.is_inhibition_withdrawn is True
        assert spies.turn_off.call_count == 1
        reset_spies(spies)

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        api = VersatileThermostatAPI.get_vtherm_api(hass)
        assert api is not old_api
        assert isinstance(api, VersatileThermostatAPI)
        assert api.get_inhibition_provider_factory("fake_inhibition") is factory

        new_entity = search_entity(hass, SWITCH_ENTITY_ID, CLIMATE_DOMAIN)
        assert new_entity is not entity
        assert len(factory.providers) == 2
        assert new_entity.inhibition_manager.provider is factory.provider
        assert new_entity.is_inhibition_withdrawn is True
        assert new_entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        # the restored withdrawal is kept: no second stop
        assert spies.turn_off.call_count == 0
        assert spies.turn_on.call_count == 0

    new_entity.remove_thermostat()


##
## Restart (AC-007, AC-008, AC-014)
##
def restored_state(hvac_mode: str, inhibition: dict | None, requested_hvac_mode=VThermHvacMode_HEAT) -> State:
    """A previous VTherm state"""
    specific_states = {"hvac_off_reason": None}
    if inhibition is not None:
        specific_states[ATTR_INHIBITION] = inhibition
    return State(
        SWITCH_ENTITY_ID,
        hvac_mode,
        {
            "current_state": {"hvac_mode": hvac_mode, "preset": "comfort", "target_temperature": 18},
            "requested_state": {"hvac_mode": str(requested_hvac_mode), "preset": "comfort", "target_temperature": 18},
            "specific_states": specific_states,
        },
    )


def inhibition_snapshot(withdrawal_active: bool, entry_handled: bool = True, physical_stop_emitted: bool = True, policy: str = "turn_off") -> dict:
    """A persisted inhibition block"""
    return {
        "schema_version": 1,
        "provider_name": "fake_inhibition",
        "provider_status": "active" if withdrawal_active else "inactive",
        "withdrawal_active": withdrawal_active,
        "awaiting_confirmation": False,
        "effective_stop_policy": policy,
        "entry_handled": entry_handled,
        "physical_stop_emitted": physical_stop_emitted,
        "physical_stop_result": "sent" if physical_stop_emitted else None,
        "last_transition_at": "2026-10-11T10:00:00+00:00",
        "last_error_code": None,
    }


async def create_restarted_switch_vtherm(hass) -> BaseThermostat:
    """Create the over_switch VTherm after a restart (no command from the test)"""
    entity = await create_thermostat(hass, switch_entry(), SWITCH_ENTITY_ID)
    assert entity
    assert entity.is_ready
    return entity


async def test_restart_active_after_stop(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-007 - restart during an active inhibition after the stop: no second stop, still withdrawn"""
    mock_restore_cache(hass, [restored_state("off", inhibition_snapshot(True))])
    factory = FakeInhibitionFactory(status=InhibitionStatus.ACTIVE)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        provider = factory.provider
        assert provider.restored_states and provider.restored_states[0].entity_id == SWITCH_ENTITY_ID

        state = entity.inhibition_manager.state
        assert state.withdrawal_active is True
        assert state.entry_handled is True
        assert state.physical_stop_emitted is True
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert_no_command(spies)

        await send_temperature_change_event(entity, 15, datetime.now(tz=get_tz(hass)))
        await entity.async_control_heating(timestamp=entity.now)
        assert_no_command(spies)

        # exit to the restored requested state
        await provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.start_cycle.call_count == 1

    entity.remove_thermostat()


async def test_restart_active_snapshot_provider_inactive(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Restart, active snapshot but provider INACTIVE: single exit to the restored requested state"""
    mock_restore_cache(hass, [restored_state("off", inhibition_snapshot(True))])
    factory = FakeInhibitionFactory(status=InhibitionStatus.INACTIVE)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert spies.turn_off.call_count == 0
        assert spies.set_hvac_mode.call_count == 1

    entity.remove_thermostat()


async def test_restart_inactive(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-008 - restart while inactive: normal operation with the requested state"""
    mock_restore_cache(hass, [restored_state("heat", inhibition_snapshot(False, False, False))])
    factory = FakeInhibitionFactory(status=InhibitionStatus.INACTIVE)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert spies.turn_off.call_count == 0

    entity.remove_thermostat()


async def test_restart_active_snapshot_unknown_provider(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """Restart, active snapshot, provider UNKNOWN: withdrawal kept, the restored stop is not resent"""
    mock_restore_cache(hass, [restored_state("off", inhibition_snapshot(True))])
    factory = FakeInhibitionFactory(status=InhibitionStatus.UNKNOWN)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.is_inhibition_withdrawn is True
        assert entity.inhibition_manager.state.awaiting_confirmation is True
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert_no_command(spies)

    entity.remove_thermostat()


async def test_restart_after_crash_before_guard(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """AC-014 - the entry was not persisted as handled: one recovery stop (may be redundant)"""
    mock_restore_cache(hass, [restored_state("off", inhibition_snapshot(True, entry_handled=False, physical_stop_emitted=False))])
    factory = FakeInhibitionFactory(status=InhibitionStatus.ACTIVE)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.is_inhibition_withdrawn is True
        assert entity.inhibition_manager.state.entry_handled is True
        assert spies.turn_off.call_count == 1
        assert spies.start_cycle.call_count == 0

    entity.remove_thermostat()


async def test_restart_old_state_without_block_unknown(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """An old state without the block is a V0 snapshot: a new UNKNOWN provider is a safe withdrawal"""
    mock_restore_cache(hass, [restored_state("heat", None)])
    factory = FakeInhibitionFactory(status=InhibitionStatus.UNKNOWN)
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.is_inhibition_withdrawn is True
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert spies.turn_off.call_count == 1
        assert spies.start_cycle.call_count == 0

    entity.remove_thermostat()


async def test_restart_without_provider_ignores_snapshot(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """ABSENT: a persisted withdrawal is ignored, historic behavior"""
    mock_restore_cache(hass, [restored_state("off", inhibition_snapshot(True))])

    with spy_switch_commands():
        entity = await create_restarted_switch_vtherm(hass)
        assert entity.inhibition_manager.provider_name is None
        assert entity.is_inhibition_withdrawn is False
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT

    entity.remove_thermostat()


##
## Other VTherm types
##
async def test_over_climate_inhibition(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, fake_underlying_climate):
    """over_climate: one set_hvac_mode(OFF), no regulation, direct changes not followed"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
            CONF_AUTO_REGULATION_DTEMP: 0.01,
            CONF_AUTO_REGULATION_PERIOD_MIN: 0,
            CONF_REPAIR_INCORRECT_STATE: True,
        },
    )

    # fmt: off
    with patch.object(UnderlyingClimate, "set_hvac_mode", new_callable=AsyncMock, return_value=True) as set_hvac_mode, \
        patch.object(UnderlyingClimate, "set_temperature", new_callable=AsyncMock) as set_temperature, \
        patch.object(FeatureRepairIncorrectStateManager, "check_and_repair", new_callable=AsyncMock, return_value=False) as check_and_repair:
        # fmt: on
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert entity.is_over_climate
        now = datetime.now(tz=get_tz(hass))
        entity._set_now(now)
        await send_temperature_change_event(entity, 15, now)
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        set_hvac_mode.reset_mock()
        set_temperature.reset_mock()
        check_and_repair.reset_mock()

        await factory.provider.async_notify(InhibitionStatus.ACTIVE)

        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_INHIBITION
        assert set_hvac_mode.call_count == 1
        assert set_hvac_mode.call_args.args[0] == VThermHvacMode_OFF
        assert entity.inhibition_manager.state.physical_stop_result == InhibitionPhysicalStopResult.SENT

        # holding: no regulation, no repair, no command
        set_hvac_mode.reset_mock()
        await entity.async_set_temperature(temperature=22)
        for _ in range(3):
            await entity.async_control_heating(timestamp=entity.now, force=True)
            await send_temperature_change_event(entity, 14, entity.now)
        assert set_hvac_mode.call_count == 0
        assert set_temperature.call_count == 0
        assert check_and_repair.call_count == 0

        # a direct change of the underlying is not followed as a new intent
        entity._follow_underlying_temp_change = True
        await entity.underlying_changed(
            entity.underlying_entity(0),
            VThermHvacMode_COOL,
            None,
            None,
            None,
            State("climate.mock_climate", "cool"),
            State("climate.mock_climate", "off"),
        )
        assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
        assert set_hvac_mode.call_count == 0

        # exit: the intent (heat, 22°) is applied once
        await factory.provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.target_temperature == 22
        assert set_hvac_mode.call_count == 1
        assert set_hvac_mode.call_args.args[0] == VThermHvacMode_HEAT
        assert set_temperature.call_count >= 1

    entity.remove_thermostat()


async def test_over_valve_inhibition(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, fake_underlying_valve):
    """over_valve: one stop, no valve command while withdrawn, resume on exit"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_UNDERLYING_LIST: ["number.mock_valve"],
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            VThermPreset.FROST + PRESET_TEMP_SUFFIX: 7,
            VThermPreset.ECO + PRESET_TEMP_SUFFIX: 17,
            VThermPreset.COMFORT + PRESET_TEMP_SUFFIX: 19,
            VThermPreset.BOOST + PRESET_TEMP_SUFFIX: 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_DTEMP: 0.01,
            CONF_AUTO_REGULATION_PERIOD_MIN: 0,
        },
    )

    # fmt: off
    with patch.object(UnderlyingValve, "turn_off", new_callable=AsyncMock) as turn_off, \
        patch.object(UnderlyingValve, "set_valve_open_percent", new_callable=AsyncMock) as set_valve_open_percent, \
        patch.object(UnderlyingValve, "send_percent_open", new_callable=AsyncMock) as send_percent_open:
        # fmt: on
        entity = await create_thermostat(hass, entry, "climate.theovervalvemockname")
        assert entity.is_over_valve
        now = datetime.now(tz=get_tz(hass))
        entity._set_now(now)
        await send_temperature_change_event(entity, 15, now)
        await send_ext_temperature_change_event(entity, 5, now)
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert set_valve_open_percent.call_count >= 1
        for mock in (turn_off, set_valve_open_percent, send_percent_open):
            mock.reset_mock()

        await factory.provider.async_notify(InhibitionStatus.ACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert turn_off.call_count == 1

        for _ in range(3):
            await entity.async_control_heating(timestamp=entity.now, force=True)
            await send_temperature_change_event(entity, 14, entity.now)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert turn_off.call_count == 1
        assert set_valve_open_percent.call_count == 0
        assert send_percent_open.call_count == 0

        await factory.provider.async_notify(InhibitionStatus.INACTIVE)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert set_valve_open_percent.call_count >= 1

    entity.remove_thermostat()


##
## Other command paths
##
async def test_keep_alive_does_not_overwrite_direct_command(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """The switch keep-alive does not resend any command while the control is withdrawn"""
    factory = FakeInhibitionFactory()
    register_factories(hass, factory)

    with spy_switch_commands() as spies:
        entity = await create_heating_switch_vtherm(hass, switch_entry(**{CONF_HEATER_KEEP_ALIVE: 10}))
        await factory.provider.async_notify(InhibitionStatus.ACTIVE)
        reset_spies(spies)

        hass.states.async_set("switch.mock_switch", STATE_ON)
        await hass.async_block_till_done()
        under: UnderlyingSwitch = entity.underlying_entity(0)
        await under._keep_alive_callback()
        await under._keep_alive_callback()
        assert_no_command(spies)

    entity.remove_thermostat()


async def test_overpowering_does_not_command_withdrawn_vtherm(hass: HomeAssistant):
    """Power shedding sends no turn_off to a withdrawn VTherm"""
    VersatileThermostatAPI.get_vtherm_api(hass)
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    fake_vtherm.async_underlying_entity_turn_off = AsyncMock()
    power_manager = FeaturePowerManager(fake_vtherm, hass)

    type(fake_vtherm).is_inhibition_withdrawn = PropertyMock(return_value=True)
    await power_manager.set_overpowering(True)
    assert power_manager.is_overpowering_detected is True
    fake_vtherm.async_underlying_entity_turn_off.assert_not_awaited()

    await power_manager.set_overpowering(False)
    type(fake_vtherm).is_inhibition_withdrawn = PropertyMock(return_value=False)
    await power_manager.set_overpowering(True)
    fake_vtherm.async_underlying_entity_turn_off.assert_awaited_once()
