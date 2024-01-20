# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging

# from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant, CoreState  # , callback

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_ADD_CENTRAL_BOILER_CONTROL,
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
    is_central_boiler = entry.data.get(CONF_ADD_CENTRAL_BOILER_CONTROL)

    if vt_type != CONF_THERMOSTAT_CENTRAL_CONFIG or not is_central_boiler:
        return

    entities = [
        ActivateBoilerThresholdNumber(hass, unique_id, name, entry.data),
    ]

    async_add_entities(entities, True)


class ActivateBoilerThresholdNumber(NumberEntity, RestoreEntity):
    """Representation of the threshold of the number of VTherm
    which should be active to activate the boiler"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        self._hass = hass
        self._config_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)
        self._attr_name = "Boiler Activation threshold"
        self._attr_unique_id = "boiler_activation_threshold"
        self._attr_value = self._attr_native_value = 1  # default value
        self._attr_native_min_value = 1
        self._attr_native_max_value = 9
        self._attr_step = 1  # default value
        self._attr_mode = NumberMode.AUTO

    @property
    def icon(self) -> str | None:
        if isinstance(self._attr_native_value, int):
            val = int(self._attr_native_value)
            return f"mdi:numeric-{val}-box-outline"
        else:
            return "mdi:numeric-0-box-outline"

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

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.register_central_boiler_activation_number_threshold(self)

        old_state: CoreState = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        if old_state is not None:
            self._attr_value = self._attr_native_value = int(float(old_state.state))

    @overrides
    def set_native_value(self, value: float) -> None:
        """Change the value"""
        int_value = int(value)
        old_value = int(self._attr_native_value)

        if int_value == old_value:
            return

        self._attr_value = self._attr_native_value = int_value

    def __str__(self):
        return f"VersatileThermostat-{self.name}"
