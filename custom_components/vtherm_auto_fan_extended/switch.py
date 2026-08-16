"""Enable ``switch`` platform for the auto fan plugin.

A single switch entity enables or disables the auto fan without losing the
threshold configuration. When it is off, the manager no longer drives the
underlying ``fan_mode``.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    CONF_TARGET_VTHERM,
    DEFAULT_AUTO_FAN_ENABLED,
    ENTITY_ENABLE_SUFFIX,
    PLATFORM_SWITCH,
)
from .manager import AutoFanFeatureManager
from .registry import add_entities_registry, entity_bucket, get_manager

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the switch add-entities callback for the target VTherm."""
    target_uid = entry.data.get(CONF_TARGET_VTHERM)
    if target_uid is None:
        return

    add_entities_registry(hass).setdefault(target_uid, {})[
        PLATFORM_SWITCH
    ] = async_add_entities

    manager = get_manager(hass, target_uid)
    if manager is not None:
        manager.ensure_entities()


class AutoFanEnableSwitch(RestoreEntity, SwitchEntity):
    """Enable/disable the auto fan feature."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: AutoFanFeatureManager) -> None:
        """Initialize the enable switch."""
        self._manager = manager
        self._attr_is_on = DEFAULT_AUTO_FAN_ENABLED
        self._attr_name = "Auto fan"
        self._attr_unique_id = (
            f"{manager.vtherm_unique_id}_{ENTITY_ENABLE_SUFFIX}"
        )
        self._attr_device_info = manager.device_info

    async def async_added_to_hass(self) -> None:
        """Restore the previous state and register with the manager."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == STATE_ON
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["switch"] = self

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from the manager."""
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["switch"] = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the auto fan and re-evaluate."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await self._manager.on_config_changed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the auto fan and re-evaluate."""
        self._attr_is_on = False
        self.async_write_ha_state()
        await self._manager.on_config_changed()
