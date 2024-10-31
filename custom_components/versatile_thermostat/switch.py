## pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback

from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commons import VersatileThermostatBaseEntity

from .const import *  # pylint: disable=unused-wildcard-import,wildcard-import

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat switches with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)
    auto_start_stop_feature = entry.data.get(CONF_USE_AUTO_START_STOP_FEATURE)

    if vt_type == CONF_THERMOSTAT_CLIMATE and auto_start_stop_feature is True:
        # Creates a switch to enable the auto-start/stop
        enable_entity = AutoStartStopEnable(hass, unique_id, name, entry)
        async_add_entities([enable_entity], True)


class AutoStartStopEnable(VersatileThermostatBaseEntity, SwitchEntity, RestoreEntity):
    """The that enables the ManagedDevice optimisation with"""

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigEntry
    ):
        super().__init__(hass, unique_id, name)
        self._attr_name = "Enable auto start/stop"
        self._attr_unique_id = f"{self._device_name}_enbale_auto_start_stop"
        self._default_value = (
            entry_infos.data.get(CONF_AUTO_START_STOP_LEVEL)
            != AUTO_START_STOP_LEVEL_NONE
        )
        self._attr_is_on = self._default_value

    @property
    def icon(self) -> str | None:
        """The icon"""
        return "mdi:power-settings"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Récupérer le dernier état sauvegardé de l'entité
        last_state = await self.async_get_last_state()

        # Si l'état précédent existe, vous pouvez l'utiliser
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
        else:
            # If no previous state set it to false by default
            self._attr_is_on = self._default_value

        self.update_my_state_and_vtherm()

    def update_my_state_and_vtherm(self):
        """Update the auto_start_stop_enable flag in my VTherm"""
        self.async_write_ha_state()
        if self.my_climate is not None:
            self.my_climate.set_auto_start_stop_enable(self._attr_is_on)

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.turn_on()

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.turn_off()

    @overrides
    def turn_off(self, **kwargs: Any):
        self._attr_is_on = False
        self.update_my_state_and_vtherm()

    @overrides
    def turn_on(self, **kwargs: Any):
        self._attr_is_on = True
        self.update_my_state_and_vtherm()
