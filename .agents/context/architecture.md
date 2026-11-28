# Architecture: verified code map

Paths without a folder are in `custom_components/versatile_thermostat/`. `path::Symbol` points at a class, method or constant. Runtime sequences: `runtime-flow.md`.

## Entity and class hierarchy

```
Entity
  VersatileThermostatBaseEntity (base_entity.py)  -> sensors, binary sensors, switches, auto start/stop select
ClimateEntity + RestoreEntity
  BaseThermostat (base_thermostat.py, Generic[T] = underlying class)
    ThermostatOverClimate (thermostat_climate.py)            T = UnderlyingClimate
    ThermostatProp (thermostat_prop.py)                      proportional base, owns an algorithm handler
      ThermostatOverSwitch (thermostat_switch.py)            T = UnderlyingSwitch
      ThermostatOverValve (thermostat_valve.py)              T = UnderlyingValve (+ ValveCommandMixin)
      ThermostatOverClimateValve (thermostat_climate_valve.py)  MRO: ValveCommandMixin, ThermostatProp, ThermostatOverClimate
BaseFeatureManager (base_manager.py) -> feature_*_manager.py
```

| Class | Role |
|-------|------|
| `base_thermostat.py::BaseThermostat` | Everything shared: requested/current state, presets, managers, sensor listeners, `update_states`, `async_control_heating`, services, attributes, restore, events |
| `thermostat_prop.py::ThermostatProp` | Holds `_algo_handler` (`TPIHandler` or a plugin handler built by `_init_algorithm_handler`), `on_percent` (safety override, `max_on_percent` clamp), `recalculate`, `_bind_scheduler` |
| `thermostat_switch.py::ThermostatOverSwitch` | Builds one `UnderlyingSwitch` per entity and one `CycleScheduler`; periodic control timer; energy counter |
| `thermostat_valve.py::ThermostatOverValve` | Builds `UnderlyingValve` list and scheduler; valve opening filters; SLEEP mode (valve fully open); deferred recalculation |
| `thermostat_climate.py::ThermostatOverClimate` | Setpoint regulation (`_send_regulated_temperature`, `pi_algorithm.py::PITemperatureRegulator`), fan/swing, tracking of device-side changes (`underlying_changed`), device temperature sync, core auto start/stop |
| `thermostat_climate_valve.py::ThermostatOverClimateValve` | Climate + proportional valve regulation: `_underlyings` are the climates, `_underlyings_valve_regulation` (`UnderlyingValveRegulation`) are what the scheduler drives |
| `valve_command.py::ValveCommandMixin` | `apply_valve_command_percent`: percent rounding, delta-percent and period filters, shared by both valve thermostats |
| `base_entity.py::VersatileThermostatBaseEntity` | Finds its climate by `device_info` (retry each second), listens to the climate state, `my_climate_is_initialized` hook |
| `base_manager.py::BaseFeatureManager` | Contract: `post_init`, `start_listening`, `stop_listening`, `refresh_state`, `restore_state`, `add_listener`, `is_configured`, `is_detected` |

`vtherm_type` and `is_over_*` properties are overridden per subclass. Thermostat type to class is chosen in `climate.py::async_setup_entry` (valve regulation mode selects `ThermostatOverClimateValve`). Entity `unique_id` is the config entry id.

## Feature managers (`feature_*_manager.py`, plus `inhibition_manager.py`)

Created in `BaseThermostat.__init__` and registered with `register_manager` (list `_managers`), except auto start/stop (created in `ThermostatOverClimate.post_init`) and the two central ones. Lifecycle calls: `post_init(entry_infos)` in `BaseThermostat.post_init`; `start_listening` in `async_startup`; `restore_state` in `get_my_previous_state`; `refresh_state` in `init_underlyings_completed` and on events; `stop_listening` in `remove_thermostat`; `add_custom_attributes` (optional, read by `getattr`) in `update_custom_attributes`.

