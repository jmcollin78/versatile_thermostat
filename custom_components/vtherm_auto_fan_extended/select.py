"""Rest-mode ``select`` platform for the auto fan plugin.

A single select entity holds the fan_mode applied when the temperature gap is
below every active threshold (nothing to stir). Its options follow the fan
modes exposed by the underlying climate.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    CONF_TARGET_VTHERM,
    ENTITY_REST_MODE_SUFFIX,
    PLATFORM_SELECT,
)
from .manager import AutoFanFeatureManager
from .registry import add_entities_registry, entity_bucket, get_manager

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the select add-entities callback for the target VTherm."""
    target_uid = entry.data.get(CONF_TARGET_VTHERM)
    if target_uid is None:
        return

    add_entities_registry(hass).setdefault(target_uid, {})[
        PLATFORM_SELECT
    ] = async_add_entities

    manager = get_manager(hass, target_uid)
    if manager is not None:
        manager.ensure_entities()


class RestModeSelect(RestoreEntity, SelectEntity):
    """Rest fan_mode applied when the temperature gap is low."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        manager: AutoFanFeatureManager,
        default_option: str | None,
    ) -> None:
        """Initialize the rest-mode select."""
        self._manager = manager
        self._attr_current_option = default_option
        self._attr_name = "Auto fan rest mode"
        self._attr_unique_id = (
            f"{manager.vtherm_unique_id}_{ENTITY_REST_MODE_SUFFIX}"
        )
        self._attr_device_info = manager.device_info

    @property
    def options(self) -> list[str]:
        """The rest-mode options follow the underlying fan modes."""
        return self._manager.available_fan_modes

    async def async_added_to_hass(self) -> None:
        """Restore the previous option and register with the manager."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in self.options:
            self._attr_current_option = last.state
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["select"] = self

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from the manager."""
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["select"] = None

    async def async_select_option(self, option: str) -> None:
        """Update the rest mode and re-evaluate the auto fan."""
        self._attr_current_option = option
        self.async_write_ha_state()
        await self._manager.on_config_changed()
