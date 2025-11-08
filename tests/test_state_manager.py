# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import logging
from unittest.mock import patch, PropertyMock, AsyncMock, MagicMock

from homeassistant.components.climate import HVACMode

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.state_manager import StateManager
from custom_components.versatile_thermostat.vtherm_state import VThermState
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_state_manager_create(
    hass: HomeAssistant,
):
    """Test the StateManager class direclty"""
    state_manager = StateManager()
    assert state_manager is not None
    assert state_manager.current_state == VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE, target_temperature=None)
    assert state_manager.requested_state == VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE, target_temperature=None)
    assert state_manager.current_state.is_changed is True
    assert state_manager.requested_state.is_changed is True

    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    assert state_manager.current_state.is_changed is False
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is False

    state_manager.current_state.force_changed()
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_target_temperature(22)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is False

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_preset(VThermPreset.ECO)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is False

    json = state_manager.current_state.to_dict()
    assert json == {
       "hvac_mode": str(VThermHvacMode_HEAT),
       "preset": str(VThermPreset.ECO),
       "target_temperature": 22,
    }

    json["hvac_mode"] = str(VThermHvacMode_COOL)
    json["preset"] = str(VThermPreset.BOOST)
    json["target_temperature"] = 24

    restored_state = VThermState.from_dict(json)
    assert restored_state.hvac_mode == VThermHvacMode_COOL
    assert restored_state.preset == VThermPreset.BOOST
    assert restored_state.target_temperature == 24

async def test_vtherm_state_save_and_restor_newfmt(hass: HomeAssistant) -> None:
    """Test saving and restoring the VTherm states with new format"""
    vtherm = BaseThermostat(hass, "unique_id", "name", {})

    # Simulate changing the state
    vtherm.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    vtherm.current_state.set_preset(VThermPreset.ECO)
    vtherm.current_state.set_target_temperature(22)

    vtherm.requested_state.set_hvac_mode(VThermHvacMode_COOL)
    vtherm.requested_state.set_preset(VThermPreset.COMFORT)
    vtherm.requested_state.set_target_temperature(23)

    # Save the state using Home Assistant's state mechanism
    state_dict = {
        "current_state": vtherm.current_state.to_dict(),
        "requested_state": vtherm.requested_state.to_dict(),
        "preset_mode": str(vtherm.current_state.preset),
        "temperature": vtherm.current_state.target_temperature,
    }

    # Simulate what Home Assistant does - store extra state data
    vtherm_restored = BaseThermostat(hass, "unique_id", "name", {})
    mock_state = MagicMock()
    mock_state.state = HVACMode.OFF
    mock_state.attributes = state_dict
    with patch.object(vtherm_restored, 'async_get_last_state', return_value=mock_state):
        # Create a new thermostat instance to simulate restoration
        await vtherm_restored.get_my_previous_state()


    # Check that the current state has been restored
    assert vtherm_restored.current_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.current_state.preset == VThermPreset.ECO
    assert vtherm_restored.current_state.target_temperature == 22

    # Check that the requested state has been restored
    assert vtherm_restored.requested_state.hvac_mode == VThermHvacMode_COOL
    assert vtherm_restored.requested_state.preset == VThermPreset.COMFORT
    assert vtherm_restored.requested_state.target_temperature == 23

async def test_vtherm_state_save_and_restor_oldfmt(hass: HomeAssistant) -> None:
    """Test saving and restoring the VTherm states with old format (ie retrocompatibility)"""
    # Save the state using Home Assistant's state mechanism
    state_dict = {
        "preset_mode": "eco",
        "temperature": 22,
    }

    # Simulate what Home Assistant does - store extra state data
    vtherm_restored = BaseThermostat(hass, "unique_id", "name", {})
    mock_state = MagicMock()
    mock_state.attributes = state_dict
    mock_state.state = HVACMode.HEAT
    with patch.object(vtherm_restored, 'async_get_last_state', return_value=mock_state):
        # Create a new thermostat instance to simulate restoration
        await vtherm_restored.get_my_previous_state()


    # Check that the current state has been restored
    assert vtherm_restored.current_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.current_state.preset == VThermPreset.ECO
    assert vtherm_restored.current_state.target_temperature == 22

    # Check that the requested state has been restored
    assert vtherm_restored.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.requested_state.preset == VThermPreset.ECO
    assert vtherm_restored.requested_state.target_temperature == 22
