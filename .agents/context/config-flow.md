# Configuration: flow, options, central config, migrations

## Files

| File | Role |
|------|------|
| `custom_components/versatile_thermostat/config_flow.py` | Flow classes, menu, one `async_step_*` per form, validation |
| `custom_components/versatile_thermostat/config_schema.py` | One `vol.Schema` per form (`STEP_*`), plus `build_step_*_schema()` for schemas that depend on runtime data |
| `custom_components/versatile_thermostat/const.py` | `CONF_*` keys, defaults, `CONFIG_VERSION` / `CONFIG_MINOR_VERSION`, flow exceptions |
| `custom_components/versatile_thermostat/__init__.py` | `async_migrate_entry`, `update_listener` (reload on change) |
| `custom_components/versatile_thermostat/translations/*.json` | Form labels, menu labels, error texts |
| `custom_components/versatile_thermostat/base_thermostat.py` | `BaseThermostat.clean_central_config_doublon`: merge of central and own configuration |

There is no `strings.json`: `translations/en.json` is the source file and the other 12 language files are copies translated from it.

## Data model

- Everything lives in `ConfigEntry.data` (flat dict). `entry.options` is not used: the options flow rewrites `data` with `async_update_entry`.
- Keys are `CONF_*` constants whose value is a snake_case string stored in the entry. Never rename a value without a migration.
- Per-feature convention: `CONF_USE_<FEATURE>_FEATURE` enables a feature (menu entry appears), `CONF_USE_<FEATURE>_CENTRAL_CONFIG` means "take the values from the central configuration".
- Thermostat type: `CONF_THERMOSTAT_TYPE` in {`CONF_THERMOSTAT_CENTRAL_CONFIG`, `CONF_THERMOSTAT_SWITCH`, `CONF_THERMOSTAT_CLIMATE`, `CONF_THERMOSTAT_VALVE`} (`CONF_THERMOSTAT_TYPES`).
- Underlying entities are one list, `CONF_UNDERLYING_LIST` (the old `heater_entity2_id`-style keys only survive in the migration).
- Presets are stored as flat `<preset>_temp` style keys (see `STEP_PRESETS_DATA_SCHEMA`), not as a nested dict.
- `ALL_CONF` in `const.py` is not referenced by any other module (grep): do not rely on it being kept in sync.

## Flow classes (`config_flow.py`)

- `VersatileThermostatBaseConfigFlow` holds all steps, validation and merge logic; `VersatileThermostatConfigFlow` (creation, `async_create_entry(data=infos)`) and `VersatileThermostatOptionsFlowHandler` (starts from `config_entry.data.copy()`, `async_step_init` -> menu, finalize = `async_update_entry` then `async_create_entry(title=None, data=None)`) only differ by their finalize and init.
- `VERSION` / `MINOR_VERSION` of the flow come from `CONFIG_VERSION` / `CONFIG_MINOR_VERSION`, so a new entry is created at the current version and never goes through migration.
- All steps share the state dict `self._infos`; nothing is written to the entry before `finalize`.
- `__init__` calls `_init_central_config_flags` then `_init_feature_flags` on `_infos`:
  - a `CONF_USE_*_CENTRAL_CONFIG` flag is forced to `False` when no central configuration exists, `True` when the infos are empty (creation) and a central exists;
  - `CONF_USE_*_FEATURE` flags are derived (window: central flag or sensor or auto thresholds present; presence: central flag or sensor; auto start/stop only for climate; central boiler: both service keys present).
- `generic_step(step_id, schema, user_input, next_step)` is the engine of every form:
  - no `user_input`: shows the form, pre-filled by `add_suggested_values_to_schema` (suggested values, not defaults);
  - with `user_input`: `validate_input(user_input, step_id)`; known exceptions are mapped to translation error codes (`errors[field]` or `errors["base"]`); on success `merge_user_input`, `_init_central_config_flags` again, then `await next_step()`.
- `merge_user_input` removes from `_infos` every key of the schema absent from `user_input`. An `Optional` field without `default` that the user clears is therefore deleted; an `Optional` with `default=` is always refilled by voluptuous and cannot be cleared.
- `async_step_finalize` (base) deletes keys of disabled features (window, motion, power, presence, central boiler), resets their `*_CENTRAL_CONFIG` flag, resets the auto start/stop level, and removes the temporary `COMES_FROM`. A key of a new feature must be cleaned there when the feature is off, otherwise stale values reach the runtime.

