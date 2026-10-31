"""HA history adapter tests: native State events and duration accounting."""

from datetime import datetime, timedelta, UTC
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from homeassistant.core import State

from custom_components.versatile_thermostat.tpi_history import (
    build_grid,
    check_classic_tpi,
    history_sources,
    interval_values,
    require_history,
)
from custom_components.versatile_thermostat.tpi_identification import (
    IdentificationError,
)

START = datetime(2026, 10, 1, tzinfo=UTC)
SOURCES = {
    "temperature_source": "sensor.inside",
    "external_temperature_source": "sensor.outside",
    "heating_source": "switch.heater",
    "window_source": "binary_sensor.window",
    "climate_source": "climate.test",
    "safety_source": "binary_sensor.safety",
    "power_source": None,
    "inverse_switch": False,
    "primary_resolution": 10,
}


def histories(days):
    def state(entity_id, value, when, attrs=None):
        return State(
            entity_id, value, attrs or {}, last_changed=when, last_updated=when
        )

    result = {}
    for entity_id, value in [("sensor.inside", "20"), ("sensor.outside", "8")]:
        result[entity_id] = [
            state(
                entity_id,
                value,
                START + timedelta(minutes=30 * i),
                {"unit_of_measurement": "°C"},
            )
            for i in range(days * 48 + 1)
        ]
    for entity_id, value in [
        ("switch.heater", "on"),
        ("climate.test", "heat"),
        ("binary_sensor.window", "off"),
        ("binary_sensor.safety", "off"),
    ]:
        result[entity_id] = [state(entity_id, value, START)]
    return result


@pytest.mark.parametrize(
    "days,accepted", [(6, False), (7, True), (10, True), (14, True), (20, True)]
)
def test_coverage(days, accepted):
    _, summary = build_grid(
        histories(days), SOURCES, START, START + timedelta(days=days)
    )
    assert summary["history_usable_days"] == min(days, 14)
    assert summary["history_available_days"] == min(days, 14)
    if accepted:
        require_history(summary)
    else:
        with pytest.raises(IdentificationError, match="insufficient_history"):
            require_history(summary)


def test_short_events_are_not_missed():
    stamps = [(0, 0), (0.2, 1), (0.3, 0)]
    assert interval_values(stamps, np.array([0.0]))[0] == pytest.approx(0.1)
    assert interval_values(stamps, np.array([0.0]), maximum=True)[0] == 1


def test_missing_and_nonoverlapping_histories():
    states = histories(10)
    states["sensor.outside"] = []
    with pytest.raises(IdentificationError, match="missing_external_temperature"):
        build_grid(states, SOURCES, START, START + timedelta(days=10))
    states = histories(10)
    states["switch.heater"] = []
    with pytest.raises(IdentificationError, match="missing_heating_history"):
        build_grid(states, SOURCES, START, START + timedelta(days=10))
    states = histories(10)
    states["sensor.outside"] = [
        State(
            "sensor.outside",
            "8",
            {"unit_of_measurement": "°C"},
            last_updated=START + timedelta(days=11),
        )
    ]
    with pytest.raises(IdentificationError, match="histories_do_not_overlap"):
        build_grid(states, SOURCES, START, START + timedelta(days=10))


@pytest.mark.parametrize(
    "function,config,learning,accepted",
    [
        ("tpi", {}, False, True),
        ("smartpi", {}, False, False),
        ("tpi", {"auto_tpi_mode": True}, False, False),
        ("tpi", {"auto_tpi_continuous_kext": True}, False, False),
        ("tpi", {}, True, False),
    ],
)
def test_classic_tpi_only(function, config, learning, accepted):
    thermostat = SimpleNamespace(
        proportional_function=function,
        entry_infos=config,
        auto_tpi_manager=SimpleNamespace(learning_active=learning),
    )
    if accepted:
        check_classic_tpi(thermostat)
    else:
        with pytest.raises(IdentificationError, match="not_classic_tpi"):
            check_classic_tpi(thermostat)


