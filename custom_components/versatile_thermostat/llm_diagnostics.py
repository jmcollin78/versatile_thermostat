"""Read-only data sources for the LLM diagnostic tools."""

from __future__ import annotations

import inspect
import logging
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from typing import Any

import probatio
from homeassistant.components.homeassistant import async_should_expose
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er, llm

from .const import DOMAIN
from .llm_diagnostic_time import ExactTimestamp, parse_timestamp, utc_timestamp

LOG_LIMIT = 5000
LEVELS = {name: getattr(logging, name) for name in ("DEBUG", "INFO", "WARNING", "ERROR")}
ERROR_MESSAGES = {
    "invalid_parameters": ("Paramètres invalides", "Invalid parameters"),
    "invalid_period": ("Période inversée", "Invalid period"),
    "target_not_vtherm": ("Cible non VTherm", "Target is not a VTherm"),
    "target_not_exposed": ("Cible non exposée", "Target is not exposed"),
    "target_not_loaded": ("Cible non chargée", "Target is not loaded"),
    "target_changed": ("Cible modifiée pendant la lecture", "Target changed during reading"),
    "target_lookup_failed": ("Recherche de la cible impossible", "Target lookup failed"),
    "collector_unavailable": ("Collecteur indisponible", "Collector unavailable"),
    "collector_incompatible": ("Collecteur incompatible", "Collector incompatible"),
    "collector_read_failed": ("Lecture du collecteur impossible", "Collector read failed"),
    "plugin_discovery_unavailable": ("Découverte des plugins indisponible", "Plugin discovery unavailable"),
}


def _error(entity_id: Any, code: str, scope: str, field: str | None = None) -> llm.ToolResult:
    french, english = ERROR_MESSAGES.get(code, (code, code))
    extra = {"configured_plugin_count": None} if scope == "plugins" else {}
    return llm.ToolResult(
        data={
            "schema_version": 1,
            "status": "error",
            "entity_id": entity_id if isinstance(entity_id, str) else None,
            "target": None,
            "queried_at": utc_timestamp(datetime.now(timezone.utc)),
            "read_started_at": None,
            "read_finished_at": None,
            "warnings": [],
            "errors": [{"code": code, "scope": scope, "field": field,
                        "plugin_id": None, "source": None,
                        "message_fr": french, "message_en": english}],
            **extra,
        },
        error=True,
    )


def _resolve_target(hass, context, entity_id: str):
    registry = er.async_get(hass)
    registered = registry.async_get(entity_id)
    if registered is None or registered.domain != "climate" or registered.platform != DOMAIN:
        return None, "target_not_vtherm"
    if not async_should_expose(hass, context.assistant, entity_id):
        return None, "target_not_exposed"
    component = hass.data.get("climate")
    entity = component.get_entity(entity_id) if component else None
    entry = hass.config_entries.async_get_entry(registered.config_entry_id)
    if (entity is None or entry is None or entry.domain != DOMAIN
            or hass.states.get(entity_id) is None
            or entity.unique_id != registered.unique_id):
        return None, "target_not_loaded"
    return (registered.config_entry_id, registered.unique_id, entity.name, entity), None


def _target(hass, context, entity_id):
    try:
        return _resolve_target(hass, context, entity_id)
    except Exception:
        return None, "target_lookup_failed"


def _same_target(hass, context, entity_id, initial):
    current, error = _target(hass, context, entity_id)
    return error is None and current is not None and current[:3] == initial[:3] and current[3] is initial[3]


def _common(entity_id: str, target, queried_at: datetime) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "success",
        "entity_id": entity_id,
        "target": {"config_entry_id": target[0], "unique_id": target[1], "name": target[2]},
        "queried_at": utc_timestamp(queried_at),
        "read_started_at": None,
        "read_finished_at": None,
        "warnings": [],
        "errors": [],
    }


def _read_logs(handler, name, level, start, end):
    entries = handler.get_entries(thermostat_name=name, min_level=level, start=start, end=end)
    count = len(entries)
    selected = entries[-LOG_LIMIT:]
    projected = [
        {"timestamp": utc_timestamp(entry.timestamp), "level": entry.level,
         "level_name": logging.getLevelName(entry.level),
         "logger_name": entry.logger_name, "message": entry.message}
        for entry in selected
    ]
    result = {
        "limit": LOG_LIMIT, "selection_policy": "last_entries_in_collector_order",
        "order": "collector_insertion", "selected_count": count,
        "returned_count": len(projected), "omitted_count": count - len(projected),
        "limit_exceeded": count > LOG_LIMIT, "truncated": count > LOG_LIMIT,
        "history_completeness": "not_guaranteed", "entries": projected,
    }
    if selected:
        result["returned_range"] = {
            "first": utc_timestamp(selected[0].timestamp),
            "last": utc_timestamp(selected[-1].timestamp),
            "minimum": utc_timestamp(min(entry.timestamp for entry in selected)),
            "maximum": utc_timestamp(max(entry.timestamp for entry in selected)),
        }
    return result


