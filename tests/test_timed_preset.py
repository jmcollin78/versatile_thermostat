# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Timed Preset feature manager and services """
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from homeassistant.exceptions import ServiceValidationError

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_timed_preset_manager import FeatureTimedPresetManager
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_timed_preset_manager_init(hass: HomeAssistant):
    """Test the FeatureTimedPresetManager initialization"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureTimedPresetManager(vtherm, hass)

    assert manager is not None
    assert manager.is_timed_preset_active is False
    assert manager.timed_preset is None
    assert manager.timed_preset_end_time is None
    assert manager.is_configured is True


async def test_timed_preset_manager_set_timed_preset(hass: HomeAssistant):
    """Test setting a timed preset"""
    # Create a mock VTherm
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = VThermPreset.ECO
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()

    now = datetime(2026, 1, 2, 10, 0, 0)
    vtherm.now = now

    manager = FeatureTimedPresetManager(vtherm, hass)

    # Set a timed preset for 30 minutes
    result = await manager.set_timed_preset(VThermPreset.BOOST, 30)

    assert result is True
    assert manager.is_timed_preset_active is True
    assert manager.timed_preset == VThermPreset.BOOST
    assert manager.timed_preset_end_time == now + timedelta(minutes=30)

    # Check that events were sent
    vtherm.send_event.assert_called_once()
    call_args = vtherm.send_event.call_args
    assert call_args[1]["data"]["type"] == "start"
    assert call_args[1]["data"]["preset"] == str(VThermPreset.BOOST)
    assert call_args[1]["data"]["duration_minutes"] == 30

    # Check that vtherm was updated
    vtherm.requested_state.force_changed.assert_called_once()
    vtherm.update_states.assert_called_once_with(force=True)
    vtherm.update_custom_attributes.assert_called_once()


async def test_timed_preset_manager_invalid_preset(hass: HomeAssistant):
    """Test setting an invalid preset"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT]  # BOOST not available
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # Try to set an unavailable preset
    result = await manager.set_timed_preset(VThermPreset.BOOST, 30)

    assert result is False
    assert manager.is_timed_preset_active is False


async def test_timed_preset_manager_invalid_duration(hass: HomeAssistant):
    """Test setting a preset with invalid duration"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # Try to set with zero duration
    result = await manager.set_timed_preset(VThermPreset.BOOST, 0)
    assert result is False

    # Try to set with negative duration
    result = await manager.set_timed_preset(VThermPreset.BOOST, -10)
    assert result is False


async def test_timed_preset_manager_cancel_timed_preset(hass: HomeAssistant):
    """Test cancelling a timed preset"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = VThermPreset.ECO
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # First, set a timed preset
    await manager.set_timed_preset(VThermPreset.BOOST, 30)
    assert manager.is_timed_preset_active is True

    # Reset mocks
    vtherm.send_event.reset_mock()
    vtherm.requested_state.force_changed.reset_mock()
    vtherm.update_states.reset_mock()

    # Cancel the timed preset
    result = await manager.cancel_timed_preset()

    assert result is True
    assert manager.is_timed_preset_active is False
    assert manager.timed_preset is None
    assert manager.timed_preset_end_time is None

    # Check that events were sent
    vtherm.send_event.assert_called_once()
    call_args = vtherm.send_event.call_args
    assert call_args[1]["data"]["type"] == "end"
    assert call_args[1]["data"]["cause"] == "cancelled"


async def test_timed_preset_manager_cancel_when_not_active(hass: HomeAssistant):
    """Test cancelling when no timed preset is active"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # Cancel when not active
    result = await manager.cancel_timed_preset()

    assert result is False


async def test_timed_preset_manager_refresh_state(hass: HomeAssistant):
    """Test refresh_state method"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = VThermPreset.ECO
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # refresh_state when not active should return False
    result = await manager.refresh_state()
    assert result is False

    # Set a timed preset
    await manager.set_timed_preset(VThermPreset.BOOST, 30)

    # refresh_state when active should return True
    result = await manager.refresh_state()
    assert result is True


