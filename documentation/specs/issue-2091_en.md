# Functional Specification — Issue #2091

## 1. Title and metadata

- **Name:** Polish translation placeholder correction
- **Version:** 2.1
- **Status:** Proposed
- **Date:** 2026-10-10
- **Owner:** Versatile Thermostat project
- **Issue:** [#2091 — Translation error](https://github.com/jmcollin78/versatile_thermostat/issues/2091)
- **Reviewed report:** [issue-2091-review.md](../tech-docs/issue-2091-review.md)
- **Sources:** [strings.json](../../custom_components/versatile_thermostat/strings.json), [pl.json](../../custom_components/versatile_thermostat/translations/pl.json), [config_flow.py](../../custom_components/versatile_thermostat/config_flow.py)

## 2. Context and objectives

Home Assistant reports two placeholder inconsistencies in the Polish translation of the options interface. These inconsistencies may produce validation errors and prevent the expected dynamic display.

The objective is to make the two Polish strings conform to the reference placeholders without changing thermostat behavior or other locales.

## 3. Actors and use cases

### Actors

- **Polish-speaking user:** views or edits thermostat options.
- **Home Assistant:** loads translations and validates their placeholders.
- **Maintainer:** verifies the correction before integration.

### Nominal use case

1. Home Assistant loads the Polish translation.
2. The options interface provides the dynamic `unit` and `name` values.
3. The Polish strings use these placeholders.
4. Translation validation completes without the two issue errors.

## 4. Functional requirements

- **FR-001 — Unit placeholder:** The system shall preserve the `{unit}` placeholder in `pl.json` at `options.step.auto_tpi_configuration.data.auto_tpi_heating_rate`.
- **FR-002 — Name placeholder:** The system shall preserve the `{name}` placeholder in `pl.json` at `options.step.heating_failure_detection.title`.
- **FR-003 — Text preservation:** The correction shall preserve the existing Polish text as far as possible and change only the required placeholders.
- **FR-004 — File scope:** The correction shall be limited to the affected Polish translation, except for documentation or tests explicitly required for validation.
- **FR-005 — No regression:** The correction shall not change thermostat control logic, the configuration flow, or user configuration values.

## 5. Business rules

- **BR-001 — Placeholder contract:** Each translation shall preserve the placeholders expected by its corresponding reference string.
- **BR-002 — Dynamic unit:** The displayed unit shall come from `{unit}` and shall not be imposed by a fixed textual value in this string.
- **BR-003 — Configuration name:** The heating-failure title shall be able to display the name supplied through `{name}`.
- **BR-004 — Related locales:** The discrepancies found in `el`, `ru`, and `sk` are outside issue #2091 and shall not be corrected within this scope.

## 6. Functional constraints

- The existing JSON structure shall remain valid.
- Translation keys shall remain unchanged.
- The correction shall be compatible with units and names injected by Home Assistant.
- CI Hassfest validation shall be able to check the placeholders.
- No personal data, permission, or Home Assistant service shall be added or changed.

## 7. Acceptance criteria

- **AC-001:** The Polish `auto_tpi_heating_rate` string contains exactly the `{unit}` placeholder expected by the reference.
- **AC-002:** The Polish `heating_failure_detection.title` string contains exactly the `{name}` placeholder expected by the reference.
- **AC-003:** `pl.json` remains valid JSON and retains its keys and structure.
- **AC-004:** Hassfest no longer reports the two validation messages from the issue.
- **AC-005:** Placeholder values are not hard-coded in the corrected strings.
- **AC-006:** No code file, other locale, or user configuration is changed by the functional correction.

## 8. Functions not covered

- General linguistic correction of the Polish translation.
- Correction of the `el`, `ru`, and `sk` discrepancies identified in the report.
- Complete audit or harmonization of all translations.
- Modification of `strings.json`, `config_flow.py`, or business logic.
- Modification of initial-configuration translations outside the two affected `options` paths.

## 9. Proposed future enhancements

- Add automated placeholder checks for all locales before submission.
- Open a separate issue for the incomplete `el`, `ru`, and `sk` translations.
- Document the local JSON and Hassfest validation procedure.

## 10. Assumptions, open questions, and traceability

### Assumptions

- `unit` and `name` are available when Home Assistant renders the affected options steps, as stated in the report.
- Correcting the two strings is sufficient to resolve the two reported errors.

### Open questions

- The exact desired Polish wording is not specified; the existing text shall be preserved as far as possible.
- Hassfest validation has not yet been executed for this specification.

### Traceability

- **Issue:** #2091.
- **Report:** [issue-2091-review.md](../tech-docs/issue-2091-review.md).
- **Placeholder reference:** [strings.json](../../custom_components/versatile_thermostat/strings.json).
- **Affected translation:** [pl.json](../../custom_components/versatile_thermostat/translations/pl.json).

## Extension 2.0 — `auto_tpi_cooling_rate`

### Scope and verified finding

The extension shall add `auto_tpi_cooling_rate` to the `strings.json` reference and to all ten `translations/*.json` files, under `config.step.auto_tpi_configuration` and `options.step.auto_tpi_configuration`, in both `data` and `data_description`. The implementation scope is strictly limited to this key, its four reference leaves, and its four leaves per locale; no other path shall be modified.

Verified finding in the actual files: `strings.json` does not define the key; `cs.json` contains only the two `config` leaves (label and description), while `fr.json` contains only the two `options` leaves; `pl.json` contains only `options.data`; `de.json`, `en.json`, `it.json`, and `zh-Hans.json` have the sections but not the key; `el.json`, `ru.json`, and `sk.json` do not have the `auto_tpi_configuration` section. The previous audit was therefore wrong about `cs` and `fr`: they are partial, not complete. Existing occurrences shall remain unchanged.

### Functional requirements

- **FR-006:** Each present locale shall contain the key at the four exact paths: `config...data`, `config...data_description`, `options...data`, and `options...data_description`.
- **FR-007:** Every existing occurrence shall preserve its exact value, punctuation, and placeholders.
- **FR-008:** Each `data` value shall be localized wording containing `{unit}`; each `data_description` value shall be localized wording containing `{unit}` and describing zero-value behavior when retained by the reference.
- **FR-009:** Text shall not be invented when it is not determinable. It shall be marked “to be defined by design” before implementation.
- **FR-010:** The implementation shall modify `strings.json` to define the four `auto_tpi_cooling_rate` reference leaves, and shall not modify code, configuration, dependencies, or any other `strings.json` key.

### Business rules and constraints

- **BR-006:** All four paths are mandatory; a key in one context is insufficient.
- **BR-007:** The dynamic placeholder shall be exactly `{unit}`; a hard-coded unit does not replace it.
- **BR-008:** The missing key in `strings.json` shall be resolved by explicitly defining the four canonical references; it is not permission to silently invent translations.
- **BR-009:** Other `el`, `ru`, `sk`, and `pl` discrepancies remain out of scope unless explicitly decided.

The ten currently inventoried files (`cs`, `de`, `el`, `en`, `fr`, `it`, `pl`, `ru`, `sk`, `zh-Hans`) are concerned. Every file shall remain valid JSON; JSON validity is not linguistic validation.

### Localized values and acceptance criteria

Existing wording in `cs` (the `config` side) and `fr` (the `options` side) is the localized wording directly determinable from inspected sources; it shall be preserved. Missing values for `cs`, `fr`, `de`, `en`, `it`, `pl`, `zh-Hans`, `el`, `ru`, and `sk` are **to be defined by design/translation**; no assumed value shall be specified. The four English references shall be defined in `strings.json` according to the approved design.

- **AC-007:** Every present file is inventoried and contains the four paths.
- **AC-008:** Every `data.auto_tpi_cooling_rate` value contains `{unit}` exactly once, unless documented otherwise.
- **AC-009:** Every `data_description.auto_tpi_cooling_rate` value contains `{unit}` exactly once, unless documented otherwise.
- **AC-010:** Before/after comparison proves that no existing occurrence changed, including the two `config` leaves in `cs`, the two `options` leaves in `fr`, and `options.data` in `pl`.
- **AC-011:** A JSON parser and Hassfest validate the files and placeholders.
- **AC-012:** A competent linguistic review is recommended for every new translation, but it is non-blocking; the localized values proposed by the design constitute the authorized implementation basis.

### Exclusions, future work, questions, and risks

Excluded: changing any `strings.json` content other than the four `auto_tpi_cooling_rate` leaves, rewriting existing translations, automatically correcting other discrepancies, or changing the Auto TPI flow. Possible future work includes automating path parity and tracking partial translations separately.

Non-blocking question: is an additional linguistic review of the proposed wordings desired? Should other discrepancies be handled separately?

Partial translations may make configuration and options inconsistent, trigger Hassfest, or display an incorrect unit. Wording may still be improved linguistically; review is therefore recommended as a risk-control measure, while JSON, structural, `{unit}`, and Hassfest validations remain mandatory. The values proposed by the design are authorized for implementation.

### Convergence with the design

This version converges with design 2.1: `strings.json` is explicitly included for the four references, the ten locales and four paths per locale remain in scope, `cs` and `fr` are described as partial according to the actual audit, and existing occurrences—including `pl.options.data`—remain preserved. JSON, structural, placeholder, and Hassfest validations remain mandatory. Linguistic review is recommended but non-blocking; the localized values proposed by the design constitute the authorized implementation basis. No blocking divergence remains.
