"""Read-only LLM diagnostic contract tests with synthetic HA data."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import llm as ha_llm

if not all(hasattr(ha_llm, name) for name in ("ToolAnnotations", "ToolResult")):
    pytest.skip(
        "Home Assistant LLM ToolAnnotations/ToolResult API is unavailable in this test environment",
        allow_module_level=True,
    )

from custom_components.versatile_thermostat import llm
from custom_components.versatile_thermostat.llm import diagnostics as diag
from custom_components.versatile_thermostat.llm.diagnostic_time import parse_timestamp

ENTITY = "climate.test"
UID = "thermostat-1"
NOW = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)


def entry(domain, entry_id, data, *, options=None, unique_id=None, loaded=True):
    return SimpleNamespace(domain=domain, entry_id=entry_id, data=data, options=options or {},
                           unique_id=unique_id, state=ConfigEntryState.LOADED if loaded else ConfigEntryState.NOT_LOADED)


def state(entity_id, attributes=None, value="heat"):
    return SimpleNamespace(entity_id=entity_id, state=value, attributes=attributes or {}, last_changed=NOW, last_updated=NOW)


@pytest.fixture(name="fixture")
def diagnostic_fixture(monkeypatch):
    thermostat = SimpleNamespace(unique_id=UID, name="Internal Name", entry_infos={"proportional_function": "tpi"})
    registered = SimpleNamespace(domain="climate", platform=diag.DOMAIN, config_entry_id="core-entry", unique_id=UID)
    states = {ENTITY: state(ENTITY)}
    entries = {diag.DOMAIN: [entry(diag.DOMAIN, "core-entry", {})]}
    sensor_ids = {}
    registry = SimpleNamespace(async_get=Mock(side_effect=lambda entity_id: registered if entity_id == ENTITY else SimpleNamespace(config_entry_id="plugin-entry")),
                               async_get_entity_id=Mock(side_effect=lambda kind, platform, unique: sensor_ids.get((kind, platform, unique))))
    exposed = Mock(return_value=True)
    monkeypatch.setattr(diag.er, "async_get", lambda hass: registry)
    monkeypatch.setattr(diag, "async_should_expose", exposed)
    async def executor(func):
        return func()
    hass = SimpleNamespace(data={"climate": SimpleNamespace(get_entity=Mock(return_value=thermostat)), diag.DOMAIN: {}},
                           states=SimpleNamespace(get=Mock(side_effect=states.get)),
                           config_entries=SimpleNamespace(async_entries=Mock(side_effect=lambda domain: entries.get(domain, [])),
                                                          async_get_entry=Mock(return_value=entries[diag.DOMAIN][0])),
                           async_add_executor_job=AsyncMock(side_effect=executor),
                           services=SimpleNamespace(async_call=AsyncMock()), auth=SimpleNamespace(async_get_user=AsyncMock()))
    context = SimpleNamespace(assistant="conversation", context=None, language="fr")
    return SimpleNamespace(hass=hass, thermostat=thermostat, entries=entries, states=states,
                           registry=registry, sensor_ids=sensor_ids, exposed=exposed, context=context)


async def call(tool, fixture, **args):
    return await tool.async_call(fixture.hass, SimpleNamespace(tool_args={"entity_id": ENTITY, **args}), fixture.context)


def log_entry(index, timestamp=NOW):
    return SimpleNamespace(timestamp=timestamp, level=logging.INFO, logger_name="full.logger", message=f"message {index}")


def install_collector(fixture, records):
    handler = SimpleNamespace(get_entries=Mock(return_value=records))
    fixture.hass.data[diag.DOMAIN]["log_handler"] = handler
    return handler


@pytest.mark.parametrize("count", [0, 4999, 5000, 5001])
async def test_log_cap_and_order(fixture, count):
    records = [log_entry(index, NOW + timedelta(seconds=index % 2)) for index in range(count)]
    handler = install_collector(fixture, records)
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.error is False
    assert result.data["selected_count"] == count
    assert result.data["returned_count"] == min(count, 5000)
    assert result.data["omitted_count"] == max(count - 5000, 0)
    assert result.data["truncated"] == (count > 5000)
    assert ("returned_range" in result.data) == bool(count)
    if count:
        assert result.data["entries"][0]["message"] == f"message {max(0, count - 5000)}"
    handler.get_entries.assert_called_once()
    assert handler.get_entries.call_args.kwargs["thermostat_name"] == "Internal Name"
    fixture.hass.services.async_call.assert_not_awaited()
    fixture.hass.auth.async_get_user.assert_not_awaited()


@pytest.mark.parametrize("value", ["2026-11-08", "2026-11-08T00:00:00", "2026-11-08T00:00:00+01:99", "invalid"])
async def test_invalid_date(fixture, value):
    install_collector(fixture, [])
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture, start_time=value)
    assert result.error and result.data["errors"][0]["code"] == "invalid_parameters"
    fixture.hass.async_add_executor_job.assert_not_awaited()


async def test_exact_offset_and_default_start(fixture):
    handler = install_collector(fixture, [])
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture, end_time="2026-11-08T02:00:00.123456789+02:00")
    assert result.data["filters"]["end_time"] == "2026-11-08T00:00:00.123456789Z"
    assert result.data["filters"]["start_time"] == "2026-11-07T23:00:00.123456789Z"
    assert handler.get_entries.call_args.kwargs["start"].microsecond == 123457
    assert handler.get_entries.call_args.kwargs["end"].microsecond == 123456
    assert parse_timestamp("2026-11-08T02:00:00+02:00") == parse_timestamp("2026-11-08T00:00:00Z")


@pytest.mark.parametrize("error", ["missing", "incompatible", "failure"])
async def test_collector_errors(fixture, error):
    if error == "incompatible":
        fixture.hass.data[diag.DOMAIN]["log_handler"] = object()
    elif error == "failure":
        install_collector(fixture, []).get_entries.side_effect = RuntimeError("private data")
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.error
    assert result.data["errors"][0]["code"] == {"missing": "collector_unavailable", "incompatible": "collector_incompatible", "failure": "collector_read_failed"}[error]
    assert "private data" not in json.dumps(result.data)


async def test_target_revalidated_after_executor(fixture):
    install_collector(fixture, [log_entry(0)])
    async def executor(func):
        result = func()
        fixture.exposed.return_value = False
        return result
    fixture.hass.async_add_executor_job.side_effect = executor
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.error and result.data["errors"][0]["code"] == "target_changed"
    assert "entries" not in result.data


async def test_cancellation_propagates(fixture):
    handler = install_collector(fixture, [])
    fixture.hass.async_add_executor_job.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    handler.get_entries.assert_not_called()
    fixture.hass.services.async_call.assert_not_awaited()


async def test_plugin_cancellation_propagates(fixture):
    fixture.hass.config_entries.async_entries.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)


@pytest.mark.parametrize("domain,data,sensor_key,attributes", [
    ("vtherm_smartpi", {"target_vtherm_unique_id": UID}, ("sensor", "smartpi_diag_" + UID), {"control": {"phase": "HEAT", "kp": 0, "private": "secret"}}),
    ("vtherm_hysteresis", {"target_vtherm_unique_id": UID}, None, {"specific_states": {"hysteresis": {"is_active": False, "on_percent": 0}}}),
    ("vtherm_pellet_stove", {"target_vtherm_unique_id": UID}, ("sensor", "vtherm_pellet_stove_" + UID + "_debug"), {"phase": "idle", "on_percent": 0}),
    ("vtherm_auto_fan_extended", {"target_vtherm_unique_id": UID}, None, {"auto_fan": {"enabled": False, "current_gap": 0}}),
    ("vtherm_heating_failure_detection", {"vtherm_unique_id": UID}, None, {"heating_failure_detection_manager": {"heating_failure_state": "unknown", "failure_detection_enable_template": "secret"}}),
    ("vtherm_climate_replication", {"target_climate": ENTITY, "physical_climate": "climate.source"}, None, {}),
    ("vtherm_inhibition", {"vtherm_unique_id": UID}, ("binary_sensor", UID + "_inhibition"), {"status": "UNKNOWN", "retry_pending": False}),
])
async def test_seven_plugin_adapters(fixture, domain, data, sensor_key, attributes):
    fixture.entries[domain] = [entry(domain, "plugin-entry", data, loaded=False)]
    if sensor_key:
        fixture.sensor_ids[(sensor_key[0], domain, sensor_key[1])] = "sensor.diagnostic"
        fixture.states["sensor.diagnostic"] = state("sensor.diagnostic", attributes, "unavailable")
    else:
        fixture.states[ENTITY] = state(ENTITY, attributes)
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert not result.error
    plugin = result.data["plugins"][0]
    assert plugin["domain"] == domain
    assert plugin["facts"]["loaded"]["value"] is False
    assert plugin["facts"]["configuration_applied"]["knowledge"] == "unknown"
    assert "secret" not in json.dumps(result.data)
    if domain == "vtherm_heating_failure_detection":
        assert plugin["diagnostics"]["producer"] == "unknown"
    if domain == "vtherm_auto_fan_extended":
        assert plugin["facts"]["enabled"]["value"] is False
        assert plugin["diagnostics"]["values"]["current_gap"] == 0
    fixture.hass.services.async_call.assert_not_awaited()
    fixture.hass.auth.async_get_user.assert_not_awaited()


async def test_unresolved_algorithm_is_not_counted_as_another_plugin(fixture):
    fixture.thermostat.entry_infos["proportional_function"] = "unknown_external"
    fixture.entries["vtherm_smartpi"] = [entry("vtherm_smartpi", "smart", {"target_vtherm_unique_id": UID})]
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.data["identified_configured_plugin_count"] == 1
    assert result.data["proven_unresolved_selection_count"] == 1
    assert result.data["configured_plugin_count"] is None
    assert result.data["unresolved_links"][0]["facts"]["selected"]["value"] is True


async def test_global_not_applied_when_algorithm_not_selected(fixture):
    fixture.entries["vtherm_smartpi"] = [entry("vtherm_smartpi", "global", {}, unique_id="vtherm_smartpi")]
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.data["plugins"] == []
    assert result.data["configured_plugin_count"] == 0


@pytest.mark.parametrize("available", [True, False])
async def test_selected_global_hysteresis_completeness_and_logical_activity(fixture, available):
    domain = "vtherm_hysteresis"
    fixture.thermostat.entry_infos["proportional_function"] = "hysteresis"
    fixture.entries[domain] = [entry(domain, "global", {}, unique_id=domain)]
    values: dict[str, object] = {key: None for key in diag.HYSTERESIS_FIELDS}
    values["is_active"] = False
    fixture.states[ENTITY] = state(ENTITY, {"specific_states": {"hysteresis": values}}, "heat" if available else "unavailable")
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    plugin = result.data["plugins"][0]
    assert plugin["links"][0]["applies_to_target"]["value"] is True
    assert plugin["facts"]["configuration_applied"]["knowledge"] == "unknown"
    assert plugin["facts"]["active"]["knowledge"] == ("known" if available else "unknown")
    if available:
        assert plugin["facts"]["active"]["value"] is False
        assert plugin["facts"]["active"]["reason"] == "published_logical_controller_state"
        assert plugin["diagnostics"]["status"] == result.data["diagnostics_status"] == "complete"
        assert "field_not_published" not in plugin["diagnostics"]["reasons"]
    else:
        assert plugin["diagnostics"]["status"] == "partial"


@pytest.mark.parametrize("algorithm", ["hysteresis", "tpi", None])
async def test_hysteresis_shared_publication_is_not_attributed_to_unselected_entry(fixture, algorithm):
    domain = "vtherm_hysteresis"
    fixture.thermostat.entry_infos["proportional_function"] = algorithm
    fixture.entries[domain] = [
        entry(domain, "first", {"target_vtherm_unique_id": UID}),
        entry(domain, "second", {"target_vtherm_unique_id": UID}, loaded=False),
    ]
    values = dict.fromkeys(diag.HYSTERESIS_FIELDS, None)
    values["is_active"] = True
    fixture.states[ENTITY] = state(ENTITY, {"specific_states": {"hysteresis": values}})

    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    first, second = result.data["plugins"]
    assert [plugin["config_entry_id"] for plugin in (first, second)] == ["first", "second"]
    assert result.data["status"] == "partial"
    assert result.data["coverage"]["discovery"]["status"] == "complete"
    assert second["facts"]["configured"]["value"] is True
    assert second["facts"]["loaded"]["value"] is False
    assert second["facts"]["selected"]["value"] is (None if algorithm is None else False)
    for plugin in (second,) if algorithm == "hysteresis" else (first, second):
        diagnostic = plugin["diagnostics"]
        assert diagnostic["status"] == "partial"
        assert diagnostic["producer"] == "unknown"
        assert diagnostic["values"]["is_active"] is True
        assert diagnostic["sources"][0]["source_entity_id"] == ENTITY
        assert diagnostic["sources"][0]["attribute_path"] == "specific_states.hysteresis"
        assert "shared_source_identity_unverified" in diagnostic["reasons"]
        assert diagnostic["field_facts"]["is_active"]["reason"] == "shared_source_identity_unverified"
        assert diagnostic["field_facts"]["is_active"]["scope"] == "state_source"
        assert plugin["facts"]["active"]["knowledge"] == "unknown"
    if algorithm == "hysteresis":
        assert first["facts"]["selected"]["value"] is True
        assert first["diagnostics"]["status"] == "complete"
        assert first["diagnostics"]["producer"] == domain
        assert first["facts"]["active"]["value"] is True


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("complete", "success"),
        ("empty", "success"),
        ("partial", "partial"),
        ("unavailable", "partial"),
        ("unresolved", "partial"),
        ("discovery", "partial"),
        ("error", "error"),
    ],
)
async def test_plugin_global_status_reflects_actual_gaps(fixture, scenario, expected):
    if scenario in ("complete", "partial", "unavailable"):
        domain = "vtherm_hysteresis"
        fixture.thermostat.entry_infos["proportional_function"] = "hysteresis"
        fixture.entries[domain] = [entry(domain, "plugin-entry", {"target_vtherm_unique_id": UID})]
        if scenario != "unavailable":
            values = dict.fromkeys(diag.HYSTERESIS_FIELDS, None)
            values["is_active"] = True
            if scenario == "partial":
                del values["hvac_mode"]
            fixture.states[ENTITY] = state(ENTITY, {"specific_states": {"hysteresis": values}})
    elif scenario == "unresolved":
        fixture.thermostat.entry_infos["proportional_function"] = "unknown_external"
    elif scenario in ("discovery", "error"):

        def entries(domain):
            if scenario == "error" or domain == "vtherm_smartpi":
                raise RuntimeError("discovery failed")
            return fixture.entries.get(domain, [])

        fixture.hass.config_entries.async_entries.side_effect = entries

    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.data["status"] == expected
    assert result.error is (expected == "error")
    if scenario == "complete":
        assert result.data["coverage"]["discovery"]["status"] == "complete"
        assert result.data["diagnostics_status"] == "complete"
        assert result.data["errors"] == []
    elif scenario in ("partial", "unavailable"):
        assert result.data["diagnostics_status"] == scenario
    elif scenario == "unresolved":
        assert result.data["unresolved_links"]
    elif scenario in ("discovery", "error"):
        assert result.data["coverage"]["discovery"]["status"] == "partial"
        assert result.data["errors"]


async def test_published_tools(fixture, monkeypatch):
    monkeypatch.setattr(llm, "_get_vtherm_entity_ids", lambda hass, context: [ENTITY])
    tools = llm.async_get_tools(fixture.hass, fixture.context, ha_llm.LLM_API_ASSIST)
    names = [tool.name for tool in tools.tools]
    assert len(names) == 12
    assert names.count("versatile_thermostat__get_logs") == 1
    assert names.count("versatile_thermostat__get_plugins") == 1
    assert all(tool.annotations.read_only for tool in tools.tools if tool.name.endswith(("__get_logs", "__get_plugins")))
    assert llm.async_get_tools(fixture.hass, fixture.context, "other") is None
    fixture.hass.data["climate"].get_entity.return_value = None
    assert len(llm.async_get_tools(fixture.hass, fixture.context, ha_llm.LLM_API_ASSIST).tools) == 10


@pytest.mark.parametrize("arguments", [
    {"unexpected": True}, {"min_level": "TRACE"}, {"start_time": 42},
    {"start_time": "2026-11-08T01:00:00Z", "end_time": "2026-11-08T00:00:00Z"},
])
async def test_invalid_parameters_and_period(fixture, arguments):
    handler = install_collector(fixture, [])
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture, **arguments)
    assert result.error
    assert result.data["errors"][0]["code"] in ("invalid_parameters", "invalid_period")
    handler.get_entries.assert_not_called()


@pytest.mark.parametrize("change,code", [
    ("foreign", "target_not_vtherm"), ("unexposed", "target_not_exposed"),
    ("orphan", "target_not_loaded"), ("absent_state", "target_not_loaded"),
])
async def test_inaccessible_target(fixture, change, code):
    install_collector(fixture, [])
    if change == "foreign":
        fixture.registry.async_get(ENTITY).platform = "other"
    elif change == "unexposed":
        fixture.exposed.return_value = False
    elif change == "orphan":
        fixture.hass.data["climate"].get_entity.return_value = None
    else:
        del fixture.states[ENTITY]
    for tool in (diag.GetVThermLogsTool, diag.GetVThermPluginsTool):
        result = await call(tool(llm.READ_ONLY_ANNOTATIONS), fixture)
        assert result.error and result.data["errors"][0]["code"] == code


async def test_unavailable_state_does_not_invalidate_loaded_target(fixture):
    fixture.states[ENTITY] = state(ENTITY, value="unavailable")
    install_collector(fixture, [])
    assert not (await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture)).error


async def test_local_diagnostic_failure_preserves_plugin(fixture, monkeypatch):
    fixture.entries["vtherm_smartpi"] = [entry("vtherm_smartpi", "smart", {"target_vtherm_unique_id": UID})]
    fixture.entries["vtherm_auto_fan_extended"] = [entry("vtherm_auto_fan_extended", "fan", {"target_vtherm_unique_id": UID})]
    original = diag._diagnostics
    def broken(hass, registry, domain, uid, entity_id, observed_at, config_entry_id=None):
        if domain == "vtherm_smartpi":
            raise RuntimeError("private failure")
        return original(hass, registry, domain, uid, entity_id, observed_at, config_entry_id)
    monkeypatch.setattr(diag, "_diagnostics", broken)
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert len(result.data["plugins"]) == 2
    assert result.data["plugins"][0]["diagnostics"]["status"] == "unavailable"
    assert result.data["errors"][0]["code"] == "plugin_read_failed"
    assert result.data["status"] == "partial"
    assert "private failure" not in json.dumps(result.data)


async def test_failure_global_and_legacy_are_not_claimed_applied(fixture):
    domain = "vtherm_heating_failure_detection"
    fixture.entries[domain] = [entry(domain, "global", {"enabled": False})]
    fixture.hass.data[domain] = {"entries": {"global": {"enabled": False}}}
    fixture.thermostat.entry_infos["use_heating_failure_detection_feature"] = True
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    plugin = result.data["plugins"][0]
    assert plugin["links"][0]["applies_to_target"]["knowledge"] == "unknown"
    assert plugin["facts"]["configuration_applied"]["knowledge"] == "unknown"
    assert result.data["unresolved_links"][0]["link_proof"] == "unproven"


async def test_unloaded_failure_global_is_not_claimed_applicable(fixture):
    domain = "vtherm_heating_failure_detection"
    fixture.entries[domain] = [entry(domain, "global", {"enabled": False}, loaded=False)]
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.data["plugins"] == []
    assert result.data["configured_plugin_count"] is None
    assert result.data["unresolved_links"][0]["link_proof"] == "unproven"


async def test_failure_targeted_values_override_global(fixture):
    domain = "vtherm_heating_failure_detection"
    global_config = {"enabled": False}
    targeted = {"vtherm_unique_id": UID, "enabled": True}
    fixture.entries[domain] = [entry(domain, "global", global_config), entry(domain, "target", targeted)]
    fixture.hass.data[domain] = {"entries": {"global": global_config, "target": targeted}}
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert [plugin["config_entry_id"] for plugin in result.data["plugins"]] == ["target"]


async def test_unresolved_smartpi_keeps_published_diagnostic(fixture):
    fixture.thermostat.entry_infos["proportional_function"] = "smartpi"
    fixture.sensor_ids[("sensor", "vtherm_smartpi", "smartpi_diag_" + UID)] = "sensor.smartpi"
    fixture.states["sensor.smartpi"] = state("sensor.smartpi", {"control": {"phase": "HEAT", "kp": 0}})
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    link = result.data["unresolved_links"][0]
    assert link["link_proof"] == "proven"
    assert link["diagnostics"]["values"]["control"] == {"phase": "HEAT", "kp": 0}
    assert link["diagnostics"]["producer"] == "unknown"
    assert result.data["configured_plugin_count"] is None


async def test_unresolved_complete_publication_remains_partial(fixture):
    fixture.thermostat.entry_infos["proportional_function"] = "smartpi"
    fixture.sensor_ids[("sensor", "vtherm_smartpi", "smartpi_diag_" + UID)] = "sensor.smartpi"
    values = {block: dict.fromkeys(fields, None) for block, fields in diag.SMARTPI_FIELDS.items()}
    fixture.states["sensor.smartpi"] = state("sensor.smartpi", values)
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    diagnostic = result.data["unresolved_links"][0]["diagnostics"]
    assert diagnostic["producer"] == "unknown"
    assert diagnostic["status"] == "partial"
    assert diagnostic["reasons"] == ["configured_identity_unresolved"]


@pytest.mark.parametrize("broken", [False, True])
async def test_unresolved_diagnostic_failure_marks_minimum_not_met(fixture, monkeypatch, broken):
    fixture.thermostat.entry_infos["proportional_function"] = "smartpi"
    fixture.sensor_ids[("sensor", "vtherm_smartpi", "smartpi_diag_" + UID)] = "sensor.smartpi"
    fixture.states["sensor.smartpi"] = state("sensor.smartpi", {"control": {"kp": object()}})
    if broken:
        def fail(*args):
            raise RuntimeError("private failure")
        monkeypatch.setattr(diag, "_diagnostics", fail)
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert result.data["unresolved_links"][0]["diagnostics"]["producer"] == "unknown"
    assert result.data["state_minimum_status"] == "not_met"


async def test_sensor_must_belong_to_configured_plugin(fixture):
    fixture.entries["vtherm_smartpi"] = [entry("vtherm_smartpi", "other-entry", {"target_vtherm_unique_id": UID})]
    fixture.sensor_ids[("sensor", "vtherm_smartpi", "smartpi_diag_" + UID)] = "sensor.smartpi"
    fixture.states["sensor.smartpi"] = state("sensor.smartpi", {"control": {"phase": "HEAT"}})
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    diagnostic = result.data["plugins"][0]["diagnostics"]
    assert diagnostic["values"] == {}
    assert diagnostic["producer"] == "unknown"
    assert diagnostic["reasons"] == ["source_identity_unverified"]


async def test_invalid_inhibition_source_is_reported(fixture):
    domain = "vtherm_inhibition"
    fixture.entries[domain] = [entry(domain, "plugin-entry", {"vtherm_unique_id": UID})]
    fixture.sensor_ids[("binary_sensor", domain, UID + "_inhibition")] = "binary_sensor.inhibition"
    fixture.states["binary_sensor.inhibition"] = state("binary_sensor.inhibition", {
        "sources": {"sensor.window": {"state": "on", "contribution": object()}}
    })
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    plugin = result.data["plugins"][0]
    assert plugin["diagnostics"]["values"]["sources"] == {"sensor.window": {"state": "on"}}
    assert "invalid_fields:sources.sensor.window.contribution" in plugin["diagnostics"]["reasons"]
    assert plugin["state_minimum_status"] == result.data["state_minimum_status"] == "not_met"


async def test_bad_entry_does_not_hide_other_entries(fixture):
    domain = "vtherm_smartpi"
    fixture.thermostat.entry_infos["proportional_function"] = "smartpi"
    fixture.entries[domain] = [entry(domain, "broken", None), entry(domain, "valid", {"target_vtherm_unique_id": UID})]
    result = await call(diag.GetVThermPluginsTool(llm.READ_ONLY_ANNOTATIONS), fixture)
    assert [plugin["config_entry_id"] for plugin in result.data["plugins"]] == ["valid"]
    assert result.data["coverage"]["discovery"]["status"] == "partial"
    assert result.data["errors"][0]["field"] == "config_entry"


def test_naive_source_date_preserved_without_invented_timezone():
    value = diag._date_value(datetime(2026, 11, 8, 1, 2, 3))
    assert value == {"raw": "2026-11-08T01:02:03", "normalized": None,
                     "knowledge": "unknown", "reason": "source_timezone_unknown"}


def test_source_publication_times_are_utc_and_preserve_raw(fixture):
    fixture.states[ENTITY].last_updated = datetime(2026, 11, 8, 2, tzinfo=timezone(timedelta(hours=2)))
    fixture.states[ENTITY].last_changed = datetime(2026, 11, 8, 1)
    _, source = diag._source(fixture.hass, ENTITY, None, NOW)
    assert source["state_last_updated"] == "2026-11-08T00:00:00Z"
    assert source["state_last_updated_raw"] == "2026-11-08T02:00:00+02:00"
    assert source["state_last_updated_knowledge"] == "known"
    assert source["state_last_changed"] is None
    assert source["state_last_changed_raw"] == "2026-11-08T01:00:00"
    assert source["state_last_changed_reason"] == "source_timezone_unknown"


async def test_real_collector_synthetic_one_hour(fixture):
    from vtherm_api.log_collector import VThermLogHandler

    handler = VThermLogHandler()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)
    for index in range(3600):
        message = f"Internal Name - synthetic {index}" if index % 2 else f"synthetic unattributed {index}"
        record = logging.LogRecord("synthetic.test", logging.INFO, "", 1, message, (), None)
        record.created = (start + timedelta(seconds=index)).timestamp()
        handler.emit(record)
    other = logging.LogRecord("synthetic.test", logging.INFO, "", 1, "Other - excluded", (), None)
    other.created = end.timestamp()
    handler.emit(other)
    fixture.hass.data[diag.DOMAIN]["log_handler"] = handler
    result = await call(diag.GetVThermLogsTool(llm.READ_ONLY_ANNOTATIONS), fixture,
                        start_time=start.isoformat(), end_time=end.isoformat(), min_level="INFO")
    assert result.data["selected_count"] == 3600
    assert result.data["returned_count"] == 3600
    assert result.data["omitted_count"] == 0
    assert result.data["entries"][0]["message"] == "synthetic unattributed 0"
    size = len(json.dumps(result.data, ensure_ascii=False).encode("utf-8"))
    print(f"AC-011 synthetic: 3600/hour, 1800 unattributed, 0 omitted, {size} bytes, direct ToolResult")