class GetVThermLogsTool(llm.Tool):
    """Read the existing in-memory collector for an exposed VTherm."""

    name = f"{DOMAIN}__get_logs"
    title = "Get VTherm logs / Journaux VTherm"
    description = (
        "EN: Read collector logs, not Recorder history; interpretation belongs to the agent. "
        "FR: Lit les journaux du collecteur, pas l'historique Recorder ; "
        "leur interprétation relève de l'agent. Read-only / lecture seule."
    )
    integration = DOMAIN

    def __init__(self, annotations):
        self.annotations = annotations
        self.parameters = probatio.Schema({
            probatio.Required("entity_id"): str,
            probatio.Optional("start_time"): str,
            probatio.Optional("end_time"): str,
            probatio.Optional("min_level", default="DEBUG"): probatio.In(list(LEVELS)),
        })

    async def async_call(self, hass, tool_input, llm_context):
        args = tool_input.tool_args
        entity_id = args.get("entity_id") if isinstance(args, Mapping) else None
        if not isinstance(args, Mapping):
            return _error(entity_id, "invalid_parameters", "parameters")
        unexpected = next((key for key in args if key not in ("entity_id", "start_time", "end_time", "min_level")), None)
        if unexpected is not None:
            return _error(entity_id, "invalid_parameters", "parameters", unexpected)
        for field in ("entity_id", "start_time", "end_time", "min_level"):
            if field in args and not isinstance(args[field], str):
                return _error(entity_id, "invalid_parameters", "parameters", field)
        if not isinstance(entity_id, str):
            return _error(entity_id, "invalid_parameters", "parameters", "entity_id")
        if args.get("min_level", "DEBUG") not in LEVELS:
            return _error(entity_id, "invalid_parameters", "parameters", "min_level")
        for field in ("start_time", "end_time"):
            if field in args:
                try:
                    parse_timestamp(args[field])
                except (ValueError, TypeError, OverflowError):
                    return _error(entity_id, "invalid_parameters", "parameters", field)
        try:
            data = self.parameters(args)
            now = datetime.now(timezone.utc)
            end = parse_timestamp(data["end_time"]) if "end_time" in data else ExactTimestamp.from_datetime(now)
            start = parse_timestamp(data["start_time"]) if "start_time" in data else end.minus_hour()
            collector_start, collector_end = start.ceil(), end.floor()
        except (ValueError, TypeError, probatio.Invalid, OverflowError):
            return _error(entity_id, "invalid_parameters", "parameters")
        if start > end:
            return _error(entity_id, "invalid_period", "parameters")
        target, error = _target(hass, llm_context, entity_id)
        if error or target is None:
            return _error(entity_id, error or "target_lookup_failed", "target")
        handler = hass.data.get(DOMAIN, {}).get("log_handler")
        if handler is None:
            return _error(entity_id, "collector_unavailable", "collector")
        getter = getattr(handler, "get_entries", None)
        if not callable(getter):
            return _error(entity_id, "collector_incompatible", "collector")
        try:
            inspect.signature(getter).bind(thermostat_name=target[2], min_level=LEVELS[data["min_level"]], start=collector_start, end=collector_end)
        except (TypeError, ValueError):
            return _error(entity_id, "collector_incompatible", "collector")
        result = _common(entity_id, target, now)
        result["read_started_at"] = utc_timestamp(datetime.now(timezone.utc))
        try:
            logs = await hass.async_add_executor_job(partial(_read_logs, handler, target[2], LEVELS[data["min_level"]], collector_start, collector_end))
        except Exception:
            if not _same_target(hass, llm_context, entity_id, target):
                return _error(entity_id, "target_changed", "target")
            return _error(entity_id, "collector_read_failed", "collector")
        result["read_finished_at"] = utc_timestamp(datetime.now(timezone.utc))
        if not _same_target(hass, llm_context, entity_id, target):
            return _error(entity_id, "target_changed", "target")
        result["filters"] = {
            "requested_start_time": data.get("start_time"), "requested_end_time": data.get("end_time"),
            "start_time": start.isoformat(), "end_time": end.isoformat(),
            "normalization_policy": "explicit_offset_to_utc", "normalization_path": "stdlib_aware_datetime",
            "min_level": data["min_level"], "thermostat_name": target[2],
        }
        result.update(logs)
        return llm.ToolResult(data=result)


