"""Shared accessors for the plugin registries stored in ``hass.data``.

These helpers give the manager and the entity platforms a single, decoupled
place to publish and read the live managers, the ``async_add_entities``
callbacks and the created entities, keyed by VTherm ``unique_id``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .const import (
    DATA_ADD_ENTITIES,
    DATA_ENTITIES,
    DATA_MANAGERS,
    DOMAIN,
)

if TYPE_CHECKING:
    from .manager import AutoFanFeatureManager


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    """Return the plugin data storage in hass."""
    return hass.data.setdefault(DOMAIN, {})


def managers(hass: HomeAssistant) -> dict[str, "AutoFanFeatureManager"]:
    """Return the registry of live managers keyed by VTherm unique_id."""
    return _domain_data(hass).setdefault(DATA_MANAGERS, {})


def get_manager(hass: HomeAssistant, unique_id: str) -> "AutoFanFeatureManager | None":
    """Return the manager bound to a VTherm unique_id, if any."""
    return managers(hass).get(unique_id)


def add_entities_registry(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Return the registry of async_add_entities callbacks by unique_id."""
    return _domain_data(hass).setdefault(DATA_ADD_ENTITIES, {})


def entities_registry(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Return the registry of created entities by unique_id."""
    return _domain_data(hass).setdefault(DATA_ENTITIES, {})


def entity_bucket(hass: HomeAssistant, unique_id: str) -> dict[str, Any]:
    """Return the entity bucket for a VTherm unique_id, creating it if needed."""
    return entities_registry(hass).setdefault(
        unique_id, {"numbers": {}, "select": None, "switch": None, "sensor": None}
    )
