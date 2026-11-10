# pylint: disable=unused-argument, line-too-long, protected-access
"""Test the FeatureRepairIncorrectStateManager"""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import PropertyMock, AsyncMock, MagicMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_repair_incorrect_state_manager import (
    FeatureRepairIncorrectStateManager,
)
from custom_components.versatile_thermostat.const import (
    CONF_REPAIR_INCORRECT_STATE,
    REPAIR_MAX_ATTEMPTS,
    REPAIR_MIN_DELAY_AFTER_INIT_SEC,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

MANAGER_LOGGER = "custom_components.versatile_thermostat.feature_repair_incorrect_state_manager"


async def test_repair_manager_pause_and_retry_logs(hass: HomeAssistant, caplog):
    """When an underlying never converges, repairs are paused for
    REPAIR_MAX_ATTEMPTS - 1 cycles and then retried. The logs must describe
    that pause/retry and must not claim that repairs were stopped."""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).is_ready = PropertyMock(return_value=True)

    # An underlying whose state never matches the desired state
    underlying = MagicMock()
    underlying.entity_id = "switch.the_heater"
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


async def test_switch_repair_does_not_turn_on_when_vtherm_off():
    """Issue 2219: a stale on-part must not switch the device on while the VTherm is off"""
    thermostat = MagicMock()
    switch = MagicMock(spec=UnderlyingSwitch)
    switch._thermostat = thermostat
    switch._is_on_part_running = True
    switch.turn_on = AsyncMock()
    switch.turn_off = AsyncMock()
    is_device_active = PropertyMock(return_value=False)
    type(switch).is_device_active = is_device_active

    try:
        # VTherm off, device off: nothing to do
        thermostat.is_on = False
        assert await UnderlyingSwitch.check_and_repair(switch) is False
        switch.turn_on.assert_not_called()

        # VTherm off, device on: repair turns it off
        is_device_active.return_value = True
        assert await UnderlyingSwitch.check_and_repair(switch) is True
        switch.turn_on.assert_not_called()
        switch.turn_off.assert_called_once()

        # VTherm on: the on-part is still repaired as before
        thermostat.is_on = True
        is_device_active.return_value = False
        assert await UnderlyingSwitch.check_and_repair(switch) is True
        switch.turn_on.assert_called_once()
    finally:
        del type(switch).is_device_active
