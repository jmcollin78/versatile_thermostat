"""Threshold ``number`` platform for the auto fan plugin.

One number entity is created per underlying ``fan_mode``. It holds the
temperature gap above which that fan_mode becomes a candidate. A value of ``0``
means the fan_mode does not participate in the auto fan.
"""

from __future__ import annotations

from homeassistant.components.number import (
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    CONF_TARGET_VTHERM,
    ENTITY_THRESHOLD_PREFIX,
    PLATFORM_NUMBER,
    THRESHOLD_MAX,
    THRESHOLD_MIN,
    THRESHOLD_STEP,
)
from .manager import AutoFanFeatureManager
from .registry import add_entities_registry, entity_bucket, get_manager

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the number add-entities callback for the target VTherm."""
    target_uid = entry.data.get(CONF_TARGET_VTHERM)
    if target_uid is None:
        return

    add_entities_registry(hass).setdefault(target_uid, {})[
        PLATFORM_NUMBER
    ] = async_add_entities

    manager = get_manager(hass, target_uid)
    if manager is not None:
        manager.ensure_entities()


class ThresholdNumber(RestoreNumber):
    """Temperature-gap threshold for a single fan_mode."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_native_min_value = THRESHOLD_MIN
    _attr_native_max_value = THRESHOLD_MAX
    _attr_native_step = THRESHOLD_STEP
    _attr_mode = NumberMode.BOX
    _attr_should_poll = False

    def __init__(
        self,
        manager: AutoFanFeatureManager,
        fan_mode: str,
        default_value: float,
        unit: str,
    ) -> None:
        """Initialize the threshold number for a fan_mode."""
        self._manager = manager
        self._fan_mode = fan_mode
        self._default_value = default_value
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = default_value
        self._attr_name = f"Fan mode threshold {fan_mode}"
        self._attr_unique_id = (
            f"{manager.vtherm_unique_id}_{ENTITY_THRESHOLD_PREFIX}_"
            f"{slugify(fan_mode)}"
        )
        self._attr_device_info = manager.device_info

    async def async_added_to_hass(self) -> None:
        """Restore the previous value and register with the manager."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._attr_native_value = last.native_value
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["numbers"][
            self._fan_mode
        ] = self

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from the manager."""
        entity_bucket(self.hass, self._manager.vtherm_unique_id)["numbers"].pop(
            self._fan_mode, None
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the threshold and re-evaluate the auto fan."""
        self._attr_native_value = value
        self.async_write_ha_state()
        await self._manager.on_config_changed()
