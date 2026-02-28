"""Test continuous Kext learning in AutoTpiManager."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)

import logging
_LOGGER = logging.getLogger(__name__)

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
        store_instance.async_load = AsyncMock(return_value=None)
        store_instance.async_save = AsyncMock()
        yield store_instance

@pytest.fixture
def manager(mock_hass, mock_store, mock_config_entry):
    """Create a manager instance with continuous Kext enabled."""
    return AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test_id",
        name="test_name",
        cycle_min=5,
        coef_int=0.6,
        coef_ext=0.01,
        heater_heating_time=10,
        heater_cooling_time=5,
        continuous_kext=True,
        continuous_kext_alpha=0.1 # 10% learning rate
    )

async def test_should_learn_continuous_basics(manager):
    """Test _should_learn basic conditions with Continuous Kext."""
    # Setup state
    manager.state.autolearn_enabled = False
    manager.state.coeff_outdoor_autolearn = 10 # Bootstrapped
    manager.state.last_power = 0.5 # Valid power
    manager.state.consecutive_failures = 0
    manager.state.previous_state = "heat"
    manager.state.last_state = "heat"
    manager.state.last_order = 20.0
    manager._current_temp_out = 0.0 # DeltaOut = 20 > 1.0
    
    # Should be True
    assert manager._should_learn() is True

async def test_should_learn_continuous_disabled(manager):
    """Test _should_learn when disabled."""
    manager._continuous_kext = False
    manager.state.autolearn_enabled = False
    assert manager._should_learn() is False

async def test_perform_learning_continuous_kext_skips_indoor(manager):
    """Test that indoor learning is skipped when only continuous kext is active."""
    manager.state.autolearn_enabled = False # Main learning OFF
    
    # Setup for Indoor Learning Success
    manager.state.last_state = "heat"
    manager.state.last_order = 20.0
    manager.state.last_temp_in = 19.0
    manager.state.coeff_indoor_heat = 0.5
    manager.state.last_power = 0.5 
    manager.state.max_capacity_heat = 2.0
    
    # Current state (Rise = 0.2, TargetDiff = 1.0)
    current_temp_in = 19.2 
    current_temp_out = 0.0
    manager._current_target_temp = 20.0 # Match last_order
    
    await manager._perform_learning(current_temp_in, current_temp_out)
    
    # Indoor coeff should NOT change
    assert manager.state.coeff_indoor_heat == 0.5
    assert "learned_indoor" not in manager.state.last_learning_status

async def test_perform_learning_continuous_kext_allows_outdoor(manager):
    """Test that outdoor learning IS performed when only continuous kext is active."""
    manager.state.autolearn_enabled = False # Main learning OFF
    
    manager.state.last_state = "heat"
    manager.state.last_order = 20.0
    manager.state.last_temp_in = 19.5
    manager.state.coeff_outdoor_heat = 0.01
    manager.state.last_power = 0.5 
    
    current_temp_in = 19.5 
    current_temp_out = 0.0
    manager._current_target_temp = 20.0 # Match last_order
    
    await manager._perform_learning(current_temp_in, current_temp_out)
    
    assert "learned_outdoor" in manager.state.last_learning_status
    assert manager.state.coeff_outdoor_heat != 0.01

async def test_filtered_state_hides_indoor_counters(manager):
    """Test get_filtered_state hides indoor counters when autolearn is False."""
    manager.state.autolearn_enabled = False
    manager.state.coeff_indoor_autolearn = 100
    manager.state.coeff_outdoor_autolearn = 50
    
    state = manager.get_filtered_state()
    
    assert "coeff_indoor_autolearn" not in state
    assert "coeff_outdoor_autolearn" in state

async def test_on_cycle_completed_triggers_perform_learning(manager):
    """Test that on_cycle_completed calls process_cycle which triggers learning."""
    manager.state.autolearn_enabled = False
    manager.state.last_state = "heat"
    manager.state.coeff_outdoor_autolearn = 10
    manager.state.previous_state = "heat"
    manager.state.last_order = 20.0
    manager.state.last_params = {"hvac_mode": "heat", "on_percent": 0.5, "on_time_sec": 150, "off_time_sec": 150}
    manager.state.last_power = 0.5
    
    # Required for validation
    manager.state.max_capacity_heat = 10.0 
    manager.state.capacity_heat_learn_count = 10
    manager._current_hvac_mode = "heat"
    
    manager._current_target_temp = 20.0
    manager._current_temp_in = 19.0
    manager._current_temp_out = 0.0
    
    # Start cycle to set correct state
    manager.state.cycle_active = True
    # Ensure the cycle duration is >= cycle_min (5 min) so it completes
    start_time = datetime.now(timezone.utc) - timedelta(minutes=6)
    manager._cycle_start_date = start_time
    manager.state.cycle_start_date = start_time
    manager._current_cycle_params = {"hvac_mode": "heat", "on_percent": 0.5, "on_time_sec": 150, "off_time_sec": 150} # Essential for confirmation
    
    # Check for cycle boundary: elapsed_sec >= cycle_min * 60
    # elapsed = 6 min > 5 min. Should complete.

    # We patch _perform_learning to verify it is called
    with patch.object(manager, "_perform_learning", wraps=manager._perform_learning) as mock_perform:
        # params return for data_provider (Closing cycle params)
        params = {"on_time_sec": 150, "off_time_sec": 150, "hvac_mode": "heat"}
        
        # We need to simulate the "current" time being later
        current_time = datetime.now(timezone.utc)
        
        # Call process_cycle directly or via on_cycle_completed if that's exposed
        # on_cycle_completed calls process_learning_completion but NOT _perform_learning directly.
        # process_cycle(timestamp, data_provider, event_sender)
        # data_provider returns the params
        async def mock_data_provider():
            return params
            
        async def mock_event_sender(p):
            pass

        await manager.process_cycle(
            datetime.now(timezone.utc),
            mock_data_provider,
            mock_event_sender
        )
        
        mock_perform.assert_called_once()
