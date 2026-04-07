# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant, CoreState
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.versatile_thermostat.thermostat_prop import ThermostatProp
from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from custom_components.versatile_thermostat.const import *
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF

from .commons import *

@pytest.fixture
def mock_prop_thermostat(hass: HomeAssistant, skip_hass_states_is_state):
    """Fixture to create a ThermostatProp with a TPI algorithm."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="the_unique_id",
        data={
            CONF_NAME: "ThePropThermostat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.temp",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.ext_temp",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 100,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.heater",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
        },
    )
    entity = ThermostatProp(hass, "the_unique_id", "ThePropThermostat", entry.data)
    entity._prop_algorithm = MagicMock(spec=TpiAlgorithm)
    entity._prop_algorithm.calculate.return_value = None
    entity._prop_algorithm.on_percent = 0.5
    entity._prop_algorithm.calculated_on_percent = 0.5
    
    return entity

async def test_feedback_safety(hass: HomeAssistant, mock_prop_thermostat):
    """Test that update_realized_power is called when safety is active."""
    entity = mock_prop_thermostat
    
    # Normal case: on_percent should be 0.5 (from algo)
    assert entity.on_percent == 0.5
    # Should NOT have been called yet (or called with 0.5 matching calculated)
    # Actually implementation calls it if discrepancy OR always? 
    # Current impl: checks logic in on_percent -> calls if algo has method.
    
    # Let's reset mock to be sure
    entity._prop_algorithm.update_realized_power.reset_mock()
    
    # Trigger Safety
    entity.set_safety(0.1)
    
    # Check on_percent
    assert entity.on_percent == 0.1
    
    # Verify feedback was sent
    entity._prop_algorithm.update_realized_power.assert_called_with(0.1)

async def test_feedback_clamping(hass: HomeAssistant, mock_prop_thermostat):
    """Test that update_realized_power is called when clamping is active."""
    entity = mock_prop_thermostat
    entity._max_on_percent = 0.3
    
    # Algo requests 0.5
    entity._prop_algorithm.on_percent = 0.5
    
    # Reset mock
    entity._prop_algorithm.update_realized_power.reset_mock()
    
    # Check on_percent - should be clamped to 0.3
    assert entity.on_percent == 0.3
    
    # Verify feedback was sent with clamped value
    entity._prop_algorithm.update_realized_power.assert_called_with(0.3)

async def test_feedback_no_algo_method(hass: HomeAssistant, mock_prop_thermostat):
    """Test that no error occurs if algo doesn't have the method."""
    entity = mock_prop_thermostat
    # Replace algo with one that has no update_realized_power
    entity._prop_algorithm = MagicMock()
    del entity._prop_algorithm.update_realized_power
    
    # Trigger feedback situation
    entity.set_safety(0.1)
    
    # Should not raise
    assert entity.on_percent == 0.1

async def test_feedback_timing(hass: HomeAssistant, mock_prop_thermostat):
    """Test that update_realized_power is called when timing forces changes."""
    entity = mock_prop_thermostat
    
    # Initialize handler
    from custom_components.versatile_thermostat.prop_handler_tpi import TPIHandler
    handler = TPIHandler(entity)
    entity._algo_handler = handler
    
    # Set delays and cycle
    # _cycle_min has no setter, so must set private attr
    entity._cycle_min = 10 
    # minimal_activation_delay has setter
    entity.minimal_activation_delay = 300 
    
    assert entity.cycle_min == 10
    assert entity.minimal_activation_delay == 300
    
    # Ensure the mock HAS the method (MagicMock spec can sometimes be tricky with hasattr)
    entity._prop_algorithm.update_realized_power = MagicMock()

    # CASE 1: on_percent too low -> forced to 0
    # 0.01 * 600 = 6 sec < 300 sec -> failure -> 0
    entity._prop_algorithm.on_percent = 0.01
    
    # Call _get_tpi_data (where the logic resides)
    data = await handler._get_tpi_data()
    
    assert data["on_time_sec"] == 0
    assert data["off_time_sec"] == 600
    
    # Check if called at all
    assert entity._prop_algorithm.update_realized_power.called
    # Verify feedback was sent with 0
    entity._prop_algorithm.update_realized_power.assert_called_with(0.0)
    
    entity._prop_algorithm.update_realized_power.reset_mock()
    
    # CASE 2: on_percent high but off time too short -> forced to 1
    # 0.99 * 600 = 594 sec. Off = 6 sec.
    # If minimal_deactivation_delay is 300
    entity.minimal_deactivation_delay = 300
    entity._prop_algorithm.on_percent = 0.99
    
    data = await handler._get_tpi_data()
    
    assert data["on_time_sec"] == 600
    assert data["off_time_sec"] == 0
    
    # Verify feedback was sent with 1.0 (realized percent)
    entity._prop_algorithm.update_realized_power.assert_called_with(1.0)


@pytest.mark.asyncio
async def test_tpi_off_cancels_running_cycle_even_if_underlying_is_already_off():
    """HVAC OFF must cancel the master cycle even during an already-off PWM phase."""
    from custom_components.versatile_thermostat.prop_handler_tpi import TPIHandler

    thermostat = SimpleNamespace(
        vtherm_hvac_mode=VThermHvacMode_OFF,
        cycle_min=5,
        is_device_active=False,
        cycle_scheduler=SimpleNamespace(
            is_cycle_running=True,
            cancel_cycle=AsyncMock(),
        ),
        async_underlying_entity_turn_off=AsyncMock(),
        _on_time_sec=None,
        _off_time_sec=None,
    )

    handler = TPIHandler(thermostat)

    await handler.control_heating(force=True)

    assert thermostat._on_time_sec == 0
    assert thermostat._off_time_sec == 300
    thermostat.cycle_scheduler.cancel_cycle.assert_awaited_once()
    thermostat.async_underlying_entity_turn_off.assert_not_awaited()
