"""Independent physical simulations and failure guards for experimental TPI fitting."""

import json
import math
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from custom_components.versatile_thermostat import tpi_identification as m


def simulate(module, seed=0, scenario="noise", days=14, minutes=10):
    rng = np.random.default_rng(seed)
    n = int(days * 1440 / minutes) + 1
    dt = minutes / 60
    h, c, power, gains = 30.0, 3000.0, 1000.0, 40.0
    if scenario == "light_room":
        h, c, power = 50.0, 1000.0, 1500.0
    if scenario == "heavy_room":
        h, c, power = 20.0, 6000.0, 1200.0
    if scenario == "weak_heater":
        power = 2.0
    a = math.exp(-h * dt / c)
    g = 1 - a
    b = power / h * g
    q = gains / h * g
    true = np.empty(n)
    observed = np.empty(n)
    duty = np.empty(n)
    true[0] = 19.0
    t = np.arange(n) * minutes
    outside = 8 + 3 * np.sin(t * 2 * np.pi / 1440)
    target = 19 + 1.5 * ((t % 1440 >= 420) & (t % 1440 < 1320))
    sd = (
        0.0
        if scenario
        in ("clean", "quantized", "constant", "weak_excitation", "collinear")
        else 0.03
    )
    quantum = 0.1 if scenario in ("quantized", "coloured", "delayed") else 0.0
    perturbation = 0.0
    last_sensor_stamp = 0
    stamps = np.arange(n, dtype=float) * minutes
    for i in range(n):
        observed[i] = true[i] + rng.normal(0, sd)
        if quantum:
            observed[i] = np.round(observed[i] / quantum) * quantum
        if scenario == "delayed" and i % 6:
            observed[i] = observed[i - 1]
            stamps[i] = last_sensor_stamp
        else:
            last_sensor_stamp = stamps[i]
        duty[i] = round(
            float(
                np.clip(
                    0.6 * (target[i] - observed[i]) + 0.03 * (target[i] - outside[i]),
                    0,
                    1,
                )
            ),
            2,
        )
        if scenario == "constant":
            duty[i] = 0.5
        if scenario == "weak_excitation":
            duty[i] = 0.35 + 0.001 * math.sin(i / 31)
        if scenario == "collinear":
            duty[i] = 0.03 * (observed[i] - outside[i])
        if i < n - 1:
            if scenario in ("coloured", "delayed"):
                perturbation = 0.97 * perturbation + rng.normal(0, 0.0008)
            true[i + 1] = a * true[i] + g * outside[i] + b * duty[i] + q + perturbation
    grid = module.Grid(
        np.arange(n * minutes, dtype=float),
        np.repeat(observed, minutes),
        np.repeat(outside, minutes),
        np.repeat(duty, minutes),
        np.zeros(n * minutes),
        np.zeros(n * minutes, dtype=bool),
        np.repeat(stamps, minutes),
    )
    if scenario == "gaps":
        grid.temp_in[3000:3120] = np.nan
        grid.excluded[5000:5060] = True
        grid.window[8000:8020] = 1
    rows, _ = module.aggregate_cycles(grid, minutes)
    reference = {"g": g, "B": b, "q": q, "A": a, "resolution_min": minutes}
    return (
        grid,
        rows,
        reference,
        {"coef_ext": h / power, "coef_int": (a - math.exp(-dt / 6)) / b},
    )


def optimizer_result(
    g=0.0015, b=0.055, q=0.006, Q=0.0009, R=0.0009, success=True, fun=-5.0
):
    return SimpleNamespace(
        x=np.array([np.log(g), np.log(b), q / 0.01, np.log(Q), np.log(R)]),
        success=success,
        fun=fun,
    )


def refused(fit):
    assert fit["status"] == "unavailable", fit
    assert "reason" in fit
    assert not any(k in fit for k in ["coef_int_6h", "coef_ext", "g", "B", "q"]), fit
    json.dumps(fit, allow_nan=False)


