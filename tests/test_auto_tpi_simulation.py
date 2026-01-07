"""Simulation test for AutoTpiManager to verify multi-cycle behavior and convergence."""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)
from custom_components.versatile_thermostat.prop_algorithm import PropAlgorithm
from custom_components.versatile_thermostat.const import CONF_TPI_COEF_INT, CONF_TPI_COEF_EXT

class ThermalModel:
    def __init__(self, room_temp, ext_temp, capacity, insulation_loss, time_constant_hours=None):
        self.room_temp = room_temp
        self.ext_temp = ext_temp
        self.capacity = capacity # degrees gained per hour at 100% power
        self.insulation_loss = insulation_loss # degrees lost per hour per degree difference
        self.time_constant_hours = time_constant_hours 
        
    def step(self, on_percent: float, duration_minutes: float):
        dt_h = duration_minutes / 60.0
        heat_gain_rate = self.capacity * on_percent
        heat_loss_rate = self.insulation_loss * (self.room_temp - self.ext_temp)
        net_change_rate = heat_gain_rate - heat_loss_rate
        self.room_temp += net_change_rate * dt_h
        return self.room_temp

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = asyncio.get_event_loop()
    
    # Avoid RuntimeWarning: coroutine never awaited
    def fake_create_task(coro):
        return hass.loop.create_task(coro)
    hass.async_create_task = MagicMock(side_effect=fake_create_task)
    
    return hass

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {}
    return entry

@pytest.fixture
def mock_store():
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.Store") as mock_store_cls:
        store_instance = mock_store_cls.return_value
        store_instance.async_load = AsyncMock(return_value=None)
        store_instance.async_save = AsyncMock()
        yield store_instance

@pytest.mark.asyncio
async def test_auto_tpi_convergence_simulation(mock_hass, mock_store, mock_config_entry):
    """
    Simulate multiple TPI cycles and verify that the algorithm learns and updates coefficients without saturation.
    
    Scenario:
    - Room: 50m3 roughly.
    - Capacity: 5 deg/h
    - Insulation: Loss of 0.1 deg/h per degree delta.
    
    Convergence Target:
    - Kext should converge to Loss_Coef / Capacity = 0.1 / 5.0 = 0.02.
    - Kint should adjust to reach target.
    """
    
    # 1. Physics Constants
    REAL_CAPACITY = 5.0 
    REAL_LOSS_COEF = 0.1 
    
    manager = AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="sim_test",
        name="SimTest",
        cycle_min=10,
        coef_int=0.3, # Start LOW
        coef_ext=0.01, # Start LOW
        heater_heating_time=1,
        heater_cooling_time=1,
    )
    # Enable autolearn configuration
    manager.state.autolearn_enabled = True
    manager.state.max_capacity_heat = REAL_CAPACITY 
    
    prop_algo = PropAlgorithm(
        function_type="tpi",
        tpi_coef_int=0.3, 
        tpi_coef_ext=0.01,
        cycle_min=10,
        minimal_activation_delay=0,
        minimal_deactivation_delay=0,
        vtherm_entity_id="climate.sim_test"
    )
    
    # Start cold
    model = ThermalModel(room_temp=17.0, ext_temp=5.0, capacity=REAL_CAPACITY, insulation_loss=REAL_LOSS_COEF)
    target_temp = 20.0
    sim_time = datetime(2024, 1, 1, 8, 0, 0)
    
    # Print header for analysis
    print(f"\n{'Cycle':<5} | {'RoomT':<8} | {'ExtT':<8} | {'Power%':<8} | {'Kint':<8} | {'Kext':<8} | {'Status'}")
    print("-" * 80)

    with patch("custom_components.versatile_thermostat.auto_tpi_manager.dt_util") as mock_dt_util, \
         patch("custom_components.versatile_thermostat.auto_tpi_manager.async_call_later") as mock_call_later:
        
        mock_dt_util.now.side_effect = lambda: sim_time
        
        async def data_provider():
            await manager.update(
                room_temp=model.room_temp,
                ext_temp=model.ext_temp,
                target_temp=target_temp,
                hvac_mode="heat",
                is_overpowering_detected=False
            )
            
            new_params = await manager.calculate()
            if new_params:
                # Correctly update PropAlgorithm with new learned coefficients using CONSTANT keys
                kint = new_params.get(CONF_TPI_COEF_INT)
                kext = new_params.get(CONF_TPI_COEF_EXT)
                
                # Check directly vs Manager state to ensure we are in sync
                # NOTE: During bootstrap, kint/kext will be aggressive (1.0/0.1) while state remains at initial (0.3/0.01)
                # until capacity is learned. So we check equality only if NOT in bootstrap.
                if manager.is_in_bootstrap:
                     # Verify we are using aggressive defaults
                     assert kint == 1.0
                     assert kext == 0.1
                else: 
                     assert kint == manager.state.coeff_indoor_heat
                     assert kext == manager.state.coeff_outdoor_heat

                if kint is not None and kext is not None:
                     prop_algo.update_parameters(tpi_coef_int=kint, tpi_coef_ext=kext)
            
            prop_algo.calculate(
                target_temp=target_temp,
                current_temp=model.room_temp,
                ext_current_temp=model.ext_temp,
                slope=None,
                hvac_mode="heat"
            )
            on_percent = prop_algo.on_percent
            
            return {
                "on_time_sec": on_percent * 600,
                "off_time_sec": (1 - on_percent) * 600,
                "on_percent": on_percent,
                "hvac_mode": "heat"
            }
        
        manager._data_provider = data_provider
        manager._event_sender = MagicMock()
        await manager.start_cycle_loop(data_provider, manager._event_sender)
        
        for i in range(50):
            cycle_data = await data_provider()
            power = cycle_data["on_percent"]
            
            # Step Physics
            model.step(power, 10.0)
            sim_time += timedelta(minutes=10)
            
            # Tick Manager
            await manager._tick()
            
            status = manager.state.last_learning_status
            print(f"{i+1:<5} | {model.room_temp:<8.3f} | {model.ext_temp:<8.1f} | {power:<8.2f} | {manager.state.coeff_indoor_heat:<8.3f} | {manager.state.coeff_outdoor_heat:<8.3f} | {status}")
            
            # Perturbation: Drop external temp to force Kext learning
            if i == 30:
                 model.ext_temp = 0.0

        final_kext = manager.state.coeff_outdoor_heat
        final_kint = manager.state.coeff_indoor_heat
        
        # Verification
        # 1. Kint should have increased to compensate for startup load
        assert final_kint > 0.3, f"Kint should have increased from 0.3, got {final_kint}"
        
        # 2. Kext should have increased towards ideal 0.02
        assert final_kext > 0.01, f"Kext should have increased from 0.01, got {final_kext}"
        
        # Ideal Kext is 0.02. We accept a range.
        assert 0.015 < final_kext < 0.03, f"Kext should be close to 0.02, got {final_kext}"
        
        # 3. Room temp should be stable near target (within 0.1 deg)
        assert abs(model.room_temp - target_temp) < 0.1, f"Room temp {model.room_temp} should be close to target {target_temp}"

