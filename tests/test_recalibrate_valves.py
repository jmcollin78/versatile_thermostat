""" Tests for recalibrate valves service in thermostat_climate_valve.py """
# pylint: disable=protected-access, wildcard-import, unused-wildcard-import

import asyncio
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.const import *
from custom_components.versatile_thermostat.const import CONF_THERMOSTAT_CLIMATE
from custom_components.versatile_thermostat.thermostat_climate_valve import ThermostatOverClimateValve
from .commons import create_thermostat


class DummyUnderlying:
    """ Dummy underlying with valve regulation support for testing """
    def __init__(self, opening, closing):
        self.opening_degree_entity_id = opening
        self.closing_degree_entity_id = closing

    async def send_value_to_number(self, entity_id, value):
        """ Simulate sending value to number entity """
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_recalibrate_starts_task(hass, skip_hass_states_get, monkeypatch):
    """ Test that recalibrate valves service starts a background task """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="name",
        unique_id="unique",
        data={
            CONF_NAME: "name",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_SYNC_ENTITY_LIST: ["number.mock_offset_calibration"],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
        },
    )
    # Create a thermostat using helper
    thermostat:ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.name")

    # patch underlyings valve regulation to include our dummy underlying
    dummy = DummyUnderlying("number.mock_opening_degree", "number.mock_closing_degree")
    thermostat._underlyings_valve_regulation = [dummy]

    called = {}

    def fake_create_task(coro):
        # schedule the coroutine to actually run to avoid 'never awaited' warnings
        called["task"] = True
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            # If no running loop (should not happen in pytest-asyncio), fallback
            asyncio.create_task(coro)

    monkeypatch.setattr(hass, "async_create_task", fake_create_task)

    result = await thermostat.service_recalibrate_valves(0)

    assert isinstance(result, dict)
    assert result.get("message") == "calibrage en cours"
    assert called.get("task", False) is True


@pytest.mark.asyncio
async def test_recalibrate_concurrent_guard(hass, skip_hass_states_get, monkeypatch):
    """ Test that recalibrate valves service refuses to start if already running """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="name",
        unique_id="unique",
        data={
            CONF_NAME: "name",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_SYNC_ENTITY_LIST: ["number.mock_offset_calibration"],
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
        },
    )
    thermostat = await create_thermostat(hass, entry, "climate.name")

    dummy = DummyUnderlying("number.mock_opening_degree", "number.mock_closing_degree")
    thermostat._underlyings_valve_regulation = [dummy]

    called = {}

    def fake_create_task(coro):
        # do not swallow the coroutine: schedule to run and mark called
        called["task"] = True
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.create_task(coro)

    monkeypatch.setattr(hass, "async_create_task", fake_create_task)

    thermostat._recalibrate_lock = asyncio.Lock()
    await thermostat._recalibrate_lock.acquire()

    result = await thermostat.service_recalibrate_valves(0)

    assert isinstance(result, dict)
    assert called.get("task", False) is False

    thermostat._recalibrate_lock.release()
