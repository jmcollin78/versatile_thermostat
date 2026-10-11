# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the manual override with automatic revert to the previous preset (issue #1875) """
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_timed_preset_manager import FeatureTimedPresetManager
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


def build_over_switch_entry(extra: dict | None = None, unique_id="uniqueId") -> MockConfigEntry:
    """Build an over_switch VTherm config entry with presets"""
    data = {
        CONF_NAME: "TheOverSwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        "eco_temp": 17,
        "comfort_temp": 19,
        "boost_temp": 21,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_UNDERLYING_LIST: ["switch.mock_switch"],
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_MINIMAL_ACTIVATION_DELAY: 30,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.3,
    }
    if extra:
        data.update(extra)
    return MockConfigEntry(domain=DOMAIN, title="TheOverSwitchMockName", unique_id=unique_id, data=data)


#
# Task 1 - configuration
#
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_default_zero(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm without the option has the manual override disabled"""
    entity: BaseThermostat = await create_thermostat(hass, build_over_switch_entry(), "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 0
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_specific(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm with its own advanced configuration uses its own duration"""
    entry = build_over_switch_entry({CONF_USE_ADVANCED_CENTRAL_CONFIG: False, CONF_MANUAL_OVERRIDE_DURATION_MIN: 20})
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 20
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_from_central(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm using the central advanced configuration takes the central duration"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG | {CONF_MANUAL_OVERRIDE_DURATION_MIN: 45})

    entry = build_over_switch_entry({CONF_USE_ADVANCED_CENTRAL_CONFIG: True, CONF_MANUAL_OVERRIDE_DURATION_MIN: 20})
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 45
    entity.remove_thermostat()
