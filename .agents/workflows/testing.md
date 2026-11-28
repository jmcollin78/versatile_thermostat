# Testing

## Setup and configuration

- Create a virtualenv on a local (non-network) filesystem with the Python version required by the pinned Home Assistant release, then `pip install -r requirements_test.txt`. It pulls `requirements_dev.txt` (pinned `homeassistant`, `vtherm_api`, frontend and media helpers), `pytest`, `pytest-asyncio`, `pytest-timeout`, `scipy`, `coverage` and `pytest-homeassistant`. `pytest-xdist` (used by CI with `-n auto`) is not listed there (unverified how CI gets it).
- The tests import `pytest_homeassistant.common` (`MockConfigEntry`, `async_fire_time_changed`, `mock_restore_cache`). The module is named `pytest_homeassistant`; an environment that only has the package `pytest-homeassistant-custom-component` fails at conftest import with `ModuleNotFoundError: pytest_homeassistant`. Install exactly from `requirements_test.txt` (that `pytest-homeassistant` provides this module name is unverified here).
- Configuration: `pyproject.toml` `[tool.pytest.ini_options]` sets `addopts = ["-p", "no:respx"]`, `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"` and the `scientific` marker. `setup.cfg` also sets `testpaths = tests` and `asyncio_mode = auto`. Async tests need no decorator.
- CI (`.github/workflows/`) runs `pytest -qq --timeout=9 --durations=10 -n auto -p no:respx -p no:sugar tests`: 9 s per test, parallel with xdist. A test must not depend on running alone or on order.
- Do not pass `-p no:logging`: `caplog` is used in many test files (e.g. `tests/test_inhibition.py`) and needs the logging plugin. `-p no:sugar` is fine when the optional sugar plugin is installed.
- Run from the repository root (tests import `custom_components...` and use relative `.commons`).
- Tests marked `scientific` are skipped unless `--run-scientific` is given (`tests/conftest.py`); `tests/README.md` describes them.

## Running

| Goal | Command |
|------|---------|
| One file | `pytest -q tests/test_window.py` |
| One test | `pytest -q tests/test_window.py::test_name` |
| By keyword | `pytest -q tests -k "preset"` |
| Slowest tests | add `--durations=10` |
| Full suite | `pytest -q tests`: slow; start it as a background job and wait for the completion notification; never poll it |
| Scientific checks | `pytest -q --run-scientific -m scientific` |

Run targeted files first, the full suite once at the end of a task. With `pytest-xdist` installed, `-n auto` speeds up the full suite.

## Layout

- `tests/__init__.py` makes `tests` a package; test files are `tests/test_<area>.py`, flat, no sub-folders. Non-test helpers: `tests/commons.py`, `tests/const.py`, `tests/conftest.py`, `tests/tpi_runtime.py` (builds native TPI runtime objects without HA lifecycle) and `tests/auto_tpi_sim.py` (closed-loop room simulation harness for the Auto TPI manager).
- Regression files named `test_issue_<n>.py` and `test_bugs.py` exist for specific reported cases; prefer the area file for new tests.

