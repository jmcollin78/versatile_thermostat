# pylint: disable=unused-argument, line-too-long, protected-access
"""Test the FeatureRepairIncorrectStateManager"""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import PropertyMock, AsyncMock, MagicMock, patch

import pytest

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_repair_incorrect_state_manager import (
    FeatureRepairIncorrectStateManager,
)
from custom_components.versatile_thermostat.const import (
    CONF_REPAIR_INCORRECT_STATE,
    REPAIR_MAX_ATTEMPTS,
    REPAIR_MIN_DELAY_AFTER_INIT_SEC,
)
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate, UnderlyingSwitch, UnderlyingValve, UnderlyingValveRegulation
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

MANAGER_LOGGER = "custom_components.versatile_thermostat.feature_repair_incorrect_state_manager"


@pytest.mark.parametrize("hvac_mode", [HVACMode.OFF, HVACMode.HEAT])
@pytest.mark.parametrize("on_percent", [0.0, 0.000001, 0.5])
@pytest.mark.parametrize("commanded_on", [False, True])
async def test_switch_repair_requires_current_demand_for_on(hass: HomeAssistant, hvac_mode, on_percent, commanded_on):
    """A stale ON state cannot restart a heater without a current heating demand."""
    thermostat = MagicMock(is_inversed=False)
    thermostat.hvac_mode = hvac_mode
    thermostat.on_percent = on_percent
    underlying = UnderlyingSwitch(hass, thermostat, "climate.pellet_stove", 0, "set_hvac_mode/hvac_mode:heat", "set_hvac_mode/hvac_mode:off")
    underlying._is_on_part_running = commanded_on
    underlying._is_initialized = True
    underlying._state_manager.get_state = MagicMock(return_value=State(underlying.entity_id, "off" if commanded_on else "heat"))
    expected_repair = not commanded_on or (hvac_mode != HVACMode.OFF and on_percent > 0)

    with patch.object(underlying, "turn_on", new_callable=AsyncMock) as turn_on, patch.object(underlying, "turn_off", new_callable=AsyncMock) as turn_off:
        assert await underlying.check_and_repair() is expected_repair
        assert turn_on.await_count == int(expected_repair and commanded_on)
        assert turn_off.await_count == int(expected_repair and not commanded_on)


@pytest.mark.parametrize("entity_type", ["switch", "climate", "valve", "valve_regulation"])
@pytest.mark.parametrize("age, eligible", [(0, False), (9.999, False), (10, True), (10.001, True)])
async def test_repair_manager_command_grace(hass: HomeAssistant, caplog, age, eligible, entity_type):
    """The manager skips the underlying check until its command is ten seconds old."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock(spec=BaseThermostat)
    thermostat.name = "thermostat"
    thermostat.is_ready = True
    thermostat.now = now
    underlying = MagicMock()
    underlying.entity_id = f"{entity_type}.heater"
    underlying.last_command_sent_datetime = now - timedelta(seconds=age)
    underlying.check_and_repair = AsyncMock(return_value=True)
    thermostat.all_underlying_entities = [underlying]
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    manager._ready_start_time = now - timedelta(seconds=REPAIR_MIN_DELAY_AFTER_INIT_SEC + 1)
    caplog.set_level(logging.WARNING, logger=MANAGER_LOGGER)

    assert await manager.check_and_repair() is eligible
    assert underlying.check_and_repair.await_count == int(eligible)
    assert manager._consecutive_repair_count == int(eligible)
    assert bool([record for record in caplog.records if record.name == MANAGER_LOGGER and record.levelno == logging.WARNING]) is eligible


async def test_repair_manager_independent_commands_and_counters(hass: HomeAssistant):
    """Recent commands skip only their own object and leave global accounting intact."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock(spec=BaseThermostat)
    thermostat.name = "thermostat"
    thermostat.is_ready = True
    thermostat.now = now
    underlyings = [MagicMock(entity_id=name, check_and_repair=AsyncMock(return_value=True)) for name in ("switch.heater", "climate.heater", "number.valve", "number.regulation")]
    for underlying, age in zip(underlyings, (0, 10, 9, 20)):
        underlying.last_command_sent_datetime = now - timedelta(seconds=age)
    thermostat.all_underlying_entities = underlyings
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    manager._ready_start_time = now - timedelta(seconds=REPAIR_MIN_DELAY_AFTER_INIT_SEC + 1)

    assert await manager.check_and_repair() is True
    assert [underlying.check_and_repair.await_count for underlying in underlyings] == [0, 1, 0, 1]
    assert manager._consecutive_repair_count == 1
    for underlying in underlyings:
        underlying.last_command_sent_datetime = now
    assert await manager.check_and_repair() is False
    assert manager._consecutive_repair_count == 0
    thermostat.now = now + timedelta(seconds=10)
    assert await manager.check_and_repair() is True
    assert [underlying.check_and_repair.await_count for underlying in underlyings] == [1, 2, 1, 2]
    assert manager._consecutive_repair_count == 1


