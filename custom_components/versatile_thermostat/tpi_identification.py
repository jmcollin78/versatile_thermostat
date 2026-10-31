"""Read-only thermal identification, ported from the workspace vtherm_tpi_fit.py.

No Home Assistant I/O. Arrays use UTC epoch minutes and Celsius. The OLS
reference is preserved; an offline experimental Kalman fit models sensor noise.
"""

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import minimize

MIN_DAYS = 7
MAX_DAYS = 14
MAX_GAP_MINUTES = 60
PREFERRED_CLOSED_LOOP_HOURS = 6.0
TAU_CHOICES = (3, 4, 5, 6, 8, 10, 12)
RESOLUTIONS = (10, 20, 30, 60)
BOOTSTRAP_REPETITIONS = 1000
BOOTSTRAP_SEED = 20261030
# Conservative screening policies, not statistical guarantees of accuracy.
MIN_HEATER_STD = 0.05
MAX_LATENT_START_RELATIVE_SPAN = 0.25
LATENT_BOUND_MARGIN = math.log(1.05)


class IdentificationError(ValueError):
    """A refusal that can be returned directly to an LLM client."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Grid:
    """Minute samples; invalid values are NaN, exclusions are explicit masks."""

    time: np.ndarray
    temp_in: np.ndarray
    temp_out: np.ndarray
    heater: np.ndarray
    window: np.ndarray
    excluded: np.ndarray
    temperature_timestamps: np.ndarray | None = None

    @property
    def valid(self) -> np.ndarray:
        """Minutes usable for identification, including physical bounds."""
        return (
            np.isfinite(self.temp_in)
            & np.isfinite(self.temp_out)
            & np.isfinite(self.heater)
            & np.isfinite(self.window)
            & (self.window < 0.5)
            & ~self.excluded
            & (self.temp_in >= 5)
            & (self.temp_in <= 35)
            & (self.temp_out >= -30)
            & (self.temp_out <= 45)
            & (self.heater >= 0)
            & (self.heater <= 1)
        )


def sample_previous(
    points: list[tuple[float, float]],
    times: np.ndarray,
    max_age: float | None = MAX_GAP_MINUTES,
) -> np.ndarray:
    """Causal fill. An explicit unknown invalidates until the next valid event.

    Temperatures expire after 60 elapsed minutes (not 60 rows). Binary HA
    states persist until an event; they are not periodic sensor measurements.
    """
    if not points:
        return np.full(len(times), np.nan)
    # Last event wins at a duplicate timestamp, as in the reference script.
    ordered = sorted(dict(points).items())
    stamps, values = np.asarray(ordered, dtype=float).T
    indices = np.searchsorted(stamps, times, side="right") - 1
    result = values[np.maximum(indices, 0)].copy()
    invalid = indices < 0
    if max_age is not None:
        invalid |= times - stamps[np.maximum(indices, 0)] > max_age
    result[invalid] = np.nan
    return result


def aggregate_cycles(grid: Grid, minutes: int) -> tuple[np.ndarray, dict]:
    """Return [UTC minute, Text-Tint, u, deltaT], without bridging gaps.

    All required channels must cover 80% of each bin. Both endpoints must be
    valid; exclusion anywhere in a cycle rejects it, including subminute events
    marked by the HA adapter. Unlike shift after dropna, missing bins can never
    turn a multi-cycle temperature change into a single-cycle delta.
    """
    bins: dict[int, tuple] = {}
    removed_window = removed_invalid = 0
    labels = grid.time.astype(np.int64) // minutes
    valid = grid.valid
    for label in np.unique(labels):
        idx = np.flatnonzero(labels == label)
        good = valid[idx]
        if np.any(grid.window[idx] >= 0.5):
            removed_window += 1
            continue
        if np.any(grid.excluded[idx]) or np.any(~np.isfinite(grid.window[idx])):
            removed_invalid += 1
            continue
        if len(idx) != minutes or np.count_nonzero(good) < 0.8 * minutes or not good[0]:
            removed_invalid += 1
            continue
        valid_idx = idx[good]
        bins[int(label)] = (
            grid.temp_in[idx[0]],
            float(np.mean(grid.temp_out[valid_idx])),
            float(np.mean(grid.heater[valid_idx])),
            grid.time[idx[0]],
        )
    rows = []
    for label, (inside, outside, heat, stamp) in bins.items():
        if label + 1 not in bins:
            continue
        delta = bins[label + 1][0] - inside
        if abs(delta) <= 3:
            rows.append((stamp, outside - inside, heat, delta))
    return np.asarray(rows, dtype=float).reshape((-1, 4)), {
        "window_cycles_excluded": removed_window,
        "invalid_cycles_excluded": removed_invalid,
    }


def ols(rows: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit deltaT = g * (Text - Tint) + B * u + q."""
    design = np.column_stack((rows[:, 1:3], np.ones(len(rows))))
    theta, _, rank, _ = np.linalg.lstsq(design, rows[:, 3], rcond=None)
    cond = float(np.linalg.cond(design))
    if rank < 3 or not math.isfinite(cond):
        raise IdentificationError("ill_conditioned_model")
    return theta, cond


