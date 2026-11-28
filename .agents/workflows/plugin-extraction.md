# Moving a feature into a plugin

Use this procedure for a new feature that does not need the core, and for an existing core feature with a clear boundary. Contracts and runtime surface: `context/plugin-api.md`. Candidates and progress: `context/status.md`.

## 1. Decide

A feature is a good plugin candidate when:
- it reads thermostat state and acts through a few well-defined points (setpoint, command, underlying calls, attributes, events);
- most users do not need it, or several implementations of it make sense;
- its code is mostly self-contained (one manager, its constants, its config step).

It should stay in the core when it is part of the safety of the thermostat or when every thermostat type needs it to work at all. Write the answer in the task plan.

## 2. Design the contract first

- List every access the feature makes to the core (grep the manager for `self._vtherm.`, private attributes, imports of core modules).
- Map each access to an existing `vtherm_api` interface member. For each missing one, design a generic addition: named for what it does, usable by other plugins, typed, documented.
- Contract changes are additive and backward compatible; bump the `vtherm_api` version and the minimum version in VT `manifest.json` together.
- Never pass private core objects across the boundary.

## 3. Implement in order

1. `vtherm_api`: the contract additions with their tests.
2. VT core: implement the new runtime members and hooks generically, with tests that use a fake plugin.
3. Plugin: an independent integration that registers through `vtherm_api` and depends only on it. Same behaviour, events and entities as the core feature when it replaces one.
4. VT core cleanup: remove the feature's manager, constants, config steps, translations, docs sections and tests. Add a migration or a repair issue so existing users are told how to keep the feature.

## 4. Verify

- Core test suite passes without the plugin installed.
- Plugin tests cover the old behaviour (port the relevant core tests).
- No import of a private VT module anywhere in the plugin.
- Docs: the core docs describe the plugin as an add-on; translations updated.
- Record the contract additions in `context/plugin-api.md` and the outcome in `context/status.md` and `context/decisions.md`.
