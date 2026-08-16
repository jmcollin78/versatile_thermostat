"""Current fan mode ``sensor`` platform for the auto fan plugin.

A single sensor entity exposes the ``fan_mode`` actually sent to the underlying
climate by the manager. It has no entity category so it appears in the
"Sensors" section of the VTherm device, and restores its last value across
restarts.
"""

from __future__ import annotations

from homeassistant.components.sensor import RestoreSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    CONF_TARGET_VTHERM,
    ENTITY_CURRENT_FAN_MODE_SUFFIX,
    PLATFORM_SENSOR,
)
from .manager import AutoFanFeatureManager
from .registry import add_entities_registry, entity_bucket, get_manager

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the sensor add-entities callback for the target VTherm."""
    target_uid = entry.data.get(CONF_TARGET_VTHERM)
    if target_uid is None:
        return

    add_entities_registry(hass).setdefault(target_uid, {})[
        PLATFORM_SENSOR
    ] = async_add_entities

    manager = get_manager(hass, target_uid)
    if manager is not None:
        manager.ensure_entities()


class AutoFanCurrentFanModeSensor(RestoreSensor):
    """Sensor exposing the fan_mode currently sent to the underlying."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:fan-auto"

    def __init__(self, manager: AutoFanFeatureManager) -> None:
        """Initialize the current-fan-mode sensor."""
        self._manager = manager
        self._attr_name = "Auto fan current fan mode"
        self._attr_native_value = None
        self._attr_unique_id = (
            f"{manager.vtherm_unique_id}_{ENTITY_CURRENT_FAN_MODE_SUFFIX}"
        )
        self._attr_device_info = manager.device_info

    async def async_added_to_hass(self) -> None:
        """Restore the previous value and register with the manager."""
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            self._attr_native_value = last.native_value
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["sensor"] = self

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from the manager."""
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["sensor"] = None

    @callback
    def update_fan_mode(self, fan_mode: str) -> None:
        """Update the sensor with the fan_mode sent to the underlying."""
        self._attr_native_value = fan_mode
        self.async_write_ha_state()
