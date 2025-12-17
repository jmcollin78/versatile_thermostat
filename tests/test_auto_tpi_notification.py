"""Test the AutoTpiManager notification logic."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.versatile_thermostat.auto_tpi_manager import AutoTpiManager

@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
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
    """Create a manager instance."""
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
    )

async def test_detect_failures_notification(manager, mock_hass):
    """Test that notification is sent after 3 consecutive failures."""
    await manager.async_load_data()
    
    # Setup state for failure detection
    # Heat mode failure: current_temp < last_order - 1.0 AND current_temp < last_temp_in
    # And we need enough learning cycles to enable detection
    manager.state.autolearn_enabled = True
    manager.state.last_state = "heat"
    manager.state.last_order = 20.0
    manager.state.coeff_indoor_autolearn = 30 # > 25
    
    # 1st Failure
    manager.state.last_temp_in = 19.0
    current_temp = 18.0 # < 20-1 and < 19
    
    await manager._detect_failures(current_temp)
    assert manager.state.consecutive_failures == 1
    assert manager.state.autolearn_enabled is True
    mock_hass.services.async_call.assert_not_called()
    
    # 2nd Failure
    await manager._detect_failures(current_temp)
    assert manager.state.consecutive_failures == 2
    assert manager.state.autolearn_enabled is True
    mock_hass.services.async_call.assert_not_called()
    
    # 3rd Failure
    await manager._detect_failures(current_temp)
    assert manager.state.consecutive_failures == 3
    assert manager.state.autolearn_enabled is False
    
    # Verify notification call
    mock_hass.services.async_call.assert_called_once()
    args = mock_hass.services.async_call.call_args
    assert args[0][0] == "persistent_notification"
    assert args[0][1] == "create"
    service_data = args[0][2]
    assert service_data["title"] == "Versatile Thermostat: Auto TPI Learning Stopped"
    assert "Reason: Temperature dropped while heating" in service_data["message"]