PLUGIN_DOMAINS = {
    "vtherm_smartpi": ("CAT-01", "smartpi"),
    "vtherm_hysteresis": ("CAT-01", "hysteresis"),
    "vtherm_pellet_stove": ("CAT-01", "pellet_regulation"),
    "vtherm_auto_fan_extended": ("CAT-02", None),
    "vtherm_heating_failure_detection": ("CAT-02", None),
    "vtherm_climate_replication": ("CAT-03", None),
    "vtherm_inhibition": ("CAT-04", None),
}

SMARTPI_FIELDS = {
    "control": ("phase", "mode", "hysteresis_state", "kp", "ki", "restart_reason"),
    "power": ("current_cycle_percent", "next_cycle_percent", "pi_percent", "ff_percent", "hold_percent"),
    "temperature": ("sensor", "ext_sensor", "error", "integral_error", "integral_mode", "integral_hold_mode", "integral_guard_source"),
    "model": ("a", "b", "confidence", "tau_reliable", "deadtime_heat_s", "deadtime_cool_s"),
    "ab_learning": ("stage", "bootstrap_progress_percent", "bootstrap_status", "accepted_samples_a", "accepted_samples_b", "target_samples", "last_reason", "a_drift_state", "b_drift_state"),
    "governance": ("regime", "thermal_update_decision", "thermal_update_reason"),
    "feedforward": ("ff3_status", "ff3_twin_usable", "twin_status", "deadband_power_source"),
    "setpoint": ("filtered_setpoint", "trajectory_active", "trajectory_source"),
    "autocalib": ("state", "model_degraded", "last_trigger_ts", "next_check_ts", "snapshot_age_h"),
    "calibration": ("state", "retry_count", "last_time"),
}
HYSTERESIS_FIELDS = ("is_active", "hvac_mode", "on_percent", "last_reason", "activation_threshold", "deactivation_threshold", "hysteresis_on", "hysteresis_off", "max_on_percent", "min_on_percent")
PELLET_FIELDS = ("phase", "available", "is_heating", "on_percent", "current_level", "current_level_index", "observed_cycle", "observed_phase", "pending_command", "command_error", "last_reason", "last_on_at", "last_off_at", "next_action_allowed_at", "remaining_on_sec", "remaining_off_sec", "boost_active", "boost_until")
AUTO_FAN_FIELDS = ("enabled", "current_gap", "selected_fan_mode", "sent_fan_mode", "rest_mode", "thresholds")
FAILURE_FIELDS = ("heating_failure_state", "cooling_failure_state", "heating_failure_threshold", "cooling_failure_threshold", "detection_delay_min", "temperature_change_tolerance", "is_detection_enabled_by_template", "heating_tracking", "cooling_tracking")
TRACKING_FIELDS = ("is_tracking", "initial_temperature", "current_temperature", "remaining_time_min", "elapsed_time_min", "root_cause", "root_cause_entity_id")
INHIBITION_FIELDS = ("status", "raw_status", "stop_underlyings", "bypass", "active_sources", "pending_status", "pending_until", "last_change", "unavailable_since", "missing_sources", "sources", "vtherm_entity_id", "vtherm_available", "last_api_call", "last_api_call_at", "last_error", "retry_pending", "waiting_for_vtherm_start", "next_retry_at")
DATE_FIELDS = {"last_on_at", "last_off_at", "next_action_allowed_at", "boost_until", "pending_until", "last_change", "unavailable_since", "last_api_call_at", "next_retry_at", "last_trigger_ts", "next_check_ts", "last_time"}
FAILURE_CONFIG_KEYS = {"enabled", "heating_percent_threshold", "cooling_percent_threshold", "temperature_delta", "delay_minutes", "activation_template"}


def _fact(value=None, knowledge="unknown", source=None, scope="runtime_component", reason=None):
    return {"value": value, "knowledge": knowledge, "source": source, "scope": scope, "reason": reason}


def _minimum_met(diagnostic):
    return not any(reason.startswith("invalid_fields:") or reason == "plugin_read_failed" for reason in diagnostic.get("reasons", ()))


