# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Auto Start/Stop stop mode select (off/fan_only/dry) - FR 2034 """
from datetime import datetime, timedelta
import logging

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.select import (
    AutoStartStopStopModeSelect,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


PRESET_TEMPS = {
    "frost": 7.0,
    "eco": 17.0,
    "comfort": 19.0,
    "boost": 21.0,
    "eco_ac": 27.0,
    "comfort_ac": 25.0,
    "boost_ac": 23.0,
    "frost_away": 7.1,
    "eco_away": 17.1,
    "comfort_away": 19.1,
    "boost_away": 21.1,
    "eco_ac_away": 27.1,
    "comfort_ac_away": 25.1,
    "boost_ac_away": 23.1,
}


def _build_config_entry() -> MockConfigEntry:
    """Build a MockConfigEntry for an over_climate VTherm with auto-start/stop MEDIUM."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        },
    )


def _find_stop_mode_select(hass: HomeAssistant):
    """Find the auto-start/stop stop mode select entity"""
    component = hass.data[SELECT_DOMAIN]
    for entity in list(component.entities):
        if entity.unique_id and entity.unique_id.endswith("_auto_start_stop_stop_mode"):
            return entity
    return None


async def test_stop_mode_select_options_with_full_support(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """The select should propose off/fan_only/dry when the underlying supports them"""

    config_entry = _build_config_entry()

    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "mock_climate",
        {},
        hvac_modes=[
            VThermHvacMode_OFF,
            VThermHvacMode_COOL,
            VThermHvacMode_HEAT,
            VThermHvacMode_FAN_ONLY,
            VThermHvacMode_DRY,
        ],
    )

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )
    assert vtherm is not None
    await set_all_climate_preset_temp(hass, vtherm, PRESET_TEMPS, "overclimate")

    select_entity = _find_stop_mode_select(hass)
    assert select_entity is not None

    # Resolve the associated VTherm (done automatically after a short delay in production)
    assert select_entity.my_climate is not None
    await hass.async_block_till_done()

    # Default value should be off to keep the current behavior
    assert select_entity.current_option == AUTO_START_STOP_STOP_MODE_OFF
    assert vtherm.auto_start_stop_manager.stop_mode == VThermHvacMode_OFF

    # fan_only and dry are proposed because the underlying supports them
    assert select_entity.options == [
        AUTO_START_STOP_STOP_MODE_OFF,
        AUTO_START_STOP_STOP_MODE_FAN_ONLY,
        AUTO_START_STOP_STOP_MODE_DRY,
    ]

    vtherm.remove_thermostat()


async def test_stop_mode_select_options_filtered_by_underlying(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """The select should only propose off when the underlying does not support fan_only/dry"""

    config_entry = _build_config_entry()

    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "mock_climate",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT],
    )

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )
    assert vtherm is not None
    await set_all_climate_preset_temp(hass, vtherm, PRESET_TEMPS, "overclimate")

    select_entity = _find_stop_mode_select(hass)
    assert select_entity is not None

    # Resolve the associated VTherm (done automatically after a short delay in production)
    assert select_entity.my_climate is not None
    await hass.async_block_till_done()

    assert select_entity.options == [AUTO_START_STOP_STOP_MODE_OFF]

    vtherm.remove_thermostat()


async def _drive_to_auto_stop(hass: HomeAssistant, vtherm: ThermostatOverClimate, now: datetime) -> datetime:
    """Drive the VTherm through the temperature sequence that triggers an auto-stop.
    Returns the last 'now' used."""
    # Set mode to Heat and preset to Comfort (target 19)
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == VThermHvacMode_HEAT

    # reset accumulated error (only for testing)
    now = now + timedelta(minutes=5)
    vtherm.auto_start_stop_manager._auto_start_stop_algo._accumulated_error = 0
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 19, now, False)
    await hass.async_block_till_done()

    now = now + timedelta(minutes=5)
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 20, now, False)
    await hass.async_block_till_done()

    now = now + timedelta(minutes=5)
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 21, now, False)
    await hass.async_block_till_done()
    return now


async def test_stop_mode_fan_only_and_immediate_change(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """When stop mode is fan_only, an auto-stop should switch to fan_only (not off).
    Changing the select while the stop is active must update the hvac_mode immediately."""

    config_entry = _build_config_entry()

    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "mock_climate",
        {},
        hvac_modes=[
            VThermHvacMode_OFF,
            VThermHvacMode_COOL,
            VThermHvacMode_HEAT,
            VThermHvacMode_FAN_ONLY,
            VThermHvacMode_DRY,
        ],
    )

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, config_entry, "climate.overclimate"
    )
    assert vtherm is not None
    await set_all_climate_preset_temp(hass, vtherm, PRESET_TEMPS, "overclimate")

    select_entity = _find_stop_mode_select(hass)
    assert select_entity is not None

    # Resolve the associated VTherm (done automatically after a short delay in production)
    assert select_entity.my_climate is not None
    await hass.async_block_till_done()

    # 1. Select fan_only as the stop mode
    await select_entity.async_select_option(AUTO_START_STOP_STOP_MODE_FAN_ONLY)
    await hass.async_block_till_done()
    assert vtherm.auto_start_stop_manager.stop_mode == VThermHvacMode_FAN_ONLY

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 2. Drive the VTherm to an auto-stop condition
    now = await _drive_to_auto_stop(hass, vtherm, now)
    await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_FAN_ONLY, timeout=3.0, hass=hass)

    # 3. The VTherm should be in fan_only (not off), stop is kept
    assert vtherm.auto_start_stop_manager.is_auto_stop_detected is True
    assert vtherm.hvac_mode == VThermHvacMode_FAN_ONLY
    assert vtherm.hvac_off_reason is None
    assert vtherm.hvac_mode_reason == HVAC_MODE_REASON_AUTO_START_STOP_FAN_ONLY

    # 4. Change the select to off while the stop is active -> immediate switch to off
    await select_entity.async_select_option(AUTO_START_STOP_STOP_MODE_OFF)
    await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_OFF, timeout=3.0, hass=hass)
    assert vtherm.auto_start_stop_manager.is_auto_stop_detected is True
    assert vtherm.hvac_mode == VThermHvacMode_OFF
    assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
    assert vtherm.hvac_mode_reason == HVAC_OFF_REASON_AUTO_START_STOP

    # 5. Change back to dry while the stop is active -> immediate switch to dry
    await select_entity.async_select_option(AUTO_START_STOP_STOP_MODE_DRY)
    await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_DRY, timeout=3.0, hass=hass)
    assert vtherm.hvac_mode == VThermHvacMode_DRY
    assert vtherm.hvac_off_reason is None
    assert vtherm.hvac_mode_reason == HVAC_MODE_REASON_AUTO_START_STOP_DRY

    # 6. Rising temperature -> the auto-stop is released and the VTherm restarts in heat
    now = now + timedelta(minutes=20)
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await wait_for_local_condition(lambda: vtherm.hvac_mode == VThermHvacMode_HEAT, timeout=3.0, hass=hass)
    assert vtherm.auto_start_stop_manager.is_auto_stop_detected is False
    assert vtherm.hvac_mode == VThermHvacMode_HEAT
    assert vtherm.hvac_off_reason is None
    assert vtherm.hvac_mode_reason is None

    vtherm.remove_thermostat()


async def test_stop_mode_select_restore_kept_before_underlying_ready(hass: HomeAssistant, skip_hass_states_is_state):
    """A restored value must not be discarded while the underlying hvac_modes
    are not available yet (HA start/restart scenario)."""

    select = AutoStartStopStopModeSelect(hass, "overClimateUniqueId", "overClimate", {CONF_NAME: "overClimate"})
    # Simulate the value restored from the previous run
    select._attr_current_option = AUTO_START_STOP_STOP_MODE_DRY
    # Avoid touching the real state machine
    select.async_write_ha_state = MagicMock()

    fake_climate = MagicMock()
    select._my_climate = fake_climate

    # 1. VTherm not initialized yet -> only off is exposed, but dry must be kept
    fake_climate.is_initialized = False
    fake_climate.hvac_modes = [VThermHvacMode_OFF]
    await select.async_my_climate_changed(None)
    assert select.current_option == AUTO_START_STOP_STOP_MODE_DRY

    # 2. VTherm initialized and underlying exposes dry -> still kept
    fake_climate.is_initialized = True
    fake_climate.hvac_modes = [VThermHvacMode_OFF, VThermHvacMode_DRY]
    await select.async_my_climate_changed(None)
    assert select.current_option == AUTO_START_STOP_STOP_MODE_DRY

    # 3. VTherm initialized but underlying does not support dry -> reset to off
    fake_climate.is_initialized = True
    fake_climate.hvac_modes = [VThermHvacMode_OFF, VThermHvacMode_FAN_ONLY]
    await select.async_my_climate_changed(None)
    assert select.current_option == AUTO_START_STOP_STOP_MODE_OFF

    # 4. Underlying only supporting off/heat (e.g. generic) -> restored value reset to off
    select._attr_current_option = AUTO_START_STOP_STOP_MODE_DRY
    fake_climate.is_initialized = True
    fake_climate.hvac_modes = [VThermHvacMode_OFF, VThermHvacMode_HEAT]
    await select.async_my_climate_changed(None)
    assert select.current_option == AUTO_START_STOP_STOP_MODE_OFF
