# tests/test_tpi_overlap_bug.py

import pytest
import logging
from unittest.mock import patch, ANY, call
from datetime import datetime, timedelta

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.const import *
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT
from .commons import *

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("custom_components.versatile_thermostat").setLevel(logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_tpi_overlap_bug(hass: HomeAssistant, skip_hass_states_is_state):
    """
    Test reproduction of the bug where overlapping cycles (due to delay) cause the next cycle to be skipped.
    """
    tz = get_tz(hass)
    now = datetime.now(tz=tz)

    # 1. Configure Thermostat with TPI and 2 switches
    # Cycle 10 min.
    # Switch 1: delay 0.
    # Switch 2: delay 5 min (300s).
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TPIOverlap",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TPIOverlap",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 10,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch1",
            CONF_HEATER_2: "switch.mock_switch2",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6, # High coef to ensure high heating
            CONF_TPI_COEF_EXT: 0.1,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.tpioverlap")
    assert entity
    assert entity.nb_underlying_entities == 2
    
    # 2. Set mode to HEAT and target temp
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_temperature(temperature=20)
    
    # Force 80% heating
    # We patch calculation to return 0.8
    with patch("custom_components.versatile_thermostat.prop_algo_tpi.TpiAlgorithm.calculate", return_value=0.8) as mock_calculate:
        # Manually set on_percent because mocking calculate prevents it from being updated
        entity.prop_algorithm._calculated_on_percent = 0.8
        
        # Trigger cycle 1
        await entity.async_control_heating(timestamp=now)
        
        # Switch 1: ON at 0, OFF at 8.
        # Switch 2: ON at 5, OFF at 13.
        
        # We need to simulate that Switch 2 has `_async_cancel_cycle` set.
        # And that we are at T=10.
        
        # Let's simulate state:
        # Switch 2
        entity.underlying_entity(1)._async_cancel_cycle = "fake_task"
            
        # --- Cycle 2 Start (T=10) ---
        now_plus_10 = now + timedelta(minutes=10)
        await entity.async_control_heating(timestamp=now_plus_10)
        
        # Check if Switch 2 scheduled next cycle
        # With the fix, _async_next_cycle should be set because it was busy
        switch2 = entity.underlying_entity(1)
        
        assert switch2._async_next_cycle is not None, "Bug fix verification: _async_next_cycle should be set when cycle is busy"
        assert switch2._async_cancel_cycle == "fake_task", "Current cycle should remain active"
