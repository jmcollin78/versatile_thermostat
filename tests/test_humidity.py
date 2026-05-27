# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test humidity control for over_climate VTherms."""

from datetime import datetime, timedelta
from unittest.mock import PropertyMock, call, patch

import pytest

from homeassistant.components.climate import ClimateEntityFeature, HVACAction
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate

from .commons import *


def _humidity_config(mode: str = CONF_HUMIDITY_MODE_DRY_ONLY) -> dict:
    """Return a standard humidity feature config."""
    return {
        CONF_USE_HUMIDITY_FEATURE: True,
        CONF_HUMIDITY_MODE: mode,
        CONF_HUMIDITY_SENSOR: "sensor.mock_humidity",
        CONF_HUMIDITY_TOLERANCE: 3,
    }


async def _create_humidity_vtherm(
    hass: HomeAssistant,
    mode: str,
    fan_modes: list[str] | None = None,
    extra_config: dict | None = None,
) -> ThermostatOverClimate:
    """Create a climate VTherm with humidity support and dry-capable AC."""
    hass.states.async_set("sensor.mock_humidity", "65")
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[
            VThermHvacMode_OFF,
            VThermHvacMode_COOL,
            VThermHvacMode_DRY,
            VThermHvacMode_HEAT,
        ],
        fan_modes=fan_modes,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_AC_CONFIG | _humidity_config(mode) | (extra_config or {}),
    )

    vtherm: ThermostatOverClimate = await create_thermostat(
        hass, entry, "climate.theoverclimatemockname"
    )
    await hass.async_block_till_done()
    return vtherm


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_target_and_external_sensor_in_dry_mode_without_auto_start_stop(
    hass: HomeAssistant,
):
    """Dry mode keeps running at target unless auto start/stop is enabled."""
    vtherm = await _create_humidity_vtherm(hass, CONF_HUMIDITY_MODE_DRY_ONLY)

    assert vtherm.humidity_manager.is_configured is True
    assert vtherm.current_humidity == 65
    assert vtherm.target_humidity == 55
    assert vtherm.supported_features & ClimateEntityFeature.TARGET_HUMIDITY

    await vtherm.async_set_humidity(50)
    await hass.async_block_till_done()

    assert vtherm.target_humidity == 50

    await vtherm.async_set_hvac_mode(VThermHvacMode_DRY)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY
    assert vtherm.hvac_action == HVACAction.DRYING

    hass.states.async_set("sensor.mock_humidity", "49")
    await wait_for_local_condition(
        lambda: vtherm.hvac_action == HVACAction.IDLE,
        hass=hass,
    )

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_dry_only_auto_start_stop_turns_off_at_target(
    hass: HomeAssistant,
):
    """Dry-only mode uses humidity hysteresis for off/on when auto start/stop is enabled."""
    vtherm = await _create_humidity_vtherm(
        hass,
        CONF_HUMIDITY_MODE_DRY_ONLY,
        extra_config={
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    await vtherm.async_set_humidity(50)
    await hass.async_block_till_done()

    await vtherm.async_set_hvac_mode(VThermHvacMode_DRY)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY

    hass.states.async_set("sensor.mock_humidity", "49")
    await wait_for_local_condition(
        lambda: vtherm.vtherm_hvac_mode == VThermHvacMode_OFF,
        hass=hass,
    )

    assert vtherm.hvac_off_reason == HVAC_OFF_REASON_HUMIDITY_TARGET_REACHED

    hass.states.async_set("sensor.mock_humidity", "54")
    await wait_for_local_condition(
        lambda: vtherm.vtherm_hvac_mode == VThermHvacMode_DRY,
        hass=hass,
    )


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_dry_only_auto_start_stop_level_none_ignores_enable_switch(
    hass: HomeAssistant,
):
    """Dry-only humidity auto-off requires an active auto start/stop level."""
    vtherm = await _create_humidity_vtherm(
        hass,
        CONF_HUMIDITY_MODE_DRY_ONLY,
        extra_config={
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        },
    )

    await vtherm.auto_start_stop_manager.set_auto_start_stop_enable(True)
    await vtherm.async_set_humidity(50)
    await vtherm.async_set_hvac_mode(VThermHvacMode_DRY)
    await hass.async_block_till_done()

    assert vtherm.auto_start_stop_manager.auto_start_stop_enable is True
    assert vtherm.auto_start_stop_manager.auto_start_stop_level == AUTO_START_STOP_LEVEL_NONE
    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY

    hass.states.async_set("sensor.mock_humidity", "49")
    await wait_for_local_condition(
        lambda: vtherm.hvac_action == HVACAction.IDLE,
        hass=hass,
    )

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_dry_only_does_not_change_cool_mode(
    hass: HomeAssistant,
):
    """Dry-only humidity control leaves requested cool mode untouched."""
    vtherm = await _create_humidity_vtherm(hass, CONF_HUMIDITY_MODE_DRY_ONLY)

    await vtherm.async_set_temperature(temperature=24)
    await send_temperature_change_event(vtherm, 23, datetime.now(get_tz(hass)), sleep=False)
    await vtherm.async_set_hvac_mode(VThermHvacMode_COOL)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_COOL


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_unavailable_sensor_clears_measurement(
    hass: HomeAssistant,
):
    """Invalid humidity sensor states stop humidity-driven decisions."""
    vtherm = await _create_humidity_vtherm(hass, CONF_HUMIDITY_MODE_DRY_ONLY)

    assert vtherm.humidity_manager.current_humidity == 65
    assert vtherm.humidity_manager.is_humidity_available is True

    hass.states.async_set("sensor.mock_humidity", STATE_UNAVAILABLE)
    await wait_for_local_condition(
        lambda: vtherm.humidity_manager.current_humidity is None,
        hass=hass,
    )

    assert vtherm.humidity_manager.is_humidity_available is False
    assert vtherm.humidity_manager.last_humidity_measure is None
    assert vtherm.humidity_manager.is_humidity_too_high is False


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_stale_measurement_does_not_drive_hvac(
    hass: HomeAssistant,
):
    """Humidity measurements older than safety delay are ignored for regulation."""
    vtherm = await _create_humidity_vtherm(
        hass,
        CONF_HUMIDITY_MODE_DRY_ONLY,
        extra_config={CONF_HUMIDITY_SAFETY_DELAY_MIN: 5},
    )
    old_measure = datetime.now(get_tz(hass)) - timedelta(minutes=10)

    assert vtherm.humidity_manager._update_current_humidity(65, old_measure) is True

    assert vtherm.humidity_manager.current_humidity is None
    assert vtherm.humidity_manager.is_humidity_available is False
    assert vtherm.humidity_manager.is_humidity_too_high is False
    assert (
        vtherm.humidity_manager.calculate_hvac_mode(
            VThermHvacMode_DRY,
            VThermHvacMode_OFF,
            [VThermHvacMode_DRY],
        )
        is None
    )


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_dry_only_auto_fan_uses_humidity_gap(
    hass: HomeAssistant,
):
    """Dry-only mode drives auto fan from humidity instead of temperature."""
    vtherm = await _create_humidity_vtherm(
        hass,
        CONF_HUMIDITY_MODE_DRY_ONLY,
        fan_modes=["low", "medium", "high", "quiet", "auto"],
        extra_config={CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_MEDIUM},
    )

    assert vtherm._auto_activated_fan_mode == "medium"
    assert vtherm._auto_deactivated_fan_mode == "quiet"

    await vtherm.async_set_humidity(50)
    await hass.async_block_till_done()

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await vtherm.async_set_hvac_mode(VThermHvacMode_DRY)
        await hass.async_block_till_done()

        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("medium")])

    with patch.object(type(vtherm), "fan_mode", new_callable=PropertyMock, return_value="medium"):
        with patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
        ) as mock_send_fan_mode:
            hass.states.async_set("sensor.mock_humidity", "52")
            await hass.async_block_till_done()

            mock_send_fan_mode.assert_has_calls([call.set_fan_mode("quiet")])