def _safe_value(value):
    if isinstance(value, Enum):
        value = value.value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, datetime):
        return utc_timestamp(value)
    if isinstance(value, (tuple, list)):
        return [_safe_value(item) for item in value]
    if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
        return {key: _safe_value(item) for key, item in value.items()}
    raise ValueError("unsupported published value")


def _date_value(value):
    if isinstance(value, datetime):
        try:
            return {"raw": value.isoformat(), "normalized": utc_timestamp(value), "knowledge": "known"}
        except ValueError:
            return {"raw": value.isoformat(), "normalized": None, "knowledge": "unknown", "reason": "source_timezone_unknown"}
    try:
        if isinstance(value, str):
            return {"raw": value, "normalized": parse_timestamp(value).isoformat(), "knowledge": "known"}
    except (ValueError, OverflowError):
        pass
    return {"raw": _safe_value(value), "normalized": None, "knowledge": "unknown", "reason": "source_timezone_unknown"}


def _project(mapping, fields):
    if not isinstance(mapping, Mapping):
        raise ValueError("unsupported published schema")
    result = {}
    invalid = []
    for key in fields:
        if key not in mapping:
            continue
        value = mapping[key]
        try:
            if key in DATE_FIELDS and value is not None:
                result[key] = _date_value(value)
            elif key in ("heating_tracking", "cooling_tracking"):
                result[key], nested_invalid = _project(value, TRACKING_FIELDS)
                invalid.extend(f"{key}.{name}" for name in nested_invalid)
            elif key == "sources":
                if not isinstance(value, Mapping):
                    raise ValueError("unsupported sources")
                result[key] = {}
                for source, details in value.items():
                    if not isinstance(source, str):
                        invalid.append(key)
                        continue
                    try:
                        result[key][source], nested_invalid = _project(details, ("state", "contribution"))
                        invalid.extend(f"{key}.{source}.{name}" for name in nested_invalid)
                    except (ValueError, TypeError, OverflowError):
                        invalid.append(f"{key}.{source}")
            elif key == "thresholds":
                if not isinstance(value, Mapping) or any(not isinstance(name, str) or isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) for name, number in value.items()):
                    raise ValueError("unsupported thresholds")
                result[key] = dict(value)
            else:
                result[key] = _safe_value(value)
        except (ValueError, TypeError, OverflowError):
            invalid.append(key)
    return result, invalid


def _source(hass, entity_id, path, observed_at):
    state = hass.states.get(entity_id) if entity_id else None
    source = {"source_entity_id": entity_id, "attribute_path": path,
              "state_last_updated": None, "state_last_changed": None,
              "observed_at": utc_timestamp(observed_at), "measurement_at": None,
              "restoration": "unknown"}
    if state is None:
        return None, source
    for field in ("last_updated", "last_changed"):
        value = getattr(state, field, None)
        if value is not None:
            date = _date_value(value)
            source[f"state_{field}"] = date["normalized"]
            source[f"state_{field}_raw"] = date["raw"]
            source[f"state_{field}_knowledge"] = date["knowledge"]
            if "reason" in date:
                source[f"state_{field}_reason"] = date["reason"]
    source["availability"] = "unavailable" if state.state in ("unavailable", "unknown") else "available"
    return state, source


