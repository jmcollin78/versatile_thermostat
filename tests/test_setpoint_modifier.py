# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test that an external feature manager can adjust the regulated temperature of an over climate thermostat """
import logging
import math
from datetime import datetime
from unittest.mock import PropertyMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.base_manager import BaseFeatureManager
from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate
from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

CONFIG = PARTIAL_CLIMATE_NOT_REGULATED_CONFIG | {CONF_AUTO_REGULATION_PERIOD_MIN: 1, CONF_AUTO_REGULATION_DTEMP: 0.5}


_UNSET = object()


class FakeSetpointModifier(BaseFeatureManager):
    """An external feature manager which lowers the regulated temperature"""

    def __init__(
        self, thermostat, configured: bool = True, delta: float = -1.0, fail: bool = False, result_is_none: bool = False, result=_UNSET, configured_fails: bool = False
    ) -> None:
        super().__init__(thermostat, thermostat.hass, "fake_setpoint_modifier")
        self.configured = configured
        self.delta = delta
        self.fail = fail
        self.result_is_none = result_is_none
        self.result = result
        self.configured_fails = configured_fails
        self.calls: list[tuple[float, float, str | None]] = []

    def post_init(self, entry_infos) -> None:
        """Nothing to read from the entry"""

    async def start_listening(self) -> None:
        """Nothing to listen to"""

    async def refresh_state(self) -> bool:
        """Nothing to refresh"""
        return False

    def adjust_regulated_temperature(self, desired: float, regulation_step: float, command_cause: str | None) -> float | None:
        """Record the call and return the adjusted temperature"""
        self.calls.append((desired, regulation_step, command_cause))
        if self.fail:
            raise RuntimeError("faulty plugin")
        if self.result is not _UNSET:
            return self.result
        return None if self.result_is_none else desired + self.delta

    @property
    def is_configured(self) -> bool:
        """The manager is configured when the test says so"""
        if self.configured_fails:
            raise RuntimeError("faulty is_configured")
        return self.configured

    @property
    def is_detected(self) -> bool:
        """The manager never detects anything"""
        return False


class FakeSetpointModifierFactory:
    """The factory of the fake external feature manager. It keeps the managers it creates"""

    name = "fake_setpoint_modifier"

    def __init__(self, **options) -> None:
        self.options = options
        self.managers: list[FakeSetpointModifier] = []

    def supports(self, thermostat) -> bool:
        """Only over climate thermostats are supported"""
        return getattr(thermostat, "is_over_climate", False)

    def create(self, thermostat) -> FakeSetpointModifier:
        """Create the fake manager"""
        manager = FakeSetpointModifier(thermostat, **self.options)
        self.managers.append(manager)
        return manager


async def create_modified_thermostat(hass: HomeAssistant, **options) -> tuple[ThermostatOverClimate, FakeSetpointModifierFactory, datetime]:
    """Register the fake plugin, create the thermostat and return it with the factory and the simulated date"""
    factory = FakeSetpointModifierFactory(**options)
    VersatileThermostatAPI.get_vtherm_api(hass).register_feature_manager(factory)

    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=CONFIG)
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert isinstance(entity, ThermostatOverClimate)
    await wait_for_local_condition(lambda: entity.is_ready is True)
    now = datetime.now(tz=get_tz(hass))
    entity._set_now(now)
    await send_temperature_change_event(entity, 18, now)
    await entity.async_set_temperature(temperature=21)
    return entity, factory, now


@pytest.fixture(name="unregister_fake_modifier", autouse=True)
def unregister_fake_modifier_fixture(hass: HomeAssistant):
    """Remove the fake plugin after each test"""
    yield
    VersatileThermostatAPI.get_vtherm_api(hass).unregister_feature_manager("fake_setpoint_modifier")


async def test_modifier_adjusts_regulated_temperature(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """The temperature sent to the device is the one returned by the plugin"""
    entity, factory, _ = await create_modified_thermostat(hass)
    manager = factory.managers[0]

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 20
    assert entity.regulated_target_temp == 20
    # The plugin receives the regulated temperature, the rounding step and the command cause
    desired, regulation_step, command_cause = manager.calls[-1]
    assert desired == 21
    assert regulation_step == 0.5
    assert command_cause is None

    entity.remove_thermostat()


async def test_modifier_not_configured_is_ignored(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A plugin which is not configured for this thermostat changes nothing"""
    entity, factory, _ = await create_modified_thermostat(hass, configured=False)

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21
    assert not factory.managers[0].calls

    entity.remove_thermostat()


async def test_modifier_returning_none_keeps_temperature(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A plugin which returns nothing leaves the regulated temperature as it is"""
    entity, _, _ = await create_modified_thermostat(hass, result_is_none=True)

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21

    entity.remove_thermostat()


async def test_faulty_modifier_does_not_break_regulation(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, caplog):
    """The error of a plugin is logged and the regulation goes on"""
    entity, _, _ = await create_modified_thermostat(hass, fail=True)

    with caplog.at_level(logging.ERROR):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21
    assert "Error while adjusting the regulated temperature" in caplog.text

    entity.remove_thermostat()


async def _async_result(*_args):
    """A modifier which wrongly is a coroutine function"""
    return 20.0


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf, "20", True, [20]])
async def test_invalid_result_is_ignored(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, caplog, invalid):
    """A result which is not a finite number is ignored: the regulated temperature is sent as it is"""
    entity, _, _ = await create_modified_thermostat(hass, result=invalid)

    with caplog.at_level(logging.WARNING):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21
    assert "returned an invalid regulated temperature" in caplog.text

    entity.remove_thermostat()


