# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long
"""Tests for hvac_mode handling in climate.set_temperature (issue #2261)."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.vtherm_central_api import (
    VersatileThermostatAPI,
)

from .commons import *


async def test_over_climate_set_temperature_with_hvac_mode_turns_on_vtherm(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Issue #2261: climate.set_temperature with hvac_mode turns on an off over_climate VTherm."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    )
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 18, VThermPreset.BOOST: 21}
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    assert entity is not None

    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF

    under = entity.underlying_entity(0)
    with patch.object(under, "hass_services_async_call", new_callable=AsyncMock) as mock_under_call:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity.entity_id,
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 19,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.target_temperature == 19
    assert entity.requested_state.target_temperature == 19
    assert entity.vtherm_preset_mode == VThermPreset.NONE

    assert [call.args for call in mock_under_call.call_args_list] == [
        (CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, {ATTR_ENTITY_ID: "climate.mock_climate", "hvac_mode": HVACMode.HEAT}),
        (CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: "climate.mock_climate", ATTR_TEMPERATURE: 19}),
    ]

    entity.remove_thermostat()


async def test_over_climate_set_temperature_without_hvac_mode_stays_off(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Regression guard: climate.set_temperature without hvac_mode keeps an off VTherm off."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    )
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    under = entity.underlying_entity(0)
    with patch.object(under, "hass_services_async_call", new_callable=AsyncMock) as mock_under_call:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity.entity_id,
                ATTR_TEMPERATURE: 19,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity.target_temperature == 19
    mock_under_call.assert_not_called()

    entity.remove_thermostat()


async def test_over_climate_set_temperature_with_hvac_mode_off_turns_off_without_sending_temp(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Calling climate.set_temperature with hvac_mode=off turns off the underlying without sending temperature."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_HEAT,
        hvac_action=HVACAction.HEATING,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    )
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()
    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT

    under = entity.underlying_entity(0)
    with patch.object(under, "hass_services_async_call", new_callable=AsyncMock) as mock_under_call:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity.entity_id,
                ATTR_HVAC_MODE: HVACMode.OFF,
                ATTR_TEMPERATURE: 18,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity.target_temperature == 18
    assert [call.args for call in mock_under_call.call_args_list] == [
        (CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, {ATTR_ENTITY_ID: "climate.mock_climate", "hvac_mode": HVACMode.OFF}),
    ]

    entity.remove_thermostat()


async def test_set_temperature_rejects_unsupported_hvac_mode_without_side_effects(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """An unsupported hvac_mode raises ServiceValidationError and leaves temperature, preset, and mode untouched."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    )
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 18, VThermPreset.BOOST: 21}
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    await entity.async_set_preset_mode(VThermPreset.ECO)
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity.entity_id,
                ATTR_HVAC_MODE: HVACMode.COOL,
                ATTR_TEMPERATURE: 22,
            },
            blocking=True,
        )

    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.requested_state.hvac_mode == VThermHvacMode_OFF
    assert entity.target_temperature == 16
    assert entity.vtherm_preset_mode == VThermPreset.ECO

    entity.remove_thermostat()


async def test_set_temperature_with_hvac_mode_respects_lock(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """When locked, climate.set_temperature with hvac_mode changes neither mode nor temperature."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG
        | {
            CONF_LOCK_USERS: True,
            CONF_LOCK_AUTOMATIONS: True,
        },
    )
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 18, VThermPreset.BOOST: 21}
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    await entity.async_set_preset_mode(VThermPreset.ECO)
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    entity.lock_manager.change_lock_state(True)
    await hass.async_block_till_done()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: entity.entity_id,
            ATTR_HVAC_MODE: HVACMode.HEAT,
            ATTR_TEMPERATURE: 21,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.target_temperature == 16

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_set_temperature_with_hvac_mode_and_manual_override(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """With manual_override_duration_min enabled, hvac_mode is still applied alongside manual override."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG
        | {
            CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
            CONF_MANUAL_OVERRIDE_DURATION_MIN: 60,
        },
    )
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 18, VThermPreset.BOOST: 21}
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: entity.entity_id,
            ATTR_HVAC_MODE: HVACMode.HEAT,
            ATTR_TEMPERATURE: 22,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.target_temperature == 22
    assert entity.timed_preset_manager.is_manual_override is True
    assert entity.vtherm_preset_mode == VThermPreset.NONE

    entity.remove_thermostat()


async def test_set_temperature_with_hvac_mode_respects_open_window(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """When a window is open (turn_off action), requested_state.hvac_mode updates while current_state stays off."""
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_HEAT],
        hvac_mode=VThermHvacMode_OFF,
        hvac_action=HVACAction.OFF,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG
        | {
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
        },
    )
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()

    # Open the window
    entity.window_manager._window_state = STATE_ON
    await entity.update_states(force=True)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: entity.entity_id,
            ATTR_HVAC_MODE: HVACMode.HEAT,
            ATTR_TEMPERATURE: 20,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.requested_state.target_temperature == 20
    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_switch_set_temperature_with_hvac_mode(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
    fake_underlying_switch,
):
    """over_switch VTherm also applies hvac_mode from climate.set_temperature."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
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
        },
    )
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: entity.entity_id,
            ATTR_HVAC_MODE: HVACMode.HEAT,
            ATTR_TEMPERATURE: 21,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert entity.target_temperature == 21

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_valve_set_temperature_leaving_sleep_refreshes_central_boiler(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
    fake_underlying_valve,
):
    """over_valve leaving SLEEP via climate.set_temperature(hvac_mode=heat) refreshes central boiler accounting."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["number.mock_valve"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theovervalvemockname")
    await entity.service_set_hvac_mode_sleep()
    await hass.async_block_till_done()
    assert entity.is_sleeping is True

    mock_boiler = AsyncMock()
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    with patch.object(api, "_central_boiler_manager", mock_boiler):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity.entity_id,
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 21,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    assert entity.is_sleeping is False
    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.target_temperature == 21
    mock_boiler.refresh_active_devices.assert_awaited_once()

    entity.remove_thermostat()