| File | Class | Role |
|------|-------|------|
| `feature_window_manager.py` | `FeatureWindowManager` | Window sensor and auto detection (`open_window_algorithm.py`), delay timers, bypass, action turn off / fan only / eco / frost |
| `feature_motion_manager.py` | `FeatureMotionManager` | Motion sensor with on/off delays; supplies the preset used by the activity preset |
| `feature_presence_manager.py` | `FeaturePresenceManager` | Presence sensor; absence selects the `*_away` preset temperatures |
| `feature_power_manager.py` | `FeaturePowerManager` | Per-VTherm overpowering state, power reservation with the central power manager, `set_overpowering` |
| `feature_safety_manager.py` | `FeatureSafetyManager` | Stale temperature detection (delay, min on percent, default on percent); safety state `set_safety` on proportional thermostats |
| `feature_lock_manager.py` | `FeatureLockManager` | Lock by code for users and/or automations; `check_is_locked` used by `BaseThermostat.check_lock` |
| `feature_timed_preset_manager.py` | `FeatureTimedPresetManager` | Timed preset and manual override with expiry timer, resume of the interrupted preset |
| `feature_heating_failure_detection_manager.py` | `FeatureHeatingFailureDetectionManager` | Heating/cooling failure from on percent vs temperature trend; stuck valve analysis |
| `feature_repair_incorrect_state_manager.py` | `FeatureRepairIncorrectStateManager` | `check_and_repair` each cycle: re-sends the desired command when an underlying differs; bounded attempts |
| `feature_humidity_manager.py` | `FeatureHumidityManager` | Optional humidity sensor resolution (`humidity.py`), exposed as `current_humidity` |
| `feature_auto_start_stop_manager.py` | `FeatureAutoStartStopManager` | Auto stop/start of a climate (`auto_start_stop_algorithm.py`); `set_inert` when a plugin owns the feature |
| `feature_central_power_manager.py` | `FeatureCentralPowerManager` | Central power/max power sensors, shedding (`calculate_shedding`), sorted by temperature gap |
| `feature_central_boiler_manager.py` | `FeatureCentralBoilerManager` | Counts active VTherms/power, activates/deactivates a boiler by service call, keep-alive |
| `inhibition_manager.py` | `InhibitionManager` (not a feature manager) | Command gate towards underlyings for plugin inhibition; owned as `BaseThermostat._inhibition` |

Central managers are owned by `vtherm_central_api.py::VersatileThermostatAPI` (not by a thermostat). External (plugin) managers are built in `BaseThermostat._load_external_feature_managers` from the `vtherm_api` factory registry; they go into `_managers` and `_external_managers`. Lookups by stable name use `get_feature_manager`: it returns the plugin manager built by the factory of that name, or a core manager whose `name` equals the key; core managers are named after the VTherm, so in practice only plugin managers match. `CONF_AUTO_START_STOP_STABLE_NAME` and `"heating_failure_detection"` have a core legacy manager that is refreshed directly (per cycle for heating failure), never found by that lookup; the TPI handler therefore sees heating failure only through the plugin.

## Underlyings (`underlyings.py`, `underlying_state_manager.py`)

| Class | Role |
|-------|------|
| `UnderlyingEntity` | Base: owns an `UnderlyingStateManager` (state listener, initialized flag), `hass_services_async_call` (single service-call wrapper, honours the inhibition gate), `check_overpowering`, `send_value_to_number`, `check_and_repair` |
| `UnderlyingSwitch` | on/off command (inverse, virtual `command/arg:value` strings via `build_command`), keep-alive (`keep_alive.py`), `turn_on` checks overpowering, calls `hass.services.async_call` directly and tests `is_command_blocked` itself |
| `UnderlyingClimate` | `set_hvac_mode` (power check, before-mode hook, delayed setpoint resend), `set_temperature` (clamp to device step/range), fan/swing/humidity, `_underlying_changed` filters real changes then calls `thermostat.underlying_changed` |
| `UnderlyingValve` | Number entity opening: `set_valve_open_percent`, `_get_controlled_percent` (`opening_degree_algorithm.py`), `send_percent_open` |
| `UnderlyingValveRegulation` | Valve of a TRV driven through opening/closing degree numbers beside its climate; notifies the after-valve-command hook; seeds unknown degrees at startup |

`UnderlyingEntityType` (switch, climate, valve, valve_regulation) is what `CycleScheduler` uses to detect valve mode. `UnderlyingStateManager` caches states, calls `on_change`, reports `is_all_states_initialized`.

## Cycle scheduler and proportional algorithms

