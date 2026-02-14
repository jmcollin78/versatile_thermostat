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

@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = MagicMock()
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
    """Test _should_learn_continuous_kext basic conditions."""
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
    assert manager._should_learn_continuous_kext() is True

async def test_should_learn_continuous_disabled(manager):
    """Test _should_learn_continuous_kext when disabled."""
    manager._continuous_kext = False
    assert manager._should_learn_continuous_kext() is False

async def test_should_learn_continuous_not_bootstrapped(manager):
    """Test _should_learn_continuous_kext when not bootstrapped."""
    manager.state.coeff_outdoor_autolearn = 0
    manager.state.coeff_outdoor_cool_autolearn = 0
    assert manager._should_learn_continuous_kext() is False

async def test_should_learn_continuous_filtered(manager):
    """Test _should_learn_continuous_kext filtered conditions."""
    manager.state.coeff_outdoor_autolearn = 10
    manager.state.last_power = 0.5
    manager.state.previous_state = "heat"
    manager.state.last_order = 20.0
    manager._current_temp_out = 0.0

    # Boiler Off
    manager._central_boiler_off = True
    assert manager._should_learn_continuous_kext() is False
    manager._central_boiler_off = False

    # Saturated Power (assuming saturation at 1.0)
    manager.state.last_power = 1.0
    assert manager._should_learn_continuous_kext() is False
    manager.state.last_power = 0.5

    # Small Outdoor Delta
    manager._current_temp_out = 19.5 # Delta = 0.5 < 1.0
    assert manager._should_learn_continuous_kext() is False
    manager._current_temp_out = 0.0

async def test_learn_kext_continuous_heat(manager):
    """Test value update in Heat mode."""
    # Setup
    manager.state.autolearn_enabled = False
    manager.state.last_state = "heat"
    manager.state.previous_state = "heat" # Must not be stop
    manager.state.coeff_outdoor_autolearn = 10
    manager.state.coeff_indoor_heat = 0.5
    manager.state.coeff_outdoor_heat = 1.0 # Initial Kext
    
    manager.state.last_order = 20.0 
    manager.state.last_power = 0.5
    
    # Scenario: Too Cold (GapIn > 0). Expect Kext INCREASE.
    # GapIn = Target - In = 20 - 19 = 1.0
    # GapOut = Target - Out = 20 - 0 = 20.0
    # Correction = Kint * (GapIn / GapOut) = 0.5 * (1.0 / 20.0) = 0.5 * 0.05 = 0.025
    # Target Kext = Old Kext + Correction = 1.0 + 0.025 = 1.025
    # New Kext (EMA) = Old * (1-alpha) + Target * alpha
    # Alpha = 0.1
    # New = 1.0 * 0.9 + 1.025 * 0.1 = 0.9 + 0.1025 = 1.0025
    
    current_temp_in = 19.0
    current_temp_out = 0.0
    
    # Update current temp out on manager for _should_learn check
    manager._current_temp_out = current_temp_out
    
    # Setup current target temp to match last order (no setpoint change)
    manager._current_target_temp = 20.0
    
    await manager._learn_kext_continuous(current_temp_in, current_temp_out)
    
    assert manager.state.last_learning_status == "continuous_kext_learned_heat"
    assert manager.state.coeff_outdoor_heat == pytest.approx(1.0025, abs=0.0001)

async def test_learn_kext_continuous_cool(manager):
    """Test value update in Cool mode."""
    # Setup
    manager.state.autolearn_enabled = False
    manager.state.last_state = "cool"
    manager.state.previous_state = "cool" # Must not be stop
    manager.state.coeff_outdoor_cool_autolearn = 10
    manager.state.coeff_indoor_cool = 0.5
    manager.state.coeff_outdoor_cool = 1.0 # Initial Kext
    
    manager.state.last_order = 25.0 
    manager.state.last_power = 0.5
    
    # Scenario: Too Hot (GapIn < 0). Need more cooling power -> Increase Kext.
    # Wait, my previous math analysis:
    # GapIn = Target - In = 25 - 26 = -1.0
    # GapOut = Target - Out. Out=35. GapOut = 25 - 35 = -10.0
    # Correction = Kint * (-1.0 / -10.0) = 0.5 * 0.1 = 0.05
    # Target Kext = 1.0 + 0.05 = 1.05
    # New Kext = 1.0 * 0.9 + 1.05 * 0.1 = 0.9 + 0.105 = 1.005
    
    current_temp_in = 26.0
    current_temp_out = 35.0
    
    manager._current_temp_out = current_temp_out
    
    manager._current_target_temp = 25.0
    
    await manager._learn_kext_continuous(current_temp_in, current_temp_out)
    
    assert manager.state.last_learning_status == "continuous_kext_learned_cool"
    assert manager.state.coeff_outdoor_cool == pytest.approx(1.005, abs=0.0001)

async def test_learn_kext_continuous_setpoint_change(manager):
    """Test no learning if setpoint changed."""
    manager.state.autolearn_enabled = False
    manager.state.last_state = "heat"
    manager.state.previous_state = "heat"
    manager.state.coeff_outdoor_autolearn = 10
    manager.state.last_order = 20.0
    manager.state.last_power = 0.5
    manager._current_temp_out = 0.0
    
    manager._current_target_temp = 21.0 # Changed
    
    await manager._learn_kext_continuous(19.0, 0.0)
    
    assert manager.state.last_learning_status == "continuous_kext_setpoint_changed"

async def test_on_cycle_completed_triggers_continuous(manager):
    """Test that on_cycle_completed calls continuous learning."""
    manager.state.autolearn_enabled = False
    manager.state.last_state = "heat"
    manager.state.coeff_outdoor_autolearn = 10
    manager.state.previous_state = "heat"
    manager.state.last_order = 20.0
    manager.state.last_power = 0.5
    
    # Avoid bootstrap logic
    manager.state.max_capacity_heat = 10.0 
    manager.state.capacity_heat_learn_count = 10
    manager._current_hvac_mode = "heat"
    
    manager._current_target_temp = 20.0
    manager._current_temp_in = 19.0
    manager._current_temp_out = 0.0
    
    # Clean previous state errors
    manager.state.last_learning_status = "unknown"
    
    # Setup cycle timing to pass validation (duration ~ cycle_min)
    now = datetime.now(timezone.utc)
    manager.state.cycle_start_date = now - timedelta(minutes=5) # 5 min ago
    manager.state.cycle_active = True
    
    # We pass minimal prev_params to satisfy validation (Total 300s = 5min)
    params = {"on_time_sec": 150, "off_time_sec": 150, "hvac_mode": "heat"}
    
    with patch.object(manager, "_learn_kext_continuous", wraps=manager._learn_kext_continuous) as mock_learn:
        await manager.on_cycle_completed(params, params)
        
        mock_learn.assert_called_once()
        assert manager.state.last_learning_status == "continuous_kext_learned_heat"
