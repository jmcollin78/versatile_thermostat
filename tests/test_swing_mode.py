# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

"""Test the swing mode of a over_climate Vtherm"""
from unittest.mock import patch, call

from datetime import datetime  # , timedelta

from homeassistant.core import HomeAssistant

# from homeassistant.components.climate import HVACAction
from homeassistant.config_entries import ConfigEntryState

# from homeassistant.helpers.entity_component import EntityComponent
# from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_swing_horizontal_mode(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that swing horizontal mode is handled correctly"""

    swing_horizontal_modes = ["auto", "1", "2", "3"]

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_NONE,
        },  # 5 minutes security delay
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass, "mock_climate", "MockClimateName", {}, swing_horizontal_modes=swing_horizontal_modes, swing_horizontal_mode="1"
    )

    # fake_underlying_climate = MockClimate(
    #     hass=hass,
    #     unique_id="mock_climate",
    #     name="mock_climate",
    #     swing_horizontal_modes=swing_horizontal_modes,
    #     swing_horizontal_mode="1",
    # )

    # 1. Init swing horizontal mode
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.swing_horizontal_modes == swing_horizontal_modes
    assert entity.swing_horizontal_mode == "1"

    # 2. Change swing horizontal mode
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode") as mock_send_fan_mode:
        await entity.async_set_swing_horizontal_mode("auto")
        assert entity._swing_horizontal_mode == "auto"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_swing_mode(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that swing mode is handled correctly"""

    swing_modes = ["auto", "1", "2", "3"]

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_NONE,
        },  # 5 minutes security delay
    )

    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, swing_modes=swing_modes, swing_mode="1")

    # fake_underlying_climate = MockClimate(
    #     hass=hass,
    #     unique_id="mock_climate",
    #     name="mock_climate",
    #     swing_modes=swing_modes,
    #     swing_mode="1",
    # )

    # 1. Init swing mode
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.swing_modes == swing_modes
    assert entity.swing_mode == "1"

    # 2. Change swing mode
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode") as mock_send_fan_mode:
        await entity.async_set_swing_mode("auto")
        assert entity._swing_mode == "auto"
