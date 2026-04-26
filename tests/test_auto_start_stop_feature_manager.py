# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import logging
from datetime import datetime
from unittest.mock import PropertyMock, MagicMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat

from custom_components.versatile_thermostat.feature_auto_start_stop_manager import (
    FeatureAutoStartStopManager,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_auto_start_stop_feature_manager_create(
    hass: HomeAssistant,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    auto_start_stop_manager = FeatureAutoStartStopManager(fake_vtherm, hass)

    assert auto_start_stop_manager is not None
    assert auto_start_stop_manager.is_configured is False
    assert auto_start_stop_manager.is_auto_stopped is False
    assert auto_start_stop_manager.auto_start_stop_enable is False
    assert auto_start_stop_manager.name == "the name"

    assert len(auto_start_stop_manager._active_listener) == 0

    custom_attributes = {}
    auto_start_stop_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_auto_start_stop_configured"] is False
    # assert custom_attributes["auto_start_stop_enable"] is False
    # assert custom_attributes["auto_start_stop_level"] == AUTO_START_STOP_LEVEL_NONE
    # assert custom_attributes["auto_start_stop_dtmin"] is None
    # assert custom_attributes["auto_start_stop_accumulated_error"] is None
    # assert custom_attributes["auto_start_stop_accumulated_error_threshold"] is None
    # assert custom_attributes["auto_start_stop_last_switch_date"] is None


@pytest.mark.parametrize(
    "use_auto_start_stop_feature, level, is_configured",
    [
        # fmt: off
        ( True, AUTO_START_STOP_LEVEL_NONE, True),
        ( True, AUTO_START_STOP_LEVEL_VERY_SLOW, True),
        ( True, AUTO_START_STOP_LEVEL_SLOW, True),
        ( True, AUTO_START_STOP_LEVEL_MEDIUM, True),
        ( True, AUTO_START_STOP_LEVEL_FAST, True),
        # Level is missing , will be set to None
        ( True, None, True),
        ( False, AUTO_START_STOP_LEVEL_NONE, False),
        ( False, AUTO_START_STOP_LEVEL_VERY_SLOW, False),
        ( False, AUTO_START_STOP_LEVEL_SLOW, False),
        ( False, AUTO_START_STOP_LEVEL_MEDIUM, False),
        ( False, AUTO_START_STOP_LEVEL_FAST, False),
        # Level is missing , will be set to None
        ( False, None, False),
        # fmt: on
    ],
)
async def test_auto_start_stop_feature_manager_post_init(
    hass: HomeAssistant, use_auto_start_stop_feature, level, is_configured
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).have_valve_regulation = PropertyMock(return_value=False)

    # 1. creation
    auto_start_stop_manager = FeatureAutoStartStopManager(fake_vtherm, hass)
    assert auto_start_stop_manager is not None

    # 2. post_init
    auto_start_stop_manager.post_init(
        {
            CONF_USE_AUTO_START_STOP_FEATURE: use_auto_start_stop_feature,
            CONF_AUTO_START_STOP_LEVEL: level,
        }
    )

    assert auto_start_stop_manager.is_configured is is_configured
    assert (
        auto_start_stop_manager.auto_start_stop_level == level
        if level and is_configured
        else AUTO_START_STOP_LEVEL_NONE
    )
    should_be_enabled = level not in [None, AUTO_START_STOP_LEVEL_NONE] and is_configured
    assert auto_start_stop_manager.auto_start_stop_enable is should_be_enabled
    assert auto_start_stop_manager._auto_start_stop_algo is not None

    custom_attributes = {}
    auto_start_stop_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_auto_start_stop_configured"] is is_configured

    if auto_start_stop_manager.is_configured:
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_enable"] is should_be_enabled
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == level if level and is_configured else AUTO_START_STOP_LEVEL_NONE
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == auto_start_stop_manager._auto_start_stop_algo.dt_min
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_accumulated_error"] == auto_start_stop_manager._auto_start_stop_algo.accumulated_error
        assert (
            custom_attributes["auto_start_stop_manager"]["auto_start_stop_accumulated_error_threshold"] == auto_start_stop_manager._auto_start_stop_algo.accumulated_error_threshold
        )
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_last_switch_date"] == auto_start_stop_manager._auto_start_stop_algo.last_switch_date


# ──────────────────────────────────────────────────────────────────────────────
# Tests for restore_state()
# ──────────────────────────────────────────────────────────────────────────────


def _make_manager(hass, level=AUTO_START_STOP_LEVEL_MEDIUM) -> FeatureAutoStartStopManager:
    """Helper: create a fully post_init'd FeatureAutoStartStopManager."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="test_vtherm")
    type(fake_vtherm).have_valve_regulation = PropertyMock(return_value=False)
    type(fake_vtherm).is_over_climate = PropertyMock(return_value=True)
    type(fake_vtherm).is_on = PropertyMock(return_value=False)
    fake_vtherm.hvac_off_reason = None

    manager = FeatureAutoStartStopManager(fake_vtherm, hass)
    manager.post_init(
        {
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_AUTO_START_STOP_LEVEL: level,
        }
    )
    return manager


async def test_restore_state_when_auto_stopped(hass: HomeAssistant):
    """Test that restore_state correctly restores manager and algo state
    when the VTherm was auto-stopped before the restart."""

    manager = _make_manager(hass)
    last_switch = datetime(2026, 1, 2, 8, 30, 0)

    old_state = MagicMock()
    old_state.attributes = {
        "auto_start_stop_manager": {
            "is_auto_stop_detected": True,
            "auto_start_stop_enable": True,
            "auto_start_stop_level": AUTO_START_STOP_LEVEL_MEDIUM,
            "auto_start_stop_accumulated_error": -4.5,
            "auto_start_stop_accumulated_error_threshold": 5.0,
            "auto_start_stop_last_switch_date": last_switch.isoformat(),
        }
    }

    manager.restore_state(old_state)

    # Manager flag must be restored
    assert manager.is_auto_stop_detected is True
    # Algorithm intermediate state must be restored
    assert manager._auto_start_stop_algo.accumulated_error == -4.5
    assert manager._auto_start_stop_algo.last_switch_date == last_switch
    # Algorithm internal _last_should_be_off must be in sync
    assert manager._auto_start_stop_algo._last_should_be_off is True


async def test_restore_state_when_not_auto_stopped(hass: HomeAssistant):
    """Test restore_state when VTherm was running normally (not auto-stopped).
    Algorithm intermediate values (accumulated_error, last_switch_date) must
    still be restored so the algorithm continues from where it left off."""

    manager = _make_manager(hass)
    last_switch = datetime(2026, 1, 1, 12, 0, 0)

    old_state = MagicMock()
    old_state.attributes = {
        "auto_start_stop_manager": {
            "is_auto_stop_detected": False,
            "auto_start_stop_enable": True,
            "auto_start_stop_level": AUTO_START_STOP_LEVEL_MEDIUM,
            "auto_start_stop_accumulated_error": 2.0,
            "auto_start_stop_accumulated_error_threshold": 5.0,
            "auto_start_stop_last_switch_date": last_switch.isoformat(),
        }
    }

    manager.restore_state(old_state)

    assert manager.is_auto_stop_detected is False
    assert manager._auto_start_stop_algo.accumulated_error == 2.0
    assert manager._auto_start_stop_algo.last_switch_date == last_switch
    assert manager._auto_start_stop_algo._last_should_be_off is False


async def test_restore_state_none_old_state(hass: HomeAssistant):
    """Test that restore_state(None) does not raise and keeps defaults."""

    manager = _make_manager(hass)

    manager.restore_state(None)  # must not raise

    assert manager.is_auto_stop_detected is False
    assert manager._auto_start_stop_algo.accumulated_error == 0
    assert manager._auto_start_stop_algo.last_switch_date is None


async def test_restore_state_no_manager_attribute(hass: HomeAssistant):
    """Test that restore_state is a no-op when auto_start_stop_manager attribute is absent.
    This covers backward-compatibility with states saved before this feature."""

    manager = _make_manager(hass)

    old_state = MagicMock()
    old_state.attributes = {}  # no auto_start_stop_manager key

    manager.restore_state(old_state)

    assert manager.is_auto_stop_detected is False
    assert manager._auto_start_stop_algo.accumulated_error == 0
    assert manager._auto_start_stop_algo.last_switch_date is None