@pytest.mark.usefixtures("skip_hass_states_is_state", "fake_temp_sensor", "fake_ext_temp_sensor", "skip_send_event")
async def test_humidity_cool_assist_switches_between_cool_and_dry(
    hass: HomeAssistant,
):
    """Cool assist keeps cooling primary and uses dry only after temperature is satisfied."""
    vtherm = await _create_humidity_vtherm(hass, CONF_HUMIDITY_MODE_COOL_ASSIST)

    await vtherm.async_set_temperature(temperature=24)
    await send_temperature_change_event(vtherm, 26, datetime.now(get_tz(hass)), sleep=False)
    await vtherm.async_set_hvac_mode(VThermHvacMode_COOL)
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_COOL

    await send_temperature_change_event(vtherm, 24, datetime.now(get_tz(hass)), sleep=False)
    await wait_for_local_condition(
        lambda: vtherm.vtherm_hvac_mode == VThermHvacMode_DRY,
        hass=hass,
    )

    assert vtherm.hvac_action == HVACAction.DRYING

    hass.states.async_set("sensor.mock_humidity", "54")
    await hass.async_block_till_done()

    assert vtherm.vtherm_hvac_mode == VThermHvacMode_DRY

    await send_temperature_change_event(vtherm, 26, datetime.now(get_tz(hass)), sleep=False)
    await wait_for_local_condition(
        lambda: vtherm.vtherm_hvac_mode == VThermHvacMode_COOL,
        hass=hass,
    )