| Area | Test files |
|------|------------|
| Config flow, options | `test_config_flow.py` |
| Migration of entries | `test_migration.py` |
| Central config, central mode | `test_central_config.py`, `test_central_mode.py` |
| Central boiler | `test_central_boiler.py`, `test_central_boiler_startup.py` |
| Power / overpowering | `test_power.py`, `test_central_power_manager.py` |
| Window, motion, presence | `test_window.py`, `test_window_feature_manager.py`, `test_open_window_algo.py`, `test_motion.py`, `test_presence.py` |
| Presets, timed preset, setpoint | `test_timed_preset.py`, `test_set_temperature_hvac_mode.py`, `test_setpoint_modifier.py`, `test_manual_override.py` |
| Over switch / cycles | `test_start.py`, `test_multiple_switch.py`, `test_switch_ac.py`, `test_switch_keep_alive.py`, `test_cycle_scheduler.py`, `test_cycle_tick_logic.py`, `test_inverted_switch.py`, `test_virtual_switch.py` |
| Over valve | `test_valve.py`, `test_recalibrate_valves.py` |
| Over climate | `test_overclimate.py`, `test_overclimate_valve.py`, `test_overclimate_sync_device_temp.py`, `test_auto_regulation.py`, `test_auto_fan_mode.py`, `test_swing_mode.py` |
| Auto start/stop | `test_auto_start_stop.py`, `test_auto_start_stop_feature_manager.py`, `test_auto_start_stop_stop_mode.py` |
| TPI and PI algorithms | `test_tpi.py`, `test_tpi_regulation.py`, `test_tpi_class_isolation.py`, `test_pi.py`, `test_ema.py` |
| Auto TPI, identification | `test_auto_tpi*.py`, `test_tpi_identification.py`, `test_tpi_identification_safety.py`, `test_tpi_history.py`, `test_tpi_valve_history.py` |
| Safety, failure, repair | `test_safety.py`, `test_heating_failure_detection.py`, `test_repair_incorrect_state_manager.py`, `test_underlying_unavailable.py`, `test_last_seen.py` |
| State machine, underlyings | `test_state_manager.py`, `test_under_state_manager.py`, `test_underlying_hooks.py`, `test_check_initial_state.py`, `test_resend_setpoint_after_adoption.py` |
| Platforms (entities) | `test_sensors.py`, `test_binary_sensors.py`, `test_temp_number.py`, `test_unrecorded_attributes.py` |
| Plugins, API, LLM | `test_external_feature_manager.py`, `test_runtime_api_refresh.py`, `test_llm_central_configuration.py`, `test_llm_diagnostics.py`, `test_llm_tpi.py`, `test_recorder_export.py`, `test_service_configuration.py` |
| Lock, humidity, feedback, inhibition | `test_lock.py`, `test_humidity.py`, `test_feedback.py`, `test_inhibition.py`, `test_reload_race_condition.py` |

## Fixtures (`tests/conftest.py`)

- Autouse `isolate_singleton_state` resets `VersatileThermostatAPI` after every test (`reset_vtherm_api`). The `hass` fixture comes from the Home Assistant test plugin; its checks for lingering tasks and timers fail a test that leaves some, hence `@pytest.mark.parametrize("expected_lingering_tasks", [True])` and `expected_lingering_timers` in 31 test files (tests that start cycles or timers).
- `pytest_runtest_setup` allows sockets to localhost only.
- API and central config: `init_vtherm_api` (create the API), `init_central_config` (`create_central_config(hass, FULL_CENTRAL_CONFIG)`), `init_central_config_with_boiler_fixture`, `init_central_power_manager`.
- Fake underlyings and sensors registered in HA: `fake_underlying_switch` (`switch.mock_switch`), `fake_underlying_switch_ac`, `fake_underlying_valve`, `fake_opening_degree`, `fake_underlying_climate`, `fake_underlying_climate_off_cool`, `fake_temp_sensor` (`sensor.mock_temp_sensor`, value 20), `fake_ext_temp_sensor`, `fake_presence_sensor`.
- Patch fixtures: `skip_turn_on_off_heater` (patches `UnderlyingEntity.turn_on/turn_off`), `skip_control_heating` (patches `BaseThermostat.async_control_heating`), `skip_hass_states_is_state` (`StateMachine.is_state` returns False), `skip_hass_states_get` (`StateMachine.get` returns a fixed state, needed by config flow tests that validate entities), `skip_send_event` (patches `BaseThermostat.send_event`), `skip_validate_input` (kept, marked as unused).

## Helpers (`tests/commons.py`, `tests/const.py`)

- `tests/commons.py` re-exports the HA and VT imports used everywhere (`from .commons import *` is the convention) and holds `FULL_CENTRAL_CONFIG*`, mock entity classes (`MockClimate`, `MockSwitch`, `MockNumber`, `MockTemperatureSensor`, `MockBinarySensor`, `MagicMockClimate`), registration (`register_mock_entity`, `create_and_register_mock_climate`), builders (`create_thermostat`, `create_central_config`), lookup (`search_entity`, `count_entities`), event senders (`send_temperature_change_event`, `send_ext_temperature_change_event`, `send_window_change_event`, `send_motion_change_event`, `send_presence_change_event`, `send_power_change_event`, `send_climate_change_event`, ...), `set_climate_preset_temp`, `SideEffects`, `wait_for_local_condition(check, timeout, hass)` and `set_entity_states`.
- `tests/const.py` holds ready-made `MOCK_TH_OVER_*_USER_CONFIG` / `*_MAIN_CONFIG` / `*_FEATURE_*` dicts for flow tests (one dict per form step).

