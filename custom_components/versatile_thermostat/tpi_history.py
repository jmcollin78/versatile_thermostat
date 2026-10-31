"""Adapt official Home Assistant Recorder states to thermal identification."""

from datetime import timedelta
from functools import partial
import math
from typing import Any

import numpy as np

from homeassistant.components.recorder import get_instance
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from homeassistant.const import UnitOfTemperature

from .const import (
    CONF_AUTO_TPI_CONTINUOUS_KEXT,
    CONF_AUTO_TPI_MODE,
    CONF_INVERSE_SWITCH,
    CONF_TEMP_SENSOR,
    CONF_UNDERLYING_LIST,
    CONF_USE_POWER_FEATURE,
    CONF_USE_WINDOW_FEATURE,
    CONF_VSWITCH_OFF_CMD_LIST,
    CONF_VSWITCH_ON_CMD_LIST,
    CONF_WINDOW_SENSOR,
    DOMAIN,
    PROPORTIONAL_FUNCTION_TPI,
)
from .tpi_identification import (
    Grid,
    IdentificationError,
    MAX_DAYS,
    MIN_DAYS,
    sample_previous,
)
from .recorder_export import read_recorder_history


def get_thermostat(hass: HomeAssistant, entity_id: str) -> Any:
    """Use the loaded climate component, as VTherm base entities do."""
    component = hass.data.get("climate")
    entity = component.get_entity(entity_id) if component else None
    if entity is None or not hasattr(entity, "entry_infos"):
        raise IdentificationError("invalid_vtherm")
    return entity


def check_classic_tpi(thermostat: Any) -> None:
    """Reject other regulation, configured Auto-TPI and running learning."""
    config = thermostat.entry_infos
    manager = getattr(thermostat, "auto_tpi_manager", None)
    if (
        thermostat.proportional_function != PROPORTIONAL_FUNCTION_TPI
        or config.get(CONF_AUTO_TPI_MODE, False)
        or config.get(CONF_AUTO_TPI_CONTINUOUS_KEXT, False)
        or (manager is not None and manager.learning_active)
    ):
        raise IdentificationError("not_classic_tpi")


def history_sources(hass: HomeAssistant, thermostat: Any) -> dict:
    """Resolve merged configuration and related diagnostic entity registry IDs.

    CycleScheduler gives every relay the same duty with staggered phases.
    FeaturePowerManager.calculate_underlying_startup_power allocates P/N to
    each relay. Reconstruct that convention from all actual switch histories.
    Neither valve opening nor a regulated climate HVAC action measures heat.
    """
    if not thermostat.is_over_switch:
        raise IdentificationError("unsupported_thermostat_type")
    check_classic_tpi(thermostat)
    if not thermostat.is_initialized:
        raise IdentificationError("vtherm_not_initialized")
    config = thermostat.entry_infos
    if thermostat.temperature_unit != UnitOfTemperature.CELSIUS:
        raise IdentificationError("unsupported_temperature_unit")
    inside = config.get(CONF_TEMP_SENSOR)
    outside = thermostat.ext_temp_sensor_entity_id
    if not inside:
        raise IdentificationError("missing_internal_temperature")
    if not outside:
        raise IdentificationError("missing_external_temperature")
    heaters = config.get(CONF_UNDERLYING_LIST, [])
    if not heaters:
        raise IdentificationError("missing_heating_history")
    if (
        len(set(heaters)) != len(heaters)
        or any(not entity_id.startswith("switch.") for entity_id in heaters)
        or config.get(CONF_VSWITCH_ON_CMD_LIST)
        or config.get(CONF_VSWITCH_OFF_CMD_LIST)
    ):
        raise IdentificationError("ambiguous_heating_history")
    registry = er.async_get(hass)
    climate_entry = registry.async_get(thermostat.entity_id)
    diagnostics = {}
    if climate_entry:
        for entry in er.async_entries_for_config_entry(
            registry, climate_entry.config_entry_id
        ):
            if entry.domain == "binary_sensor" and entry.platform == DOMAIN:
                if entry.translation_key in (
                    "safety_state",
                    "overpowering_state",
                    "window_state",
                ):
                    diagnostics[entry.translation_key] = entry.entity_id
    # Safety is always provided by VTherm. Missing/excluded histories cannot be
    # interpreted as proof that no protective override occurred.
    if "safety_state" not in diagnostics:
        raise IdentificationError("missing_exclusion_history")
    if config.get(CONF_USE_POWER_FEATURE) and "overpowering_state" not in diagnostics:
        raise IdentificationError("missing_exclusion_history")
    window = config.get(CONF_WINDOW_SENSOR)
    if config.get(CONF_USE_WINDOW_FEATURE) and not window:
        window = diagnostics.get("window_state")
        if not window:
            raise IdentificationError("missing_exclusion_history")
    cycle = float(thermostat.cycle_min)
    if not math.isfinite(cycle) or cycle < 1 or not cycle.is_integer():
        raise IdentificationError("unsupported_cycle_length")
    return {
        "temperature_source": inside,
        "external_temperature_source": outside,
        "heating_source": heaters[0],
        "heating_sources": list(heaters),
        "heating_source_kind": "physical_switches",
        "heating_aggregation": "equal_power_shares_vtherm_P_over_N",
        "heating_weights": [1 / len(heaters)] * len(heaters),
        "window_source": window,
        "safety_source": diagnostics["safety_state"],
        "power_source": (
            diagnostics.get("overpowering_state")
            if config.get(CONF_USE_POWER_FEATURE)
            else None
        ),
        "climate_source": thermostat.entity_id,
        "inverse_switch": bool(config.get(CONF_INVERSE_SWITCH)),
        "primary_resolution": int(cycle),
    }


