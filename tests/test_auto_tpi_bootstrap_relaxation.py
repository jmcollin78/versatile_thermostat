"""Test Auto TPI Bootstrap Relaxation."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)

import logging
_LOGGER = logging.getLogger(__name__)

# Log test execution
@pytest.fixture(autouse=True)
def log_test_execution(request):
    _LOGGER.info("Starting test: %s", request.node.name)
    yield
    _LOGGER.info("Finished test: %s", request.node.name)

# Patch async_call_later
@pytest.fixture(autouse=True)
def mock_async_call_later():
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.async_call_later") as mock_call_later:
        yield mock_call_later

@pytest.fixture
def mock_hass():
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = MagicMock()
    hass.config_entries = MagicMock()
    return hass

@pytest.fixture
def mock_config_entry():
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {}
    return entry

@pytest.fixture
def mock_store():
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.Store") as mock_store_cls:
        store_instance = mock_store_cls.return_value
        store_instance.async_load = MagicMock(return_value=None) 
        store_instance.async_save = MagicMock()
        yield store_instance

@pytest.fixture
def manager(mock_hass, mock_store, mock_config_entry):
    manager = AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test_id_relax",
        name="test_name",
        cycle_min=60,
        coef_int=0.6,
        coef_ext=0.01,
        enable_update_config=True 
    )
    # Force enable learning
    manager.state.autolearn_enabled = True
    return manager

async def test_bootstrap_relaxation_logic(manager):
    """
    Test that thresholds are relaxed after normalized failures.
    We verify _should_learn_capacity indirectly or by spying.
    Here we will invoke _should_learn_capacity directly or via internal checks.
    """
    
    # 1. Setup Bootstrap State
    manager.state.max_capacity_heat = 0.0 # Force bootstrap
    manager.state.capacity_heat_learn_count = 0
    manager.state.bootstrap_failure_count = 0
    
    # === PHASE 1: STANDARD THRESHOLDS (0-5 failures) ===
    # Case: Power 60% (Too low for standard 80%)
    manager.state.last_power = 0.60
    manager.state.last_temp_in = 19.0
    manager._current_temp_in = 19.1 # Rise 0.1 (OK)
    manager._current_target_temp = 20.0 # Gap 1.0 (OK)
    
    # Should FAIL and increment counter
    assert manager._should_learn_capacity() is False
    assert manager.state.bootstrap_failure_count == 1
    
    # Allow 4 more failures (Total 5)
    for _ in range(4):
        manager.state.last_power = 0.60
        manager._should_learn_capacity()
        
    assert manager.state.bootstrap_failure_count == 5
    
    # Next one: Failure 6. Still standard threshold (failures > 5 check is AFTER entering with current count?)
    # Logic: if failures > 5: Relax.
    # Currently failures=5. So logic uses standard.
    assert manager._should_learn_capacity() is False
    assert manager.state.bootstrap_failure_count == 6
    
    # === PHASE 2: TIMEOUT (6 failures) ===
    # Logic: if failures > 5 -> Force capacity 0.3 & Reset

    # Trigger failure #6
    assert manager._should_learn_capacity() is False
    
    # Now failure count should be 0 (reset) AND max_capacity_heat should be 0.3
    assert manager.state.bootstrap_failure_count == 0
    assert manager.state.max_capacity_heat == 0.3
    assert manager.state.capacity_heat_learn_count == 3
    
    # Verify is_in_bootstrap property updates
    assert manager.is_in_bootstrap is False # exited bootstrap
    assert manager.learning_active is True # still active
    
    # Verify that now we are NOT in bootstrap anymore
    # The next call should use standard thresholds (no failure increment if power low, but strict power/rise)
    # But since max_capacity_heat > 0, in_bootstrap is False.
    
    # Test valid normal cycle
    manager.state.last_power = 0.90
    manager.state.last_temp_in = 19.0
    manager._current_temp_in = 19.1
    
    assert manager._should_learn_capacity() is True
