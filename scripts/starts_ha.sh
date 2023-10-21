#!/bin/bash

set -e
set -x

cd "$(dirname "$0")/.."
pwd

# Create config dir if not present
if [[ ! -d "${PWD}/config" ]]; then
    mkdir -p "${PWD}/config"
    # Add defaults configuration
    hass --config "${PWD}/config" --script ensure_config
    # Overwrite configuration.yaml if provided
    if [ -f ${PWD}/.devcontainer/configuration.yaml ]; then
        rm -f ${PWD}/config/configuration.yaml
        ln -s ${PWD}/.devcontainer/configuration.yaml ${PWD}/config/configuration.yaml
    fi
fi

# Set the path to custom_components
## This let's us have the structure we want <root>/custom_components/integration_blueprint
## while at the same time have Home Assistant configuration inside <root>/config
## without resulting to symlinks.
export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"

# Start Home Assistant
hass --config "${PWD}/config" --debug