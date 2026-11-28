# Plugin API (`vtherm_api`)

Contracts between VT and its plugins. The `vtherm_api` package (separate repository, published on PyPI) owns the contracts; VT implements the core side. Read this before touching a contract, a hook call site, or extracting a feature (`workflows/plugin-extraction.md`).

## Purpose and rule

- VT favors moving features out of the core into plugins. The core keeps only generic contracts and hooks: no code path specific to one plugin.
- Plugins use only the public runtime surface (protocols below). They never import VT modules (`custom_components/versatile_thermostat/...`) and never touch private attributes (`_underlyings`, `_managers`, `_entry_infos`...). A missing accessor is a contract gap: add it to `vtherm_api` first.
- The core never imports a plugin. It discovers plugins only through the registries of `VThermAPI` and detects optional capabilities with `getattr`/`hasattr` on the registered object.
- Every call into plugin code is guarded in the core: exception logged, never propagated, the core value or command wins.

## Dependency and versioning

- VT `manifest.json` `requirements` lists `vtherm_api>=<minimum>` (the minimum version in `manifest.json`); `requirements_dev.txt` pins the same minimum. Raise it in both when the core starts to need a newer contract.
- `custom_components/versatile_thermostat/vtherm_central_api.py::VersatileThermostatAPI` extends `VThermAPI` (central config, central power and boiler managers). `hass.data[DOMAIN][VTHERM_API_NAME]` holds one instance; the class that calls `get_vtherm_api(hass)` first builds it, so VT must be set up before plugins (plugins declare `dependencies: ["versatile_thermostat"]`).
- The API instance carries the registries. VT drops it with the last config entry only when no feature manager or algorithm is registered (`VersatileThermostatAPI.remove_entry`); plugins re-register when VT rebuilds it.
- Plugin manifests: all example plugins declare `dependencies: ["versatile_thermostat"]`. One lists `vtherm_api>=<minimum>` in `requirements`; two rely on the version VT brings. A plugin needing a recent contract must declare its own minimum.
- The package version is `__version__` in its `__init__.py`; releases are tags of that version, published to PyPI by a workflow. Versions are immutable.
- Compatibility rules (package tests and docs): plugin-implemented protocols stay backward compatible (a plugin written against an older version must keep importing and registering); new capabilities are separate optional protocols detected with `hasattr`/`isinstance`, never new required members of an existing plugin-side protocol. The core-provided runtime protocol may grow in a minor version (new members the core implements). Enum values (`ValveCommandCause`, `PowerCommandKind`, `EventType`) may grow in a minor version: plugin code must ignore unknown values.
- The core calls an optional capability only when the plugin object has it AND (for feature managers) `is_configured` is True.
- The local checkout of the package can lag behind the released tag. Check the pinned version before assuming a contract exists.

## Registry facade: `VThermAPI` (`vtherm_api.py`)

| Call | Who | Meaning |
|------|-----|---------|
| `VThermAPI.get_vtherm_api(hass=None)` | plugin, core | singleton accessor (None until a hass is known) |
| `register_prop_algorithm(factory)` / `unregister_prop_algorithm(name)` / `get_prop_algorithm(name)` / `list_prop_algorithms()` | plugin registers, core reads | proportional algorithm factories by name |
| `register_feature_manager(factory)` / `unregister_feature_manager(name)` / `get_feature_manager(name)` / `list_feature_managers()` / `get_feature_manager_factories()` | plugin registers, core iterates | feature manager factories, sorted by name |
| `set_inhibition(entity_id, stop_underlyings)` / `unset_inhibition(entity_id)` / `is_inhibition_started(entity_id)` | plugin | inhibition facade |
| `register_ui_plugin(...)` / `unregister_ui_plugin(id)` / `get_ui_plugins()` | plugin registers | dashboard UI plugin declarations |
| `link_to_vtherm(vtherm, plugin_entity_id)` / `register_manager(manager)` | plugin | older path for plugin climate entities (see PluginClimate) |
| `now`, `hass` | both | clock (overridable in tests) and hass |

- Registration happens in the plugin's `async_setup`/`async_setup_entry`, idempotently (check `get_*(name)` first), and unregistration in `async_unload_entry`.
- Consumers in VT: `base_thermostat.py::BaseThermostat._load_external_feature_managers` (feature managers), `thermostat_prop.py::ThermostatProp._init_algorithm_handler` (algorithms), `inhibition_manager.py` and `base_thermostat.py::async_set_inhibition` (facade targets).

## Contracts

### Proportional algorithm (`interfaces.py`)