## Step structure

- `async_step_user` (creation only): thermostat type; the central type is removed from the list when a central configuration already exists (a single one is allowed).
- `async_step_menu`: a hub, shown again after almost every step. `menu_options` is built from `_infos`:
  - always: `main`, `features`, `advanced`, `lock`; `type` and `humidity` unless central;
  - `tpi` when `CONF_PROP_FUNCTION == PROPORTIONAL_FUNCTION_TPI`, or central, or valve regulation selected;
  - `presets` for switch / valve / climate; `central_boiler` for central with the boiler feature;
  - `window`, `motion`, `power`, `presence`, `heating_failure_detection` when their `CONF_USE_*_FEATURE` is true;
  - `auto_start_stop` for climate without valve regulation; `valve_regulation` when `CONF_AUTO_REGULATION_MODE == CONF_AUTO_REGULATION_VALVE`; `sync_device_internal_temp` when its flag is set;
  - last entry: `finalize` if `check_config_complete`, otherwise the fake step `configuration_not_complete` (which re-shows the menu).
- The `type` and `features` forms pick their schema by thermostat type (`build_step_thermostat_switch_schema`, `build_step_thermostat_valve_schema`, `STEP_THERMOSTAT_CLIMATE`; `STEP_FEATURES_DATA_SCHEMA`, `STEP_CLIMATE_FEATURES_DATA_SCHEMA`, `STEP_CLIMATE_VALVE_FEATURES_DATA_SCHEMA`, `STEP_CENTRAL_FEATURES_DATA_SCHEMA`). Enabling a feature in `features` is what makes its menu entry appear.
- `async_step_type` for a climate not in valve regulation deletes the TPI keys from `_infos` (including `CONF_PROP_FUNCTION`).
- `check_config_complete` holds the "mandatory fields set" rules per type; a new mandatory field must be added there or the user can finalize an incomplete entry.
- `validate_input` runs entity existence checks, window auto-detection consistency, central config presence, service-call string parsing, valve-regulation cardinality and degree checks, virtual switch and lock code checks. New validation = new exception class in `const.py`, a `except` branch in `generic_step`, and an error key in the translations (`config.error` and `options.error`).

## "Use central configuration" pattern

- A central configuration is a config entry of type `CONF_THERMOSTAT_CENTRAL_CONFIG`; `VersatileThermostatAPI.find_central_configuration()` returns it.
- Inheritable groups: main, tpi, window, motion, power, presets, presence, advanced, lock, central mode (flags `CONF_USE_*_CENTRAL_CONFIG`, `CONF_USE_CENTRAL_MODE`).
- Per-VTherm form of a group (e.g. window): `STEP_WINDOW_DATA_SCHEMA` holds only the `use central` checkbox. When unchecked, `async_step_<group>` routes to `async_step_spec_<group>`, which shows the full schema under the same translation `step_id`, using `self._infos[COMES_FROM]` as a marker so that the second pass of the same step knows it comes from `spec_*`. The `next_step` of each `spec_*` differs (menu, the step itself, or the next feature step): read it before changing it.
- The central entry uses the full `STEP_CENTRAL_*` schema directly, with no checkbox.
- Runtime merge (`clean_central_config_doublon`): when a flag is true, every key of the matching `STEP_CENTRAL_*` schema is deleted from the VTherm copy, then the VTherm copy is layered over a copy of the central `data`. Consequences:
  - a new option of an inheritable group must be added to the `STEP_CENTRAL_<GROUP>_*` schema, or a stale local value would shadow the central one;
  - an option that must stay local even when the group is central needs the `excluded_keys` argument (precedent: `CONF_POWER_UNIT` for power);
  - presets are merged differently (`BaseThermostat.init_presets` reads the central entry).
- Heating failure detection has a `CONF_USE_HEATING_FAILURE_DETECTION_CENTRAL_CONFIG` flag and `spec_*` step like the others, but it is absent from `_init_central_config_flags` and from `clean_central_config_doublon` (grep); check how the manager reads its keys before extending it.
- Changing the central entry triggers `reload_all_vtherm` (see below); changing a VTherm reloads only that entry.

## Reload on change and options flow

