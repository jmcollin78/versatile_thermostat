# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name, wildcard-import, unused-wildcard-import, invalid-name
"""Test the HVAC mode mapper offered to the external feature managers: a plugin translates the HVAC mode sent to an
underlying climate and the one read from it. The fake device speaks `auto` for what VTherm calls `heat`, and `heat`
has no VTherm equivalent."""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant, ServiceRegistry, State
from homeassistant.components.climate import HVACAction

from vtherm_api import UNSUPPORTED_HVAC_MODE

from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate

from .commons import *
from .const import *
from .fake_plugin import FakePluginManager, FaultyConfiguredMixin, register_plugin

logging.getLogger().setLevel(logging.DEBUG)

CLIMATE = "climate.mock_climate"
DEVICE_MODES = ["off", "auto", "cool"]


class HeatAutoMapper(FakePluginManager):
    """The device calls `auto` what VTherm calls `heat`, and has no `heat`"""

    to_map = {"heat": "auto"}
    from_map = {"auto": "heat", "heat": UNSUPPORTED_HVAC_MODE}

    def to_underlying_hvac_mode(self, climate_entity_id, hvac_mode):
        self.events.append(("to", climate_entity_id, hvac_mode))
        return self.to_map.get(hvac_mode)

    def from_underlying_hvac_mode(self, climate_entity_id, underlying_hvac_mode):
        self.events.append(("from", climate_entity_id, underlying_hvac_mode))
        return self.from_map.get(underlying_hvac_mode)

    async def async_before_underlying_hvac_mode(self, climate_entity_id, hvac_mode, current_hvac_mode, command_cause):
        self.events.append(("before_hvac_mode", climate_entity_id, hvac_mode, current_hvac_mode, command_cause))


class OtherMapper(HeatAutoMapper):
    """Disagrees with the first one"""

    to_map = {"heat": "dry"}
    from_map = {"auto": "cool", "heat": UNSUPPORTED_HVAC_MODE}


class OffMapper(FakePluginManager):
    """Tries to translate `off`, and to translate to `off`"""

    def to_underlying_hvac_mode(self, climate_entity_id, hvac_mode):
        return "auto" if hvac_mode in ("off", "cool") else None

    def from_underlying_hvac_mode(self, climate_entity_id, underlying_hvac_mode):
        return "heat" if underlying_hvac_mode == "off" else ("off" if underlying_hvac_mode == "auto" else None)


class RaisingMapper(FakePluginManager):
    """Raises"""

    def to_underlying_hvac_mode(self, climate_entity_id, hvac_mode):
        raise RuntimeError("boom to")

    def from_underlying_hvac_mode(self, climate_entity_id, underlying_hvac_mode):
        raise RuntimeError("boom from")


class InvalidMapper(FakePluginManager):
    """Returns values which are not modes"""

    def to_underlying_hvac_mode(self, climate_entity_id, hvac_mode):
        return 42

    def from_underlying_hvac_mode(self, climate_entity_id, underlying_hvac_mode):
        return ["heat"]


class FaultyHeatAutoMapper(FaultyConfiguredMixin, HeatAutoMapper):
    """is_configured raises"""


async def create_vtherm(hass: HomeAssistant, device_modes=None, device_mode=HVACMode.OFF, tracking: bool = False):
    """Create an over_climate VTherm over a fake device. The plugins have to be registered before"""
    fake_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=device_mode, hvac_modes=device_modes or DEVICE_MODES)
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG)
    vtherm: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    if tracking:
        vtherm.set_follow_underlying_temp_change(True)
        vtherm._on_external_command_received()
    await hass.async_block_till_done()
    return vtherm, fake_climate


def calls(events: list, kind: str) -> list:
    """The events of a kind"""
    return [e for e in events if e[0] == kind]


def device_modes_sent(events: list) -> list:
    """The modes of the climate.set_hvac_mode calls"""
    return [e[4]["hvac_mode"] for e in events if e[0] == "service"]


def sent_modes(vtherm) -> list[str]:
    """The VTherm modes as strings"""
    return [str(mode) for mode in vtherm.vtherm_hvac_modes]


async def test_mode_list_is_in_the_vtherm_space(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The device modes are translated, the unsupported ones are removed and there is no duplicate"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"])

    assert sent_modes(vtherm) == ["off", "heat", "cool"]
    assert "auto" not in sent_modes(vtherm)
    assert [str(m) for m in vtherm.underlying_entity(0).hvac_modes] == ["off", "heat", "cool"]