- `cycle_scheduler.py::CycleScheduler`: one per proportional thermostat. `start_cycle(hvac_mode, on_percent, force)` converts percent to seconds with `calculate_cycle_times` (min on/off delays), then `_start_cycle_switch` (staggered ticks, `cycle_tick_logic.py`, `_tick`) or `_start_cycle_valve` (direct opening, window kept for callbacks). Fires cycle start/end callbacks, underlying power hooks and command receipts. `_on_master_cycle_end` restarts the cycle with the stored request.
- `prop_handler_tpi.py::TPIHandler`: algorithm handler for TPI: builds `TpiAlgorithm` and `AutoTpiManager`, `control_heating` (feeds Auto TPI, computes times, calls `start_cycle`), TPI services, config entry write-back.
- `prop_algo_tpi.py::TpiAlgorithm`: pure calculation `coef_int * dT + coef_ext * dText`, clamps, threshold hysteresis, `update_realized_power`; `on_percent` is None when no temperature.
- `auto_tpi_manager.py::AutoTpiManager`: learns coefficients from cycles (`on_cycle_started`, `on_cycle_completed`), persists in a `Store`, writes coefficients to the config entry without reload.
- `tpi_history.py`, `tpi_identification.py`, `tpi_regulation.py`, `recorder_export.py`: read-only recorder reads and thermal identification, used only by `llm/`.
- `pi_algorithm.py::PITemperatureRegulator` and `ema.py::ExponentialMovingAverage`: setpoint self-regulation of over_climate; EMA of room temperature (slope).
- Plugin algorithms: `ThermostatProp._init_algorithm_handler` asks the `vtherm_api` registry; the handler contract is `InterfacePropAlgorithmHandler`.

## Auto TPI lifecycle

- Built by `TPIHandler` (`prop_handler_tpi.py`) as `AutoTpiManager`; the handler registers its `on_cycle_started` / `on_cycle_completed` on the `CycleScheduler` (`register_cycle_start_callback`, `register_cycle_end_callback`).
- Load: `TPIHandler.async_added_to_hass` calls `AutoTpiManager.async_load_data` (persistence is a HA `Store`, saved by `async_save_data`, also on shutdown); learned coefficients are applied only while `learning_active`. Disabling the feature in the configuration stops learning at startup.
- Per control cycle: `TPIHandler.control_heating` feeds `AutoTpiManager.update` (temperatures, mode, overpowering, central boiler off, `is_heating_failure`), then `calculate`; while learning, the returned coefficients go to `TpiAlgorithm.update_parameters`.
- Learning runs at the end of a scheduler cycle: `on_cycle_completed` calls `_perform_learning` when `_should_learn`, else `_learn_kext_continuous` when the continuous Kext option (`CONF_AUTO_TPI_CONTINUOUS_KEXT`) is on and `_should_learn_continuous_kext`.
- Written coefficients: `async_update_learning_data` writes them to the config entry without reload (`skip_reload_on_config_update`) and calls the handler callback `_apply_written_coefficients` so the regulation uses them at once.
- Repair issue: `_report_previous_learning` (called by `async_load_data`) raises a persistent repair issue (translation key `auto_tpi_relearn`) when the stored learning state has an incompatible format; `start_learning` with reset removes it.
- Services: `set_auto_tpi_mode` (`TPIHandler.service_set_auto_tpi_mode` -> `start_learning` / `stop_learning`), `set_tpi_parameters`; diagnostics sensor with the `_auto_tpi_learning` unique id suffix.

## State objects

- `state_manager.py::StateManager`: `requested_state` (what the user/automation asked) and `current_state` (effective). `calculate_current_state` runs `calculate_current_hvac_mode`, `calculate_current_preset`, `calculate_current_target_temperature` in priority order (see `runtime-flow.md`).
- `vtherm_state.py::VThermState`: hvac mode, target temperature, preset, per-field changed flags (`force_changed`, `reset_changed`), `to_dict`/`from_dict` (persisted as attributes `current_state`, `requested_state`).
- `vtherm_hvac_mode.py::VThermHvacMode`: value object including `sleep`, with `from_ha_hvac_mode`, `to_ha_hvac_mode`, `to_legacy_ha_hvac_mode`; constants `VThermHvacMode_OFF` etc.
- `vtherm_preset.py`: `VThermPreset` (none, frost, eco, comfort, boost, safety, power, activity), `VThermPresetWithAC`, `...WithAway`, `...WithACAway`, `HIDDEN_PRESETS` (power, safety).

