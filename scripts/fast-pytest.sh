#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="${ROOT_DIR}/.venv/bin"

# Disable auto-loading of every installed pytest plugin; load only what we need.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

PLUGINS=(
  -p xdist.plugin
  -p pytest_homeassistant_custom_component.plugins
  -p pytest_asyncio.plugin
  -p pytest_socket
)

PYTEST_ARGS=()
if [[ " $* " != *" -n "* ]]; then
  PYTEST_ARGS+=(-n auto --dist loadfile)
fi

"${VENV_BIN}/python" -m pytest "${PYTEST_ARGS[@]}" "${PLUGINS[@]}" "$@"
