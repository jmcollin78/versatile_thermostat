# Runtime flow

Paths without a folder are in `custom_components/versatile_thermostat/`. Static map: `architecture.md`.

## 1. Integration setup and unload

1. `__init__.py::async_setup`: stores YAML params in `VersatileThermostatAPI.set_global_config`, calls `central_boiler_manager.notify_vtherms_starting`, registers the `reload` admin service, creates the shared `VThermLogHandler` in `hass.data[DOMAIN]["log_handler"]` and the log download endpoint.
2. If HA is not running yet, `_async_startup_internal` waits for `EVENT_HOMEASSISTANT_STARTED`; else it runs immediately: `api.init_vtherm_links()`, `api.notify_central_mode_change()`, `async_migrate_auto_start_stop`.
3. `async_setup_entry` (once per config entry, central config included): `api.add_entry` (stores the entry in `hass.data[DOMAIN]`), registers `update_listener`, forwards `PLATFORMS` (climate, sensor, number, binary_sensor, switch, select), then `api.init_vtherm_links(entry_id)` if HA is running.
4. `update_listener`: skipped when `api.skip_reload_on_config_update` is set; central entry change -> `reload_all_vtherm`; other entry -> reload the entry, `reload_central_boiler_entities_list`, `init_vtherm_links(entry_id)`.
5. `async_unload_entry`: unload platforms; central entry also `api.reset_central_config` and `central_boiler_manager.stop_listening`; `api.remove_entry` drops the API from `hass.data` only when no entry and no plugin registration remain.
6. `async_migrate_entry`: cumulative `version <= N` blocks (see `config-flow.md`).
7. A central config entry creates no thermostat: `climate.py::async_setup_entry` only calls `central_power_manager.post_init`; `binary_sensor.py` calls `central_boiler_manager.post_init`.

## 2. Entity construction and startup

Construction (platform `async_setup_entry`, `climate.py`):
1. `BaseThermostat.__init__` creates the managers and `InhibitionManager`, then calls `post_init`.
2. `BaseThermostat.post_init`: `clean_central_config_doublon` merges central config with the entry (central keys removed from the entry when its `CONF_USE_*_CENTRAL_CONFIG` is true); `manager.post_init(entry_infos)` for each manager; `_load_external_feature_managers`; temperatures, cycle length, sensors ids, EMA.
3. Subclass `post_init` (called first through `super()`): builds underlyings and the `CycleScheduler` (`_bind_scheduler`), proportional subclasses call `_init_algorithm_handler` (TPI always; plugin algorithm may be missing and is retried at startup).
4. `async_add_entities([entity], True)`, then entity services are registered on the climate platform.

`async_added_to_hass` (HA adds the entity):
1. `ThermostatProp`: `_algo_handler.async_added_to_hass` (loads Auto TPI storage and applies learned coefficients when learning is active).
2. `BaseThermostat`: `async_track_state_change_event` on room, last-seen and outdoor sensors; `remove_thermostat` registered for removal.
3. Switch/valve/climate classes: listen to underlying switch/valve entities and install `async_track_time_interval(async_control_heating, cycle_min)`.
4. The thermostat does not start here: startup is triggered by the API (`init_vtherm_links`) because other entities must exist.

`BaseThermostat.async_startup(central_configuration)`, called by `init_vtherm_links` for every climate whose `device_info` model is the domain (all at HA start, one with `entry_id`):
1. `async_get_last_state`; `_inhibition.restore_state`.
2. Retry `_load_external_feature_managers` (plugins may register later).
3. `manager.start_listening()` for all managers (sensor listeners, timers).
4. `get_my_previous_state`: restores `current_state` / `requested_state` (attributes), off reasons, total energy (unit conversion), `restore_specific_previous_state`, `manager.restore_state(old_state)`; without state, target = min (max in AC) temperature.
5. `under.startup()` for each underlying (starts its `UnderlyingStateManager`), registers cycle start callbacks on the scheduler.
6. `init_presets(central_configuration)`: reads preset temperatures from the registered `Number` entities (central ones when inherited), builds `_attr_preset_modes`, re-applies the requested preset.
7. Reads the current room and outdoor sensor states (`_async_update_temp`, `_async_update_ext_temp`), sets `_is_startup_done`; if `is_ready`, `init_underlyings_completed`.
8. Otherwise each underlying calls it later: `UnderlyingEntity._underlying_changed` sees all states initialized, runs `check_initial_state` and calls `thermostat.init_underlyings_completed` when every underlying is initialized.

