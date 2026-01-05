# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Scheduler Feature Manager """
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

import pytest

from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

from custom_components.versatile_thermostat.feature_scheduler_manager import (
    FeatureSchedulerManager,
    PRESET_KEYWORDS,
)
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from custom_components.versatile_thermostat.const import (
    CONF_USE_SCHEDULER_FEATURE,
    CONF_SCHEDULER_CALENDAR,
    CONF_SCHEDULER_DEFAULT_PRESET,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_scheduler_manager_init(hass: HomeAssistant):
    """Test the FeatureSchedulerManager initialization"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    assert manager is not None
    assert manager.is_configured is False
    assert manager.scheduled_preset is None
    assert manager.has_active_event is False
    assert manager.calendar_entity_id is None


async def test_scheduler_manager_post_init_enabled(hass: HomeAssistant):
    """Test post_init when scheduler is enabled"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure with scheduler enabled
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "eco",
    }

    manager.post_init(entry_infos)

    assert manager.is_configured is True
    assert manager.calendar_entity_id == "calendar.heating_schedule"
    assert manager.default_preset == "eco"
    assert manager.scheduled_preset is None


async def test_scheduler_manager_post_init_disabled(hass: HomeAssistant):
    """Test post_init when scheduler is disabled"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure with scheduler disabled
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: False,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
    }

    manager.post_init(entry_infos)

    assert manager.is_configured is False


async def test_scheduler_manager_post_init_no_calendar(hass: HomeAssistant):
    """Test post_init when no calendar is provided"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure with scheduler enabled but no calendar
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        # No CONF_SCHEDULER_CALENDAR
    }

    manager.post_init(entry_infos)

    assert manager.is_configured is False


async def test_get_preset_from_event_title_exact_match(hass: HomeAssistant):
    """Test preset extraction with exact keyword match"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Test exact matches
    assert manager._get_preset_from_event_title("boost") == VThermPreset.BOOST
    assert manager._get_preset_from_event_title("BOOST") == VThermPreset.BOOST
    assert manager._get_preset_from_event_title("Boost") == VThermPreset.BOOST
    assert manager._get_preset_from_event_title("comfort") == VThermPreset.COMFORT
    assert manager._get_preset_from_event_title("confort") == VThermPreset.COMFORT
    assert manager._get_preset_from_event_title("eco") == VThermPreset.ECO
    assert manager._get_preset_from_event_title("frost") == VThermPreset.FROST
    assert manager._get_preset_from_event_title("hg") == VThermPreset.FROST
    assert manager._get_preset_from_event_title("hors gel") == VThermPreset.FROST
    assert manager._get_preset_from_event_title("away") == VThermPreset.FROST


async def test_get_preset_from_event_title_partial_match(hass: HomeAssistant):
    """Test preset extraction with partial keyword match"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Test partial matches (keyword in title)
    assert manager._get_preset_from_event_title("Mode boost chauffage") == VThermPreset.BOOST
    assert manager._get_preset_from_event_title("Chauffage comfort") == VThermPreset.COMFORT
    assert manager._get_preset_from_event_title("eco mode soir") == VThermPreset.ECO
    assert manager._get_preset_from_event_title("Hors gel nuit") == VThermPreset.FROST


async def test_get_preset_from_event_title_no_match(hass: HomeAssistant):
    """Test preset extraction with no matching keyword"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Test no matches
    assert manager._get_preset_from_event_title("random event") is None
    assert manager._get_preset_from_event_title("heating") is None
    assert manager._get_preset_from_event_title("") is None
    assert manager._get_preset_from_event_title(None) is None


async def test_scheduler_manager_refresh_state_not_configured(hass: HomeAssistant):
    """Test refresh_state when not configured"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Not configured, refresh_state should return False
    result = await manager.refresh_state()
    assert result is False


async def test_scheduler_manager_refresh_state_calendar_on(hass: HomeAssistant):
    """Test refresh_state when calendar has active event"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.send_event = MagicMock()
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure scheduler
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # Mock calendar state with active event
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_ON,
        {"message": "comfort"}
    )
    hass.states.async_set("calendar.heating_schedule", STATE_ON, {"message": "comfort"})

    with patch.object(hass.states, "get", return_value=calendar_state):
        result = await manager.refresh_state()

    assert result is True
    assert manager.scheduled_preset == VThermPreset.COMFORT
    assert manager.has_active_event is True
    assert manager.current_event_title == "comfort"

    # Event should be sent
    vtherm.send_event.assert_called_once()
    vtherm.update_states.assert_called_once()


async def test_scheduler_manager_refresh_state_calendar_off(hass: HomeAssistant):
    """Test refresh_state when calendar has no active event"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure scheduler
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # Mock calendar state with no active event
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_OFF,
        {}
    )

    with patch.object(hass.states, "get", return_value=calendar_state):
        result = await manager.refresh_state()

    assert result is False  # No change from initial None state
    assert manager.scheduled_preset is None
    assert manager.has_active_event is False