async def test_timed_preset_manager_remaining_time(hass: HomeAssistant):
    """Test remaining_time_min property"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = VThermPreset.ECO
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()

    start_time = datetime(2026, 1, 2, 10, 0, 0)
    vtherm.now = start_time

    manager = FeatureTimedPresetManager(vtherm, hass)

    # remaining_time_min when not active should be 0
    assert manager.remaining_time_min == 0

    # Set a timed preset for 30 minutes
    await manager.set_timed_preset(VThermPreset.BOOST, 30)

    # remaining_time_min should be 30
    assert manager.remaining_time_min == 30

    # Simulate time passing (10 minutes later)
    vtherm.now = start_time + timedelta(minutes=10)
    assert manager.remaining_time_min == 20

    # Simulate more time passing (25 minutes later from start)
    vtherm.now = start_time + timedelta(minutes=25)
    assert manager.remaining_time_min == 5

    # Simulate time after expiration (35 minutes later)
    vtherm.now = start_time + timedelta(minutes=35)
    assert manager.remaining_time_min == 0  # Should be 0, not negative


async def test_timed_preset_manager_custom_attributes(hass: HomeAssistant):
    """Test add_custom_attributes method"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = VThermPreset.ECO
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()
    vtherm.now = datetime(2026, 1, 2, 10, 0, 0)

    manager = FeatureTimedPresetManager(vtherm, hass)

    # Test when not active
    attrs = {}
    manager.add_custom_attributes(attrs)
    assert "timed_preset_manager" in attrs
    assert attrs["timed_preset_manager"]["is_active"] is False
    assert attrs["timed_preset_manager"]["remaining_time_min"] == 0
    assert attrs["timed_preset_manager"]["preset"] is None
    assert attrs["timed_preset_manager"]["end_time"] is None

    # Set a timed preset
    await manager.set_timed_preset(VThermPreset.BOOST, 30)

    # Test when active
    attrs = {}
    manager.add_custom_attributes(attrs)
    assert "timed_preset_manager" in attrs
    assert attrs["timed_preset_manager"]["is_active"] is True
    assert attrs["timed_preset_manager"]["preset"] == str(VThermPreset.BOOST)
    assert attrs["timed_preset_manager"]["remaining_time_min"] == 30
    assert attrs["timed_preset_manager"]["end_time"] is not None


async def test_service_set_timed_preset_success(hass: HomeAssistant):
    """Test the service_set_timed_preset method with valid preset"""
    # Create a BaseThermostat with mocked managers
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    # Mock the necessary attributes
    vtherm._vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=False)
    vtherm._timed_preset_manager = MagicMock()
    vtherm._timed_preset_manager.set_timed_preset = AsyncMock(return_value=True)

    # Call the service
    await vtherm.service_set_timed_preset("boost", 30)

    # Verify the timed_preset_manager was called correctly
    vtherm._timed_preset_manager.set_timed_preset.assert_called_once()
    call_args = vtherm._timed_preset_manager.set_timed_preset.call_args
    assert call_args[0][0] == VThermPreset.BOOST
    assert call_args[0][1] == 30


async def test_service_set_timed_preset_invalid_preset(hass: HomeAssistant):
    """Test the service_set_timed_preset method with invalid preset"""
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    # Mock the necessary attributes - BOOST is not in the list
    vtherm._vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT]
    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=False)

    # Call the service and expect an error
    with pytest.raises(ServiceValidationError) as exc_info:
        await vtherm.service_set_timed_preset("boost", 30)

    assert "boost" in str(exc_info.value)
    assert "not available" in str(exc_info.value)


async def test_service_set_timed_preset_invalid_duration(hass: HomeAssistant):
    """Test the service_set_timed_preset method with invalid duration"""
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    vtherm._vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=False)

    # Call the service with negative duration
    with pytest.raises(ServiceValidationError) as exc_info:
        await vtherm.service_set_timed_preset("boost", -10)

    assert "positive" in str(exc_info.value)


async def test_service_set_timed_preset_locked(hass: HomeAssistant):
    """Test the service_set_timed_preset method when thermostat is locked"""
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    vtherm._vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=True)
    vtherm._timed_preset_manager = MagicMock()
    vtherm._timed_preset_manager.set_timed_preset = AsyncMock(return_value=True)

    # Call the service (should return without doing anything)
    await vtherm.service_set_timed_preset("boost", 30)

    # Verify the timed_preset_manager was NOT called
    vtherm._timed_preset_manager.set_timed_preset.assert_not_called()


async def test_service_cancel_timed_preset_success(hass: HomeAssistant):
    """Test the service_cancel_timed_preset method"""
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=False)
    vtherm._timed_preset_manager = MagicMock()
    vtherm._timed_preset_manager.cancel_timed_preset = AsyncMock(return_value=True)

    # Call the service
    await vtherm.service_cancel_timed_preset()

    # Verify the timed_preset_manager was called
    vtherm._timed_preset_manager.cancel_timed_preset.assert_called_once()


async def test_service_cancel_timed_preset_locked(hass: HomeAssistant):
    """Test the service_cancel_timed_preset method when thermostat is locked"""
    vtherm = BaseThermostat(hass, "unique_id", "test_vtherm", {})

    vtherm._lock_manager = MagicMock()
    vtherm._lock_manager.check_is_locked = MagicMock(return_value=True)
    vtherm._timed_preset_manager = MagicMock()
    vtherm._timed_preset_manager.cancel_timed_preset = AsyncMock(return_value=True)

    # Call the service (should return without doing anything)
    await vtherm.service_cancel_timed_preset()

    # Verify the timed_preset_manager was NOT called
    vtherm._timed_preset_manager.cancel_timed_preset.assert_not_called()