def test_invalid_minutes_window_and_safety():
    states = histories(10)

    def event(entity_id, value, minute):
        return State(entity_id, value, last_updated=START + timedelta(minutes=minute))

    states["binary_sensor.window"] += [
        event("binary_sensor.window", "on", 1.2),
        event("binary_sensor.window", "off", 1.3),
    ]
    states["binary_sensor.safety"] += [
        event("binary_sensor.safety", "on", 20),
        event("binary_sensor.safety", "off", 30),
    ]
    states["switch.heater"] += [
        event("switch.heater", "unavailable", 40),
        event("switch.heater", "on", 50),
    ]
    grid, summary = build_grid(states, SOURCES, START, START + timedelta(days=10))
    assert grid.window[1] == 1
    assert not np.any(grid.valid[20:30])
    assert not np.any(grid.valid[40:50])
    assert summary["history_usable_days"] < 10


def test_multiple_switches_use_vtherm_equal_power_convention():
    states = histories(10)
    states["switch.second"] = [State("switch.second", "off", last_updated=START)]
    sources = {**SOURCES, "heating_sources": ["switch.heater", "switch.second"]}
    grid, _ = build_grid(states, sources, START, START + timedelta(days=10))
    np.testing.assert_equal(grid.heater, np.full(len(grid.time), 0.5))
    del states["switch.second"]
    with pytest.raises(IdentificationError, match="missing_heating_history"):
        build_grid(states, sources, START, START + timedelta(days=10))


def test_source_resolution_multiple_switches_and_unsupported_virtual():
    from unittest.mock import Mock

    thermostat = SimpleNamespace(
        entity_id="climate.test",
        proportional_function="tpi",
        auto_tpi_manager=None,
        is_over_switch=True,
        is_initialized=True,
        temperature_unit="°C",
        cycle_min=5,
        ext_temp_sensor_entity_id="sensor.outside",
        entry_infos={
            "temperature_sensor_entity_id": "sensor.inside",
            "underlying_entity_ids": ["switch.first", "switch.second"],
        },
    )
    entries = [
        SimpleNamespace(
            domain="binary_sensor",
            platform="versatile_thermostat",
            translation_key="safety_state",
            entity_id="binary_sensor.safety",
        )
    ]
    registry = Mock()
    with patch(
        "custom_components.versatile_thermostat.tpi_history.er.async_get",
        return_value=registry,
    ), patch(
        "custom_components.versatile_thermostat.tpi_history.er.async_entries_for_config_entry",
        return_value=entries,
    ):
        sources = history_sources(None, thermostat)
        assert sources["heating_weights"] == [0.5, 0.5]
        assert sources["primary_resolution"] == 5
        thermostat.entry_infos["vswitch_on_command"] = ["turn_on"]
        with pytest.raises(IdentificationError, match="ambiguous_heating_history"):
            history_sources(None, thermostat)


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Prepare the database before the project's autouse HA fixture starts."""


@pytest.mark.freeze_time("2026-10-01 00:00:00")
async def test_native_recorder_roundtrip(recorder_mock, hass, freezer):
    """Read real Recorder State objects through the public history API."""
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )
    from custom_components.versatile_thermostat.tpi_history import async_load_history

    hass.states.async_set("sensor.inside", "20", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.outside", "8", {"unit_of_measurement": "°C"})
    hass.states.async_set("switch.heater", "on")
    hass.states.async_set("climate.test", "heat")
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set("binary_sensor.safety", "off")
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=2))
    hass.states.async_set("switch.heater", "off")
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=4))
    grid, summary = await async_load_history(hass, SOURCES)
    valid = grid.valid
    assert summary["history_requested_days"] == 14
    assert summary["history_usable_days"] == pytest.approx(4 / 1440)
    np.testing.assert_equal(grid.heater[valid], [1, 1, 0, 0])
    np.testing.assert_equal(grid.temp_in[valid], [20, 20, 20, 20])