- Plugin implements `InterfacePropAlgorithmFactory` (`name`, `create(runtime)`) and `InterfacePropAlgorithmHandler` (`init_algorithm`, `async_added_to_hass`, `async_startup`, `remove`, `control_heating`, `on_state_changed`, `on_scheduler_ready`, `should_publish_intermediate`).
- Selection: the thermostat's proportional function name is looked up in the registry (TPI is built in and never looked up). `ThermostatProp._init_algorithm_handler` calls `factory.create(self)` then `init_algorithm()`. If the factory is not registered yet it retries in `ThermostatProp.async_startup` (after Home Assistant started) and raises `ValueError` if still missing.
- Lifecycle calls: `async_added_to_hass` and `async_startup` from the thermostat's same-named methods; `on_scheduler_ready(scheduler)` when the cycle scheduler is bound (`ThermostatProp._bind_scheduler`); `control_heating(timestamp, force)` each control cycle; `on_state_changed(changed)` from `ThermostatProp.update_states` on every update; `remove()` from `remove_thermostat`; `should_publish_intermediate()` read in `BaseThermostat.async_control_heating`.
- The handler gets the runtime view and drives the thermostat through `cycle_scheduler.start_cycle`, `async_underlying_entity_turn_off`, `async_control_heating`.

### Feature manager (`interfaces.py`)

- Plugin implements `InterfaceFeatureManagerFactory` (`name`, `supports(runtime)`, `create(runtime)`) and `InterfaceFeatureManager` (`post_init`, `start_listening`, `stop_listening`, `refresh_state`, `restore_state`, `add_listener`, `is_configured`, `is_detected`, `name`, `hass`). Optional by convention, not in the protocol: `add_custom_attributes(attrs)` (the core calls it with `getattr`), used to publish attributes.
- Creation: `BaseThermostat._load_external_feature_managers` runs at the end of `post_init` and again at the start of `async_startup` (plugin loaded after the thermostat). Per factory: `supports(thermostat)`, `create`, `post_init(entry_infos)`, then registration in `_managers`, `_external_managers` and a stable-name index.
- Calls on every manager (internal and external): `start_listening` (startup), `restore_state(old_state)` (restore), `stop_listening` (unload), `refresh_state()` (startup and every control cycle, external managers refreshed after the regulation and before state publication; not during the safety early exit of over_climate, unverified), `add_custom_attributes` (attribute build). The bool returned by `refresh_state` is ignored for external managers.
- Lookup by stable name: runtime `get_feature_manager(name)` returns the manager built by the factory of that name. The core reads it for generic purposes: `prop_handler_tpi.py` reads `is_detected` of the manager named `heating_failure_detection`; `BaseThermostat.auto_start_stop_manager` resolves the manager named `auto_start_stop` (constant `CONF_AUTO_START_STOP_STABLE_NAME` in `const.py`), the core manager becomes inert when it exists.
- Time-based state must use the runtime `now` clock, never a wall clock.
- Optional capability protocols (a manager implements only the ones it needs):

| Protocol (module) | Method | Called by the core | Contract |
|------------------|--------|--------------------|----------|
| `InterfaceSetpointModifier` (`setpoint_modifier.py`) | `adjust_regulated_temperature(desired, regulation_step, command_cause) -> float \| None` | `thermostat_climate.py::ThermostatOverClimate._adjust_regulated_temperature` (also `_before_underlying_hvac_mode_change`) | sync, chained in registration order, after self-regulation and before offset, rounding and delta filter; `None` or invalid keeps the value |
| `InterfaceUnderlyingHvacModeHook` (`underlying_hooks.py`) | `async_before_underlying_hvac_mode(climate_entity_id, hvac_mode, current_hvac_mode, command_cause)` | `underlyings.py::UnderlyingClimate` via `BaseThermostat.async_before_underlying_hvac_mode` | notification before `climate.set_hvac_mode`, only if the command is really sent |
| `InterfaceValveCommandHook` | `async_after_valve_command(command: ValveCommand)` | `underlyings.py::UnderlyingValveRegulation` via `BaseThermostat.async_after_valve_command` | notification after opening/closing degrees were sent |
| `InterfaceUnderlyingPowerHook` | `async_on_underlying_power(command: UnderlyingPowerCommand)` | `cycle_scheduler.py::CycleScheduler._fire_underlying_power` via `BaseThermostat.async_on_underlying_power` | per underlying at cycle start, valve update, stop; use the command timestamps, not the reception time |
| `InterfaceCalibrationOffsetModifier` (`calibration_modifier.py`) | `adjust_calibration_offset(request) -> float \| None` | no consumer in the core | chained, sync, before the offset is compared and written |
| `InterfaceValveWriteHook` (`valve_write.py`) | `async_before_valve_write(request) -> ValveWriteDecision \| None` | no consumer in the core | can change or take over the valve write; `ValveCommandCause.RECALIBRATION` and `ValveCommand.written_by_plugin` also have no producer yet |