async def test_coroutine_result_is_ignored(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, caplog):
    """A modifier written as a coroutine function is ignored, without a never awaited warning"""
    entity, factory, _ = await create_modified_thermostat(hass)
    factory.managers[0].adjust_regulated_temperature = _async_result

    with caplog.at_level(logging.WARNING):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21
    assert "returned an invalid regulated temperature" in caplog.text

    entity.remove_thermostat()


async def test_is_configured_failure_is_isolated(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, caplog):
    """A plugin whose is_configured raises does not break the regulation"""
    entity, _, _ = await create_modified_thermostat(hass, configured_fails=True)

    with caplog.at_level(logging.ERROR):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert entity._underlyings[0].last_sent_temperature == 21
    assert "Error while reading is_configured" in caplog.text

    entity.remove_thermostat()


async def test_several_modifiers_are_applied_in_order(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """Each modifier receives the value returned by the previous one, in the order of registration. A failing one keeps the value it received"""
    entity, factory, _ = await create_modified_thermostat(hass)
    first = factory.managers[0]
    second = FakeSetpointModifier(entity, delta=-0.5)
    third = FakeSetpointModifier(entity, fail=True)
    entity._external_managers.extend([second, third])

    assert entity._adjust_regulated_temperature(21, 0.5, None) == 19.5
    assert [call[0] for call in first.calls] == [21]
    assert [call[0] for call in second.calls] == [20]
    assert [call[0] for call in third.calls] == [19.5]

    entity.remove_thermostat()


async def test_temperature_not_sent_before_mode_when_device_is_on(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A device which already runs does not need the temperature ahead of its mode: only a device which is off does"""
    entity, _, _ = await create_modified_thermostat(hass)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    with patch.object(UnderlyingClimate, "set_temperature") as mock_set_temperature, patch.object(UnderlyingClimate, "hvac_mode", new_callable=PropertyMock) as mock_mode:
        mock_mode.return_value = VThermHvacMode_HEAT
        await entity._before_underlying_hvac_mode_change(None)
        mock_set_temperature.assert_not_called()

        mock_mode.return_value = VThermHvacMode_OFF
        await entity._before_underlying_hvac_mode_change(None)
        mock_set_temperature.assert_called_once()

    entity.remove_thermostat()


async def record_commands(entity: ThermostatOverClimate, mode) -> list[tuple[str, float | str]]:
    """Switch the thermostat on and return the commands sent to the underlying, in order"""
    commands: list[tuple[str, float | str]] = []
    original_set_temperature = UnderlyingClimate.set_temperature
    original_set_hvac_mode = UnderlyingClimate.set_hvac_mode

    async def spy_set_temperature(self, temperature, *args, **kwargs):
        commands.append(("temperature", temperature))
        return await original_set_temperature(self, temperature, *args, **kwargs)

    async def spy_set_hvac_mode(self, hvac_mode, *args, **kwargs):
        commands.append(("hvac_mode", hvac_mode))
        return await original_set_hvac_mode(self, hvac_mode, *args, **kwargs)

    with patch.object(UnderlyingClimate, "set_temperature", spy_set_temperature), patch.object(UnderlyingClimate, "set_hvac_mode", spy_set_hvac_mode):
        await entity.async_set_hvac_mode(mode)
        await entity.hass.async_block_till_done()
    return commands


async def test_modifier_temperature_sent_before_mode(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """With a plugin, the adjusted temperature reaches the device before it is switched on"""
    entity, _, _ = await create_modified_thermostat(hass)

    commands = await record_commands(entity, VThermHvacMode_HEAT)

    assert commands[0] == ("temperature", 20)
    assert commands[1][0] == "hvac_mode"
    # Nothing sends the unadjusted temperature
    assert ("temperature", 21) not in commands

    entity.remove_thermostat()


async def test_without_modifier_mode_is_sent_first(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """Without a plugin the order of the commands is not changed"""
    entity, _, _ = await create_modified_thermostat(hass, configured=False)

    commands = await record_commands(entity, VThermHvacMode_HEAT)

    assert commands[0][0] == "hvac_mode"

    entity.remove_thermostat()


async def test_modifier_not_called_before_mode_for_underlying_tracking(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A device switched on by the user already runs: no temperature is sent ahead of its mode"""
    entity, _, _ = await create_modified_thermostat(hass)

    with patch.object(UnderlyingClimate, "set_temperature") as mock_set_temperature:
        # The mode change comes from the device
        entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
        await entity._before_underlying_hvac_mode_change(COMMAND_CAUSE_UNDERLYING_TRACKING)

    mock_set_temperature.assert_not_called()

    entity.remove_thermostat()
