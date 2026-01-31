
# tests/test_energy_bug.py

import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.prop_algorithm import PROPORTIONAL_FUNCTION_TPI
from .commons import *

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_energy_increment_bug(hass: HomeAssistant):
    """Test reproduction of energy increment bug when switch is off at end of cycle"""
    
    # 0. Setup Central Config (required for Power Feature to be "configured")
    await create_central_config(hass)

    # 1. Setup VTherm over switch with TPI
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="EnergyBug",
        unique_id="uniqueIdEnergyBug",
        data={
            CONF_NAME: "EnergyBug",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 10,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_DEVICE_POWER: 1000, # 1000 Watts
            CONF_USE_POWER_FEATURE: True,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.energybug")
    assert entity
    assert entity.power_manager.is_configured

    tz = get_tz(hass)
    now = datetime.now(tz=tz)

    # Set initial state
    await send_temperature_change_event(entity, 19, now) # Current temp
    await send_ext_temperature_change_event(entity, 5, now)
    await hass.async_block_till_done()

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_temperature(temperature=20)
    await hass.async_block_till_done()

    # TPI Calculation:
    # Error = 1 degree.
    # Coef Int = 0.6 -> 0.6
    # Coef Ext = 0.01 * (20 - 5) = 0.15
    # Total = 0.75 (75%)
    # On Time = 0.75 * 10 min = 7.5 min = 450 sec.
    # Off Time = 2.5 min = 150 sec.

    assert entity.proportional_algorithm.on_percent == 0.75
    
    # Verify mean_cycle_power initial check (active=True, active=False)
    # Mocking is_device_active on entity is hard because it's a property calculating from underlyings.
    # But we can check via underlying switch state.
    
    underlying = entity.underlying_entity(0)
    
    # Start cycle
    # The cycle start triggered turn_on on underlying.
    # Checking underlying state (mocked)
    hass.states.async_set("switch.mock_switch", STATE_ON)
    await hass.async_block_till_done() # Allow state change to propagate if needed

    # verify entity.is_device_active is True
    underlying = entity.underlying_entity(0)
    assert underlying.is_device_active is True
    
    assert entity.is_device_active is True
    assert entity.power_manager.mean_cycle_power == 750.0
    
    # Simulate end of ON cycle
    # UnderlyingSwitch._turn_off_later does:
    # 1. turn_off() (sets switch OFF)
    # 2. calls incremente_energy()
    
    # We simulate this manually to observe the bug
    
    # 1. Turn off
    hass.states.async_set("switch.mock_switch", STATE_OFF)
    assert entity.is_device_active is False
    
    # 2. Check mean_cycle_power when OFF
    # BUG FIX: It SHOULD be 750.0 (average over cycle) even if device is OFF, because it's an average over the cycle duration
    current_mean_power = entity.power_manager.mean_cycle_power
    assert current_mean_power == 750.0, f"Fix failed: mean_cycle_power is {current_mean_power} instead of 750.0"