async def test_mode_list_without_manager_is_unchanged(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """No plugin: the list of the device is the list of the VTherm"""
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"])

    assert vtherm._external_managers == []
    assert [str(m) for m in vtherm.underlying_entity(0).hvac_modes] == ["off", "heat", "auto", "cool"]
    assert sent_modes(vtherm) == ["off", "heat", "auto", "cool"]
    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") is None


async def test_send_the_translated_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """VTherm asks for heat, the device receives auto, and the before hook receives the mode really sent"""
    events = register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass)
    under = vtherm.underlying_entity(0)
    events.clear()

    with record_hvac_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["auto"]
    assert hass.states.get(CLIMATE).state == "auto"
    assert calls(events, "before_hvac_mode") == [("before_hvac_mode", CLIMATE, "auto", "off", None)]
    # the VTherm keeps its own mode, and the underlying too
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert under._hvac_mode == VThermHvacMode_HEAT
    # the property is in the VTherm space
    assert str(under.hvac_mode) == "heat"
    assert ("to", CLIMATE, "heat") in events
    # off is never asked to the plugin
    assert ("to", CLIMATE, "off") not in events


async def test_no_resend_and_no_repair_when_the_device_shows_the_mapped_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The device is in auto, VTherm in heat: nothing is resent, nothing is repaired"""
    events = register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass)
    under = vtherm.underlying_entity(0)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).state == "auto"
    vtherm._set_now(vtherm.now + timedelta(minutes=10))
    events.clear()

    with record_hvac_services(events):
        assert await under.set_hvac_mode(VThermHvacMode_HEAT) is False
        assert await under.check_and_repair() is False
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert device_modes_sent(events) == []
    assert calls(events, "before_hvac_mode") == []


async def test_unsupported_device_mode_is_repaired(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The device shows a mode with no VTherm equivalent: it is a drift, and the repair sends the translated mode"""
    events = register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, fake_climate = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"])
    under = vtherm.underlying_entity(0)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).state == "auto"

    # the device goes by itself in its heat mode, which VTherm does not understand
    fake_climate.set_hvac_mode("heat")
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE).state == "heat"
    assert under.hvac_mode == UNSUPPORTED_HVAC_MODE
    vtherm._set_now(vtherm.now + timedelta(minutes=10))
    events.clear()

    with record_hvac_services(events):
        assert await under.check_and_repair() is True
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["auto"]
    assert hass.states.get(CLIMATE).state == "auto"


async def test_repair_follows_the_vtherm_off(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The device in auto while VTherm is off is repaired with off, which is never translated"""
    events = register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, fake_climate = await create_vtherm(hass)
    under = vtherm.underlying_entity(0)
    fake_climate.set_hvac_mode("auto")
    await hass.async_block_till_done()
    vtherm._set_now(vtherm.now + timedelta(minutes=10))
    events.clear()

    with record_hvac_services(events):
        assert await under.check_and_repair() is True
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["off"]


async def test_initial_state_uses_the_translated_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """At startup the mode of the underlying is the translated one, and an unsupported mode is no mode"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, fake_climate = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"])
    under = vtherm.underlying_entity(0)

    # the device is on whereas VTherm is off: the check would turn it off, which is not the point here
    with patch.object(under, "set_hvac_mode", new=AsyncMock()):
        fake_climate.set_hvac_mode("auto")
        await hass.async_block_till_done()
        await under.check_initial_state()
        assert under._hvac_mode == VThermHvacMode_HEAT

        fake_climate.set_hvac_mode("heat")
        await hass.async_block_till_done()
        await under.check_initial_state()
        assert under._hvac_mode is None


async def test_tracking_does_not_adopt_the_mapped_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The device turned on by hand shows auto: VTherm follows with heat, never with auto"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass, tracking=True)
    under = vtherm.underlying_entity(0)
    under._last_off_sent_datetime = None
    old = State(CLIMATE, "off", {"hvac_action": HVACAction.OFF})
    new = State(CLIMATE, "auto", {"hvac_action": HVACAction.HEATING})

    with patch.object(vtherm, "update_states", new=AsyncMock()), patch.object(vtherm, "underlying_changed", wraps=vtherm.underlying_changed) as callback:
        await under._underlying_changed(CLIMATE, new, old)

    callback.assert_awaited_once()
    assert callback.await_args.args[1] == VThermHvacMode_HEAT
    assert vtherm.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm._underlying_tracking_attempts == 1