def _diagnostics(hass, registry, domain, uid, entity_id, observed_at, config_entry_id=None):
    if domain == "vtherm_climate_replication":
        return {"status": "partial", "producer": domain, "values": {}, "sources": [], "reasons": ["runtime_link_unverifiable"]}
    sensor = {
        "vtherm_smartpi": ("sensor", f"smartpi_diag_{uid}"),
        "vtherm_pellet_stove": ("sensor", f"{domain}_{uid}_debug"),
        "vtherm_inhibition": ("binary_sensor", f"{uid}_inhibition"),
    }.get(domain)
    source_id = registry.async_get_entity_id(sensor[0], domain, sensor[1]) if sensor else entity_id
    if sensor and source_id and config_entry_id is not None:
        registered = registry.async_get(source_id)
        if registered is None or registered.config_entry_id != config_entry_id:
            return {"status": "unavailable", "producer": "unknown", "values": {}, "sources": [], "reasons": ["source_identity_unverified"]}
    path = {"vtherm_hysteresis": "specific_states.hysteresis", "vtherm_auto_fan_extended": "auto_fan", "vtherm_heating_failure_detection": "heating_failure_detection_manager"}.get(domain)
    state, source = _source(hass, source_id, path, observed_at)
    producer = "unknown" if domain == "vtherm_heating_failure_detection" else domain
    if state is None:
        return {"status": "unavailable", "producer": producer, "values": {}, "sources": [source], "reasons": ["source_not_published"]}
    attributes = state.attributes
    if path:
        for key in path.split("."):
            attributes = attributes.get(key) if isinstance(attributes, Mapping) else None
    if attributes is None:
        return {"status": "unavailable", "producer": producer, "values": {}, "sources": [source], "reasons": ["source_not_published"]}
    if domain == "vtherm_smartpi":
        values, invalid, missing = {}, [], False
        for block, keys in SMARTPI_FIELDS.items():
            if block in attributes:
                try:
                    values[block], errors = _project(attributes[block], keys)
                    invalid.extend(f"{block}.{key}" for key in errors)
                    missing |= any(key not in attributes[block] for key in keys)
                except ValueError:
                    invalid.append(block)
            else:
                missing = True
    else:
        fields = {"vtherm_hysteresis": HYSTERESIS_FIELDS, "vtherm_pellet_stove": PELLET_FIELDS,
                  "vtherm_auto_fan_extended": AUTO_FAN_FIELDS, "vtherm_heating_failure_detection": FAILURE_FIELDS,
                  "vtherm_inhibition": INHIBITION_FIELDS}[domain]
        values, invalid = _project(attributes, fields)
        missing = any(key not in attributes for key in fields)
        for key in ("heating_tracking", "cooling_tracking"):
            if key in attributes and isinstance(attributes[key], Mapping):
                missing |= any(field not in attributes[key] for field in TRACKING_FIELDS)
        if isinstance(attributes.get("sources"), Mapping):
            missing |= any(isinstance(details, Mapping) and any(field not in details for field in ("state", "contribution")) for details in attributes["sources"].values())
    if sensor:
        values["state"] = state.state
    reasons = ["field_not_published"] if missing else []
    if source["availability"] == "unavailable":
        reasons.append("last_publication_unavailable")
    if invalid:
        reasons.append("invalid_fields:" + ",".join(invalid))
    if producer == "unknown":
        reasons.append("state_origin_unverifiable")
    return {"status": "partial" if reasons else "complete", "producer": producer, "values": values, "sources": [source], "reasons": reasons}


def _plugin_record(hass, registry, domain, entry, category, target, entity_id, observed_at, selected, relation):
    plugin_id = f"{domain}:{entry.entry_id}"
    source = f"config_entry:{entry.entry_id}"
    facts = {
        "configured": _fact(True, "known", source, "integration_entry"),
        "selected": _fact(selected, "known" if selected is not None else "unknown", "merged_target_configuration", "runtime_component"),
        "loaded": _fact(entry.state == ConfigEntryState.LOADED, "known", source, "integration_entry"),
        "handler_loaded": _fact(reason="no_public_handler_contract"),
        "configuration_applied": _fact(reason="application_unverifiable"),
        "enabled": _fact(reason="not_published"),
        "operational_ready": _fact(reason="not_published"),
        "active": _fact(reason="not_published"),
        "available": _fact(reason="source_not_published", scope="state_source"),
    }
    if domain == "vtherm_climate_replication":
        runtime = hass.data.get(domain, {}).get(entry.entry_id, {})
        if isinstance(runtime, Mapping) and isinstance(runtime.get("enabled"), bool):
            facts["enabled"] = _fact(runtime["enabled"], "known", f"runtime:{domain}:{entry.entry_id}", "runtime_component")
    if domain == "vtherm_heating_failure_detection":
        runtime = hass.data.get(domain, {}).get("entries", {})
        if isinstance(runtime, Mapping):
            facts["runtime_configuration_present"] = _fact(entry.entry_id in runtime, "known", f"runtime:{domain}:entries", "runtime_component")
        declared = entry.options or entry.data
        if "enabled" in declared and isinstance(declared["enabled"], bool):
            facts["declared_enabled"] = _fact(declared["enabled"], "known", source, "integration_entry")
    try:
        diagnostic = _diagnostics(hass, registry, domain, target[1], entity_id, observed_at, entry.entry_id)
    except Exception:
        diagnostic = {"status": "unavailable", "producer": "unknown", "values": {}, "sources": [], "reasons": ["plugin_read_failed"]}
    if diagnostic["sources"] and "availability" in diagnostic["sources"][0]:
        available = diagnostic["sources"][0]["availability"] == "available"
        facts["available"] = _fact(available, "known", diagnostic["sources"][0]["source_entity_id"], "state_source")
    if domain == "vtherm_auto_fan_extended" and "enabled" in diagnostic["values"]:
        facts["enabled"] = _fact(diagnostic["values"]["enabled"], "known", entity_id, "state_source")
    if (domain == "vtherm_hysteresis" and selected is True
            and facts["available"]["value"] is True
            and isinstance(diagnostic["values"].get("is_active"), bool)):
        facts["active"] = _fact(diagnostic["values"]["is_active"], "known", entity_id, "state_source", "published_logical_controller_state")
    source_info = diagnostic["sources"][0] if diagnostic["sources"] else None
    diagnostic["field_facts"] = {
        key: _fact(value, "known", source_info, "state_source", "last_publication_unavailable" if source_info and source_info.get("availability") == "unavailable" else None)
        for key, value in diagnostic["values"].items()
    }
    applies = _fact(reason="application_unverifiable", source=source, scope="integration_entry") if relation == "global_configuration" else _fact(True, "known", source, "integration_entry")
    link = {"relation": relation, "target": entity_id, "source": source, "applies_to_target": applies}
    if domain == "vtherm_climate_replication":
        link["physical_climate"] = entry.data.get("physical_climate")
    return {"plugin_id": plugin_id, "domain": domain, "config_entry_id": entry.entry_id,
            "label": domain, "categories": [category], "links": [link], "facts": facts,
            "diagnostics": diagnostic, "state_minimum_status": "met" if _minimum_met(diagnostic) else "not_met"}


