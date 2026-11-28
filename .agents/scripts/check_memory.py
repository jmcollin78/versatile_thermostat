#!/usr/bin/env python3
"""Consistency check of the shared agent memory (standard library only).

Run from anywhere:  python3 .agents/scripts/check_memory.py
Exit code 1 when a hard problem is found. Checks:
  - backticked repo paths and `path::Symbol` references still exist
  - UPPER_SNAKE constants quoted in the memory exist in the code
  - size budgets of AGENTS.md and the context files (warnings)
  - private or install-specific content: emails, URLs, IPs, secrets, entity ids,
    absolute machine paths, issue / pull-request / plan references,
    plus an optional local blocklist (env VT_MEMORY_BLOCKLIST or .agents/.local-blocklist,
    one case-insensitive word per line, never versioned)
  - the short-term tier `.agents/local/` is not tracked by git; stale task folders (warning)
  - Claude, Codex and Copilot vt-* agent profiles parse, mirror each other and agree on read-only status
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / ".agents"
LOCAL_DIR = AGENTS_DIR / "local"
PKG = ROOT / "custom_components" / "versatile_thermostat"
SEARCH_BASES = [ROOT, PKG, AGENTS_DIR, AGENTS_DIR / "context", AGENTS_DIR / "workflows", ROOT / "tests",
                PKG / "translations", ROOT / ".github" / "workflows"]
# Files of the local task folders (short-term tier): named in procedures, absent from the repository.
LOCAL_TASK_FILES = {"plan.md", "notes.md", "handoff.md"}

# Line budgets per context file (see .agents/README.md); other context files use the default.
CONTEXT_BUDGETS = {"principles.md": 80, "project.md": 80, "pitfalls.md": 150, "decisions.md": 150, "status.md": 60}
DEFAULT_CONTEXT_BUDGET = 300
MAX_AGENTS_BYTES = 12_000
STALE_TASK_DAYS = 30

# Paths of the separate vtherm_api repository or of plugins: not resolvable here.
EXTERNAL_PREFIXES = ("vtherm_api/", "src/vtherm_api/", "vtherm_api.py", "interfaces.py", "plugin_climate.py",
                     "setpoint_modifier.py", "underlying_hooks.py", "command_receipt.py", "inhibition.py",
                     "log_collector.py", "calibration_modifier.py", "valve_write.py", "ui_plugin.py",
                     "factory.py", "handler.py")
# A line stating that a file does not exist is not a broken reference.
ABSENCE = re.compile(r"(\bno `|does not exist|not exist|is absent)", re.I)
# Headings of sections that list names which intentionally do not exist.
SKIP_HEADING = re.compile(r"(do not exist|removed|rejected)", re.I)
PATHLIKE = re.compile(r"^[\w./-]+\.(py|md|json|toml|yaml|yml|txt|cfg|ini)(::[\w.]+)?$")
CONST = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
PRIVACY = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "url": re.compile(r"https?://"),
    "ipv4": re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    "hex-secret": re.compile(r"\b[0-9a-f]{32,}\b"),
    "machine-path": re.compile(r"(?:^|[\s`(])(?:/home/|/workspaces?/|/Users/|/tmp/|[A-Za-z]:\\)"),
    "issue-or-pr-reference": re.compile(r"(?:#\d{3,}\b|\bissue[-_ ]?\d{3,}|\bPR ?\d{3,})", re.I),
    "plan-file-reference": re.compile(r"\bplans/[\w.-]+"),
    "entity-id": re.compile(
        r"\b(?:climate|sensor|binary_sensor|switch|number|select|light|input_[a-z]+|automation)\.[a-z0-9_]{3,}\b"
    ),
}
# Entity-id-looking strings that are generic placeholders, not real entities.
ENTITY_ALLOW = re.compile(r"\b(?:sensor|climate|switch|number|select|binary_sensor)\.(?:thermostat|name|entity|example|my_\w+|mock_\w+|set_\w+|turn_\w+|room\w*|heater\w*|valve\w*|vtherm\w*)\b")

errors: list[str] = []
warnings: list[str] = []
_code: str | None = None


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def memory_files() -> list[Path]:
    """Versioned markdown files of the memory; the local tier is excluded."""
    files = [ROOT / "AGENTS.md", ROOT / "CLAUDE.md", *sorted(AGENTS_DIR.rglob("*.md"))]
    return [f for f in files if f.exists() and LOCAL_DIR not in f.parents]


def code_text() -> str:
    global _code
    if _code is None:
        sources = [*PKG.rglob("*.py"), *(ROOT / "tests").rglob("*.py"), *(AGENTS_DIR / "scripts").glob("*.py")]
        _code = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in sources)
    return _code


def blocklist() -> list[str]:
    path = os.environ.get("VT_MEMORY_BLOCKLIST") or str(AGENTS_DIR / ".local-blocklist")
    try:
        return [w.strip().lower() for w in Path(path).read_text(encoding="utf-8").splitlines() if w.strip()]
    except OSError:
        return []


def resolve(token: str, md: Path) -> Path | None:
    for base in [md.parent, *SEARCH_BASES]:
        candidate = (base / token).resolve()
        if candidate.exists():
            return candidate
    if "/" not in token:  # bare file name: look it up in the main folders
        for folder in (PKG, ROOT / "tests", ROOT / "documentation", AGENTS_DIR):
            for candidate in folder.rglob(token):
                if "__pycache__" not in candidate.parts:
                    return candidate
    return None


def backticked(md: Path):
    """Yield (line number, token) for backticked tokens outside skipped sections."""
    skipping = False
    for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("#"):
            skipping = bool(SKIP_HEADING.search(line))
        if not skipping:
            if ABSENCE.search(line):
                continue
            for token in re.findall(r"`([^`]+)`", line):
                yield number, token


def check_refs(md: Path) -> None:
    for number, token in backticked(md):
        if any(c in token for c in "<>*{}$ ()=,|") or "..." in token or token.startswith(("-", "/")):
            continue
        if not PATHLIKE.match(token):
            continue
        path, _, symbol = token.partition("::")
        if path.startswith(EXTERNAL_PREFIXES) or path in LOCAL_TASK_FILES:
            continue
        target = resolve(path, md)
        if target is None:
            errors.append(f"{rel(md)}:{number}: missing path `{token}`")
        elif symbol and target.is_file():
            name = symbol.split(".")[-1]
            candidates = list(PKG.rglob(path)) if "/" not in path else [target]
            if not any(re.search(rf"\b{re.escape(name)}\b", c.read_text(encoding="utf-8", errors="ignore")) for c in candidates):
                errors.append(f"{rel(md)}:{number}: symbol `{token}` not found in file")


def check_constants(md: Path) -> None:
    for number, token in backticked(md):
        if CONST.match(token) and not re.search(rf"\b{re.escape(token)}\b", code_text()):
            warnings.append(f"{rel(md)}:{number}: constant `{token}` not found in VT code (external package?)")


def check_privacy(path: Path) -> None:
    words = blocklist()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for label, rx in PRIVACY.items():
            match = rx.search(line)
            if match and not (label == "entity-id" and ENTITY_ALLOW.search(match.group(0))):
                errors.append(f"{rel(path)}:{number}: private or install-specific content ({label})")
        low = line.lower()
        if any(word in low for word in words):
            errors.append(f"{rel(path)}:{number}: blocklisted word")


def check_sizes() -> None:
    agents = ROOT / "AGENTS.md"
    if agents.stat().st_size > MAX_AGENTS_BYTES:
        warnings.append(f"AGENTS.md is {agents.stat().st_size} bytes (budget {MAX_AGENTS_BYTES})")
    for md in sorted((AGENTS_DIR / "context").glob("*.md")):
        lines = len(md.read_text(encoding="utf-8").splitlines())
        budget = CONTEXT_BUDGETS.get(md.name, DEFAULT_CONTEXT_BUDGET)
        if lines > budget:
            warnings.append(f"{rel(md)} has {lines} lines (budget {budget}): prune or split")


def check_local_tier() -> None:
    try:
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", ".agents/local"],
                                 capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tracked = []
    for path in tracked:
        errors.append(f"{path}: short-term memory must not be tracked by git")
    tasks = LOCAL_DIR / "tasks"
    if tasks.is_dir():
        limit = time.time() - STALE_TASK_DAYS * 86400
        for folder in sorted(p for p in tasks.iterdir() if p.is_dir()):
            newest = max((f.stat().st_mtime for f in folder.rglob("*") if f.is_file()), default=folder.stat().st_mtime)
            if newest < limit:
                warnings.append(f"task folder `{folder.name}` untouched for {STALE_TASK_DAYS}+ days: promote and delete")


def check_profiles() -> None:
    claude_dir, codex_dir = ROOT / ".claude" / "agents", ROOT / ".codex" / "agents"
    claude = {p.stem for p in claude_dir.glob("*.md")}
    codex = {p.stem for p in codex_dir.glob("*.toml")}
    for name in sorted(claude ^ codex):
        errors.append(f"agent profile `{name}` exists for only one of Claude/Codex")
    for name in sorted(claude & codex):
        try:
            text = (claude_dir / f"{name}.md").read_text(encoding="utf-8")
            front = dict(l.split(": ", 1) for l in text.split("---")[1].strip().splitlines() if ": " in l)
            cx = tomllib.loads((codex_dir / f"{name}.toml").read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - any parse failure is reported
            errors.append(f"agent profile `{name}` does not parse: {exc}")
            continue
        for key in ("name", "description", "model", "effort"):
            if key not in front:
                errors.append(f"Claude profile `{name}` lacks `{key}`")
        for key in ("name", "description", "model", "model_reasoning_effort", "developer_instructions"):
            if key not in cx:
                errors.append(f"Codex profile `{name}` lacks `{key}`")
        if front.get("name") != name or cx.get("name") != name:
            errors.append(f"agent profile `{name}`: name differs from file name")
        if ("Edit" not in front.get("tools", "")) != ("read-only" in cx.get("developer_instructions", "")):
            errors.append(f"agent profile `{name}`: read-only status differs between Claude and Codex")
        body = text.split("---", 2)[2].strip()
        if body != cx.get("developer_instructions", "").strip():
            errors.append(f"agent profile `{name}`: instructions differ between Claude and Codex")


def check_copilot_profiles() -> None:
    """Generated Copilot vt-* profiles must carry the same instructions as the Claude ones."""
    claude_dir, copilot_dir = ROOT / ".claude" / "agents", ROOT / ".github" / "agents"
    for claude in sorted(claude_dir.glob("*.md")):
        copilot = copilot_dir / f"{claude.stem}.agent.md"
        if not copilot.exists():
            errors.append(f"Copilot profile `{copilot.name}` missing: run .agents/scripts/gen_profiles.py")
            continue
        claude_text, copilot_text = claude.read_text(encoding="utf-8"), copilot.read_text(encoding="utf-8")
        if claude_text.split("---", 2)[2].strip() != copilot_text.split("---", 2)[2].strip():
            errors.append(f"Copilot profile `{copilot.name}`: instructions differ from the Claude profile")
        front = copilot_text.split("---", 2)[1]
        if ("'edit'" in front) == ("read-only" in copilot_text):
            errors.append(f"Copilot profile `{copilot.name}`: read-only status differs from its tools")


def main() -> int:
    for md in memory_files():
        check_refs(md)
        check_constants(md)
        check_privacy(md)
    for profile in [*(ROOT / ".claude" / "agents").glob("*.md"), *(ROOT / ".codex" / "agents").glob("*.toml")]:
        check_privacy(profile)
    check_sizes()
    check_local_tier()
    check_profiles()
    check_copilot_profiles()
    for message in warnings:
        print("WARN ", message)
    for message in errors:
        print("ERROR", message)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