@pytest.mark.parametrize("kind", ["switch", "climate", "valve", "regulation"])
@pytest.mark.parametrize("age, eligible", [(0, False), (9.999, False), (10, True), (10.001, True)])
async def test_real_underlying_repair_grace_and_direct_check(hass: HomeAssistant, kind, age, eligible):
    """The manager gates real underlying checks; direct checks retain their corrections."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock()
    thermostat.name = "thermostat"
    thermostat.now = now
    thermostat.is_ready = True
    thermostat.is_inversed = False
    thermostat.hvac_mode = HVACMode.HEAT
    thermostat.vtherm_hvac_mode = VThermHvacMode_HEAT
    thermostat.get_underlying_hvac_mode.side_effect = lambda value: value
    thermostat.power_manager.check_power_available = AsyncMock(return_value=(True, None))
    if kind == "switch":
        underlying = UnderlyingSwitch(hass, thermostat, "switch.test", 0)
        underlying._is_on_part_running = True
        state = State(underlying.entity_id, "off")
    elif kind == "climate":
        underlying = UnderlyingClimate(hass, thermostat, "climate.test")
        state = State(underlying.entity_id, HVACMode.OFF)
    elif kind == "valve":
        underlying = UnderlyingValve(hass, thermostat, "number.test")
        state = State(underlying.entity_id, "0")
    else:
        climate = UnderlyingClimate(hass, thermostat, "climate.test")
        underlying = UnderlyingValveRegulation(hass, thermostat, "number.test", "number.closing", climate)
        state = State(underlying.entity_id, "0")
    underlying._is_initialized = True
    underlying._state_manager.get_state = MagicMock(return_value=state)
    underlying._last_command_sent_datetime = now - timedelta(seconds=age)
    if kind in ("valve", "regulation"):
        underlying._hvac_mode = VThermHvacMode_HEAT
        underlying._percent_open = 40
        underlying._last_sent_opening_value = 40
    thermostat.all_underlying_entities = [underlying]
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    manager._ready_start_time = now - timedelta(seconds=31)
    with (
        patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service,
        patch("custom_components.versatile_thermostat.underlyings.async_call_later"),
        patch.object(underlying, "check_and_repair", new=AsyncMock(wraps=underlying.check_and_repair)) as check,
    ):
        assert await manager.check_and_repair() is eligible
        assert check.await_count == int(eligible)
        assert service.await_count == (2 if kind == "regulation" else 1) * int(eligible)
        if not eligible:
            assert await underlying.check_and_repair() is True
            assert service.await_count == (2 if kind == "regulation" else 1)


@pytest.mark.parametrize("kind", ["switch", "climate", "valve", "regulation"])
@pytest.mark.parametrize("observed", [None, "unknown", "unavailable"])
async def test_repair_preserves_missing_and_unavailable_state_behavior(hass: HomeAssistant, kind, observed):
    """The manager leaves each underlying's existing unavailable-state behavior intact."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock(name="thermostat", now=now, is_ready=True, is_inversed=False)
    thermostat.hvac_mode = HVACMode.HEAT
    thermostat.vtherm_hvac_mode = VThermHvacMode_HEAT
    thermostat.get_underlying_hvac_mode.side_effect = lambda value: value
    thermostat.power_manager.check_power_available = AsyncMock(return_value=(True, None))
    if kind == "switch":
        underlying = UnderlyingSwitch(hass, thermostat, "switch.test", 0)
        underlying._is_on_part_running = True
    elif kind == "climate":
        underlying = UnderlyingClimate(hass, thermostat, "climate.test")
    elif kind == "valve":
        underlying = UnderlyingValve(hass, thermostat, "number.test")
    else:
        climate = UnderlyingClimate(hass, thermostat, "climate.test")
        underlying = UnderlyingValveRegulation(hass, thermostat, "number.test", None, climate)
    underlying._is_initialized = True
    underlying._state_manager.get_state = MagicMock(return_value=State(underlying.entity_id, observed) if observed is not None else None)
    if kind in ("valve", "regulation"):
        underlying._hvac_mode = VThermHvacMode_HEAT
        underlying._percent_open = 40
        underlying._last_sent_opening_value = 40
    thermostat.all_underlying_entities = [underlying]
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    manager._ready_start_time = now - timedelta(seconds=31)
    expected_repair = kind == "climate" and observed is not None
    with patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service, patch("custom_components.versatile_thermostat.underlyings.async_call_later"):
        assert await manager.check_and_repair() is expected_repair
        assert service.await_count == int(expected_repair)