def _failure_global_applies(runtime, entry_id, values, target_uid):
    if not isinstance(runtime, Mapping) or runtime.get(entry_id) != dict(values):
        return None
    global_owners = {}
    targeted_keys = set()
    for candidate_id, candidate in runtime.items():
        if not isinstance(candidate, Mapping):
            return None
        candidate_target = candidate.get("vtherm_unique_id")
        keys = FAILURE_CONFIG_KEYS.intersection(candidate)
        if candidate_target == target_uid:
            targeted_keys.update(keys)
        elif not candidate_target:
            global_owners.update({key: candidate_id for key in keys})
    return any(owner == entry_id and key not in targeted_keys for key, owner in global_owners.items())


def _read_plugins(hass, entity_id, target, observed_at):
    registry = er.async_get(hass)
    config = target[3].entry_infos
    algorithm = config.get("proportional_function") if isinstance(config, Mapping) else None
    plugins, unresolved, errors = [], [], []
    categories = {key: {"status": "complete", "integrations": [], "reasons": []} for key in ("CAT-01", "CAT-02", "CAT-03", "CAT-04")}
    selected_attached = False
    successes = 0
    for domain, (category, algorithm_name) in PLUGIN_DOMAINS.items():
        try:
            entries = list(hass.config_entries.async_entries(domain))
            successes += 1
            categories[category]["integrations"].append({"domain": domain, "format": "config_entry", "version": "not_verified"})
            matches = []
            valid_entries = []
            for entry in entries:
                try:
                    data = entry.data
                    if algorithm_name or domain == "vtherm_auto_fan_extended":
                        if data.get("target_vtherm_unique_id") == target[1]:
                            matches.append((entry, "targeted_configuration"))
                    elif domain == "vtherm_heating_failure_detection":
                        values = entry.options or data
                        if values.get("vtherm_unique_id") == target[1]:
                            matches.append((entry, "targeted_configuration"))
                        elif not values.get("vtherm_unique_id") and FAILURE_CONFIG_KEYS.intersection(values):
                            runtime = hass.data.get(domain, {}).get("entries", {})
                            applies = _failure_global_applies(runtime, entry.entry_id, values, target[1])
                            if applies:
                                matches.append((entry, "global_configuration"))
                            elif applies is None:
                                unresolved.append({"observation_id": f"global:{domain}:{entry.entry_id}:{target[1]}", "link_proof": "unproven", "relation": "global_configuration", "target": entity_id, "source": f"config_entry:{entry.entry_id}", "facts": {"applies_to_target": _fact(reason="runtime_configuration_unavailable", source=f"config_entry:{entry.entry_id}", scope="integration_entry")}})
                                categories[category]["status"] = "partial"
                                categories[category]["reasons"].append("global_application_unverifiable")
                    elif domain == "vtherm_climate_replication" and data.get("target_climate") == entity_id:
                        matches.append((entry, "targeted_configuration"))
                    elif domain == "vtherm_inhibition":
                        values = {**data, **entry.options}
                        uid = values.get("vtherm_unique_id")
                        if (uid and uid == target[1]) or (not uid and values.get("vtherm_entity_id") == entity_id):
                            matches.append((entry, "targeted_configuration"))
                    valid_entries.append(entry)
                except Exception:
                    categories[category]["status"] = "partial"
                    categories[category]["reasons"].append("entry_schema_unavailable")
                    errors.append({"code": "plugin_read_failed", "scope": category, "plugin_id": None, "source": domain, "field": "config_entry", "message_fr": "Entrée de plugin illisible", "message_en": "Plugin entry unreadable"})
            selected_entry = None
            if algorithm_name and algorithm == algorithm_name:
                targeted = [entry for entry, _ in matches]
                global_entries = [entry for entry in valid_entries if entry.unique_id == domain and entry.data.get("target_vtherm_unique_id") is None]
                selected_entry = (targeted[-1] if domain == "vtherm_pellet_stove" else targeted[0]) if targeted else ((global_entries[-1] if domain == "vtherm_pellet_stove" else global_entries[0]) if global_entries else None)
                if selected_entry and not targeted:
                    matches.append((selected_entry, "effective_global"))
            for entry, relation in matches:
                try:
                    selected = entry is selected_entry if algorithm_name and algorithm is not None else None
                    record = _plugin_record(hass, registry, domain, entry, category, target, entity_id, observed_at, selected, relation)
                    if selected:
                        record["links"].append({"relation": "selected_algorithm", "target": entity_id, "source": "merged_target_configuration.proportional_function", "applies_to_target": _fact(True, "known", "merged_target_configuration", "runtime_component")})
                        selected_attached = True
                    plugins.append(record)
                    if "plugin_read_failed" in record["diagnostics"]["reasons"]:
                        errors.append({"code": "plugin_read_failed", "scope": category, "plugin_id": record["plugin_id"], "source": domain, "field": "diagnostics", "message_fr": "Diagnostic indisponible", "message_en": "Diagnostic unavailable"})
                except Exception:
                    categories[category]["status"] = "partial"
                    errors.append({"code": "plugin_read_failed", "scope": category, "plugin_id": f"{domain}:{entry.entry_id}", "source": domain, "field": None, "message_fr": "Lecture du plugin impossible", "message_en": "Plugin read failed"})
        except Exception:
            categories[category]["status"] = "partial"
            categories[category]["reasons"].append(f"{domain}:plugin_discovery_unavailable")
            errors.append({"code": "plugin_read_failed", "scope": category, "plugin_id": None, "source": domain, "field": None, "message_fr": "Découverte du plugin impossible", "message_en": "Plugin discovery failed"})
    if isinstance(algorithm, str) and algorithm and algorithm != "tpi" and not selected_attached:
        observation = {"observation_id": f"selection:{target[1]}:{algorithm}", "link_proof": "proven", "relation": "selected_algorithm", "target": entity_id, "algorithm": algorithm, "source": "merged_target_configuration.proportional_function", "facts": {"configured": _fact(True, "known", "merged_target_configuration", "runtime_component"), "selected": _fact(True, "known", "merged_target_configuration", "runtime_component"), "identity": _fact(reason="configured_identity_unresolved")}}
        domain = next((name for name, (_, value) in PLUGIN_DOMAINS.items() if value == algorithm), None)
        if domain:
            try:
                diagnostic = _diagnostics(hass, registry, domain, target[1], entity_id, observed_at)
                diagnostic["producer"] = "unknown"
                if diagnostic["status"] == "complete":
                    diagnostic["status"] = "partial"
                diagnostic["reasons"].append("configured_identity_unresolved")
                observation["diagnostics"] = diagnostic
            except Exception:
                observation["diagnostics"] = {"status": "unavailable", "producer": "unknown", "values": {}, "sources": [], "reasons": ["plugin_read_failed"]}
                errors.append({"code": "plugin_read_failed", "scope": "CAT-01", "plugin_id": None, "source": domain, "field": "diagnostics", "message_fr": "Diagnostic indisponible", "message_en": "Diagnostic unavailable"})
        unresolved.append(observation)
        categories["CAT-01"]["status"] = "partial"
        categories["CAT-01"]["reasons"].append("configured_identity_unresolved")
    elif algorithm is not None and not isinstance(algorithm, str):
        categories["CAT-01"]["status"] = "partial"
        categories["CAT-01"]["reasons"].append("target_configuration_schema_unsupported")
    if not isinstance(config, Mapping):
        categories["CAT-01"]["status"] = "partial"
        categories["CAT-01"]["reasons"].append("target_configuration_unavailable")
    elif config.get("use_heating_failure_detection_feature"):
        unresolved.append({"observation_id": f"legacy_failure:{target[1]}", "link_proof": "unproven", "relation": "legacy_merged", "target": entity_id, "source": "merged_target_configuration.use_heating_failure_detection_feature", "facts": {"external_plugin_application": _fact(reason="native_or_external_producer_unverifiable")}})
        categories["CAT-02"]["status"] = "partial"
        categories["CAT-02"]["reasons"].append("native_or_external_producer_unverifiable")
    partial_discovery = any(item["status"] != "complete" for item in categories.values())
    diagnostic_statuses = [plugin["diagnostics"]["status"] for plugin in plugins]
    if unresolved:
        diagnostics_status = "partial"
    elif not diagnostic_statuses:
        diagnostics_status = "not_supported"
    elif all(status == "complete" for status in diagnostic_statuses):
        diagnostics_status = "complete"
    elif all(status == "unavailable" for status in diagnostic_statuses):
        diagnostics_status = "unavailable"
    else:
        diagnostics_status = "partial"
    return {"status": "error" if not successes and not unresolved else ("partial" if partial_discovery or plugins or errors else "success"),
            "plugins": plugins, "unresolved_links": unresolved,
            "identified_configured_plugin_count": len(plugins) if successes else None,
            "proven_unresolved_selection_count": sum(link["link_proof"] == "proven" for link in unresolved),
            "configured_plugin_count": None if any(link["link_proof"] == "proven" for link in unresolved) or not successes or partial_discovery else len(plugins),
            "configured_plugin_count_reason": "configured_identity_unresolved" if any(link["link_proof"] == "proven" for link in unresolved) else ("discovery_incomplete" if partial_discovery else None),
            "coverage": {"categories": categories, "discovery": {"status": "partial" if partial_discovery else "complete"}, "third_party_exhaustive": False, "future_plugins_discovery": "not_guaranteed"},
            "diagnostics_status": diagnostics_status, "state_minimum_status": "not_met" if any(plugin["state_minimum_status"] == "not_met" for plugin in plugins) or any(not _minimum_met(link.get("diagnostics", {})) for link in unresolved) or errors else "met", "errors": errors}


