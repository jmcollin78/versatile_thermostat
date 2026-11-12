"""Experimental valve-command history: source semantics and refusal boundaries."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest
from homeassistant.core import State

from custom_components.versatile_thermostat.tpi_history import TPIHistory
from custom_components.versatile_thermostat.tpi_identification import (
    IdentificationError,
    TPIIdentification,
)
from .test_tpi_history import START, SOURCES, histories
from .test_tpi_identification import synthetic

VALVE_SOURCES = {
    **SOURCES,
    "heating_source": "climate.test",
    "heating_sources": ["climate.test"],
    "heating_source_kind": "valve_open_percent_command_proxy",
}


def event(value, minute=0, state="heat"):
    attrs = {} if value is None else {"valve_open_percent": value}
    return State(
        "climate.test", state, attrs, last_updated=START + timedelta(minutes=minute)
    )


def test_resolve_valve_command_and_reject_plain_climate():
    thermostat = SimpleNamespace(
        entity_id="climate.test",
        is_over_switch=False,
        is_over_climate=True,
        have_valve_regulation=True,
        is_initialized=True,
        temperature_unit="°C",
        cycle_min=5,
        proportional_function="tpi",
        auto_tpi_manager=None,
        ext_temp_sensor_entity_id="sensor.outside",
        entry_infos={"temperature_sensor_entity_id": "sensor.inside"},
    )
    entries = [
        SimpleNamespace(
            domain="binary_sensor",
            platform="versatile_thermostat",
            translation_key="safety_state",
            entity_id="binary_sensor.safety",
        )
    ]
    with patch(
        "custom_components.versatile_thermostat.tpi_history.er.async_get",
        return_value=Mock(),
    ), patch(
        "custom_components.versatile_thermostat.tpi_history.er.async_entries_for_config_entry",
        return_value=entries,
    ):
        sources = TPIHistory.resolve_sources(None, thermostat)
        assert sources["heating_sources"] == ["climate.test"]
        assert sources["heating_source_kind"] == "valve_open_percent_command_proxy"
        assert sources["heating_aggregation"] == "recorded_valve_command_divided_by_100"
        assert sources["inverse_switch"] is False
        thermostat.have_valve_regulation = False
        with pytest.raises(IdentificationError, match="unsupported_thermostat_type"):
            TPIHistory.resolve_sources(None, thermostat)
        thermostat.have_valve_regulation = True
        thermostat.proportional_function = "smartpi"
        with pytest.raises(IdentificationError, match="not_classic_tpi"):
            TPIHistory.resolve_sources(None, thermostat)


def test_integrates_command_without_hvac_action_or_switch_fallback():
    states = histories(1)
    states["climate.test"] = [event(20), event(80, 0.25), event(None, 1), event(40, 2)]
    grid, _ = TPIHistory(None, VALVE_SOURCES).build_grid(
        states, START, START + timedelta(minutes=4)
    )
    np.testing.assert_allclose(grid.heater, [0.65, np.nan, 0.4, 0.4], equal_nan=True)
    assert not grid.valid[1]


@pytest.mark.parametrize("value", [None, True, -1, 101, "bad", "nan", float("inf")])
def test_invalid_command_is_not_zero_or_clipped(value):
    states = histories(1)
    states["climate.test"] = [event(value)]
    with pytest.raises(IdentificationError, match="missing_heating_history"):
        TPIHistory(None, VALVE_SOURCES).build_grid(
            states, START, START + timedelta(minutes=4)
        )


@pytest.mark.parametrize("state", ["unknown", "unavailable", "off", "cool"])
def test_unavailable_or_nonheating_climate_is_excluded(state):
    states = histories(1)
    states["climate.test"] = [event(60), event(60, 1, state), event(60, 2)]
    grid, _ = TPIHistory(None, VALVE_SOURCES).build_grid(
        states, START, START + timedelta(minutes=4)
    )
    assert not grid.valid[1]
    assert grid.valid[0] and grid.valid[2]


def test_no_backfill_from_future_command():
    states = histories(1)
    states["climate.test"] = [event(None), event(50, 2)]
    grid, _ = TPIHistory(None, VALVE_SOURCES).build_grid(
        states, START, START + timedelta(minutes=4)
    )
    assert not np.any(grid.valid[:2])
    np.testing.assert_equal(grid.heater[2:], [0.5, 0.5])


def test_recorded_valve_pipeline_recovers_known_linear_model():
    original, g, gain = synthetic()
    states = histories(10)
    for entity_id, values in [
        ("sensor.inside", original.temp_in),
        ("sensor.outside", original.temp_out),
    ]:
        states[entity_id] = [
            State(
                entity_id,
                str(values[i]),
                {"unit_of_measurement": "°C"},
                last_updated=START + timedelta(minutes=i),
            )
            for i in range(0, len(values), 10)
        ]
    states["climate.test"] = [
        event(original.heater[i] * 100, i) for i in range(0, len(original.time), 10)
    ]
    grid, summary = TPIHistory(None, VALVE_SOURCES).build_grid(
        states, START, START + timedelta(days=10)
    )
    TPIHistory.require_history(summary)
    result = TPIIdentification(grid, 10).analyze()
    assert result["proposed"]["coef_ext"] == pytest.approx(g / gain)
    assert result["recommendation_reliable"] is False
    assert result["estimate_quality"] == "exploratory"
    # A good fit on an ideal linear proxy does not validate a hydronic installation.
    assert result["experimental_estimator"]["status"] == "unavailable"


@pytest.mark.freeze_time("2026-10-01 00:00:00")
async def test_recorder_retains_attribute_only_valve_command_changes(
    recorder_mock, hass, freezer
):
    """Exercise the actual Recorder query, including climate attribute changes."""
    from pytest_homeassistant.components.recorder.common import (
        async_wait_recording_done,
    )

    hass.states.async_set("sensor.inside", "20", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.outside", "8", {"unit_of_measurement": "°C"})
    hass.states.async_set("binary_sensor.safety", "off")
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set("climate.test", "heat", {"valve_open_percent": 20})
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=2))
    hass.states.async_set("climate.test", "heat", {"valve_open_percent": 80})
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=4))
    grid, summary = await TPIHistory(hass, VALVE_SOURCES).async_load()
    np.testing.assert_allclose(grid.heater[grid.valid], [0.2, 0.2, 0.8, 0.8])
    assert summary["history_usable_days"] == pytest.approx(4 / 1440)


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Start the Recorder test database before the global HA fixture."""