async def test_tracking_follows_a_translated_transition(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A change of the device to another supported mode is followed with the mode of the VTherm space"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass, tracking=True)
    under = vtherm.underlying_entity(0)
    under._last_off_sent_datetime = None
    vtherm.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    old = State(CLIMATE, "auto", {"hvac_action": HVACAction.HEATING})
    new = State(CLIMATE, "cool", {"hvac_action": HVACAction.COOLING})

    with patch.object(vtherm, "update_states", new=AsyncMock()):
        await under._underlying_changed(CLIMATE, new, old)

    assert vtherm.requested_state.hvac_mode == VThermHvacMode_COOL


async def test_tracking_ignores_an_unsupported_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A mode with no equivalent is no change: VTherm keeps its mode"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"], tracking=True)
    under = vtherm.underlying_entity(0)
    under._last_off_sent_datetime = None
    vtherm.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
    old = State(CLIMATE, "auto", {"hvac_action": HVACAction.HEATING})
    new = State(CLIMATE, "heat", {"hvac_action": HVACAction.HEATING})

    with patch.object(vtherm, "update_states", new=AsyncMock()) as update, patch.object(vtherm, "underlying_changed", wraps=vtherm.underlying_changed) as callback:
        await under._underlying_changed(CLIMATE, new, old)

    callback.assert_not_awaited()
    update.assert_not_awaited()
    assert vtherm.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm._underlying_tracking_attempts == 0


async def test_underlying_changed_of_the_vtherm_uses_translated_modes(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """ThermostatOverClimate.underlying_changed decides the transition on the translated modes, even if the filtered mode is absent"""
    register_plugin(hass, HeatAutoMapper, "mapper")
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "auto", "cool"], tracking=True)
    under = vtherm.underlying_entity(0)
    vtherm.requested_state.set_hvac_mode(VThermHvacMode_HEAT)

    # heat is unsupported: not a valid transition, even if the raw state is a valid mode
    old = State(CLIMATE, "auto", {})
    new = State(CLIMATE, "heat", {})
    with patch.object(vtherm, "update_states", new=AsyncMock()):
        await vtherm.underlying_changed(under, None, None, None, None, new, old)
    assert vtherm._underlying_tracking_attempts == 0
    assert vtherm.requested_state.hvac_mode == VThermHvacMode_HEAT

    # auto -> cool is a valid transition and the reported mode is cool
    old = State(CLIMATE, "auto", {})
    new = State(CLIMATE, "cool", {})
    with patch.object(vtherm, "update_states", new=AsyncMock()):
        await vtherm.underlying_changed(under, VThermHvacMode_COOL, None, None, None, new, old)
    assert vtherm.requested_state.hvac_mode == VThermHvacMode_COOL


async def test_off_is_never_translated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A translation from or to off is ignored"""
    register_plugin(hass, OffMapper, "mapper")
    vtherm, _ = await create_vtherm(hass)

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "off") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "off") is None
    # a translation to off is ignored
    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "cool") == "auto"
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") is None
    assert "to 'off' is not allowed" in caplog.text
    # states which are not modes are not translated either
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "unavailable") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "unknown") is None
    assert vtherm.vtherm_hvac_mode_of_underlying(CLIMATE, "off") == "off"


async def test_off_is_sent_untranslated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """VTherm turning off sends off, whatever the mapper"""
    register_plugin(hass, OffMapper, "mapper")
    events: list = []
    vtherm, fake_climate = await create_vtherm(hass)
    under = vtherm.underlying_entity(0)
    fake_climate.set_hvac_mode("cool")
    await hass.async_block_till_done()

    with record_hvac_services(events):
        await under.set_hvac_mode(VThermHvacMode_OFF)
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["off"]


async def test_two_managers_which_disagree_log_a_warning(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """The first result wins (the managers are called in the alphabetical order of their names), a warning tells the other disagrees, only once"""
    register_plugin(hass, HeatAutoMapper, "a_mapper")
    register_plugin(hass, OtherMapper, "b_other")
    vtherm, _ = await create_vtherm(hass)

    # the list of the modes asked the translation of the modes of the device when the VTherm was created
    assert caplog.text.count("translate the mode 'auto'") == 1
    caplog.clear()
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") == "heat"
    assert "translate the mode" not in caplog.text

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") == "auto"
    assert caplog.text.count("translate the mode 'heat'") == 1
    caplog.clear()
    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") == "auto"
    assert "translate the mode" not in caplog.text


async def test_two_managers_which_agree_log_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """Two managers which translate the same way do not disagree"""
    register_plugin(hass, HeatAutoMapper, "a_mapper")
    register_plugin(hass, HeatAutoMapper, "b_same")
    vtherm, _ = await create_vtherm(hass)
    caplog.clear()

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") == "auto"
    assert "differently" not in caplog.text


async def test_the_first_manager_which_translates_wins(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager which does not translate (None) leaves the mode to the next one"""

    class Silent(FakePluginManager):
        """Never translates"""

        def to_underlying_hvac_mode(self, climate_entity_id, hvac_mode):
            return None

        def from_underlying_hvac_mode(self, climate_entity_id, underlying_hvac_mode):
            return None

    register_plugin(hass, Silent, "a_silent")
    register_plugin(hass, HeatAutoMapper, "b_mapper")
    vtherm, _ = await create_vtherm(hass)

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") == "auto"
    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "cool") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "heat") == UNSUPPORTED_HVAC_MODE