def physical(theta: np.ndarray) -> bool:
    """Reference physical guard."""
    g, gain, _ = theta
    return bool(np.all(np.isfinite(theta)) and 0 < g < 1 and 0 < 1 - g < 1 and gain > 0)


def kint_for_tau(
    a: float, gain: float, minutes: int, tau_hours: float = PREFERRED_CLOSED_LOOP_HOURS
) -> float:
    """Reference closed-loop convergence calculation."""
    return (a - math.exp(-(minutes / 60) / tau_hours)) / gain


def coefficients_in_range(coef_int: float, coef_ext: float) -> bool:
    """Check actual service limits; never clip an unidentifiable estimate."""
    return (
        math.isfinite(coef_int)
        and math.isfinite(coef_ext)
        and 0 <= coef_int <= 10
        and 0 <= coef_ext <= 1
    )


def fit_resolution(grid: Grid, minutes: int) -> tuple[dict, np.ndarray]:
    """Reference 70/30 chronological holdout validation."""
    rows, excluded = aggregate_cycles(grid, minutes)
    if len(rows) < 40:
        raise IdentificationError("insufficient_cycles")
    split = int(len(rows) * 0.70)
    train, test = rows[:split], rows[split:]
    theta, cond = ols(train)
    if not physical(theta):
        raise IdentificationError("invalid_physical_model")
    if cond >= 1000:
        raise IdentificationError("ill_conditioned_model")
    g, gain, bias = map(float, theta)
    a = 1 - g
    prediction = np.column_stack((test[:, 1:3], np.ones(len(test)))) @ theta
    error = test[:, 3] - prediction
    den = float(np.sum((test[:, 3] - np.mean(test[:, 3])) ** 2))
    return {
        "resolution_min": minutes,
        "cycles": len(rows),
        "train_cycles": len(train),
        "validation_cycles": len(test),
        "train_end": float(train[-1, 0]),
        "validation_start": float(test[0, 0]),
        "g": g,
        "B": gain,
        "q": bias,
        "A": a,
        "coef_ext": g / gain,
        "tau_natural_h": -(minutes / 60) / math.log(a),
        "condition_number": cond,
        "validation": {
            "mae": float(np.mean(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(error**2))),
            "r2_delta": float(1 - np.sum(error**2) / den) if den > 0 else None,
        },
        **excluded,
    }, train


