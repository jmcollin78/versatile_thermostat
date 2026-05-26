# pylint: disable=missing-function-docstring, protected-access

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import State

from custom_components.versatile_thermostat.underlyings import UnderlyingClimate
from custom_components.versatile_thermostat.vtherm_hvac_mode import (
    VThermHvacMode_COOL,
    VThermHvacMode_HEAT,
    VThermHvacMode_OFF,
)


def _make_thermostat(hvac_mode, target_temperature, current_temperature):
    thermostat = MagicMock()
    thermostat.vtherm_hvac_mode = hvac_mode
    thermostat.target_temperature = target_temperature
    thermostat.current_temperature = current_temperature
    thermostat.now = None
    thermostat.init_underlyings_completed = AsyncMock()
    thermostat.underlying_changed = AsyncMock()

    power_manager = MagicMock()
    power_manager.add_power_consumption_to_central_power_manager = MagicMock()
    power_manager.sub_power_consumption_to_central_power_manager = MagicMock()
    power_manager.check_power_available = AsyncMock(return_value=(True, None))
    thermostat.power_manager = power_manager
    return thermostat


@pytest.mark.asyncio
async def test_underlying_climate_turn_off_delegates_to_hvac_off(hass):
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    thermostat = _make_thermostat(VThermHvacMode_COOL, 20, 26)
    under = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    under.set_hvac_mode = AsyncMock()

    await under.turn_off()

    under.set_hvac_mode.assert_awaited_once_with(VThermHvacMode_OFF)


@pytest.mark.asyncio
async def test_underlying_climate_turn_on_restores_vtherm_mode(hass):
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    thermostat = _make_thermostat(VThermHvacMode_HEAT, 22, 18)
    under = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    under.set_hvac_mode = AsyncMock()

    await under.turn_on()

    under.set_hvac_mode.assert_awaited_once_with(VThermHvacMode_HEAT)


@pytest.mark.asyncio
async def test_underlying_climate_repair_turns_idle_cool_mode_off(hass):
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    thermostat = _make_thermostat(VThermHvacMode_COOL, 25, 23)
    under = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    under.turn_off = AsyncMock()
    under.turn_on = AsyncMock()
    under.state_manager.get_state = MagicMock(
        return_value=State(
            "climate.test",
            HVACMode.COOL,
            {
                "hvac_action": HVACAction.IDLE,
                "temperature": 25,
                "current_temperature": 23,
            },
        )
    )

    repaired = await under.check_and_repair()

    assert repaired is True
    under.turn_off.assert_awaited_once()
    under.turn_on.assert_not_awaited()


@pytest.mark.asyncio
async def test_underlying_climate_repair_turns_off_climate_back_on_when_demand_returns(hass):
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    thermostat = _make_thermostat(VThermHvacMode_COOL, 20, 26)
    under = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    under.turn_off = AsyncMock()
    under.turn_on = AsyncMock()
    under.state_manager.get_state = MagicMock(
        return_value=State(
            "climate.test",
            HVACMode.OFF,
            {
                "hvac_action": HVACAction.OFF,
                "temperature": 20,
                "current_temperature": 26,
            },
        )
    )

    repaired = await under.check_and_repair()

    assert repaired is True
    under.turn_on.assert_awaited_once()
    under.turn_off.assert_not_awaited()
