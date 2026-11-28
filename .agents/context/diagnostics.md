# Diagnostics: investigating a user's problem

Package: `custom_components/versatile_thermostat/`; bare file names below are relative to it.

## 1. Thermostat state attributes

- `documentation/en/base-attributes.md` is NOT about state attributes: it documents the config-flow "Main attributes" page (names such as `cycle_min`).
- State attributes are documented in `documentation/en/reference.md`: sections "Custom attributes" (per VTherm and central configuration), "State messages", "Events", "Sensors". The table there is partial; the code is the reference.
- Built in `BaseThermostat.update_custom_attributes` (`base_thermostat.py`). Top level: `hvac_action`, `hvac_mode`, `preset_mode`, `ema_temp`, `is_ready`. Then four dicts:
  - `specific_states`: `is_initialized`, `is_on`, `should_device_be_active`, `is_device_active`, `device_actives`, `hvac_off_reason`, `hvac_mode_reason`, `last_temperature_datetime`, `last_ext_temperature_datetime`, `last_update_datetime`, `is_sleeping`, `is_locked`, `not_initialized_entities`, `unavailable_underlying_entities`, `messages`.
  - `configuration`: type, `cycle_min`, `proportional_function`, central-mode and boiler flags, `max_on_percent`.
  - `preset_temperatures`: all preset temperatures (home/away, plus cool variants for AC `over_climate`).
  - Feature sections added through `add_custom_attributes(extra_state_attributes)` of each manager and of `state_manager.py` (`current_state`, `requested_state`).
- Per-feature sections (only present when the feature is configured, each with an `is_<feature>_configured` flag at top level): `safety_manager`, `power_manager`, `window_manager`, `presence_manager`, `motion_manager`, `lock_manager`, `auto_start_stop_manager`, `heating_failure_detection_manager`, `humidity_manager`, `repair_incorrect_state_manager`, `timed_preset_manager`; the inhibition block appears only once used.
- Type-specific additions: `thermostat_switch.py`, `thermostat_valve.py`, `thermostat_climate.py` (`vtherm_over_climate`, `regulated_target_temperature`, `regulation_accumulated_error`), `thermostat_climate_valve.py` (`valve_open_percent`, `power_percent`, `on_percent`), `prop_handler_tpi.py` (`auto_tpi_state`, `auto_tpi_learning`, `regulation_diagnostics`, `minimal_*_delay_sec`).
- `specific_states.messages` holds codes explaining the current state; codes are the `MSG_*` constants in `const.py` (documented in the reference "State messages" table). Prefer `messages`, `hvac_off_reason` and `hvac_mode_reason` over guessing.
- Central configuration attributes live on the central boiler binary sensor (`binary_sensor.py`, `CentralBoilerBinarySensor`), section `central_boiler_manager`.

## 2. Diagnostic entities
Created per VTherm depending on type and features (reference "Sensors"); classes in `sensor.py`, `binary_sensor.py`, `switch.py`, `select.py`, `number.py`:
- sensors: last temperature / last external temperature received, mean power, on percent, on time, off time, valve open percent, temperature slope, regulated temperature, EMA temperature, energy, Auto TPI learning (unique id suffix `_auto_tpi_learning`);
- binary sensors: safety, overpowering, heating failure, window, window bypass, motion, presence, central boiler;
- central: number-of-active-devices / total-power sensors for the boiler, central mode select, boiler threshold number; per VTherm: auto-start/stop enable switch and stop-mode select.

## 3. Events (bus)
Sent by `send_vtherm_event` (`const.py`; payload = data + `entity_id`, `name`, `state_attributes`). Enum `EventType` comes from `vtherm_api.const`: `versatile_thermostat_` + `safety_event`, `power_event`, `temperature_event`, `hvac_mode_event`, `preset_event`, `central_boiler_event`, `window_auto_event`, `auto_start_stop_event`, `timed_preset_event`, `heating_failure_event`. Emitters are the matching `feature_*_manager.py` files (preset/hvac events in `base_thermostat.py`). Every send is also logged at info level ("Sending event ...").

## 4. Logging
- Modules use `get_vtherm_logger(__name__)` from `vtherm_api.log_collector` (a `Logger` subclass that always feeds the collector, whatever the configured level). Logger root: `custom_components.versatile_thermostat`. Messages are prefixed with the thermostat name (`"%s - ..."`), which the collector uses to filter per VTherm.
- Users enable HA-level debug with `logger:` `logs:` `custom_components.versatile_thermostat: debug` (very verbose; old method, see `documentation/en/troubleshooting.md`, "Enable Logs").
- Log collector (recommended): a single ring buffer `VThermLogHandler` stored in `hass.data[DOMAIN]["log_handler"]`, created in `async_setup` (`__init__.py`). Retention `log_buffer_max_age_hours` (YAML `versatile_thermostat:` key, default = the `vtherm_api` constant `DEFAULT_MAX_AGE_HOURS`; the user doc may state a different value, check `documentation/en/reference.md`). Action `versatile_thermostat.download_logs` (`services.yaml`; fields `log_level`, `period_start`, `period_end`; default period = last 60 min) writes a file and shows a persistent notification with a download link on an HTTP endpoint registered by `async_register_log_download_endpoint`. Docs: `documentation/en/feature-logs-collector.md`, design in `documentation/tech-docs/log-collector.md`.
- Logs are in memory only: lost on HA restart.