`init_underlyings_completed`: `refresh_state` on every manager, `update_states(force=True)`, persist energy unit if changed, `recalculate`, `_inhibition.async_on_vtherm_ready`, `reset_last_change_time_from_vtherm`. `ThermostatProp.async_startup` ends with `_algo_handler.async_startup`; `ThermostatOverClimateValve` also starts its valve-regulation underlyings. `is_ready` = startup done and all underlyings initialized; `update_states` and `async_control_heating` return early until then.

## 3. Event and listener wiring

| Source | Listener | Effect |
|--------|----------|--------|
| Room temperature sensor | `_async_temperature_changed` | `_async_update_temp` (value, timestamp, EMA, window auto detection) -> `recalculate()` -> safety / auto stop refresh (if changed: `update_states` is scheduled by the manager, stop here) -> `async_control_heating(force=False)`; over_climate also `synchronize_device_temperature` |
| Last-seen sensor | `_async_last_seen_temperature_changed` | Updates `_last_temperature_measure`; leaves safety if it recovers |
| Outdoor sensor | `_async_ext_temperature_changed` | Updates outdoor value, `recalculate`, safety refresh, `async_control_heating` |
| Window / motion / presence sensors | manager `_*_sensor_changed` | Manager updates its state; on change `requested_state.force_changed()` + `update_states(True)` |
| Central power / max power sensors | `FeatureCentralPowerManager` | `refresh_state` -> delayed `calculate_shedding` -> `set_overpowering` on selected VTherms |
| Central mode select | `CentralModeSelect.async_select_option` | `api.notify_central_mode_change` -> `check_central_mode` on each VTherm -> `update_states` |
| Preset `Number` entity | `TemperatureNumber.async_set_native_value` | `set_preset_temperature` on its VTherm; central numbers call `api.init_vtherm_preset_with_central` |
| Underlying switch/valve | `_async_switch_changed`, `_async_valve_changed` | Recompute `hvac_action`, attributes, write state only (no command) |
| Underlying climate | `UnderlyingStateManager` -> `UnderlyingClimate._underlying_changed` -> `underlying_changed` | Drops non-changes and out-of-range setpoints; may adopt the device mode/setpoint when `FollowUnderlyingTemperatureChange` is on, then `requested_state.force_changed()` + `update_states` |
| Underlying (all types) | `UnderlyingEntity._underlying_changed` | Initialization completion; refresh attributes on `hvac_action` or availability change; update the central boiler active count |
| Timer | `async_track_time_interval(async_control_heating, cycle_min)` | Periodic cycle; `timestamp` set, so safety refresh runs |
| Boiler VTherm states | `FeatureCentralBoilerManager.calculate_central_boiler_state` | Activates/deactivates the boiler by service call |

## 4. Control cycle (change to command)

Entry points: sensor events, `update_states` (any state change), the periodic timer, services (`async_control_heating(force=True)`), delayed recalculation timers.

1. `BaseThermostat.update_states(force)`: if `requested_state.is_changed`, `StateManager.calculate_current_state`; on change: preset event, new target, new hvac mode (each underlying `set_hvac_mode`, `HVAC_MODE_EVENT`, overpowering cleared when OFF/SLEEP), `recalculate(force)`, `async_control_heating(force)`; then `calculate_hvac_action`, `update_custom_attributes`, `async_write_ha_state`; flags reset. Not ready: nothing happens.
2. `async_control_heating`: not ready -> return. `window_manager.manage_window_auto(in_cycle=True)`. On a periodic call, `safety_manager.refresh_and_update_if_changed` (return if changed). Safety on over_climate -> return. `_control_heating_specific`. Then `refresh_state` of external managers, legacy heating failure manager (unless a plugin owns it), `repair_incorrect_state_manager.check_and_repair`, `calculate_hvac_action`, attributes + state write (proportional handlers may skip an intermediate publish).
3. Proportional path (switch, valve, climate-valve): `ThermostatProp._control_heating_specific` -> `TPIHandler.control_heating`: `AutoTpiManager.update/calculate` (new coefficients pushed to `TpiAlgorithm.update_parameters`, then `recalculate`); OFF -> zero times, turn off underlyings or `cancel_cycle`; else `on_percent = thermostat.on_percent` (None -> keep current state, return); `CycleScheduler.start_cycle(hvac_mode, on_percent, force)`.
4. `recalculate()` (`ThermostatProp.recalculate`): `TpiAlgorithm.calculate(target, room, outdoor, slope, hvac_mode)` fills the calculated percent. `ThermostatProp.on_percent` returns the safety default percent in safety, else the algorithm percent, clamped by `max_on_percent`, and reports the realized value back.
5. `CycleScheduler.start_cycle`: clamp, valve retention (valve mode), `calculate_cycle_times`. A running switch cycle with on time > 0 is not interrupted unless `force`: parameters become pending and apply at the next `_on_master_cycle_end`. Otherwise `_cancel_cycle_impl` (fires cycle end with realized effective percent), then start callbacks (Auto TPI), command receipt, and:
   - switch: 0% / OFF -> `turn_off` active underlyings; 100% -> `turn_on` all; else offsets per underlying (`compute_circular_offsets`) and `_tick`, which schedules the next tick and calls `UnderlyingSwitch.turn_on` / `turn_off`. `turn_on` checks `check_overpowering` first (refusal -> overpowering state, `update_states`).
   - valve: `_resolve_valve_on_percent` calls `thermostat.apply_valve_command_percent` (delta-percent and period filters; sleeping = 100%; a filtered change schedules `do_recalculate_later` after 20 s), then `_apply_valve_command` -> `UnderlyingValve.set_valve_open_percent` -> `_get_controlled_percent` -> `send_percent_open` -> `send_value_to_number` (number set value service). `UnderlyingValveRegulation.send_percent_open` sends opening (and closing) degree numbers and calls the after-valve-command hook.
   - Every start fires the underlying power hook for plugins (`_fire_underlying_power`).