def _number(state: State) -> float:
    try:
        value = float(state.state)
    except (ValueError, TypeError):
        return math.nan
    unit = state.attributes.get("unit_of_measurement")
    if unit == UnitOfTemperature.FAHRENHEIT:
        value = (value - 32) * 5 / 9
    elif unit != UnitOfTemperature.CELSIUS:
        return math.nan
    return value if math.isfinite(value) else math.nan


def _binary(state: State) -> float:
    return {"on": 1.0, "off": 0.0, "open": 1.0, "closed": 0.0}.get(
        state.state, math.nan
    )


def interval_values(
    points: list[tuple[float, float]], times: np.ndarray, *, maximum: bool = False
) -> np.ndarray:
    """Integrate binary events over each minute, including subminute changes.

    Used for actual heater duty and any protective/window override. A single
    unknown interval makes that minute unknown; no interpolation across it.
    """
    result = np.full(len(times), np.nan)
    if not points:
        return result
    stamps, values = np.asarray(sorted(dict(points).items()), dtype=float).T
    for i, start in enumerate(times):
        first = np.searchsorted(stamps, start, side="right") - 1
        if first < 0:
            continue
        end = start + 1
        last = np.searchsorted(stamps, end, side="left")
        cuts = np.concatenate(([start], stamps[first + 1 : last], [end]))
        vals = values[first:last]
        if np.all(np.isfinite(vals)):
            result[i] = np.max(vals) if maximum else np.sum(vals * np.diff(cuts))
    return result


