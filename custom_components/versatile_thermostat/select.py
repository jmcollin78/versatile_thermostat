# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging
from vtherm_api.log_collector import get_vtherm_logger

from homeassistant.core import HomeAssistant, callback, Event

from homeassistant.const import EntityCategory
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.versatile_thermostat.base_thermostat import (
    ConfigData,
)

from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI

from .base_entity import VersatileThermostatBaseEntity

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_THERMOSTAT_CLIMATE,
    CONF_USE_AUTO_START_STOP_FEATURE,
    CENTRAL_MODE_AUTO,
    CENTRAL_MODES,
    AUTO_START_STOP_STOP_MODE_OFF,
    AUTO_START_STOP_STOP_MODE_FAN_ONLY,
    AUTO_START_STOP_STOP_MODE_DRY,
    AUTO_START_STOP_STOP_MODES,
    overrides,
)
from .commons import write_event_log

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat selects with config flow."""
    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    _LOGGER.debug("%s - Calling async_setup_entry entry=%s, data=%s", name, entry.entry_id, entry.data)
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)

    entities = []

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        entities.append(CentralModeSelect(hass, unique_id, name, entry.data))
    elif vt_type == CONF_THERMOSTAT_CLIMATE:
        if entry.data.get(CONF_USE_AUTO_START_STOP_FEATURE) is True:
            entities.append(AutoStartStopStopModeSelect(hass, unique_id, name, entry.data))

    if entities:
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
            entry_type=None,
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

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        api.register_central_mode_select(self)

    @overrides
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        old_option = self._attr_current_option

        if option == old_option:
            return

        if option in CENTRAL_MODES:
            write_event_log(_LOGGER, self, f"Central mode is being changed from {old_option} to {option}")
            self._attr_current_option = option
            await self.notify_central_mode_change(old_central_mode=old_option)

    @overrides
    def select_option(self, option: str) -> None:
        """Change the selected option"""
        # Update the VTherms which have temperature in central config
        self.hass.create_task(self.async_select_option(option))

    async def notify_central_mode_change(self, old_central_mode: str | None = None):
        """Notify all VTherm that the central_mode have change"""
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        # Update all VTherm states
        await api.notify_central_mode_change(old_central_mode)

    def __str__(self) -> str:
        return f"VersatileThermostat-{self.name}"


class AutoStartStopStopModeSelect(
    VersatileThermostatBaseEntity, SelectEntity, RestoreEntity
):
    """Representation of the hvac_mode applied when the auto-start/stop
    feature detects a stop condition (off, fan_only or dry)."""

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the auto-start/stop stop mode select"""
        super().__init__(hass, unique_id, name)
        self._attr_name = "Auto start/stop stop mode"
        self._attr_unique_id = f"{self._device_name}_auto_start_stop_stop_mode"
        self._attr_translation_key = "auto_start_stop_stop_mode"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_current_option = AUTO_START_STOP_STOP_MODE_OFF

    @property
    def icon(self) -> str | None:
        """The icon"""
        return "mdi:hvac"

    @property
    def options(self) -> list[str]:
        """The available options, computed from the underlying supported hvac_modes"""
        return self._build_options()

    def _build_options(self) -> list[str]:
        """Build the available options from the underlying supported hvac_modes.
        fan_only and dry are only proposed if the underlying supports them."""
        options = [AUTO_START_STOP_STOP_MODE_OFF]
        climate = self.my_climate
        if climate is not None:
            hvac_modes = climate.hvac_modes
            if AUTO_START_STOP_STOP_MODE_FAN_ONLY in hvac_modes:
                options.append(AUTO_START_STOP_STOP_MODE_FAN_ONLY)
            if AUTO_START_STOP_STOP_MODE_DRY in hvac_modes:
                options.append(AUTO_START_STOP_STOP_MODE_DRY)
        return options

    @callback
    def my_climate_is_initialized(self):
        """Called when the associated climate is resolved -> refresh the options.
        The restored option is only validated once the VTherm is fully
        initialized (its underlying hvac_modes are available)."""

        self._refresh_current_option()
        self.hass.create_task(self.update_my_state_and_vtherm())

    def _refresh_current_option(self):
        """Reset the current option to off only once the VTherm is fully
        initialized and its underlying does not support the current option.
        While the VTherm is not initialized, the restored option is kept as is
        to avoid discarding it before the underlying hvac_modes are available."""
        climate = self.my_climate
        if climate is None or not climate.is_initialized:
            return
        if self._attr_current_option not in self.options:
            self._attr_current_option = AUTO_START_STOP_STOP_MODE_OFF

    @overrides
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate changes -> refresh the available options.
        The underlying supported hvac_modes may become available only after
        the VTherm has adopted them, so the options must be recomputed."""
        if self.my_climate is None:
            return
        self._refresh_current_option()
        self.async_write_ha_state()

    @overrides
    async def async_added_to_hass(self):
        # Restore the persisted value before looking for the climate so that
        # my_climate_is_initialized validates the options against it.
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in AUTO_START_STOP_STOP_MODES:
            self._attr_current_option = last_state.state

        await super().async_added_to_hass()

        await self.update_my_state_and_vtherm()

    async def update_my_state_and_vtherm(self):
        """Update the stop mode in my VTherm auto-start/stop manager"""
        self.async_write_ha_state()
        if (
            self.my_climate is not None
            and self.my_climate.auto_start_stop_manager is not None
        ):
            await self.my_climate.auto_start_stop_manager.set_auto_start_stop_stop_mode(self._attr_current_option)

    @overrides
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == self._attr_current_option:
            return

        if option in self.options:
            write_event_log(_LOGGER, self, f"Auto start/stop stop mode is being changed from {self._attr_current_option} to {option}")
            self._attr_current_option = option
            await self.update_my_state_and_vtherm()

    @overrides
    def select_option(self, option: str) -> None:
        """Change the selected option"""
        self.hass.create_task(self.async_select_option(option))