async def test_repair_manager_readiness_disabled_and_pause(hass: HomeAssistant):
    """Disabled, startup and pause paths retain their existing accounting and checks."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock(spec=BaseThermostat)
    thermostat.name = "thermostat"
    thermostat.now = now
    thermostat.is_ready = True
    underlying = MagicMock(entity_id="switch.test", last_command_sent_datetime=now, check_and_repair=AsyncMock(return_value=True))
    thermostat.all_underlying_entities = [underlying]
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: False})
    assert await manager.check_and_repair() is False
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    thermostat.is_ready = False
    assert await manager.check_and_repair() is False
    assert manager._ready_start_time is None
    thermostat.is_ready = True
    assert await manager.check_and_repair() is False
    assert await manager.check_and_repair() is False
    manager._ready_start_time = now - timedelta(seconds=31)
    manager._consecutive_repair_count = REPAIR_MAX_ATTEMPTS
    assert await manager.check_and_repair() is False
    assert manager._consecutive_repair_count == REPAIR_MAX_ATTEMPTS + 1
    underlying.check_and_repair.assert_not_awaited()


async def test_repair_manager_pause_and_retry_logs(hass: HomeAssistant, caplog):
    """When an underlying never converges, repairs are paused for
    REPAIR_MAX_ATTEMPTS - 1 cycles and then retried. The logs must describe
    that pause/retry and must not claim that repairs were stopped."""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).is_ready = PropertyMock(return_value=True)
    fake_vtherm.now = datetime.now(timezone.utc)

    # An underlying whose state never matches the desired state
    underlying = MagicMock()
    underlying.entity_id = "switch.the_heater"
    underlying.last_command_sent_datetime = fake_vtherm.now - timedelta(seconds=10)
    underlying.check_and_repair = AsyncMock(return_value=True)
    type(fake_vtherm).all_underlying_entities = PropertyMock(return_value=[underlying])

    manager = FeatureRepairIncorrectStateManager(fake_vtherm, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    # Skip the start-up delay
    manager._ready_start_time = datetime.now(timezone.utc) - timedelta(seconds=REPAIR_MIN_DELAY_AFTER_INIT_SEC + 1)

    caplog.set_level(logging.DEBUG, logger=MANAGER_LOGGER)

    # 1. REPAIR_MAX_ATTEMPTS consecutive repairs
    for _ in range(REPAIR_MAX_ATTEMPTS):
        assert await manager.check_and_repair() is True
    assert underlying.check_and_repair.await_count == REPAIR_MAX_ATTEMPTS

    # 2. repairs are paused for REPAIR_MAX_ATTEMPTS - 1 cycles
    for skipped in range(1, REPAIR_MAX_ATTEMPTS):
        caplog.clear()
        assert await manager.check_and_repair() is False
        assert underlying.check_and_repair.await_count == REPAIR_MAX_ATTEMPTS
        pause_records = [r for r in caplog.records if r.name == MANAGER_LOGGER and r.levelno == logging.ERROR]
        assert len(pause_records) == 1
        message = pause_records[0].getMessage()
        assert "paused" in message
        assert f"{skipped}/{REPAIR_MAX_ATTEMPTS - 1}" in message
        assert "Stopped attempting" not in message

    # 3. repairs are retried on the next cycle, without a pause message
    caplog.clear()
    assert await manager.check_and_repair() is True
    assert underlying.check_and_repair.await_count == REPAIR_MAX_ATTEMPTS + 1
    records = [r for r in caplog.records if r.name == MANAGER_LOGGER]
    assert not [r for r in records if r.levelno == logging.ERROR]
    assert any("retrying repairs" in r.getMessage() for r in records)