def build_grid(
    states: dict[str, list[State]], sources: dict, start, end
) -> tuple[Grid, dict]:
    """Bound all series to the same requested UTC window, never look ahead."""
    start = max(start, end - timedelta(days=MAX_DAYS))
    times = np.arange(
        math.ceil(start.timestamp() / 60), math.floor(end.timestamp() / 60), dtype=float
    )
    required = [
        sources[key]
        for key in (
            "temperature_source",
            "external_temperature_source",
            "heating_source",
            "climate_source",
        )
    ]
    heaters = sources.get("heating_sources", [sources["heating_source"]])
    if any(not states.get(entity_id) for entity_id in heaters):
        raise IdentificationError("missing_heating_history")
    required.extend(heaters[1:])
    reasons = (
        "missing_internal_temperature",
        "missing_external_temperature",
        "missing_heating_history",
        "insufficient_history",
        *(["missing_heating_history"] * (len(heaters) - 1)),
    )
    for entity_id, reason in zip(required, reasons, strict=True):
        if not states.get(entity_id):
            raise IdentificationError(reason)
    entity_ids = list(
        dict.fromkeys(
            [
                *required,
                *(
                    sources.get(key)
                    for key in ("window_source", "safety_source", "power_source")
                    if sources.get(key)
                ),
            ]
        )
    )
    if any(not states.get(entity_id) for entity_id in entity_ids):
        raise IdentificationError("missing_exclusion_history")
    first = max(
        max(start.timestamp(), min(s.last_updated.timestamp() for s in states[e]))
        for e in entity_ids
    )
    if first >= end.timestamp():
        raise IdentificationError("histories_do_not_overlap")
    available = min(MAX_DAYS, (end.timestamp() - first) / 86400)

    def points(key, transform):
        return [
            (s.last_updated.timestamp() / 60, transform(s))
            for s in states.get(sources.get(key), [])
            if s.last_updated <= end
        ]

    inside_points = points("temperature_source", _number)
    inside = sample_previous(inside_points, times)
    temperature_timestamps = sample_previous(
        [(stamp, stamp) for stamp, _ in inside_points], times
    )
    outside = sample_previous(points("external_temperature_source", _number), times)
    heater = np.mean(
        [
            interval_values(
                [
                    (s.last_updated.timestamp() / 60, _binary(s))
                    for s in states[entity_id]
                    if s.last_updated <= end
                ],
                times,
            )
            for entity_id in heaters
        ],
        axis=0,
    )
    if sources["inverse_switch"]:
        heater = 1 - heater
    window = (
        interval_values(points("window_source", _binary), times, maximum=True)
        if sources.get("window_source")
        else np.zeros(len(times))
    )
    # Only explicit heat mode is eligible. This also excludes HA unavailability,
    # HVAC off, cooling and startup states. Dedicated binaries cover overrides
    # absent from Recorder climate attributes.
    excluded = interval_values(
        points("climate_source", lambda s: 0.0 if s.state == "heat" else 1.0),
        times,
        maximum=True,
    )
    excluded = ~np.isfinite(excluded) | (excluded > 0)
    for key in ("safety_source", "power_source"):
        if sources.get(key):
            flags = interval_values(points(key, _binary), times, maximum=True)
            excluded |= ~np.isfinite(flags) | (flags > 0)
    grid = Grid(
        times, inside, outside, heater, window, excluded, temperature_timestamps
    )
    if not np.any(np.isfinite(inside)):
        raise IdentificationError("missing_internal_temperature")
    if not np.any(np.isfinite(outside)):
        raise IdentificationError("missing_external_temperature")
    overlaps = np.isfinite(inside) & np.isfinite(outside) & np.isfinite(heater)
    if not np.any(overlaps):
        raise IdentificationError("histories_do_not_overlap")
    summary = {
        "history_requested_days": MAX_DAYS,
        "history_available_days": available,
        "history_usable_days": float(np.count_nonzero(grid.valid) / 1440),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "valid_minutes": int(np.count_nonzero(grid.valid)),
        "excluded_minutes": int(np.count_nonzero(excluded)),
        "window_minutes": int(np.count_nonzero(window > 0)),
        "temperature_unit": "°C",
        "temperature_sampling": "causal_previous_state_max_age_60_min",
        "latent_estimator_sampling": "repeated_source_timestamps_not_independent_observations",
    }
    return grid, summary


async def async_load_history(hass: HomeAssistant, sources: dict) -> tuple[Grid, dict]:
    """Recorder executor for DB work; HA executor for array processing."""
    if "recorder" not in hass.config.components:
        raise IdentificationError("recorder_unavailable")
    end = dt_util.utcnow()
    start = end - timedelta(days=MAX_DAYS)
    entity_ids = list(
        dict.fromkeys(
            [
                *(
                    sources[key]
                    for key in (
                        "temperature_source",
                        "external_temperature_source",
                        "window_source",
                        "safety_source",
                        "power_source",
                        "climate_source",
                    )
                    if sources.get(key)
                ),
                *sources.get("heating_sources", [sources["heating_source"]]),
            ]
        )
    )
    try:
        states = await get_instance(hass).async_add_executor_job(
            partial(
                read_recorder_history,
                hass,
                start,
                end,
                entity_ids,
            )
        )
    except Exception as err:  # Recorder failures must never produce coefficients.
        raise IdentificationError("recorder_unavailable") from err
    return await hass.async_add_executor_job(build_grid, states, sources, start, end)


def require_history(summary: dict) -> None:
    """Minimum seven actual days of usable minutes, not just elapsed span."""
    if summary["history_available_days"] < MIN_DAYS:
        raise IdentificationError("insufficient_history")
    if summary["history_usable_days"] < MIN_DAYS:
        raise IdentificationError("insufficient_usable_history")
