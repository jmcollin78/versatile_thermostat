"""Fail-closed isolation for this directory only, before creating hass."""

# pylint: disable=protected-access,redefined-outer-name,unused-argument

from pathlib import Path

import pytest
import custom_components
from homeassistant import loader
from homeassistant.config_entries import ConfigEntries

from .run_isolated import assert_network_barrier
from .bench import DEVICE_ID, ROOM_ID, EXTERNAL_ID


# No remote/cloud integration is allowed to be loaded, even if a test changes.
LOCAL_DOMAINS = frozenset({
    "homeassistant", "versatile_thermostat", "climate", "sensor",
    "binary_sensor", "switch", "number", "select", "button", "update",
    "persistent_notification", "recorder", "http", "system_log", "logger",
})


@pytest.fixture
def isolation_guard(monkeypatch):
    """Verify syscalls and guard integration loading before hass is constructed."""
    assert_network_barrier()
    original_component = loader.Integration.async_get_component
    original_platform = loader.Integration.async_get_platform
    original_setup = ConfigEntries.async_setup
    original_resolve = loader._resolve_integrations_from_root

    def resolve(hass, root, domains):
        domains = list(domains)
        if not set(domains) <= LOCAL_DOMAINS:
            raise RuntimeError(f"integration resolution outside allowlist: {set(domains) - LOCAL_DOMAINS}")
        return original_resolve(hass, root, domains)

    async def component(integration):
        if integration.domain not in LOCAL_DOMAINS:
            raise RuntimeError(f"integration outside isolated allowlist: {integration.domain}")
        return await original_component(integration)

    async def platform(integration, name):
        if integration.domain not in LOCAL_DOMAINS:
            raise RuntimeError(f"platform outside isolated allowlist: {integration.domain}")
        return await original_platform(integration, name)

    async def setup(entries, entry_id):
        entry = entries.async_get_entry(entry_id)
        if entry is None or entry.domain != "versatile_thermostat":
            raise RuntimeError("only the fictitious VTherm config entry is allowed")
        if (entry.data.get("underlying_entity_ids") != [DEVICE_ID]
                or entry.data.get("temperature_sensor_entity_id") != ROOM_ID
                or entry.data.get("external_temperature_sensor_entity_id") != EXTERNAL_ID):
            raise RuntimeError("entry must reference only the fictitious test entities")
        return await original_setup(entries, entry_id)

    monkeypatch.setattr(loader.Integration, "async_get_component", component)
    monkeypatch.setattr(loader.Integration, "async_get_platform", platform)
    monkeypatch.setattr(loader, "_resolve_integrations_from_root", resolve)
    monkeypatch.setattr(ConfigEntries, "async_setup", setup)


@pytest.fixture
def hass_config_dir(tmp_path, isolation_guard):
    """An empty, per-test directory, never the workspace or live HA config."""
    root = tmp_path.resolve()
    if not root.is_relative_to(Path("/tmp").resolve()):
        raise RuntimeError("test directory must be under /tmp")
    config = root / "empty_hass_config"
    config.mkdir()
    assert not list(config.iterdir())
    return str(config)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass, isolation_guard, hass_config_dir):
    """Override the repository-wide fixture that enables all custom integrations."""
    assert Path(hass.config.config_dir).resolve() == Path(hass_config_dir).resolve()
    assert not hass.config_entries.async_entries()
    integration = loader.Integration.resolve_from_root(hass, custom_components, "versatile_thermostat")
    assert integration is not None
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {"versatile_thermostat": integration}
    yield
    assert set(hass.data[loader.DATA_CUSTOM_COMPONENTS]) == {"versatile_thermostat"}