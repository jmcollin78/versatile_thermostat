# Pitfalls

Durable traps that cost time and will bite again. One bullet each, by theme. Remove a bullet when the code no longer has the trap.

## Runtime and commands

- `CycleScheduler.start_cycle(force=False)` during a running switch cycle with a non-zero on time only stores the new parameters: a new `on_percent` applies at the next cycle end unless `force=True`.
- `UnderlyingSwitch.turn_on` / `turn_off` call `hass.services.async_call` directly; every command path that bypasses the common service helper must check `is_command_blocked` itself, or the inhibition gate is skipped.
- `update_states` and `async_control_heating` return early until the thermostat `is_ready`; changes made before startup completes are picked up only by `init_underlyings_completed`.
- `init_vtherm_links` and `notify_central_mode_change` select thermostats by `device_info["model"] == DOMAIN`, not by class: any climate entity with that model (plugin climates included) receives those calls.
- Entity `unique_id` equals the config entry id; companion entities report a diagnostic category until their climate is found.
- Heating failure detection has two possible owners: the core refreshes its own manager each cycle (`async_control_heating`) only when no external manager named `heating_failure_detection` exists. `get_feature_manager` returns a core manager only when its `name` equals the key, and core managers are named after the VTherm, so `TPIHandler.control_heating` only ever sees a plugin manager: without the plugin, Auto TPI never receives a heating-failure signal (`is_heating_failure` stays false).
- `service_set_tpi_parameters` updates the config entry without `skip_reload_on_config_update`, so the entry reloads during the service call (Auto TPI sets the flag).
- `FeatureSafetyManager.refresh_state` never sets safety for `over_climate` (`should_climate_be_in_safety` stays false) although the state manager has a branch for it.

## Configuration

- `translations/en.json` is the only translation source (there is no separate strings file). A config step must be added under both `config.step` and `options.step`.
- `clean_central_config_doublon` deletes from a thermostat using a central group every key of the matching `STEP_CENTRAL_*` schema. A new inheritable option must be in that schema; an option that must stay local needs `excluded_keys` (as `CONF_POWER_UNIT`).
- Heating failure detection has a "use central" flag and a specific step but is absent from `_init_central_config_flags` and `clean_central_config_doublon`.
- `merge_user_input` removes any key of the submitted schema left out by the user: an `Optional` field with a `default` can never be cleared, and a key shared by a step and its `spec_*` variant is dropped when the active schema lacks it.
- `async_migrate_entry` runs cumulative `if version <= N` blocks (major * 100 + minor). A bump needs a new block, a raised `CONFIG_MINOR_VERSION` and the version assertion in `tests/test_migration.py` updated. A stored version newer than the code is not guarded.

## Attributes and diagnostics

- `documentation/en/base-attributes.md` documents configuration fields, not state attributes. State attributes are in the reference doc and in `BaseThermostat.update_custom_attributes`.
- Feature managers publish their sections only when the feature is configured: a missing section in `specific_states` is not a bug.
- Attributes of external feature managers are collected with `getattr(manager, "add_custom_attributes", None)` in `BaseThermostat.update_custom_attributes`; the method is not part of the `vtherm_api` interface, so a misspelled method in a plugin fails silently.

## Tests

- Never run pytest with `-p no:logging`: many tests use `caplog`.
- Tests that start cycles or timers need `expected_lingering_tasks` / `expected_lingering_timers` parametrized to true.
- The VTherm API singleton is reset after every test (`isolate_singleton_state`); CI runs tests in parallel with a short per-test timeout, so tests must not depend on order or wall-clock time.
- The tests import `pytest_homeassistant`; install exactly from `requirements_test.txt`, not a differently named Home Assistant test package.

## Release and CI

- The release workflow writes the release tag into `manifest.json` `version`: the tag is the shipped version.
- The formatting step of the pull-request and push workflows rewrites files instead of checking them, so it never fails on style. The test gate is `.github/workflows/testus.yaml` (full suite, `-n auto --timeout=9`, on pull requests and push to `main`); only the duplicate `tests` job of `pull.yml` is disabled.
- Nothing in CI checks translation keys or documentation parity across languages; several languages lag behind `en`.
