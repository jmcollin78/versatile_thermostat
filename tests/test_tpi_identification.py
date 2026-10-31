"""Scientific regression tests for the CSV-free TPI identification port."""

import json
import math

import numpy as np
import pytest

from custom_components.versatile_thermostat.tpi_identification import (
    Grid,
    IdentificationError,
    aggregate_cycles,
    analyze_grid,
    block_bootstrap,
    fit_resolution,
    kint_for_tau,
    sample_previous,
)


def synthetic(days=10, noise=0.0):
    """Known 10-minute 1R1C model with independently excited outdoor/heat input."""
    rng = np.random.default_rng(20261030)
    n = days * 144
    inside = np.empty(n)
    inside[0] = 20
    outside = 8 + 4 * np.sin(np.arange(n) / 73)
    heat = rng.uniform(0.1, 0.9, n)
    g, gain, bias = 0.002, 0.08, -0.01
    for i in range(n - 1):
        inside[i + 1] = (
            inside[i]
            + g * (outside[i] - inside[i])
            + gain * heat[i]
            + bias
            + rng.normal(0, noise)
        )
    return (
        Grid(
            np.arange(n * 10, dtype=float),
            np.repeat(inside, 10),
            np.repeat(outside, 10),
            np.repeat(heat, 10),
            np.zeros(n * 10),
            np.zeros(n * 10, dtype=bool),
        ),
        g,
        gain,
    )


@pytest.mark.parametrize("noise,tolerance", [(0, 1e-8), (0.001, 0.08)])
def test_known_model_and_chronological_validation(noise, tolerance):
    grid, g, gain = synthetic(noise=noise)
    fit, train = fit_resolution(grid, 10)
    assert fit["coef_ext"] == pytest.approx(g / gain, rel=tolerance)
    expected = (1 - g - math.exp(-(10 / 60) / 6)) / gain
    assert kint_for_tau(fit["A"], fit["B"], 10) == pytest.approx(
        expected, rel=tolerance
    )
    assert fit["train_cycles"] == int(fit["cycles"] * 0.7)
    assert fit["train_end"] < fit["validation_start"]
    assert train[-1, 0] == fit["train_end"]
    assert fit["validation"]["rmse"] < 0.01


def test_multi_resolution_and_structured_bootstrap():
    grid, _, _ = synthetic()
    result = analyze_grid(grid, 10)
    assert result["status"] == "success"
    assert [x["resolution_min"] for x in result["multi_resolution"]] == [10, 20, 30, 60]
    assert result["proposed"]["closed_loop_hours"] == 6
    assert [
        x["closed_loop_hours"] for x in result["coef_int_by_closed_loop_hours"]
    ] == [3, 4, 5, 6, 8, 10, 12]
    assert result["bootstrap"]["repetitions"] == 1000
    json.dumps(result, allow_nan=False)


def test_bootstrap_deterministic():
    grid, _, _ = synthetic()
    _, train = fit_resolution(grid, 10)
    assert block_bootstrap(train, 10, 50) == block_bootstrap(train, 10, 50)


def test_gaps_windows_and_unknown_exclude_without_bridging():
    grid, g, gain = synthetic()
    grid.temp_in[300:450] = np.nan
    grid.temp_out[700:750] = np.nan
    grid.window[1000:1005] = 1
    grid.heater[2000:2050] = np.nan
    grid.excluded[3000:3050] = True
    rows, counts = aggregate_cycles(grid, 10)
    assert counts["window_cycles_excluded"] == 1
    assert not np.any(np.isin(rows[:, 0], [290, 300, 440, 990, 1000, 2990, 3000]))
    fit, _ = fit_resolution(grid, 10)
    assert fit["coef_ext"] == pytest.approx(g / gain)


def test_insufficient_cycles_and_history():
    grid, _, _ = synthetic(days=1)
    with pytest.raises(IdentificationError, match="insufficient_cycles"):
        fit_resolution(grid, 60)
    with pytest.raises(IdentificationError, match="insufficient_usable_history"):
        analyze_grid(grid, 10)


def test_nonphysical_model_rejected():
    grid, _, _ = synthetic()
    # Replace the temperature increments with the opposite heating sign.
    grid.temp_in = -grid.temp_in + 40
    with pytest.raises(IdentificationError, match="invalid_physical_model"):
        fit_resolution(grid, 10)


def test_ill_conditioned_model_rejected():
    grid, _, _ = synthetic()
    grid.heater[:] = 0.5
    with pytest.raises(IdentificationError, match="ill_conditioned_model"):
        fit_resolution(grid, 10)


def test_fill_is_causal_elapsed_time_limited_and_unknown_invalidates():
    times = np.array([0, 30, 60, 61, 90, 91, 120], dtype=float)
    values = sample_previous([(0, 20), (90, math.nan), (120, 22)], times)
    np.testing.assert_equal(values, [20, 20, 20, math.nan, math.nan, math.nan, 22])
