# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant, CoreState, callback

from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_component import EntityComponent

from custom_components.versatile_thermostat.base_thermostat import (
    BaseThermostat,
    ConfigData,
)
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CENTRAL_MODE_AUTO,
    CENTRAL_MODES,
    overrides,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat selects with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)

    if vt_type != CONF_THERMOSTAT_CENTRAL_CONFIG:
        return

    entities = [
        CentralModeSelect(hass, unique_id, name, entry.data),
    ]

    async_add_entities(entities, True)


class CentralModeSelect(SelectEntity, RestoreEntity):
    """Representation of the central mode choice"""

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the energy sensor"""
        self._config_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)
        self._attr_name = "Central Mode"
        self._attr_unique_id = "central_mode"
        self._attr_options = CENTRAL_MODES
        self._attr_current_option = CENTRAL_MODE_AUTO

    @property
    def icon(self) -> str:
        return "mdi:form-select"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._config_id)},
            name=self._device_name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        if old_state is not None:
            self._attr_current_option = old_state.state

        @callback
        async def _async_startup_internal(*_):
            _LOGGER.debug("%s - Calling async_startup_internal", self)
            await self.notify_central_mode_change()

        if self.hass.state == CoreState.running:
            await _async_startup_internal()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, _async_startup_internal
            )

    @overrides
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        old_option = self._attr_current_option

        if option == old_option:
            return

        if option in CENTRAL_MODES:
            self._attr_current_option = option
            await self.notify_central_mode_change(old_central_mode=old_option)

    async def notify_central_mode_change(self, old_central_mode: str | None = None):
        """Notify all VTherm that the central_mode have change"""
        # Update all VTherm states
        component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
        for entity in component.entities:
            if isinstance(entity, BaseThermostat):
                _LOGGER.debug(
                    "Changing the central_mode. We have find %s to update",
                    entity.name,
                )
                await entity.check_central_mode(
                    self._attr_current_option, old_central_mode
                )

    def __str__(self) -> str:
        return f"VersatileThermostat-{self.name}"