async def test_exception_is_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A failing mapper is logged: no translation and the other managers are consulted"""
    register_plugin(hass, RaisingMapper, "a_raising")
    register_plugin(hass, HeatAutoMapper, "b_mapper")
    vtherm, _ = await create_vtherm(hass)
    caplog.clear()

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") == "auto"
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") == "heat"
    assert "boom to" in caplog.text
    assert "boom from" in caplog.text


async def test_failing_mapper_alone_changes_nothing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """With a failing mapper the VTherm works as without plugin"""
    register_plugin(hass, RaisingMapper, "raising")
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "cool"])
    events: list = []

    with record_hvac_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["heat"]
    assert hass.states.get(CLIMATE).state == "heat"
    assert sent_modes(vtherm) == ["off", "heat", "cool"]


async def test_invalid_values_are_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A result which is not a string is logged and ignored"""
    register_plugin(hass, InvalidMapper, "invalid")
    vtherm, _ = await create_vtherm(hass)
    caplog.clear()

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") is None
    assert "returned an invalid HVAC mode" in caplog.text


async def test_unsupported_to_the_device_is_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """UNSUPPORTED_HVAC_MODE has no meaning when sending a mode"""

    class ToUnsupported(HeatAutoMapper):
        """Asks for the unsupported mode"""

        to_map = {"heat": UNSUPPORTED_HVAC_MODE}

    register_plugin(hass, ToUnsupported, "mapper")
    vtherm, _ = await create_vtherm(hass)
    caplog.clear()

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") is None
    assert "is not allowed" in caplog.text


async def test_unconfigured_and_faulty_is_configured_are_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A manager which is not configured, or whose is_configured raises, is not consulted"""
    register_plugin(hass, HeatAutoMapper, "a_unconfigured", configured=False)
    events = register_plugin(hass, FaultyHeatAutoMapper, "b_faulty")
    vtherm, _ = await create_vtherm(hass)
    caplog.clear()

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") is None
    assert calls(events, "to") == []
    assert "Error while reading is_configured" in caplog.text
    assert sent_modes(vtherm) == ["off", "auto", "cool"]


async def test_manager_without_the_mapper_is_not_consulted(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager which does not implement the contract changes nothing"""
    register_plugin(hass, FakePluginManager, "plain")
    vtherm, _ = await create_vtherm(hass)

    assert vtherm.map_hvac_mode_to_underlying(CLIMATE, "heat") is None
    assert vtherm.map_hvac_mode_from_underlying(CLIMATE, "auto") is None
    assert vtherm.vtherm_hvac_mode_of_underlying(CLIMATE, "auto") == "auto"
    assert sent_modes(vtherm) == ["off", "auto", "cool"]


async def test_no_manager_keeps_the_raw_behaviour(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without plugin the modes are the raw ones, sending and reading"""
    vtherm, _ = await create_vtherm(hass, device_modes=["off", "heat", "cool"])
    under = vtherm.underlying_entity(0)
    events: list = []

    with record_hvac_services(events):
        await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert device_modes_sent(events) == ["heat"]
    assert under.hvac_mode == "heat"
    assert under._hvac_mode == VThermHvacMode_HEAT
    assert vtherm.vtherm_hvac_mode_of_underlying(CLIMATE, "heat") == "heat"


class record_hvac_services:  # pylint: disable=invalid-name
    """Record the climate.set_hvac_mode calls in a shared list, as ("service", domain, service, entity_ids, data)"""

    def __init__(self, events: list) -> None:
        self.events = events
        self._patch = None

    def __enter__(self):
        original = ServiceRegistry.async_call
        events = self.events

        async def wrapper(registry, domain, service, service_data=None, blocking=False, context=None, target=None, return_response=False):
            if (domain, service) == ("climate", "set_hvac_mode"):
                ids = (target or {}).get("entity_id") or (service_data or {}).get("entity_id")
                events.append(("service", domain, service, ids, dict(service_data or {})))
            return await original(registry, domain, service, service_data, blocking, context, target, return_response)

        self._patch = patch.object(ServiceRegistry, "async_call", wrapper)
        self._patch.__enter__()
        return self

    def __exit__(self, *args):
        return self._patch.__exit__(*args)
