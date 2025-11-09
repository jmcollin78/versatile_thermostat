# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import logging
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
    assert auto_start_stop_manager.auto_start_stop_enable is False
    assert auto_start_stop_manager._auto_start_stop_algo is not None

    custom_attributes = {}
    auto_start_stop_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_auto_start_stop_configured"] is is_configured

    if auto_start_stop_manager.is_configured:
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_enable"] is False
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_level"] == level if level and is_configured else AUTO_START_STOP_LEVEL_NONE
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_dtmin"] == auto_start_stop_manager._auto_start_stop_algo.dt_min
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_accumulated_error"] == auto_start_stop_manager._auto_start_stop_algo.accumulated_error
        assert (
            custom_attributes["auto_start_stop_manager"]["auto_start_stop_accumulated_error_threshold"] == auto_start_stop_manager._auto_start_stop_algo.accumulated_error_threshold
        )
        assert custom_attributes["auto_start_stop_manager"]["auto_start_stop_last_switch_date"] == auto_start_stop_manager._auto_start_stop_algo.last_switch_date