- `async_setup_entry` registers `update_listener`. After an options flow (or any `async_update_entry`) the listener reloads the entry; for the central entry it reloads all entries (`reload_all_vtherm`). It is skipped when `api.skip_reload_on_config_update` is set (used by code that persists data programmatically).
- Code that writes to `entry.data` at runtime therefore triggers a reload unless that flag is set; do not store frequently changing values there.

## Versions and migrations

- Current version: `CONFIG_VERSION = 2`, `CONFIG_MINOR_VERSION = 5` (`const.py`). `async_migrate_entry` encodes `major*100 + minor` and applies cumulative blocks `if version <= 2xx:` in order (`<= 200`, `201`, `202`, `203`, `204`), each starting from the same `new = {**data}`, then one `async_update_entry(data=new, version, minor_version)`.
- Entries created without a version arrive as 1.1 = 101 and run every block.
- Migration only runs when the stored version differs from the current one; there is no guard for a stored version greater than the current one (a downgrade would be silently re-stamped).
- A block must be idempotent-safe: use `new.pop(key, None)`, "set only when absent" for new defaults, and read the old value from `config_entry.data`.
- Removed keys go through a block, with their names kept as literals or in a constant list (`OBSOLETE_AUTO_TPI_KEYS`), since the `CONF_*` constant is gone.
- Migration tests: `tests/test_migration.py` and `tests/test_config_flow.py` (see `.agents/workflows/testing.md`).

## Adding an option end to end

1. `const.py`: add `CONF_<NAME> = "<snake_case>"` and `DEFAULT_<NAME>`; if it is a choice, add the value constants and a list used by the selector.
2. `config_schema.py`: add the field in the right `STEP_*` schema (and in the `STEP_CENTRAL_*` one when the group is inheritable, see above). Use `vol.Required(..., default=DEFAULT)` for a field that must always have a value, `vol.Optional` without default for a clearable one. Selectors with `translation_key=` need a `selector.<key>.options.<value>` entry.
3. `config_flow.py`: usually nothing for a field in an existing step. For a new step: `async_step_<name>` calling `generic_step`, a `menu_options` condition in `async_step_menu`, a `*_FEATURE` flag in `_init_feature_flags` and a cleanup in `async_step_finalize` if it is a feature, and rules in `check_config_complete` / `validate_input` if needed.
4. `translations/en.json`: add `config.step.<step>.data.<key>` and `data_description.<key>`, and the same under `options.step.<step>` (the two trees are kept identical: same 19 steps). Menu label: `menu_options.<step>` under the `menu` step of both trees. Then mirror the keys in the other language files (`cs`, `de`, `el`, `es`, `fr`, `it`, `ja`, `pl`, `ru`, `sk`, `zh-Hans`, `zh-Hant`). Several of these files already lack steps (e.g. `el` has fewer steps than `en`); a missing key is not detected by the test suite (no consistency test found).
5. Runtime: read the value from the merged entry infos in the manager or thermostat `post_init`, with an explicit default for entries created before the option existed.
6. Migration: only when an existing entry must receive a computed value, or a key is renamed or removed: bump `CONFIG_MINOR_VERSION`, add an `if version <= <previous>` block, update the version assertion in migration tests. A plain new optional key with a runtime default needs no migration.
7. Tests: a flow test that drives the form (`tests/test_config_flow.py`) and a runtime test with a `MockConfigEntry` containing the key; migration test if step 6 applied; check central behaviour in `tests/test_central_config.py` when inheritable.
8. Docs: the matching `documentation/en/*.md` page (reference page `documentation/en/reference.md` for parameters) and its translated copies under `documentation/fr`, `cs`, `de`, `pl`.

## Durable traps

- Updating only `config.step` in a translation file leaves the options flow without labels; both trees are required.
- Some tests depend on texts of `translations/en.json` (comments in `tests/test_temp_number.py`); renaming an English label can break them.
- `merge_user_input` deletes absent keys of the submitted schema: a key that belongs to two schemas of the same step id (`X` and `spec_X`) is removed when the active schema does not contain it.
- Adding a key to a `STEP_CENTRAL_*` schema also changes which keys are stripped from every VTherm using the central group: existing VTherm copies of that key stop being used.
- `async_step_menu` is rebuilt from `_infos` at each display; a feature flag set late (after `features`) only shows up at the next menu display.
- The flow state `COMES_FROM` is only a transient marker; it is deleted in `_init_central_config_flags` and in finalize and must never be persisted.
- The options flow edits a copy of the data; closing the dialog without `finalize` discards all changes.