def block_bootstrap(
    train: np.ndarray, minutes: int, repetitions: int = BOOTSTRAP_REPETITIONS
) -> dict:
    """Moving 24-hour blocks, reference seed, physical fits only.

    Block ends use timestamps so filtered gaps do not compress several days
    into a nominal 24-hour block. For uninterrupted data this is the reference
    row-block algorithm. No IID resampling.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(train)
    # Restrict starts to full wall-clock blocks when the span permits it.
    max_start = max(
        1,
        int(
            np.searchsorted(train[:, 0], train[-1, 0] + minutes - 24 * 60, side="right")
        ),
    )
    values = []
    for _ in range(repetitions):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, max_start))
            stop = int(np.searchsorted(train[:, 0], train[start, 0] + 24 * 60))
            indices.extend(range(start, max(start + 1, stop)))
        try:
            theta, cond = ols(train[indices[:n]])
        except (IdentificationError, np.linalg.LinAlgError):
            continue
        if physical(theta) and cond < 1000:
            g, gain, _ = theta
            ke = float(g / gain)
            ki = kint_for_tau(1 - g, gain, minutes)
            if math.isfinite(ke) and math.isfinite(ki):
                values.append((ke, ki))
    if len(values) < 30:
        raise IdentificationError("bootstrap_failed")
    samples = np.asarray(values)
    ci = np.percentile(samples, [2.5, 50, 97.5], axis=0)
    return {
        "method": "ols_moving_block_percentiles",
        "interpretation": "approximate_uncalibrated_intervals_not_accuracy_guarantees",
        "measurement_noise_bias_corrected": False,
        "repetitions": repetitions,
        "accepted": len(values),
        "block_hours": 24,
        "seed": BOOTSTRAP_SEED,
        "coef_ext_ci95": [float(ci[0, 0]), float(ci[2, 0])],
        "coef_ext_median": float(ci[1, 0]),
        "coef_int_ci95": [float(ci[0, 1]), float(ci[2, 1])],
        "coef_int_median": float(ci[1, 1]),
    }


def nominal_response(model: dict, coef_int: float, coef_ext: float) -> dict:
    """Local, unsaturated response; outdoor mismatch is reported separately.

    Constant setpoint/outdoor and constant gains are assumed. q changes the
    equilibrium offset, not the pole. Relay timing and thresholds are omitted.
    """
    pole = model["A"] - model["B"] * coef_int
    tau = -model["resolution_min"] / 60 / math.log(pole) if 0 < pole < 1 else None
    return {
        "pole": pole,
        "stable": abs(pole) < 1,
        "monotone_convergence": 0 < pole < 1,
        "time_constant_hours": tau,
        "hours_to_95_percent": -math.log(0.05) * tau if tau is not None else None,
        "outdoor_cancellation_mismatch": model["g"] - model["B"] * coef_ext,
        "interpretation": "nominal_local_unsaturated_model_not_a_room_forecast",
    }


def _cycle_observations(grid: Grid, rows: np.ndarray, minutes: int):
    """Absolute temperatures and fresh endpoints, preserving rejected gaps."""
    idx = np.searchsorted(grid.time, rows[:, 0])
    inside = grid.temp_in[idx]
    end = grid.temp_in[idx + minutes]
    fresh = np.ones(len(rows), dtype=bool)
    if grid.temperature_timestamps is not None:
        stamps = grid.temperature_timestamps
        fresh = stamps[idx + minutes] > stamps[idx]
    return inside, end, rows[:, 1] + inside, fresh


def _kalman_innovations(parameters, rows, observations, minutes):
    """Conditional Gaussian likelihood: x+=A*x+g*Text+B*u+q+w; y=x+v.

    Q and R are separate variances. At each uninterrupted segment the initial
    state is conditioned on its first observation, with variance R. Repeated
    forward-filled sensor states are not counted as independent observations.
    """
    g, gain, process, measurement = np.exp(parameters[[0, 1, 3, 4]])
    bias = parameters[2] * 0.01
    inside, end, outside, fresh = observations
    a = 1 - g
    state = variance = 0.0
    score = 0.0
    innovations = []
    previous = -math.inf
    for i, row in enumerate(rows):
        if row[0] != previous + minutes:
            state, variance = float(inside[i]), float(measurement)
        state = a * state + g * outside[i] + gain * row[2] + bias
        variance = a * a * variance + process
        if fresh[i]:
            innovation = float(end[i] - state)
            total = variance + measurement
            score += math.log(total) + innovation * innovation / total
            innovations.append(innovation)
            kalman_gain = variance / total
            state += kalman_gain * innovation
            variance *= 1 - kalman_gain
        previous = row[0]
    return score / max(1, len(innovations)), innovations


def fit_latent_model(
    grid: Grid, rows: np.ndarray, minutes: int, reference: dict
) -> dict:
    """Offline experimental MLE; not executed by the public MCP analysis.

    Gaussian independent observation/process noise is a modelling assumption,
    especially approximate for quantized, delayed sensors and feedback inputs.
    No confidence interval is inferred from the optimizer inverse Hessian.
    """
    split = int(len(rows) * 0.7)
    observations = _cycle_observations(grid, rows, minutes)
    train = rows[:split]
    train_observations = tuple(a[:split] for a in observations)
    if np.count_nonzero(train_observations[3]) < 40:
        return {"status": "unavailable", "reason": "insufficient_fresh_observations"}
    if np.count_nonzero(observations[3][split:]) < 10:
        return {
            "status": "unavailable",
            "reason": "insufficient_fresh_validation_observations",
        }
    try:
        _, condition = ols(train)
    except (IdentificationError, np.linalg.LinAlgError):
        condition = math.inf
    if condition >= 1000 or np.std(train[:, 2]) < MIN_HEATER_STD:
        return {"status": "unavailable", "reason": "latent_insufficient_excitation"}
    bounds = [
        (math.log(1e-6), math.log(0.95)),
        (math.log(1e-6), math.log(10)),
        (-300, 300),
        (math.log(1e-12), math.log(1)),
        (math.log(1e-12), math.log(1)),
    ]
    results = []
    for noise in (0.01, 0.05):
        initial = [
            math.log(reference["g"]),
            math.log(reference["B"]),
            reference["q"] / 0.01,
            math.log(1e-7),
            math.log(noise**2),
        ]
        try:
            result = minimize(
                lambda parameters: _kalman_innovations(
                    parameters, train, train_observations, minutes
                )[0],
                initial,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 150, "maxfun": 1500, "ftol": 1e-10},
            )
        except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
            continue
        if result.success and np.isfinite(result.fun) and np.all(np.isfinite(result.x)):
            results.append(result)
    if len(results) != 2:
        return {"status": "unavailable", "reason": "latent_optimizer_not_converged"}
    candidates = []
    for trial in results:
        g, gain = np.exp(trial.x[:2])
        coef_int = kint_for_tau(1 - g, gain, minutes)
        coef_ext = float(g / gain)
        if not coefficients_in_range(coef_int, coef_ext):
            return {
                "status": "unavailable",
                "reason": "latent_coefficients_out_of_range",
            }
        # Only thermal parameters trigger refusal here. Zero noise may be a
        # legitimate boundary, but must still be disclosed as not identified.
        if any(
            min(value - lo, hi - value) <= LATENT_BOUND_MARGIN
            for value, (lo, hi) in zip(trial.x[:2], bounds[:2], strict=True)
        ):
            return {
                "status": "unavailable",
                "reason": "latent_thermal_parameter_near_bound",
            }
        candidates.append((coef_int, coef_ext))
    values = np.asarray(candidates)
    relative_span = np.ptp(values, axis=0) / np.maximum(
        np.abs(np.median(values, axis=0)), 1e-9
    )
    if np.any(relative_span > MAX_LATENT_START_RELATIVE_SPAN):
        return {"status": "unavailable", "reason": "latent_initialization_sensitive"}
    result = min(results, key=lambda item: item.fun)
    g, gain, process, measurement = np.exp(result.x[[0, 1, 3, 4]])
    theta = [float(g), float(gain), float(result.x[2] * 0.01)]
    test_observations = tuple(a[split:] for a in observations)
    _, innovations = _kalman_innovations(
        result.x, rows[split:], test_observations, minutes
    )
    at_bound = any(
        min(value - lo, hi - value) <= LATENT_BOUND_MARGIN
        for value, (lo, hi) in zip(result.x, bounds, strict=True)
    )
    return {
        "status": "experimental",
        "promoted_to_proposal": False,
        "method": "conditional_gaussian_kalman_maximum_likelihood",
        "g": theta[0],
        "B": theta[1],
        "q": theta[2],
        "A": 1 - theta[0],
        "coef_ext": float(g / gain),
        "coef_int_6h": kint_for_tau(1 - g, gain, minutes),
        "process_noise_sd_c": float(math.sqrt(process)),
        "measurement_noise_sd_c": float(math.sqrt(measurement)),
        "optimizer_at_bound": at_bound,
        "initialization_relative_span": {
            "coef_int": float(relative_span[0]),
            "coef_ext": float(relative_span[1]),
        },
        "estimate_quality": "exploratory_not_validated_for_application",
        "validation_innovation_rmse_c": (
            float(np.sqrt(np.mean(np.square(innovations)))) if innovations else None
        ),
        "train_end": float(train[-1, 0]),
        "validation_start": float(rows[split, 0]),
        "limitations": [
            "uncertainty_not_calibrated",
            "white_gaussian_noise_assumption",
            "sensor_delay_and_outdoor_noise_not_modelled",
            "closed_loop_input_exogeneity_not_guaranteed",
        ],
    }


def model_diagnostics(grid: Grid, rows: np.ndarray, minutes: int, model: dict) -> dict:
    """Held-out residual correlation and free runs reset only across gaps."""
    split = int(len(rows) * 0.7)
    train, test = rows[:split], rows[split:]
    theta = np.array([model["g"], model["B"], model["q"]])
    residual = test[:, 3] - np.column_stack((test[:, 1:3], np.ones(len(test)))) @ theta
    correlations = []
    for lag in (1, 2, 3, 6):
        adjacent = test[lag:, 0] - test[:-lag, 0] == lag * minutes
        x, y = residual[:-lag][adjacent], residual[lag:][adjacent]
        value = None
        if len(x) >= 10 and np.std(x) > 1e-12 and np.std(y) > 1e-12:
            value = float(np.corrcoef(x, y)[0, 1])
        correlations.append(
            {"lag_minutes": lag * minutes, "correlation": value, "pairs": len(x)}
        )
    inside, end, outside, _ = _cycle_observations(grid, test, minutes)
    horizons = []
    for hours in (1, 3, 6):
        steps = max(1, math.ceil(hours * 60 / minutes))
        errors = []
        # Non-overlapping runs; no observed indoor temperature is fed back.
        for start in range(0, len(test) - steps + 1, steps):
            stop = start + steps
            if np.any(np.diff(test[start:stop, 0]) != minutes):
                continue
            prediction = inside[start]
            for i in range(start, stop):
                prediction = (
                    model["A"] * prediction
                    + model["g"] * outside[i]
                    + model["B"] * test[i, 2]
                    + model["q"]
                )
            errors.append(float(end[stop - 1] - prediction))
        horizons.append(
            {
                "hours": steps * minutes / 60,
                "runs": len(errors),
                "rmse_c": (
                    float(np.sqrt(np.mean(np.square(errors)))) if errors else None
                ),
            }
        )
    adjacent = grid.valid[:-1] & grid.valid[1:] & (np.diff(grid.time) == 1)
    differences = np.abs(np.diff(grid.temp_in)[adjacent])
    nonzero = differences[differences > 1e-8]
    return {
        "training_heater_std": float(np.std(train[:, 2])),
        "training_heater_range": float(np.ptp(train[:, 2])),
        "training_outdoor_minus_indoor_std_c": float(np.std(train[:, 1])),
        "unchanged_temperature_fraction": (
            float(np.mean(differences < 1e-8)) if len(differences) else None
        ),
        "small_temperature_step_c": (
            float(np.percentile(nonzero, 10)) if len(nonzero) else None
        ),
        "step_interpretation": "observed_steps_not_a_sensor_resolution_estimate",
        "held_out_residual_correlations": correlations,
        "held_out_free_run": horizons,
        "free_run_interpretation": "recorded_weather_and_heater_inputs_not_a_controller_simulation",
    }


def analyze_grid(grid: Grid, primary_resolution: int) -> dict:
    """Return structured estimates; never perform writes or generate files."""
    if np.count_nonzero(grid.valid) < MIN_DAYS * 1440:
        raise IdentificationError("insufficient_usable_history")
    fits, trains, rejected = [], {}, []
    for minutes in sorted(set((*RESOLUTIONS, primary_resolution))):
        try:
            fit, train = fit_resolution(grid, minutes)
            fits.append(fit)
            trains[minutes] = train
        except (IdentificationError, np.linalg.LinAlgError) as err:
            rejected.append({"resolution_min": minutes, "reason": str(err)})
    if not fits:
        reason = (
            rejected[0]["reason"]
            if len({x["reason"] for x in rejected}) == 1
            else "invalid_physical_model"
        )
        return {"status": "error", "reason": reason, "rejected_resolutions": rejected}
    chosen = min(fits, key=lambda fit: abs(fit["resolution_min"] - primary_resolution))
    minutes = chosen["resolution_min"]
    warnings = [
        "exploratory_estimate_measurement_noise_bias_possible",
        "bootstrap_intervals_uncalibrated",
        "six_hour_response_is_a_design_preference",
    ]
    if minutes != primary_resolution:
        warnings.append("primary_resolution_rejected_using_nearest_valid")
    ext = [fit["coef_ext"] for fit in fits]
    median, span = float(np.median(ext)), float(np.ptp(ext))
    relative = span / max(abs(median), 1e-9)
    if len(fits) < 3:
        warnings.append("insufficient_valid_resolutions_for_stability")
    elif relative > 0.25:
        warnings.append("coef_ext_unstable_across_resolutions")
    if chosen["condition_number"] >= 100:
        warnings.append("conditioning_requires_caution")
    r2 = chosen["validation"]["r2_delta"]
    if r2 is None or r2 < 0.10:
        warnings.append("low_r2_delta_not_alone_a_rejection_criterion")
    boot = block_bootstrap(trains[minutes], minutes)
    if boot["accepted"] < BOOTSTRAP_REPETITIONS / 2:
        warnings.append("low_physical_bootstrap_acceptance")
    if boot["coef_int_ci95"][0] < 0 or boot["coef_int_ci95"][1] > 10:
        warnings.append("coef_int_confidence_interval_outside_service_range")
    lo, hi = boot["coef_ext_ci95"]
    if hi - lo > max(0.02, 0.75 * abs(boot["coef_ext_median"])):
        warnings.append("wide_coef_ext_confidence_interval")
    proposed = {
        "coef_int": kint_for_tau(chosen["A"], chosen["B"], minutes),
        "coef_ext": chosen["coef_ext"],
        "closed_loop_hours": PREFERRED_CLOSED_LOOP_HOURS,
    }
    if not coefficients_in_range(proposed["coef_int"], proposed["coef_ext"]):
        return {
            "status": "error",
            "reason": "coefficients_out_of_range",
            "model": chosen,
            "warnings": warnings,
        }
    rows, _ = aggregate_cycles(grid, minutes)
    diagnostics = model_diagnostics(grid, rows, minutes, chosen)
    if diagnostics["training_heater_std"] < MIN_HEATER_STD:
        warnings.append("weak_heater_excitation")
    if any(
        abs(item["correlation"]) > 0.2
        for item in diagnostics["held_out_residual_correlations"]
        if item["correlation"] is not None
    ):
        warnings.append("temporally_correlated_validation_residuals")
    # Even bounded estimates were inaccurate under model mismatch in the
    # physical simulations. Keep this estimator offline until its use on real
    # Recorder data is validated; numerical convergence is not that validation.
    latent = {
        "status": "unavailable",
        "reason": "experimental_model_not_validated_for_application",
        "promoted_to_proposal": False,
        "message": {
            "fr": (
                "La comparaison Kalman est désactivée : sa fiabilité pour cet usage "
                "n'est pas établie. Aucun coefficient Kalman n'est proposé. "
                "L'estimation OLS reste exploratoire."
            ),
            "en": (
                "The Kalman comparison is disabled: its reliability for this use "
                "has not been established. No Kalman coefficients are proposed. "
                "The OLS estimate remains exploratory."
            ),
        },
    }
    warnings.append("experimental_latent_estimator_unavailable")
    return {
        "status": "success",
        "estimate_quality": "exploratory",
        "applicability_note": {
            "fr": (
                "Ces coefficients sont des estimations exploratoires issues de la période "
                "d'historique analysée. Leur pertinence dans d'autres conditions n'est pas "
                "établie. Si les conditions de chauffage ou l'usage du logement changent "
                "sensiblement, ou si la régulation se dégrade, relancez l'analyse sur une "
                "période représentative avant d'envisager un ajustement. Une variation de "
                "température extérieure seule n'impose pas un nouveau calcul."
            ),
            "en": (
                "These coefficients are exploratory estimates derived from the analyzed "
                "history period. Their suitability under other conditions has not been "
                "established. If heating conditions or household use change substantially, "
                "or regulation deteriorates, rerun the analysis on a representative period "
                "before considering an adjustment. A change in outdoor temperature alone "
                "does not require recalculation."
            ),
        },
        "proposal_estimator": "ols_reference",
        "experimental_estimator": latent,
        "diagnostics": diagnostics,
        "proposed_nominal_response": nominal_response(
            chosen, proposed["coef_int"], proposed["coef_ext"]
        ),
        "model": chosen,
        "validation": chosen["validation"],
        "proposed": proposed,
        "recommendation_reliable": False,
        "bootstrap": boot,
        "coef_int_by_closed_loop_hours": [
            {
                "closed_loop_hours": tau,
                "coef_int": kint_for_tau(chosen["A"], chosen["B"], minutes, tau),
            }
            for tau in TAU_CHOICES
        ],
        "multi_resolution": fits,
        "median_coef_ext": median,
        "span_coef_ext": span,
        "relative_span": relative,
        "rejected_resolutions": rejected,
        "warnings": warnings,
    }
