# Documentation and translations

## Documentation layout
- `documentation/<lang>/`: user documentation, one folder per language: `en`, `fr`, `de`, `cs`, `pl`. Same file names in each (feature pages `feature-*.md`, `over-*.md`, `reference.md`, `troubleshooting.md`, `releases.md`, `images/`, ...); some languages lag and lack pages that exist in `en` (compare with `ls documentation/en` against the other folders, or `diff -rq`).
- Source language: no single declared source (unverified). English is the most complete folder and the reference for parity checks. The project authors in French or English and the translation agent profile in `.github/agents/` translates French to English. Write or update English and French together, then propagate to `de`, `cs`, `pl`.
- `README.md`, `CONTRIBUTING.md` (English) and `README-<lang>.md`, `CONTRIBUTING-<lang>.md` for `fr`, `de`, `cs`, `pl`. Each README carries a language switch line near the top listing all five READMEs; keep it identical in every language.
- `documentation/tech-docs/`: per-topic technical notes (architecture, design, specification and review records, some with `-fr`/`_fr` twins). Historical design records, often in French or both languages; not user docs, not translated systematically. Read one only when the task is about its topic.
- `documentation/specs/`: per-topic specification files (`_en`/`_fr` pairs for most). Same status as tech-docs.
- Release notes: `documentation/<lang>/releases.md`, newest release first, `## Release X.Y` headings (localised word in `cs`, `pl`).

## Rules for documentation
- Describe the current state only, as if the product were never published before: no "new", "now", "fixed", "changed", "since version" wording outside `releases.md`.
- A user-visible change updates all five language folders (and README/CONTRIBUTING of every language if they are affected), plus `releases.md` when the change is release-worthy.
- When translating: keep markdown structure unchanged; do not translate code, identifiers, entity ids, action and attribute names, YAML keys, commands, file names, HTML tags or proper names; translate prose, table headers and comments inside YAML examples. Image links keep the same file names (images live in each language's `images/`).
- No private context: no plan or review references, issue numbers in new prose, personal names, machine paths.
- Anchors: links such as `troubleshooting.md#heading` break when a heading is translated differently; check intra-doc anchors in the target language.

## Translations of the UI (`custom_components/versatile_thermostat/translations/`)
- Files: `en`, `fr`, `de`, `cs`, `pl`, `es`, `it`, `ja`, `ru`, `sk`, `el`, `zh-Hans`, `zh-Hant`.
- Source: `en.json` (no `strings.json` exists). Top-level sections: `title`, `config`, `options`, `selector`, `entity`, `services`, `exceptions`, `issues`.
- Keys must exist in every language with the same structure; `config` and `options` often duplicate the same step texts, update both. A key added, renamed or removed in `en.json` must be applied in all other files; placeholders (`{name}`) and `\n` must be preserved.
- State when verified: not all languages are complete (several have missing keys, some have extra obsolete keys). `en` is complete by definition; `de`, `es`, `ja`, `zh-Hant` are nearly complete, `fr` and `cs` have some gaps, `el`, `sk`, `ru`, `pl` lag most. Do not make a lagging language worse; add missing keys when touching a section.
- Do not translate: entity ids, service/action names, option values used by code, YAML snippets, `{placeholders}`.
- Check missing/extra keys against `en.json` (run from the repository root):

```bash
python3 - <<'EOF'
import json, glob
def flat(d, p=""):
    out = {}
    for k, v in d.items():
        out.update(flat(v, p + k + ".") if isinstance(v, dict) else {p + k: v})
    return out
base = set(flat(json.load(open("custom_components/versatile_thermostat/translations/en.json"))))
for f in sorted(glob.glob("custom_components/versatile_thermostat/translations/*.json")):
    keys = set(flat(json.load(open(f))))
    print(f.split("/")[-1], "missing", len(base - keys), "extra", len(keys - base))
    for k in sorted(base - keys): print("   -", k)
EOF
```

- Also verify JSON validity of every edited file (the script fails on invalid JSON).
- Services: action fields documented in `services.yaml` must have matching `services` entries in the translation files.
- No automated test or workflow checks translations or documentation parity (verified: none in `tests/` or `.github/workflows/`); hassfest validates only the structure of `translations/en.json`-style files (unverified in detail).

## Checklist after a user-visible change
1. `en.json` and every other translation updated (or consciously left lagging, stated in the report).
2. `documentation/en` and the four other languages updated; `releases.md` if relevant.
3. README/CONTRIBUTING language variants if they mention the changed behaviour.
4. Key-diff script above run; no new missing key in `en`/`fr`.