- Async hooks are awaited one manager after the other by `BaseThermostat._async_call_external_hook` under `asyncio.timeout(UNDERLYING_HOOK_TIMEOUT_SEC)` (10 s, in `vtherm_api/const.py`); a timeout or exception is logged and the core command still goes out. Hooks must return quickly and start long work in a task. They are skipped while the inhibition gate blocks the command.

### Cycle scheduler and command receipt (`interfaces.py`, `command_receipt.py`)

- `InterfaceCycleScheduler` is the core-provided scheduler given to the handler in `on_scheduler_ready`: `is_cycle_running`, `register_cycle_start_callback`, `register_cycle_end_callback`, `start_cycle(hvac_mode, on_percent, force)`, `cancel_cycle()`. Implemented by `cycle_scheduler.py::CycleScheduler`.
- `InterfaceCommandReceiptScheduler` extends it (optional): `is_valve_mode`, `register_command_receipt_callback(cb) -> remove_fn`, and `start_cycle(..., *, request_id=None)`. The scheduler echoes the opaque `request_id` in an `AppliedCommandReceipt` (`kind`, requested and applied on-percent, on/off times, cycle timestamps, `is_repeat`, `alterations`) for each command it really applies. A plugin detects it with `isinstance(scheduler, InterfaceCommandReceiptScheduler)`. Receipts describe scheduler commands, not measured power; cancellation, OFF and shedding are not receipts.

### Inhibition (`inhibition.py`, `VThermAPI`)

- A plugin owns detection and policy and calls `await api.set_inhibition(entity_id, stop_underlyings)` / `unset_inhibition(entity_id)`; `is_inhibition_started` tells whether the thermostat restored its state at startup (before that both raise `InhibitionNotStartedError`).
- The facade finds the climate entity and calls `async_set_inhibition` / `async_unset_inhibition` on it (`base_thermostat.py`), delegated to `inhibition_manager.py::InhibitionManager`, which owns the state, the command gate on all underlying commands and the effective HVAC resolution. Design: `documentation/tech-docs/inhibition_manager.md` (historical record).

### Plugin climate (`plugin_climate.py`, `interfaces.py::InterfaceThermostat`)

- `PluginClimate` is a helper for a plugin that is itself a climate entity (device model = VT domain) following one VTherm. `link_to_vtherm(vtherm)` subscribes it to every `EventType` on the bus and filters by the linked entity id; subclasses override `handle_<event>`; `call_linked_vtherm_action(name, data)` calls a `climate` service on the linked entity.
- Event source in VT: `base_thermostat.py::BaseThermostat.send_event` -> `const.py::send_vtherm_event` (payload gets `entity_id`, `name`, `state_attributes`). The event types and their values are the `EventType` enum in `vtherm_api/const.py` (imported by VT `const.py`). VT does not import `PluginClimate`.

### Logging (`log_collector.py`) and constants (`const.py`)

- Every VT module and plugin gets its logger from `get_vtherm_logger(__name__)`; its ring-buffer collector feeds log export. `write_event_log(logger, vtherm, message)` writes the highlighted event line. `async_export_logs`, `async_register_log_download_endpoint` and `VThermLogHandler` are used by `__init__.py`.
- `const.py`: `DOMAIN`, `VTHERM_API_NAME`, `EventType`, `get_tz`, `NowClass` (test clock), `UNDERLYING_HOOK_TIMEOUT_SEC`. `commons_type.py::ConfigData` is the merged-configuration type.

### UI plugin registry (`ui_plugin.py`)

- Passive registry of dashboard declarations (`UiPlugin`: id, JS module URL, dashboard version constraint, `requires`, `load_after`, `load_before`); the dashboard interprets them. No consumer in VT python (the dashboard is a separate project; its use of the registry is unverified).

## Runtime surface VT exposes (`InterfaceThermostatRuntime`)

Implemented by `BaseThermostat` and its subclasses; the object handed to factories (`supports`/`create`). Grouped:

- Identity and config: `hass`, `entity_id`, `name`, `unique_id`, `entry_infos` (merged config, read-only), `has_prop`, `has_valve_regulation`.
- State: `requested_hvac_mode`, `vtherm_hvac_mode`, `vtherm_hvac_modes` (core mode objects, compare as strings), `hvac_action`, `hvac_off_reason`, `current_temperature`, `current_outdoor_temperature`, `target_temperature`, `regulated_target_temperature`, `last_temperature_slope`, `on_percent`, `is_device_active`, `is_overpowering_detected`, `now` (shared cycle clock).
- Underlyings (typed views only): `valve_diagnostics` (`ValveDiagnosticState`), `underlying_fan_modes`, `cycle_min`, `minimal_activation_delay`, `minimal_deactivation_delay`, `prop_algorithm`, `cycle_scheduler`.
- Actions: `async_set_underlying_fan_mode`, `async_underlying_entity_turn_off`, `async_control_heating`, `async_request_state_refresh` (call on transitions, not per cycle), `update_custom_attributes`, `async_write_ha_state`, `send_event(event_type, data)`, `get_feature_manager(name)`.
- `InterfaceTemperatureTimestampRuntime` (optional extension): `last_temperature_measure`, `last_ext_temperature_measure`; freshness clocks, not observation times. Judging sensor health stays VT's job.
- The core-side inhibition entry points (`async_set_inhibition`, `async_unset_inhibition`, `is_inhibition_started`) are not part of the runtime protocol; the facade reaches them on the climate entity.
- Adding a member: add it to the protocol in `vtherm_api` (minor release), implement it in `BaseThermostat`, raise the minimum in `manifest.json` and `requirements_dev.txt`.