@pytest.mark.parametrize(
    "g,b",
    [
        (0.0005020932917764445, 0.0000010102468356675683),
        (0.05, 0.08),
        (0.001, 0.0001),
        (0.1, 0.05),
    ],
)
def test_invalid_derived_coefficients_are_not_returned(g, b):
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(m, "minimize", return_value=optimizer_result(g, b)):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


@pytest.mark.parametrize("scenario", ["constant", "weak_excitation", "collinear"])
def test_no_identification_without_excitation(scenario):
    grid, rows, ref, _ = simulate(m, 0, scenario)
    with patch.object(m, "minimize", return_value=optimizer_result()) as opt:
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)
    opt.assert_not_called()


def test_optimizer_exception_is_not_an_analysis_crash():
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(m, "minimize", side_effect=FloatingPointError("numeric failure")):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_optimizer_result_is_refused(value):
    grid, rows, ref, _ = simulate(m, 0, "clean")
    r = optimizer_result()
    r.x[0] = value
    with patch.object(m, "minimize", return_value=r):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


def test_multiple_starts_must_not_disagree_strongly():
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(
        m, "minimize", side_effect=[optimizer_result(), optimizer_result(b=0.005)]
    ):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


def test_thermal_parameter_near_bound_is_refused_even_if_coefficients_in_range():
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(m, "minimize", return_value=optimizer_result(g=1.01e-6, b=0.005)):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


@pytest.mark.parametrize("seed", [0, 1])
@pytest.mark.parametrize(
    "scenario",
    [
        "clean",
        "noise",
        "quantized",
        "coloured",
        "delayed",
        "gaps",
        "light_room",
        "heavy_room",
    ],
)
def test_physical_simulation_recovers_parameters_or_refuses(seed, scenario):
    grid, rows, ref, truth = simulate(m, seed, scenario)
    # Real initialization comes from measured training data, never ground truth.
    ref, _ = m.fit_resolution(grid, 10)
    fit = m.fit_latent_model(grid, rows, 10, ref)
    json.dumps(fit, allow_nan=False)
    if fit["status"] == "unavailable":
        refused(fit)
        # Two-start convergence is deliberately required. Strong inertia can
        # also be insufficiently identified over a finite, noisy observation.
        assert scenario in ("coloured", "delayed", "gaps", "heavy_room")
        assert fit["reason"] in (
            "latent_optimizer_not_converged",
            "latent_coefficients_out_of_range",
            "latent_thermal_parameter_near_bound",
            "latent_initialization_sensitive",
        )
        return
    assert 0 <= fit["coef_int_6h"] <= 10
    assert 0 <= fit["coef_ext"] <= 1
    assert fit["promoted_to_proposal"] is False
    assert fit["train_end"] < fit["validation_start"]
    assert math.isfinite(fit["validation_innovation_rmse_c"])
    # Known physical ground truth, not an equality to the fitting equations.
    # Coloured gains/delayed readings violate the white-noise model; no
    # parameter-accuracy guarantee is inferred from these stress cases.
    if scenario not in ("coloured", "delayed"):
        assert fit["coef_int_6h"] == pytest.approx(truth["coef_int"], rel=0.10)
        assert fit["coef_ext"] == pytest.approx(truth["coef_ext"], rel=0.10)


@pytest.mark.parametrize(
    "scenario", ["constant", "weak_excitation", "collinear", "weak_heater"]
)
def test_degenerate_simulations_refuse_without_coefficients(scenario):
    grid, rows, ref, _ = simulate(m, 3, scenario)
    refused(m.fit_latent_model(grid, rows, 10, ref))