## 5. LLM / MCP package (`llm/`)
- `llm/__init__.py` is the HA `llm` platform of the integration: `async_get_tools(hass, llm_context, api_id)` returns tools only for the Assist API and only for VTherm entities exposed to Assist. HA's MCP server republishes them; there is no own server. Docs: `documentation/en/feature-llm-mcp.md` (`en` is the source; other languages may lag, see `workflows/docs-i18n.md`).
- Read tools (names `versatile_thermostat__<tool>`): `list_vtherms`, `get_status`, `diagnose` (structured snapshot of heating/idle/off decisions, power, safety, window, presence, motion, auto-start/stop, underlying entities, central config), `get_history` (Recorder export, max 14 days per request, paged), `get_logs` (collector, `min_level`, time range), `get_plugins` (plugin links and diagnostics published by plugins), `check_tpi_optimization`, `analyze_tpi_coefficients`.
- Write tools: `set_temperature`, `set_preset`, `set_hvac_mode`, `set_tpi_coefficients` (confirmation token for large changes).
- Helpers: `llm/diagnostics.py` (log reading, plugin diagnostics), `llm/central_configuration.py` (scoped central-config snapshot, deliberately excludes lock codes and templates), `llm/diagnostic_time.py` (strict timestamps).
- `recorder_export.py`: raw Recorder reads (`read_recorder_history`) and paged export (`async_export_history`) over recorded climate fields only (current temperature, target, hvac_action, preset_mode, unit), shared by `get_history` and TPI analysis (`tpi_history.py`, `tpi_identification.py`).
- No HA `diagnostics.py` platform exists (verified; the log-collector design doc lists it as a rejected alternative).

## 6. Symptom -> where to look

| Symptom | Check |
| --- | --- |
| Heater never turns on | `specific_states.messages`, `hvac_off_reason`, `is_initialized`/`not_initialized_entities`/`unavailable_underlying_entities` (VTherm stays disabled until underlyings have a state); `should_device_be_active` vs `is_device_active`; `underlyings.py`, `cycle_scheduler.py` (`over_switch`); `repair_incorrect_state_manager` section |
| Wrong preset / target temperature | `preset_mode`, `temperature`, `hvac_mode_reason`, messages `target_temp_*`; `preset_temperatures`; `vtherm_preset.py`, `state_manager.py`; central mode (`last_central_mode`), timed preset, presence/motion sections |
| Window not detected / not restored | `window_manager` (`window_state`, `window_auto_state`, `window_action`, `is_window_bypass`, delays, auto thresholds); `feature_window_manager.py`, `open_window_algorithm.py`; `window_auto_event`; reference "Window" parameters |
| Valve not following (over_valve) | `valve_open_percent`, `on_percent`, `min_opening_degrees`, `auto_regulation_dpercent`, `auto_regulation_period_min`, `last_calculation_timestamp`; `thermostat_valve.py`, `opening_degree_algorithm.py`, `valve_command.py` |
| Climate valve (TRV) stuck or no heat | `thermostat_climate_valve.py`, `heating_failure_detection_manager` section, `heating_failure_event` (`root_cause`), `HeatingFailureBinarySensor` |
| Overpowering / power shedding | `power_manager` (`overpowering_state`, `current_power`, `current_max_power`, `device_power`, `power_temp`), message `overpowering_detected`, `power_event`; `feature_power_manager.py`, `feature_central_power_manager.py`, power sensors' unit/scale |
| Central boiler not switching | `central_boiler_manager` on the central boiler binary sensor (`is_ready`, counters vs thresholds, `activation_scheduled`, service_activate/deactivate); `feature_central_boiler_manager.py`, `central_boiler_event`; per-VTherm `is_used_by_central_boiler` |
| Safety mode triggered | `safety_manager.safety_state`, `last_temperature_datetime` / `last_ext_temperature_datetime` vs `safety_delay_min`, `safety_event`, `temperature_event`; `feature_safety_manager.py`; troubleshooting "Safety Mode" (only `over_switch`/`over_valve`) |
| Auto-start/stop surprises | `auto_start_stop_manager` (`level`, `dtmin`, accumulated error vs threshold, `is_auto_stop_detected`, `last_switch_date`, `stop_mode`), `auto_start_stop_event`; `auto_start_stop_algorithm.py`, `feature_auto_start_stop_manager.py` |
| Auto TPI not learning | `specific_states.auto_tpi_state` / `auto_tpi_continuous_kext` / `auto_tpi_learning`, the Auto TPI learning sensor, repair issue (created in `auto_tpi_manager.py`), sensor resolution/noise; `auto_tpi_manager.py`, `prop_handler_tpi.py`; docs `feature-autotpi.md`, `feature-autotpi-technical.md` |
| TPI heating time odd | `on_percent`, mean/on/off time sensors, `tpi_coef_int`/`tpi_coef_ext`, `minimal_*_delay_sec`, `max_on_percent`; `prop_algo_tpi.py`, `tpi_regulation.py`, `cycle_scheduler.py` |
| over_climate regulation / setpoint ignored | `regulated_target_temperature`, `regulation_accumulated_error`, `vtherm_over_climate`; `thermostat_climate.py`, `self-regulation.md`; underlying changes tracked (`keep_alive.py`, `underlying_state_manager.py`) |
| Commands re-sent / state flips back | `repair_incorrect_state_manager` section, `feature_repair_incorrect_state_manager.py`, debug log of `underlyings.py` (`check_and_repair`) |
| Locked / presence / motion issues | `lock_manager`, `presence_manager`, `motion_manager` sections and their managers |

For anything unclear: ask the user for the `download_logs` file over the failing period plus the climate entity's full attributes (Developer Tools / States).