## Central config, API, platforms

- `vtherm_central_api.py::VersatileThermostatAPI(VThermAPI)`: singleton in `hass.data[DOMAIN]`; `find_central_configuration`, registry of preset `Number` entities, central mode select, `init_vtherm_links`, `notify_central_mode_change`, `skip_reload_on_config_update`, global YAML params (`CONF_AUTO_REGULATION_EXPERT`, `CONF_SHORT_EMA_PARAMS`, `CONF_SAFETY_MODE`, `CONF_MAX_ON_PERCENT`).
- `__init__.py`: `async_setup`, `async_setup_entry`, `update_listener`, `async_unload_entry`, `async_migrate_entry`, `reload_all_vtherm`, auto start/stop delegation migration.
- `PLATFORMS` (`const.py`), in order: climate, sensor, number, binary_sensor, switch, select. Each `async_setup_entry` branches on `CONF_THERMOSTAT_TYPE` (central config entry creates only central entities).
- `climate.py`: builds the thermostat, registers entity services. `sensor.py`: per-VTherm diagnostics sensors (last temps, slope, EMA, energy, mean power, on percent/time, valve percent, regulated temp, Auto TPI) and central boiler sensors. `binary_sensor.py`: safety, window, bypass, motion, presence, overpowering, heating failure, central boiler. `number.py`: `TemperatureNumber` (per-VTherm preset temperatures), `CentralConfigTemperatureNumber`, boiler thresholds. `select.py`: `CentralModeSelect`, `AutoStartStopStopModeSelect`. `switch.py`: `FollowUnderlyingTemperatureChange`, `AutoStartStopEnable`.

## `llm/` package

HA LLM tool provider: `llm/__init__.py::async_get_tools` returns `LLMTools` for the Assist API when VTherm entities are exposed (discovery by the HA llm integration: unverified). Tools: list, status, diagnose, history, logs, plugins, set temperature/preset/hvac mode, TPI check/analyze/set. `llm/diagnostics.py` (logs, plugins), `llm/central_configuration.py` (central config snapshot), `llm/diagnostic_time.py` (timestamps). Reads state attributes and the recorder; calls HA services; no import of thermostat classes.

## Configuration

`config_flow.py` (flow, options flow, menu, validation), `config_schema.py` (`STEP_*` schemas), `const.py` (`CONF_*`, `CONFIG_VERSION`, events helper `send_vtherm_event`, error classes, `overrides` decorator). `commons.py` (`write_event_log`, `round_to_nearest`, `check_and_extract_service_configuration`). Details: `config-flow.md`.

## Consumption of the `vtherm_api` package (separate repository)

- `const.py` re-exports `DOMAIN`, `EventType`, `NowClass`, `get_tz`; `commons_type.py` re-exports `ConfigData`; `vtherm_central_api.py` subclasses `VThermAPI`.
- `base_thermostat.py`: `UnderlyingPowerCommand`, `ValveCommand`, `ValveDiagnosticState`, `UNDERLYING_HOOK_TIMEOUT_SEC`; `cycle_scheduler.py`: command receipts, `PowerCommandKind`; `underlyings.py`: `ValveCommand`, `ValveCommandCause`; `inhibition_manager.py`: `InhibitionNotStartedError`.
- `get_vtherm_logger` in nearly every module; `__init__.py` uses the log collector (handler, export, download endpoint).
- Registries read by the core: feature manager factories (`_load_external_feature_managers`), prop algorithm factories (`ThermostatProp._init_algorithm_handler`, `config_schema.py::get_prop_function_options`). Contracts: `plugin-api.md`.

## Where do I change X?

