# Release

Only the owner publishes releases. Agents prepare and check; they never tag, push or publish.

## Version locations
- `custom_components/versatile_thermostat/manifest.json`: `version` (a plain `X.Y.Z`) and `requirements`. Also `after_dependencies`, `quality_scale`, `integration_type`.
- `hacs.json` (repository root): no integration version; holds the minimum Home Assistant version (`homeassistant`) and the packaging (`zip_release: true`, `filename: versatile_thermostat.zip`).
- No other version string exists in the code, `pyproject.toml` or `setup.cfg` (verified by grep). The release workflow overwrites `manifest.json` `version` with the release tag name inside the CI checkout, so the tag is the shipped version; keep the committed manifest value in step with it anyway.
- Tags use `X.Y.Z`; pre-releases look like `X.Y.Z.betaN` (seen in the tag list).
- Release notes: `documentation/<lang>/releases.md` (five languages, newest on top, heading `## Release X.Y`). There is no `CHANGELOG` file (verified).

## `vtherm_api` pin
- Runtime: `manifest.json` `requirements` lists `numpy`, `scipy` and `vtherm_api>=<min>`; development: `requirements_dev.txt` has `vtherm_api >= <min>`. Keep both minimums identical.
- Raise the minimum whenever the core relies on a new `vtherm_api` contract; the matching `vtherm_api` version must be published first, otherwise HA cannot install the requirement.
- Minimum Home Assistant version: `hacs.json` `homeassistant`; the development/test version is pinned in `requirements_dev.txt` (they can differ: the second is a test environment). Raise both together when the code needs a newer HA API.

## GitHub workflows (`.github/workflows/`)
- `testus.yaml` (push to `main`, pull requests): installs `requirements_test.txt`, runs `pytest -qq --timeout=9 -n auto tests` (scientific-marked tests are skipped by default). This is the test gate.
- `pull.yml` (pull requests): HACS validation and hassfest (`ignore: brands`), plus a `style` job running `black .` with `black>=24,<25` (reformats in CI, it does not use `--check`, so it never fails on formatting). Its `tests` job is disabled (`if: false`).
- `push.yml` (push to `master` and `dev`): same HACS, hassfest and black jobs. The branch names differ from `main`, so it may not trigger on the current default branch (unverified).
- `hacs.yml` (every push, pull request, daily): HACS action for category integration.
- `cron.yaml` (daily): HACS and hassfest validation.
- `release.yaml` (on a published GitHub release): sets `manifest.json` `version` to the tag, zips the integration folder as `versatile_thermostat.zip`, attaches it to the release. It runs no test.
- hassfest validates the manifest, translations and `services.yaml`; HACS validates `hacs.json`, manifest keys and repository metadata (exact rules unverified).

## Before a release (checklist)
1. Full test suite green locally (`pytest -q tests`, slow: run in the background) and on the `main` CI.
2. `manifest.json` `version` set; `vtherm_api` minimum correct in `manifest.json` and `requirements_dev.txt`; `hacs.json` HA minimum correct.
3. `translations/en.json` complete; key-diff script of `docs-i18n.md` shows no missing key for `en` and `fr`; every translation file is valid JSON.
4. `services.yaml` entries match `translations` `services` entries.
5. Documentation updated in `en`, `fr`, `de`, `cs`, `pl` (including `releases.md` with the new section in all five), README and CONTRIBUTING variants consistent, README language switch line intact.
6. Documentation describes the current state; no private context or plan references in code, docs or `.agents/`.
7. `python3 .agents/scripts/check_memory.py` passes and `.agents/context/status.md` reflects the release state.
8. Plugin-facing contracts used by released plugins were not broken (see `.agents/context/plugin-api.md`).
9. Owner creates the tag and the GitHub release; the `release.yaml` zip then appears on the release page.