def test_bureau_failure_does_not_replace_or_abort_ols_analysis():
    grid, rows, ref, truth = simulate(m, 0, "clean")
    broken = optimizer_result(
        0.0005020932917764445,
        0.0000010102468356675683,
        0.0029479598574764683,
        0.04329166566884305**2,
        0.000043391099916755444**2,
    )
    with patch.object(m, "minimize", return_value=broken):
        offline = m.fit_latent_model(grid, rows, 10, ref)
        result = m.analyze_grid(grid, 10)
    refused(offline)
    assert offline["reason"] == "latent_coefficients_out_of_range"
    assert result["status"] == "success"
    refused(result["experimental_estimator"])
    assert (
        result["experimental_estimator"]["reason"]
        == "experimental_model_not_validated_for_application"
    )
    assert "experimental_latent_estimator_unavailable" in result["warnings"]
    assert result["proposed"]["coef_int"] == pytest.approx(truth["coef_int"], abs=1e-9)
    assert result["proposed"]["coef_ext"] == pytest.approx(truth["coef_ext"], abs=1e-9)
    assert result["recommendation_reliable"] is False
    json.dumps(result, allow_nan=False)


def test_missing_fresh_holdout_is_refused_before_optimization():
    grid, rows, ref, _ = simulate(m, 0, "clean")
    split = int(len(rows) * 0.7)
    cutoff = int(rows[split, 0])
    grid.temperature_timestamps[cutoff:] = grid.temperature_timestamps[cutoff]
    with patch.object(m, "minimize") as opt:
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)
    assert fit["reason"] == "insufficient_fresh_validation_observations"
    opt.assert_not_called()


@pytest.mark.parametrize(
    "bad", [optimizer_result(success=False), optimizer_result(fun=np.nan)]
)
def test_one_converged_start_is_not_enough(bad):
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(m, "minimize", side_effect=[optimizer_result(), bad]):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)


def test_validation_data_cannot_change_thermal_parameters():
    grid, rows, ref, _ = simulate(m, 0, "noise")
    before = m.fit_latent_model(grid, rows, 10, ref)
    cutoff = int(rows[int(len(rows) * 0.7), 0]) + 10
    grid.temp_in[cutoff:] += 0.1
    after = m.fit_latent_model(grid, rows, 10, ref)
    for key in ["g", "B", "q", "coef_int_6h", "coef_ext"]:
        assert before[key] == after[key]
    assert (
        before["validation_innovation_rmse_c"] != after["validation_innovation_rmse_c"]
    )


@pytest.mark.parametrize(
    "ki,ke,valid",
    [
        (0.0, 0.0, True),
        (10.0, 1.0, True),
        (-1e-10, 0.03, False),
        (10.0 + 1e-10, 0.03, False),
        (0.5, -1e-10, False),
        (0.5, 1.0 + 1e-10, False),
        (math.nan, 0.03, False),
        (math.inf, 0.03, False),
    ],
)
def test_exact_service_limits(ki, ke, valid):
    assert m.coefficients_in_range(ki, ke) == valid


def test_an_invalid_start_cannot_be_hidden_by_a_valid_one():
    grid, rows, ref, _ = simulate(m, 0, "clean")
    with patch.object(
        m,
        "minimize",
        side_effect=[optimizer_result(), optimizer_result(b=1e-6, fun=-100)],
    ):
        fit = m.fit_latent_model(grid, rows, 10, ref)
    refused(fit)
    assert fit["reason"] == "latent_coefficients_out_of_range"


def test_public_analysis_does_not_run_or_expose_unvalidated_kalman():
    grid, _, _, _ = simulate(m, 0, "clean")
    with patch.object(m, "fit_latent_model") as experimental:
        result = m.analyze_grid(grid, 10)
    experimental.assert_not_called()
    refused(result["experimental_estimator"])
    assert (
        result["experimental_estimator"]["reason"]
        == "experimental_model_not_validated_for_application"
    )
    assert result["estimate_quality"] == "exploratory"
    assert result["recommendation_reliable"] is False
    assert result["proposal_estimator"] == "ols_reference"