## Plugin kinds that exist

| Kind | Contract used | Registration | Examples (generic) |
|------|---------------|--------------|--------------------|
| Proportional algorithm | `InterfacePropAlgorithmFactory/Handler`, runtime, `InterfaceCycleScheduler`, optional receipts | `register_prop_algorithm` | an advanced PI controller with a learned room model; an adaptive TPI; an on/off hysteresis |
| Feature manager | `InterfaceFeatureManagerFactory/Manager` plus optional hooks and modifiers | `register_feature_manager` | features extracted from the core (auto-start/stop), device-quirk workarounds, diagnostics |
| Inhibition provider | `set_inhibition` facade | calls on `VThermAPI` | a plugin that suspends control of the underlyings |
| Plugin climate | `PluginClimate`, `link_to_vtherm` | climate entity of the plugin | a climate that replicates or mirrors a VTherm |
| Dashboard UI plugin | `register_ui_plugin` | `VThermAPI` | dashboard cards and schedulers |

All example plugins are separate integrations with a config flow, a `dependencies: ["versatile_thermostat"]` manifest, a `factory.py` (factory class), a `handler.py` (algorithm) and a per-VTherm configuration entry keyed by the VTherm `unique_id` beside an optional global entry.

## How to externalize a feature

1. Define the boundary: what the feature reads (runtime members), what it writes (actions, events, attributes), what the core must still do without it.
2. Contract first, in `vtherm_api`: reuse an existing protocol; otherwise add the smallest generic one (optional protocol for an action hook, new runtime member for a missing read). Document it in the package docs, test it with plugin-style doubles and a backward-compatibility test; release a minor version.
3. Core hook, generic: call it only on configured managers, guard exceptions and timeouts, never name the plugin. Prefer a stable manager name looked up through `get_feature_manager` over a feature-specific field. Raise the `vtherm_api` minimum in `manifest.json` and `requirements_dev.txt`.
4. Plugin package: factory (`name`, `supports`, `create`), manager, config flow (global plus per-VTherm entries), entities, translations; idempotent registration in setup and unregistration in unload; reload only the affected VTherm on option change. Config resolution during transition: plugin value first, then legacy core keys read through `entry_infos`.
5. Tests on both sides: package contract tests; core tests with a fake factory/manager (`tests/test_external_feature_manager.py`, `tests/test_underlying_hooks.py`, `tests/test_inhibition.py` are the models); plugin tests against the public protocols only. Core and plugin suites must pass independently.
6. Transition, then removal: while the core feature stays, an external manager of the same stable name takes precedence and the core copy goes inert or skips its refresh (`BaseThermostat.async_control_heating` skips the core heating-failure refresh when an external manager has that name). Removal of the core code, constants, config steps, translations and tests happens in a major version, keeping persisted legacy keys readable for the plugin fallback.
7. Docs in every language point to the plugin; release notes record the move.

## Current externalization work

- Auto-start/stop: delegated. The core manager stays as a fallback and becomes inert when an external manager named `auto_start_stop` is attached; `__init__.py` migrates existing entries to the plugin's data. The runtime members `vtherm_hvac_modes` and `async_request_state_refresh` exist for it.
- Heating-failure detection: a plugin exists, not present in this repository (unverified: factory, manager, config flow, binary sensor, import of legacy settings). The core manager is instantiated and refreshed per cycle unless an external manager named `heating_failure_detection` exists; the TPI handler reads failure state only through `get_feature_manager`, so it sees the plugin manager and never the core one. Removal of the core manager, config step, sensor and strings waits for a major version.
- Auto-fan: the generic mechanism (factory registry, per-cycle `refresh_state`, fan runtime accessors) is in place and an auto-fan plugin exists outside this repository (unverified) scoped to `over_climate` thermostats. Core auto-fan code remains in `thermostat_climate.py` (legacy), and its deprecated service refuses to run once a plugin entry owns the thermostat; core removal is not done.
- Contracts published but not consumed by the core: calibration offset modifier, valve write hook, recalibration cause, UI plugin registry.
- Candidate list and order: `status.md`.
