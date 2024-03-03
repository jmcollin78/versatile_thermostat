# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging

# from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant, CoreState  # , callback

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
    NumberDeviceClass,
)
from homeassistant.components.climate import (
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
)
from homeassistant.components.sensor import UnitOfTemperature

from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_STEP_TEMPERATURE,
    CONF_AC_MODE,
    PRESET_FROST_PROTECTION,
    PRESET_ECO_AC,
    PRESET_COMFORT_AC,
    PRESET_BOOST_AC,
    PRESET_AC_SUFFIX,
    CONF_PRESETS_VALUES,
    CONF_PRESETS_WITH_AC_VALUES,
    # CONF_PRESETS_AWAY_VALUES,
    # CONF_PRESETS_AWAY_WITH_AC_VALUES,
    overrides,
)

PRESET_ICON_MAPPING = {
    PRESET_FROST_PROTECTION + "_temp": "mdi:snowflake-thermometer",
    PRESET_ECO + "_temp": "mdi:leaf",
    PRESET_COMFORT + "_temp": "mdi:sofa",
    PRESET_BOOST + "_temp": "mdi:rocket-launch",
    PRESET_ECO_AC + "_temp": "mdi:leaf-circle-outline",
    PRESET_COMFORT_AC + "_temp": "mdi:sofa-outline",
    PRESET_BOOST_AC + "_temp": "mdi:rocket-launch-outline",
}

_LOGGER = logging.getLogger(__name__)


class TemperatureNumber(NumberEntity, RestoreEntity):
    """Representation of one temperature number"""

    _attr_has_entity_name = True
    _attr_translation_key = "temperature"

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        preset_name,
        is_ac,
        is_away,
        entry_infos: ConfigEntry,
    ) -> None:
        """Initialize the temperature with entry_infos if available. Else
        the restoration will do the trick."""
        # super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))

        self.my_climate = None
        self._unique_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)

        # split = name.split("_")
        # self._attr_name = split[0]
        # if "_" + split[1] == PRESET_AC_SUFFIX:
        #     self._attr_name = self._attr_name + " AC"

        self._attr_name = preset_name + " new temperature"

        # self._attr_translation_placeholders = {
        #    "preset": preset_name,
        #    "ac": "-AC" if is_ac else "",
        #    "away": "-AWAY" if is_away else "",
        # }
        self._attr_unique_id = f"{self._device_name}_{self._attr_name}"
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

        # Initialize the values if included into the entry_infos. This will do
        # the temperature migration.
        # TODO see if this should be replace by the central config if any
        temp = None
        # if temp := entry_infos.get(preset_name, None):
        #    self._attr_value = self._attr_native_value = temp

        self._attr_mode = NumberMode.BOX
        self._preset_name = preset_name
        self._is_away = is_away
        self._is_ac = is_ac

        self._attr_native_step = entry_infos.get(CONF_STEP_TEMPERATURE, 0.5)
        self._attr_native_min_value = entry_infos.get(CONF_TEMP_MIN)
        self._attr_native_max_value = entry_infos.get(CONF_TEMP_MAX)

    @property
    def icon(self) -> str | None:
        return PRESET_ICON_MAPPING[self._preset_name]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._unique_id)},
            name=self._device_name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        old_state: CoreState = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        try:
            if old_state is not None and (value := float(old_state.state) > 0):
                self._attr_value = self._attr_native_value = value
        except ValueError:
            pass

    @overrides
    def my_climate_is_initialized(self):
        """Called when the associated climate is initialized"""
        self._attr_native_step = self.my_climate.target_temperature_step
        self._attr_native_min_value = self.my_climate.min_temp
        self._attr_native_max_value = self.my_climate.max_temp

        # Initialize the internal temp value of VTherm
        self.my_climate.init_temperature_preset(
            self._preset_name, self._attr_native_value, self._is_ac, self._is_away
        )
        return

    # @overrides
    # @property
    # def native_step(self) -> float | None:
    #     """The native step"""
    #     return self.my_climate.target_temperature_step

    @overrides
    async def async_set_native_value(self, value: float) -> None:
        """Change the value"""

        if self.my_climate is None:
            _LOGGER.warning(
                "%s - cannot change temperature because VTherm is not initialized", self
            )
            return

        float_value = float(value)
        old_value = float(self._attr_native_value)

        if float_value == old_value:
            return

        self._attr_value = self._attr_native_value = float_value

        self.async_write_ha_state()

        # Update the VTherm
        self.hass.create_task(
            self.my_climate.service_set_preset_temperature(
                self._preset_name.replace("_temp", ""), self._attr_native_value, None
            )
        )

    def __str__(self):
        return f"VersatileThermostat-{self.name}"

    @property
    def native_unit_of_measurement(self) -> str | None:
        """The unit of measurement"""
        if not self.my_climate:
            return UnitOfTemperature.CELSIUS
        return self.my_climate.temperature_unit
