# Project facts

## Identity

- Home Assistant custom integration, domain `versatile_thermostat`, distributed through HACS as a zip release (`hacs.json`).
- Version in `custom_components/versatile_thermostat/manifest.json` (`version`); minimum Home Assistant version in `hacs.json` (`homeassistant`); development Home Assistant version pinned in `requirements_dev.txt`.
- Python requirements of the integration in `manifest.json` (`requirements`): `numpy`, `scipy` and the `vtherm_api` package with a minimum version.
- The dev container (`.devcontainer/`) runs a Home Assistant instance with sample configuration for manual tests; `scripts/` holds helper scripts.
- Default branch `main`. Contributions arrive as pull requests from forks; `CONTRIBUTING*.md` describes the contributor workflow.

## Thermostat types

- `over_switch`: drives on/off switches with a proportional algorithm (TPI or a plugin algorithm) over a cycle.
- `over_valve`: drives valve opening numbers with a proportional algorithm.
- `over_climate`: drives other climate entities (setpoint, mode, fan, optional direct valve control and self-regulation).
- Central configuration: one shared configuration entry whose values other thermostats may inherit.
Details in `architecture.md` and `config-flow.md`.

## Plugin ecosystem

- The `vtherm_api` package (separate repository, published on PyPI) holds the contracts between VT and its plugins: proportional algorithms, feature managers, setpoint modifiers, underlying command hooks, inhibition, log collection, plugin climates. See `plugin-api.md`.
- Plugins are independent Home Assistant integrations that register with VT through `vtherm_api`. Public examples: algorithm plugins (an advanced PI controller with a learned room model, a hysteresis algorithm), dashboard cards, schedulers. The project website keeps a plugins catalog; the user docs link to it (`documentation/<lang>/additions.md`, `algorithms.md`).
- Direction: features with a clear boundary move from the core into plugins; the core keeps generic contracts. Roadmap in `status.md`.

## Languages

- User documentation: `documentation/<lang>/` for `en`, `fr`, `de`, `cs`, `pl`; `README*.md` and `CONTRIBUTING*.md` in the same languages.
- UI translations: `custom_components/versatile_thermostat/translations/*.json` (13 languages).
- Code, comments, docstrings, commit messages and this memory: English.
- Procedures: `workflows/docs-i18n.md`.

## Other repository folders

- `documentation/tech-docs/`, `documentation/specs/`: historical technical design records written per topic. Not maintained as current truth; verify against the code before relying on one.
- `plans/`: maintainers' working plans. Not agent memory; never cite them in code, docs or `.agents/`.
- `.github/agents/`: Copilot agent profiles; `.github/copilot-instructions.md` points to `AGENTS.md`.