## Creating a thermostat in a test

1. Request the fake underlying and sensor fixtures the thermostat refers to (`fake_underlying_switch`, `fake_temp_sensor`, ...), plus the `skip_*` fixtures the test needs, and `init_central_config` if the entry uses central config.
2. Build `MockConfigEntry(domain=DOMAIN, title=..., unique_id=..., data={CONF_NAME: ..., CONF_THERMOSTAT_TYPE: ..., CONF_UNDERLYING_LIST: [...], ...})` with all mandatory keys; `version`/`minor_version` default to the current ones unless a migration test sets them.
3. `entity = await create_thermostat(hass, entry, "climate.<slug>")` adds the entry, sets it up (asserts `LOADED`) and returns the climate entity found by slugified `CONF_NAME`. Optional `temps` sets preset temperatures.
4. Drive it with `await entity.async_set_hvac_mode(VThermHvacMode_HEAT)`, `async_set_preset_mode`, and the `send_*_change_event` helpers, which call the entity's listener directly with a synthetic `Event`, then `await hass.async_block_till_done()`.
5. Config flow tests do not create entries by hand: they drive `hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})` and `async_configure` through the menu (`{"next_step_id": "main"}`), with `skip_hass_states_get`.

## Underlyings and external effects

- Real HA entities (`MockSwitch`, `MockNumber`, `MockClimate`) are registered through `EntityComponent`, so service calls reach them. `register_mock_entity` disables polling.
- To assert commands, patch the underlying methods in the test: `patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on")` / `turn_off`, `BaseThermostat.send_event`, then assert calls; or use the `skip_*` fixtures when the call itself does not matter.
- Climate underlyings: `MockClimate` / `MagicMockClimate` carry settable hvac mode, action, fan, swing, temperature range; update the state with `set_entity_states_from_entity` or `send_climate_change_event`.
- Cycle scheduling is tested by patching `async_call_later` / `async_track_time_interval` / `async_track_point_in_time` in the module under test (for example `custom_components.versatile_thermostat.cycle_scheduler`, `keep_alive`, `feature_timed_preset_manager`) and calling the captured callbacks.
- Call `await entity.cycle_scheduler.cancel_cycle()` before forcing a new cycle when a previous start already scheduled one.

## Time

- Many tests pass `datetime.now()` as event dates and rely on short real sleeps (`send_*_change_event(..., sleep=True)` waits 0.1 s). Prefer injecting dates over sleeping long.
- Frozen time: the `freezer` fixture (`freezer.move_to(...)`, `freezer.tick(timedelta(...))`, e.g. `tests/test_cycle_scheduler.py`) or `@pytest.mark.freeze_time("...")` (e.g. `tests/test_power.py`).
- HA timers: `async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=n))` from `pytest_homeassistant.common` (e.g. `tests/test_central_boiler_startup.py`, `tests/test_inhibition.py`).
- `wait_for_local_condition` polls a condition with a timeout inside a test (acceptable for in-test waits; not a replacement for firing timers).

## Conventions

- File header usually disables pylint rules (`protected-access`, `unused-argument`, `line-too-long`) and imports `from .commons import *`.
- Tests access private attributes (`entity._prop_algorithm`, `entity._entry_infos`) freely; keep such coupling out of new code when a public property exists.
- Tests that read texts from `translations/en.json` exist (comments in `tests/test_temp_number.py`).
- A new feature needs: a unit test of the logic, an integration test through `create_thermostat`, and a config flow test when it adds options (see `.agents/context/config-flow.md`).
- Before finishing: run the touched files, then the full suite once in the background.
