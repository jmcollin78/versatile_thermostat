"""Test Auto TPI Capacity Learning interactions."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)
from custom_components.versatile_thermostat.const import (
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
)

import logging
_LOGGER = logging.getLogger(__name__)

# Log test execution
@pytest.fixture(autouse=True)
def log_test_execution(request):
    """Log the start and end of each test."""
    _LOGGER.info("Starting test: %s", request.node.name)
    yield
    _LOGGER.info("Finished test: %s", request.node.name)

# Patch async_call_later to avoid loop issues
@pytest.fixture(autouse=True)
def mock_async_call_later():
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.async_call_later") as mock_call_later:
        yield mock_call_later

@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = MagicMock()
    hass.config_entries = MagicMock()
    return hass

@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {}
    return entry

@pytest.fixture
def mock_store():
    """Mock Storage."""
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.Store") as mock_store_cls:
        store_instance = mock_store_cls.return_value
        store_instance.async_load = MagicMock(return_value=None) # Mock async_load which is awaited
        store_instance.async_save = MagicMock() # Mock async_save which is awaited
        yield store_instance

@pytest.fixture
def manager(mock_hass, mock_store, mock_config_entry):
    """Create a manager instance."""
    return AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test_id_cap",
        name="test_name",
        cycle_min=60, # 60 minutes for easy calculation
        coef_int=0.6,
        coef_ext=0.01,
        heater_heating_time=10,
        heater_cooling_time=5,
    )

async def test_complementary_learning(manager):
    """Verify that capacity learning and TPI learning happen in the same cycle."""
    
    # 1. Setup State
    # We want to trigger capacity learning:
    # - last_power >= 0.80
    # - real_rise >= 0.05
    # - target_diff >= 1.0 (since count < 3)
    
    manager.state.autolearn_enabled = True
    manager.state.last_state = "heat"
    manager.state.last_power = 0.9  # 90% power (Eligible for both Capacity and Kint learning)
    manager.state.last_temp_in = 19.0
    manager.state.last_order = 21.0
    manager.state.max_capacity_heat = 0.0 # Not known yet
    manager.state.capacity_heat_learn_count = 0
    manager.state.coeff_indoor_heat = 0.6
    
    # 2. Cycle Result
    # We simulate a rise of 1.0 degree in 1 hour (cycle_min=60)
    current_temp_in = 20.0 
    current_temp_out = 0.0
    
    # Current values at cycle end
    manager._current_temp_in = current_temp_in
    manager._current_temp_out = current_temp_out
    manager._current_target_temp = 21.0
    
    # 3. Perform Learning
    await manager._perform_learning(current_temp_in, current_temp_out)
    
    # 4. Verify Capacity Learning
    # Observed capacity = Rise / (Duration * Efficiency) = 1.0 / (1.0 * 1.0) = 1.0 deg/h
    # Adiabatic capacity = Observed + Kext * DeltaT
    # DeltaT = 19.0 - 0.0 = 19.0
    # Kext = 0.01
    # Loss = 0.01 * 19.0 = 0.19
    # Adiabatic Capacity = 1.0 + 0.19 = 1.19 deg/h
    
    # Assert capacity was updated
    assert manager.state.max_capacity_heat > 0.0
    assert manager.state.max_capacity_heat == pytest.approx(1.20, abs=0.01)
    assert manager.state.capacity_heat_learn_count == 1
    
    # 5. Verify TPI Learning (should confirm it happened too)
    # The function should NOT return early after capacity learning.
    # It should proceed to learn Kint.
    
    # Target Kint should be adjusted based on the new capacity and the gap.
    # If the test passes this, it means both happened.
    assert manager.state.last_learning_status.startswith("learned_indoor_heat")
    
    # Check that indoor coefficient changed (learned)
    assert manager.state.coeff_indoor_heat != 0.6
    
    # Log results for user visibility
    _LOGGER.info(f"Capacity Learned: {manager.state.max_capacity_heat}")
    _LOGGER.info(f"Indoor Coeff Learned: {manager.state.coeff_indoor_heat}")
    _LOGGER.info(f"Final Status: {manager.state.last_learning_status}")
