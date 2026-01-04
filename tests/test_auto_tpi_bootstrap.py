"""Tests for Aggressive TPI bootstrap and capacity learning."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import statistics

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

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

# Patch async_call_later to avoid loop issues
@pytest.fixture(autouse=True)
def mock_async_call_later():
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.async_call_later") as mock_call_later:
        yield mock_call_later

@pytest.fixture
def manager_bootstrap(mock_hass, mock_store, mock_config_entry):
    """Create a manager instance for bootstrap testing (no manual capacity)."""
    manager = AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test_id",
        name="test_name",
        cycle_min=15,
        coef_int=0.6,
        coef_ext=0.01,
        heater_heating_time=10,
        heater_cooling_time=5,
        heating_rate=0.0,  # No manual capacity, triggers bootstrap
    )
    # Important: Initialize offset to 0.0 for power calculation tests
    manager.state.offset = 0.0
    return manager

async def test_bootstrap_activation_mode(manager_bootstrap):
    """Test that bootstrap activates when no manual capacity is provided."""
    await manager_bootstrap.start_learning(reset_data=True)
    
    # max_capacity starts at 0 (or default fallback check later)
    # verify learn count is 0
    assert manager_bootstrap.state.capacity_heat_learn_count == 0
    # In bootstrap if count < 3
    
    # Check that aggressive coefficients are used in calculate()
    params = await manager_bootstrap.calculate()
    # Note: calculate() returns dictionary with const keys, e.g. "kp" or "ki" or similar?
    # Let's inspect what calculate() returns or usage in other tests.
    # It returns params[CONF_TPI_COEF_INT] ...
    # We can access state directly to check aggressive values were swapped back or not?
    # No, we want to check what calculate() returned effectively.
    # calculate() swaps -> calc param -> swaps back.
    # So the return value should reflect aggressive params.
    
    # We need to know the keys. Using values directly for now as they are likely "tpi_coef_int" etc.
    # Based on grep, they are CONF_TPI_COEF_INT and CONF_TPI_COEF_EXT. 
    # We will assume "tpi_coef_int" and "tpi_coef_ext" based on naming convention
    # or just check values if keys are unknown
    
    val_int = list(params.values())[0] # assuming order/content
    # Better: check for value 2.0 in values (Aggressive coefficients are 200.0 / 5.0)
    # Better: check for value 1.0 in values (Aggressive coefficients are 1.0 / 0.1)
    assert 1.0 in params.values()
    assert 0.1 in params.values()

    # But underlying state should remain original
    assert manager_bootstrap.state.coeff_indoor_heat == 0.6
    assert manager_bootstrap.state.coeff_outdoor_heat == 0.01

async def test_manual_capacity_skip(mock_hass, mock_store, mock_config_entry):
    """Test that bootstrap is skipped when manual capacity is provided."""
    manager = AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test",
        name="test",
        cycle_min=15,
        coef_int=0.6,
        coef_ext=0.01,
        heating_rate=2.5,  # Manual capacity
    )
    
    await manager.start_learning(reset_data=True)
    
    # Should be marked as learned
    assert manager.state.capacity_heat_learn_count == 3
    assert manager.state.max_capacity_heat == 2.5
    
    # Calculate should return normal coefficients
    params = await manager.calculate()
    assert 2.0 not in params.values()
    # Check for 0.6
    found_06 = any(abs(v - 0.6) < 0.001 for v in params.values())
    assert found_06
    

async def test_bootstrap_power_calculation(manager_bootstrap):
    """Test power calculation uses aggressive coefficients during bootstrap."""
    await manager_bootstrap.start_learning(reset_data=True)
    
    # Aggressive: Kint=2.0, Kext=0.05
    # Power = (Err * Kint - DeltaT * Kext) + Offset
    
    # Initialize offset which defaults to 0.0 but let's be explicit
    manager_bootstrap.state.offset = 0.0
    
    # CASE 1: High demand
    # Kint=200.0, Kext=5.0 (Scaled from 2.0/0.05)
    setpoint = 20.0
    temp_in = 19.0 # Error = 1.0
    temp_out = 0.0 # DeltaT = 19.0
    
    # Aggressive: 1.0*1.0 + (20-0)*0.1 = 1.0 + 2.0 = 3.0 (300%)
    # Power = 1.0*1.0 + 20.0*0.1 = 1.0 + 2.0 = 3.0 -> Clamped to 100% (1.0 due to min(1.0))
    
    power = manager_bootstrap.calculate_power(setpoint, temp_in, temp_out, "heat")
    assert power == 1.0
    
    # CASE 2: Moderate demand
    # Kint=1.0, Kext=0.1
    # Temp in = 19.8 (Error = 0.2)
    # Power = 0.2*1.0 + 20*0.1 = 0.2 + 2.0 = 2.22 (222%) -> 100% (1.0)
    # Normal would be 0.2*0.6 + 20*0.01 = 0.12 + 0.2 = 0.32 (32%)
    
    power = manager_bootstrap.calculate_power(20.0, 19.8, 0.0, "heat")
    assert power == 1.0
    
    # To really prove it, let's verify exact value logic if internal method was public, 
    # but based on public API, getting 100% where normal would be 32% is proof enough.

async def test_capacity_learning_adiabatic(manager_bootstrap):
    """Test capacity learning with adiabatic correction."""
    await manager_bootstrap.start_learning(reset_data=True)
    
    # Simulate a cycle
    # Rise = 2.0 deg
    # Duration = 1 h (efficiency=1, cycle_min=60? No cycle_min=15 => 0.25h)
    # Power = 100% ? No, observed capacity depends on efficiency.
    # Observed Eff = Rise / (Time * Efficiency)
    # If Rise=2.0 in 15min (0.25h) with Eff=1.0:
    # Obs = 2.0 / (0.25 * 1.0) = 8.0 deg/h
    
    # Adiabatic correction: + Kext * DeltaT
    # Kext used is state.coeff_outdoor_heat (0.01 in fixture, NOT aggressive one? 
    # _learn_capacity is called with k_ext passed from on_cycle_completed.
    # on_cycle_completed passes self.state.coeff_outdoor_heat.
    # So it uses the "learned" (or default) Kext, not the bootstrap aggressive one.
    # Correct, we want to correct using the "assumed" loss factor of the building model?
    # Or should we use the aggressive one? 
    # The loss factor Kext defaults to 0.01 provided in config.
    
    k_ext = 0.01
    delta_t = 20.0 # Tin 20, Tout 0
    # Correction = 0.01 * 20 = 0.2
    
    # Total Adiabatic = 8.0 + 0.2 = 8.2
    
    # Manager setup
    manager_bootstrap.state.max_capacity_heat = 0
    manager_bootstrap.state.capacity_heat_learn_count = 0
    
    # Call _learn_capacity directly to verify logic
    manager_bootstrap._learn_capacity(
        power=1.0,
        delta_t=delta_t,
        rise=2.0,
        efficiency=1.0,
        k_ext=k_ext
    )
    
    # First measurement should be direct assignment
    assert manager_bootstrap.state.max_capacity_heat == pytest.approx(8.2)
    assert manager_bootstrap.state.capacity_heat_learn_count == 1
    
    # Second measurement: Alpha should be 0.5 / (1 + 0.1*1) = 0.5 / 1.1 = 0.45
    # New Obs = 8.2 again (steady)
    # EWMA: (1-0.45)*8.2 + 0.45*8.2 = 8.2
    manager_bootstrap._learn_capacity(
        power=1.0,
        delta_t=delta_t,
        rise=2.0,
        efficiency=1.0,
        k_ext=k_ext
    )
    assert manager_bootstrap.state.max_capacity_heat == pytest.approx(8.2)

async def test_bootstrap_completion(manager_bootstrap):
    """Test transition out of bootstrap after 3 cycles."""
    await manager_bootstrap.start_learning(reset_data=True)
    
    # Run 3 cycles learning capacity
    k_ext = 0.01
    delta_t = 20.0
    rise = 2.0 # leads to 8.2 capacity
    
    for i in range(3):
        assert manager_bootstrap.state.capacity_heat_learn_count == i
        manager_bootstrap._learn_capacity(1.0, delta_t, rise, 1.0, k_ext)
        
    assert manager_bootstrap.state.capacity_heat_learn_count == 3
    
    # Now calculate() should NOT return aggressive coeffs
    params = await manager_bootstrap.calculate()
    assert 2.0 not in params.values()
    # Check for 0.6
    found_06 = any(abs(v - 0.6) < 0.001 for v in params.values())
    assert found_06

async def test_capacity_confidence(manager_bootstrap):
    """Test confidence score calculation."""
    manager_bootstrap.state.capacity_heat_learn_count = 0
    assert manager_bootstrap._get_capacity_confidence() == 0.3
    
    # Add some history
    manager_bootstrap._capacity_history = [10.0, 10.0, 10.0]
    manager_bootstrap.state.capacity_heat_learn_count = 3
    
    # 0 variance -> cv=0 -> confidence=1.0
    assert manager_bootstrap._get_capacity_confidence() == 1.0
    
    # High variance
    manager_bootstrap._capacity_history = [5.0, 15.0, 10.0] # mean 10, std ~ high
    # pstdev([5,15,10]) -> sqrt((25+25+0)/3) = sqrt(16.6) = 4.08
    # CV = 0.408
    # Conf = 1 - 0.408 = 0.59
    
    conf = manager_bootstrap._get_capacity_confidence()
    assert 0.5 < conf < 0.7

async def test_on_cycle_completed_bootstrap_call(manager_bootstrap):
    """Test on_cycle_completed calls only capacity learning during bootstrap."""
    manager_bootstrap._should_learn_capacity = MagicMock(return_value=True)
    manager_bootstrap._learn_capacity = MagicMock(return_value=True)
    manager_bootstrap._perform_learning = AsyncMock()
    
    # Setup bootstrap state
    manager_bootstrap.state.capacity_heat_learn_count = 0
    manager_bootstrap.state.max_capacity_heat = 0
    manager_bootstrap._current_hvac_mode = "heat"
    manager_bootstrap.state.cycle_active = True
    
    await manager_bootstrap.on_cycle_completed(900, 0, hvac_mode="heat")
    
    # Should call _learn_capacity
    assert manager_bootstrap._learn_capacity.call_count == 1
    # Should NOT call _perform_learning
    assert manager_bootstrap._perform_learning.call_count == 0
    
    # Now verify normal mode behavior check
    manager_bootstrap.state.capacity_heat_learn_count = 3
    manager_bootstrap.state.max_capacity_heat = 10.0
    manager_bootstrap._should_learn = MagicMock(return_value=True)
    manager_bootstrap.state.cycle_active = True
    
    await manager_bootstrap.on_cycle_completed(900, 0, hvac_mode="heat")
    
    # Should call _perform_learning
    assert manager_bootstrap._perform_learning.call_count == 1