async def test_scheduler_manager_refresh_state_calendar_unavailable(hass: HomeAssistant):
    """Test refresh_state when calendar is unavailable"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure scheduler
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # Mock calendar state unavailable
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_UNAVAILABLE,
        {}
    )

    with patch.object(hass.states, "get", return_value=calendar_state):
        result = await manager.refresh_state()

    assert result is False
    assert manager.scheduled_preset is None


async def test_scheduler_manager_preset_change_fires_event(hass: HomeAssistant):
    """Test that changing preset fires an event"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.send_event = MagicMock()
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure scheduler
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # First update: set preset to eco
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_ON,
        {"message": "eco"}
    )

    with patch.object(hass.states, "get", return_value=calendar_state):
        result = await manager.refresh_state()

    assert result is True
    assert manager.scheduled_preset == VThermPreset.ECO

    # Check event was fired
    vtherm.send_event.assert_called()
    call_args = vtherm.send_event.call_args
    assert call_args[0][0].value == "versatile_thermostat_scheduler_event"
    assert call_args[1]["data"]["old_preset"] is None
    assert call_args[1]["data"]["new_preset"] == VThermPreset.ECO


async def test_scheduler_manager_effective_preset(hass: HomeAssistant):
    """Test the effective_preset property"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.send_event = MagicMock()
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()

    manager = FeatureSchedulerManager(vtherm, hass)

    # Not configured
    assert manager.effective_preset is None

    # Configure with default preset "frost"
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # No active event -> effective preset is default
    assert manager.effective_preset == "frost"

    # Set active event with "boost"
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_ON,
        {"message": "boost"}
    )

    with patch.object(hass.states, "get", return_value=calendar_state):
        await manager.refresh_state()

    # Active event -> effective preset is scheduled
    assert manager.effective_preset == VThermPreset.BOOST


async def test_scheduler_manager_add_custom_attributes_not_configured(hass: HomeAssistant):
    """Test add_custom_attributes when not configured"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    attrs = {}
    manager.add_custom_attributes(attrs)

    assert "is_scheduler_configured" in attrs
    assert attrs["is_scheduler_configured"] is False
    assert "scheduler_manager" not in attrs


async def test_scheduler_manager_add_custom_attributes_configured(hass: HomeAssistant):
    """Test add_custom_attributes when configured"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.send_event = MagicMock()
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()

    manager = FeatureSchedulerManager(vtherm, hass)

    # Configure scheduler
    entry_infos = {
        CONF_USE_SCHEDULER_FEATURE: True,
        CONF_SCHEDULER_CALENDAR: "calendar.heating_schedule",
        CONF_SCHEDULER_DEFAULT_PRESET: "frost",
    }
    manager.post_init(entry_infos)

    # Set an active event
    calendar_state = State(
        "calendar.heating_schedule",
        STATE_ON,
        {"message": "comfort"}
    )

    with patch.object(hass.states, "get", return_value=calendar_state):
        await manager.refresh_state()

    attrs = {}
    manager.add_custom_attributes(attrs)

    assert "is_scheduler_configured" in attrs
    assert attrs["is_scheduler_configured"] is True
    assert "scheduler_manager" in attrs
    assert attrs["scheduler_manager"]["calendar_entity_id"] == "calendar.heating_schedule"
    assert attrs["scheduler_manager"]["default_preset"] == "frost"
    assert attrs["scheduler_manager"]["scheduled_preset"] == VThermPreset.COMFORT
    assert attrs["scheduler_manager"]["current_event_title"] == "comfort"


async def test_preset_keywords_coverage():
    """Test that all preset keywords are defined correctly"""
    # Verify all keywords map to valid presets
    for keyword, preset in PRESET_KEYWORDS.items():
        assert preset in [
            VThermPreset.BOOST,
            VThermPreset.COMFORT,
            VThermPreset.ECO,
            VThermPreset.FROST,
        ], f"Keyword '{keyword}' maps to invalid preset '{preset}'"

    # Verify we have entries for all main presets
    preset_values = set(PRESET_KEYWORDS.values())
    assert VThermPreset.BOOST in preset_values
    assert VThermPreset.COMFORT in preset_values
    assert VThermPreset.ECO in preset_values
    assert VThermPreset.FROST in preset_values


async def test_scheduler_manager_str_representation(hass: HomeAssistant):
    """Test the string representation of the manager"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"

    manager = FeatureSchedulerManager(vtherm, hass)

    assert "SchedulerManager" in str(manager)
    assert "test_vtherm" in str(manager)