def test_constant_valve_command_cannot_identify_coefficients():
    states = histories(10)
    states["climate.test"] = [event(50)]
    grid, summary = TPIHistory(None, VALVE_SOURCES).build_grid(
        states, START, START + timedelta(days=10)
    )
    TPIHistory.require_history(summary)
    result = TPIIdentification(grid, 10).analyze()
    assert result["status"] == "error"
    assert "proposed" not in result


@pytest.mark.parametrize("missing", ["safety_source", "power_source", "window_source"])
def test_valve_proxy_never_bypasses_required_exclusion_history(missing):
    states = histories(10)
    states["climate.test"] = [event(50)]
    sources = {**VALVE_SOURCES, "power_source": "binary_sensor.power"}
    states["binary_sensor.power"] = [
        State("binary_sensor.power", "off", last_updated=START)
    ]
    del states[sources[missing]]
    with pytest.raises(IdentificationError, match="missing_exclusion_history"):
        TPIHistory(None, sources).build_grid(states, START, START + timedelta(days=10))


@pytest.mark.parametrize(
    "scenario",
    ["linear", "nonlinear", "boiler_cycles", "water_temperature", "stuck_valve"],
)
def test_hydronic_model_mismatch_never_certifies_a_pair(scenario):
    """Independent room energy balance; command need not equal delivered heat.

    This is a stress regression, not evidence of accuracy on a real installation.
    Only the ideal linear case has a coefficient-recovery assertion.
    """
    import math
    from custom_components.versatile_thermostat.tpi_identification import Grid

    rng = np.random.default_rng(42)
    minutes, days = 10, 10
    n = days * 144
    dt = minutes / 60
    h, capacity, power = 30.0, 3000.0, 1000.0
    a = math.exp(-h * dt / capacity)
    outside = 8 + 3 * np.sin(np.arange(n) * 2 * np.pi / 144)
    command = rng.uniform(0.1, 0.9, n)
    delivered = command.copy()
    if scenario == "nonlinear":
        delivered = command**2
    elif scenario == "boiler_cycles":
        delivered *= np.arange(n) % 12 < 8
    elif scenario == "water_temperature":
        delivered *= 0.7 + 0.3 * np.sin(np.arange(n) * 2 * np.pi / 144)
    elif scenario == "stuck_valve":
        delivered[:] = 0
    inside = np.empty(n)
    inside[0] = 19
    for i in range(n - 1):
        inside[i + 1] = (
            a * inside[i] + (1 - a) * outside[i] + power / h * (1 - a) * delivered[i]
        )
    grid = Grid(
        np.arange(n * minutes, dtype=float),
        np.repeat(inside, minutes),
        np.repeat(outside, minutes),
        np.repeat(command, minutes),
        np.zeros(n * minutes),
        np.zeros(n * minutes, dtype=bool),
    )
    result = TPIIdentification(grid, minutes).analyze()
    if result["status"] == "error":
        assert "proposed" not in result
    else:
        assert scenario != "stuck_valve"
        assert result["recommendation_reliable"] is False
        assert result["estimate_quality"] == "exploratory"
        assert 0 <= result["proposed"]["coef_int"] <= 10
        assert 0 <= result["proposed"]["coef_ext"] <= 1
        if scenario == "linear":
            assert result["proposed"]["coef_ext"] == pytest.approx(h / power)
            assert result["proposed"]["coef_int"] == pytest.approx(
                (a - math.exp(-dt / 6)) / (power / h * (1 - a))
            )
