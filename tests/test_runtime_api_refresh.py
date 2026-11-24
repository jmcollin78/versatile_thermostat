# pylint: disable=unused-argument, line-too-long, protected-access, redefined-outer-name, wildcard-import, unused-wildcard-import
"""Tests of the runtime API members consumed by external feature managers.

Covers the immediate state-refresh request and the valve-regulation fact
aliased under the protocol name (``has_valve_regulation``).
"""

import logging
from unittest.mock import AsyncMock, PropertyMock, patch

from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate_valve import (
    ThermostatOverClimateValve,
)

from .commons import *
from .const import *
from .test_inhibition import heating_climate_valve_vtherm, heating_switch_vtherm

logging.getLogger().setLevel(logging.DEBUG)


##
## Immediate state refresh request
##
async def test_request_state_refresh_forces_a_recalculation(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """The request marks the requested state as changed and forces the recalculation."""
    vtherm: BaseThermostat = await heating_switch_vtherm(hass, fake_temp_sensor)
    assert vtherm.is_ready is True

    # The state is settled: no pending change before the request
    vtherm.requested_state.reset_changed()
    assert vtherm.requested_state.is_changed is False

    with patch.object(vtherm, "update_states", AsyncMock(return_value=True)) as mock_update:
        await vtherm.async_request_state_refresh()

    mock_update.assert_awaited_once_with(force=True)
    assert vtherm.requested_state.is_changed is True


async def test_request_state_refresh_is_harmless_when_nothing_changed(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A refresh on an already settled thermostat completes without error and publishes the same state."""
    vtherm: BaseThermostat = await heating_switch_vtherm(hass, fake_temp_sensor)

    before_state = hass.states.get(vtherm.entity_id)
    before_hvac_mode = vtherm.vtherm_hvac_mode
    before_target = vtherm.target_temperature

    await vtherm.async_request_state_refresh()
    await hass.async_block_till_done()

    after_state = hass.states.get(vtherm.entity_id)
    assert after_state is not None
    assert after_state.state == before_state.state
    assert vtherm.vtherm_hvac_mode == before_hvac_mode
    assert vtherm.target_temperature == before_target
    assert vtherm.requested_state.is_changed is False


async def test_request_state_refresh_is_a_noop_when_not_ready(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A thermostat that is not ready logs and returns without raising or publishing."""
    vtherm: BaseThermostat = await heating_switch_vtherm(hass, fake_temp_sensor)

    published_before = hass.states.get(vtherm.entity_id)

    with (
        patch.object(type(vtherm), "is_ready", new_callable=PropertyMock, return_value=False),
        patch.object(vtherm, "update_states", AsyncMock(return_value=True)) as mock_update,
        patch("custom_components.versatile_thermostat.base_thermostat._LOGGER") as mock_logger,
    ):
        await vtherm.async_request_state_refresh()

    mock_update.assert_not_awaited()
    assert vtherm.requested_state.is_changed is False
    assert mock_logger.debug.called
    assert "not ready" in " ".join(str(call.args[0]) for call in mock_logger.debug.call_args_list)
    assert hass.states.get(vtherm.entity_id) == published_before


##
## Valve regulation fact
##
async def test_has_valve_regulation_is_true_for_a_valve_regulated_thermostat(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A valve-regulated over_climate thermostat reports the valve fact under the protocol name."""
    vtherm, _, _, _ = await heating_climate_valve_vtherm(hass, fake_temp_sensor)

    assert isinstance(vtherm, ThermostatOverClimateValve)
    assert vtherm.have_valve_regulation is True
    assert vtherm.has_valve_regulation is True


async def test_has_valve_regulation_is_false_without_valve_regulation(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):
    """A thermostat without valve regulation reports False under the protocol name."""
    vtherm: BaseThermostat = await heating_switch_vtherm(hass, fake_temp_sensor)

    assert vtherm.have_valve_regulation is False
    assert vtherm.has_valve_regulation is False