| Change | Where |
|--------|-------|
| TPI formula, thresholds | `prop_algo_tpi.py::TpiAlgorithm.calculate` |
| Cycle timing, min on/off, repeat | `cycle_scheduler.py::calculate_cycle_times`, `CycleScheduler.start_cycle`, `_tick` |
| How demand reaches the cycle | `prop_handler_tpi.py::TPIHandler.control_heating`, `thermostat_prop.py::ThermostatProp.on_percent` |
| Valve opening filters / min-max opening | `valve_command.py::ValveCommandMixin`, `underlyings.py::UnderlyingValve._get_controlled_percent`, `opening_degree_algorithm.py` |
| Auto TPI learning rules | `auto_tpi_manager.py::AutoTpiManager._should_learn`, `_perform_learning`, `on_cycle_completed` |
| Priority between window, safety, central mode, preset, away | `state_manager.py::StateManager` (`calculate_current_*`) |
| Preset list and temperatures | `base_thermostat.py::BaseThermostat.init_presets`, `find_preset_temp`; `number.py::TemperatureNumber` |
| Sensor handling (room, outdoor, last seen) | `base_thermostat.py::_async_temperature_changed`, `_async_update_temp`, `_async_ext_temperature_changed` |
| Main control loop | `base_thermostat.py::BaseThermostat.async_control_heating`; override `_control_heating_specific` |
| Setpoint regulation of over_climate | `thermostat_climate.py::_send_regulated_temperature`, `pi_algorithm.py` |
| Reaction to a device-side change (over_climate) | `thermostat_climate.py::underlying_changed`, `underlyings.py::UnderlyingClimate._underlying_changed` |
| A command sent to a device | The matching `Underlying*` method; keep `is_command_blocked` / `hass_services_async_call` |
| Add a feature manager | New `feature_*_manager.py` from `BaseFeatureManager`; register in `BaseThermostat.__init__`; attributes in `add_custom_attributes`; `unrecorded_attributes` union in `BaseThermostat` |
| Add or change an entity service | `const.py::SERVICE_*`, `services.yaml`, `climate.py::async_setup_entry`, handler `BaseThermostat.service_*`, `translations/en.json` `services` |
| Published attributes | `base_thermostat.py::update_custom_attributes` and the subclass overrides |
| Fired events | `base_thermostat.py::send_event`, `const.py::send_vtherm_event`, `EventType` in `vtherm_api` |
| Add a platform entity | The platform file `async_setup_entry` (conditions on config); subclass `VersatileThermostatBaseEntity` |
| Startup and restore of attributes | `base_thermostat.py::async_startup`, `get_my_previous_state`, `init_underlyings_completed` |
| Central mode, central power, boiler | `select.py::CentralModeSelect`, `feature_central_power_manager.py`, `feature_central_boiler_manager.py`, `vtherm_central_api.py` |
| Config option or step, migration | `config-flow.md`; `config_flow.py`, `config_schema.py`, `const.py`, `__init__.py::async_migrate_entry` |
| Plugin hooks (before-mode, valve, power, setpoint) | `base_thermostat.py::_async_call_external_hook`, `thermostat_climate.py::_adjust_regulated_temperature`, `cycle_scheduler.py::_fire_underlying_power` |
| Inhibition by plugin | `inhibition_manager.py::InhibitionManager`, `state_manager.py` (forces OFF), `underlyings.py::UnderlyingEntity.is_command_blocked` |
| LLM tool | `llm/__init__.py` (tool class and `async_get_tools`), `llm/diagnostics.py` |
| Logs download | `__init__.py::async_setup` (collector), `base_thermostat.py::service_download_logs` |

## Large files: never read whole

Read by symbol (`grep -n "def "`) then by range.

| File | Approx. lines |
|------|-------|
| `base_thermostat.py` | ~2800 |
| `underlyings.py` | ~2100 |
| `thermostat_climate.py` | ~1800 |
| `auto_tpi_manager.py` | ~1500 |
| `llm/__init__.py` | ~1500 |
| `config_flow.py` | ~1300 |
| `sensor.py` | ~1100 |
| `cycle_scheduler.py` | ~1100 |
| `translations/en.json` | ~1100 |
| `const.py` | ~800 |
| `llm/diagnostics.py` | ~800 |
| `tpi_identification.py` | ~700 |
| `thermostat_climate_valve.py` | ~600 |
| `feature_central_boiler_manager.py` | ~600 |
| `feature_heating_failure_detection_manager.py` | ~600 |
| `number.py` | ~600 |
| `config_schema.py` | ~600 |
| `prop_handler_tpi.py` | ~600 |
| `__init__.py` | ~500 |
| `feature_window_manager.py` | ~500 |
| `feature_timed_preset_manager.py` | ~500 |