6. over_climate (no proportional handler): `ThermostatOverClimate.async_control_heating`: auto start/stop refresh (change -> `update_states`), `_send_regulated_temperature` (target or PI-regulated value, step rounding, device-temperature offset, dtemp filter, period check -> `UnderlyingClimate.set_temperature`; hvac mode other than heat/cool sends the raw target), auto fan mode, then the base cycle, `incremente_energy`.
7. over_climate with valve regulation: `_send_regulated_temperature` is overridden: sends the raw target to climates, then `set_valve_open_percent` on the valve-regulation underlyings; the proportional part runs through steps 3-5 on the valve scheduler.
8. Plugin hooks in this path: setpoint adjusters (`adjust_regulated_temperature`, over_climate), before-hvac-mode hook (`UnderlyingClimate.set_hvac_mode`), after-valve-command hook, underlying power hook. Each call is guarded by a timeout and never blocks the command.

### Periodic timers and activity per thermostat type

- Periodic control: `ThermostatOverSwitch`, `ThermostatOverValve` and `ThermostatOverClimate` each install their own `async_track_time_interval(async_control_heating, cycle_min)` in `async_added_to_hass` (`thermostat_switch.py`, `thermostat_valve.py`, `thermostat_climate.py`), removed with `async_on_remove`. `ThermostatOverClimateValve` inherits the climate one; the base class installs none.
- `hvac_action` is stored by `calculate_hvac_action`, called from `async_control_heating` and the underlying change listeners.
  - switch: base `BaseThermostat.calculate_hvac_action`: OFF when the mode is OFF, IDLE when `is_device_active` is false, else COOLING in cool mode, otherwise HEATING.
  - valve: same base logic, forced to OFF while sleeping (`is_sleeping`).
  - climate: `ThermostatOverClimate.calculate_hvac_action` takes the first underlying action that is not IDLE or OFF, else IDLE if one is IDLE, else OFF. Climate with valve regulation does the same over `_underlyings_valve_regulation`, OFF when sleeping.
- `should_device_be_active` / `is_device_active` (base: true when any underlying is): `UnderlyingSwitch` expects ON when the mode is heat or cool and the on time is above zero, and reads the observed switch state; `UnderlyingValve` compares the raw demand to the opening threshold (should) and the real opening to the closing degree (is); `UnderlyingClimate` derives both from the device `hvac_action` (simulated from target and current temperature when absent). Sleeping valve thermostats always answer false; climate with valve regulation also requires the climate itself to be active.

## 5. Presets, hvac mode and state calculation

- Requests change only `requested_state`: `async_set_hvac_mode` (`requested_state.set_hvac_mode`, `update_states(force=False)`), `async_set_preset_mode` (accepted unless central mode forbids; cancels a manual override; `update_states(True)`), `async_set_temperature` (sets target, preset NONE or starts a manual override via `FeatureTimedPresetManager`, `update_states(True)`). All three are wrapped by `check_lock`.
- `StateManager.calculate_current_hvac_mode`, first match wins: inhibition (OFF), central mode Stopped (OFF), safety (OFF; for proportional thermostats only when the default on percent is 0), window (OFF / fan only; eco and frost actions only change the target), auto stop (stop mode), central Cool only / Heat only, central Frost protection, else the requested mode. The off/mode reasons (`HVAC_OFF_REASON_*`) are set here.
- `calculate_current_preset`: overpowering -> `power` preset, safety -> `safety`, central frost, active timed preset, else requested preset.
- `calculate_current_target_temperature`: window eco/frost temperature, motion (activity preset), absence (away temperatures), else the current preset temperature (`find_preset_temp`), else the requested target.
- Hidden presets (`HIDDEN_PRESETS`) never become the requested preset.
- Consumers: `BaseThermostat.target_temperature`, `preset_mode`, `vtherm_hvac_mode` read `current_state`; `requested_state` keeps the user's intent so the VTherm returns to it when an override ends.