class GetVThermPluginsTool(llm.Tool):
    """Read configured plugin links and previously published diagnostics."""

    name = f"{DOMAIN}__get_plugins"
    title = "Get VTherm plugins / Plugins VTherm"
    description = ("EN: Read configured plugin links and published diagnostics; coverage is limited and interpretation belongs to the agent. "
                   "FR: Lit les liens configurés et diagnostics publiés des plugins ; couverture limitée et interprétation par l'agent. Read-only / lecture seule.")
    integration = DOMAIN

    def __init__(self, annotations):
        self.annotations = annotations
        self.parameters = probatio.Schema({probatio.Required("entity_id"): str})

    async def async_call(self, hass, tool_input, llm_context):
        args = tool_input.tool_args
        entity_id = args.get("entity_id") if isinstance(args, Mapping) else None
        if not isinstance(args, Mapping) or not isinstance(entity_id, str):
            return _error(entity_id, "invalid_parameters", "parameters", "entity_id")
        unexpected = next((key for key in args if key != "entity_id"), None)
        if unexpected is not None:
            return _error(entity_id, "invalid_parameters", "parameters", unexpected)
        try:
            self.parameters(args)
        except (ValueError, TypeError, probatio.Invalid):
            return _error(entity_id, "invalid_parameters", "parameters")
        target, error = _target(hass, llm_context, entity_id)
        if error or target is None:
            return _error(entity_id, error or "target_lookup_failed", "target")
        now = datetime.now(timezone.utc)
        result = _common(entity_id, target, now)
        result["read_started_at"] = utc_timestamp(datetime.now(timezone.utc))
        try:
            result.update(_read_plugins(hass, entity_id, target, now))
        except Exception:
            return _error(entity_id, "plugin_discovery_unavailable", "plugins")
        result["read_finished_at"] = utc_timestamp(datetime.now(timezone.utc))
        if result["status"] == "error":
            result["errors"].append({"code": "plugin_discovery_unavailable", "scope": "plugins", "plugin_id": None, "source": None, "field": None, "message_fr": "Découverte indisponible", "message_en": "Discovery unavailable"})
        return llm.ToolResult(data=result, error=result["status"] == "error")