## 6. Persistence

- Climate state: HA `RestoreEntity`; attributes `current_state`, `requested_state` (via `StateManager.add_custom_attributes`), `specific_states` (off reasons, total energy and unit), manager sections (lock, window bypass, timed preset, auto start/stop, overpowering state, inhibition). `async_will_remove_from_hass` forces `async_dump_states`.
- Other entities restoring their last state: `TemperatureNumber`, central numbers, `CentralModeSelect`, switches, `AutoStartStopStopModeSelect`.
- Auto TPI learning data: `Store` (`AutoTpiManager.async_save_data` / `async_load_data`); coefficients written to the config entry without reload (`skip_reload_on_config_update`).
- `set_tpi_parameters` writes the config entry through `_async_update_tpi_config_entry` (the entry update triggers the update listener; the handler checks `is_removed` afterwards).
- Configuration: only in `ConfigEntry.data`.

## 7. Services

Registered in `climate.py::async_setup_entry` with `platform.async_register_entity_service`; schemas in the same file, documentation in `services.yaml`, names in `const.py::SERVICE_*`; HA service `reload` registered in `async_setup`.

| Service | Handler |
|---------|---------|
| `set_presence` | `BaseThermostat.service_set_presence` (updates presence, `async_control_heating(force=True)`) |
| `set_safety` | `service_set_safety` (updates manager values, control cycle) |
| `set_window_bypass` | `service_set_window_bypass_state` |
| `set_auto_regulation_mode`, `set_auto_fan_mode` | `ThermostatOverClimate.service_set_auto_regulation_mode`, `service_set_auto_fan_mode_deprecated` |
| `set_hvac_mode_sleep` | `service_set_hvac_mode_sleep` in `ThermostatOverValve` and `ThermostatOverClimateValve`; the base raises `NotImplementedError` for other types |
| `recalibrate_valves` | `service_recalibrate_valves` in `ThermostatOverClimateValve` only; the base raises `ServiceValidationError` |
| `lock`, `unlock` | `service_lock`, `service_unlock` |
| `set_tpi_parameters`, `set_auto_tpi_mode` | `ThermostatProp` delegates to the handler (`TPIHandler.service_*`); other handlers raise a validation error |
| `set_timed_preset`, `cancel_timed_preset` | `service_set_timed_preset`, `service_cancel_timed_preset` |
| `download_logs` | `service_download_logs` (log collector export) |

Entity-level setters (`async_set_temperature`, `async_set_preset_mode`, `async_set_hvac_mode`, fan/swing) are the standard climate services. Presets temperatures change through the `Number` entities, not a service.

## 8. Events fired

`BaseThermostat.send_event` -> `const.py::send_vtherm_event` adds `entity_id`, `name`, `state_attributes` and fires on the bus. Types (`EventType`, defined in the `vtherm_api` package): preset and hvac mode (`update_states`), safety (start/end) and temperature (emitted by the safety manager), power (overpowering start/end), window auto, auto start/stop, timed preset, heating failure, central boiler (fired for the boiler entity, `binary_sensor.py` listens to it).

## 9. Safety and protections

- Safety (`FeatureSafetyManager.refresh_state`): room or outdoor sensor older than the delay and on percent above the minimum -> `set_safety(default_on_percent)` and `safety` preset; applies to proportional thermostats only (the over_climate branch is disabled in code). Refreshed on sensor events and periodic cycles; a change is applied through `update_states` scheduled at the next loop turn.
- Overpowering: central shedding picks VTherms by temperature gap; `set_overpowering` turns underlyings off; `turn_on` re-checks the budget; `power` preset.
- Window: hvac mode or target change as in section 5; `manage_window_auto` runs on each temperature update and each cycle.
- Repair: `check_and_repair` re-sends commands when an underlying disagrees with the desired state (bounded attempts, delay after ready).
- Heating failure: the core manager is refreshed each cycle in `async_control_heating` (unless a plugin owns it). The TPI handler reads `is_detected` through `get_feature_manager("heating_failure_detection")`, which only returns a plugin manager: without the plugin `AutoTpiManager.update` always gets `is_heating_failure=False`.
- Inhibition: `InhibitionManager.async_set` closes the command gate (`blocks_command`) and forces OFF; reopening reconciles underlyings.
- Lock: `check_lock` drops user and/or automation calls while locked.
- Keep-alive: `UnderlyingSwitch._keep_alive_callback` re-sends the last commanded switch state.
- Unavailable room sensor: `on_percent` None keeps the current switch state; unavailable underlyings are listed in `specific_states.messages`.
