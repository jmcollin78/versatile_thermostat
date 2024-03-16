# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging

# from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant, CoreState  # , callback

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
    NumberDeviceClass,
    DOMAIN as NUMBER_DOMAIN,
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .vtherm_api import VersatileThermostatAPI
from .commons import VersatileThermostatBaseEntity

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_STEP_TEMPERATURE,
    CONF_AC_MODE,
    PRESET_FROST_PROTECTION,
    PRESET_ECO_AC,
    PRESET_COMFORT_AC,
    PRESET_BOOST_AC,
    PRESET_AWAY_SUFFIX,
    PRESET_TEMP_SUFFIX,
    CONF_PRESETS_VALUES,
    CONF_PRESETS_WITH_AC_VALUES,
    CONF_PRESETS_AWAY_VALUES,
    CONF_PRESETS_AWAY_WITH_AC_VALUES,
    CONF_USE_PRESETS_CENTRAL_CONFIG,
    CONF_USE_PRESENCE_CENTRAL_CONFIG,
    CONF_USE_PRESENCE_FEATURE,
    overrides,
)

PRESET_ICON_MAPPING = {
    PRESET_FROST_PROTECTION + PRESET_TEMP_SUFFIX: "mdi:snowflake-thermometer",
    PRESET_ECO + PRESET_TEMP_SUFFIX: "mdi:leaf",
    PRESET_COMFORT + PRESET_TEMP_SUFFIX: "mdi:sofa",
    PRESET_BOOST + PRESET_TEMP_SUFFIX: "mdi:rocket-launch",
    PRESET_ECO_AC + PRESET_TEMP_SUFFIX: "mdi:leaf-circle-outline",
    PRESET_COMFORT_AC + PRESET_TEMP_SUFFIX: "mdi:sofa-outline",
    PRESET_BOOST_AC + PRESET_TEMP_SUFFIX: "mdi:rocket-launch-outline",
    PRESET_FROST_PROTECTION
    + PRESET_AWAY_SUFFIX
    + PRESET_TEMP_SUFFIX: "mdi:snowflake-thermometer",
    PRESET_ECO + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: "mdi:leaf",
    PRESET_COMFORT + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: "mdi:sofa",
    PRESET_BOOST + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: "mdi:rocket-launch",
    PRESET_ECO_AC + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: "mdi:leaf-circle-outline",
    PRESET_COMFORT_AC + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: "mdi:sofa-outline",
    PRESET_BOOST_AC
    + PRESET_AWAY_SUFFIX
    + PRESET_TEMP_SUFFIX: "mdi:rocket-launch-outline",
}

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
    # is_central_boiler = entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE)

    entities = []

    if vt_type != CONF_THERMOSTAT_CENTRAL_CONFIG:
        # Creates non central temperature entities
        if not entry.data.get(CONF_USE_PRESETS_CENTRAL_CONFIG, False):
            for preset in CONF_PRESETS_VALUES:
                entities.append(
                    TemperatureNumber(
                        hass, unique_id, name, preset, False, False, entry.data
                    )
                )
            if entry.data.get(CONF_AC_MODE, False):
                for preset in CONF_PRESETS_WITH_AC_VALUES:
                    entities.append(
                        TemperatureNumber(
                            hass, unique_id, name, preset, True, False, entry.data
                        )
                    )

        if entry.data.get(
            CONF_USE_PRESENCE_FEATURE, False
        ) is True and not entry.data.get(CONF_USE_PRESENCE_CENTRAL_CONFIG, False):
            for preset in CONF_PRESETS_AWAY_VALUES:
                entities.append(
                    TemperatureNumber(
                        hass, unique_id, name, preset, False, True, entry.data
                    )
                )

            if entry.data.get(CONF_AC_MODE, False):
                for preset in CONF_PRESETS_AWAY_WITH_AC_VALUES:
                    entities.append(
                        TemperatureNumber(
                            hass, unique_id, name, preset, True, True, entry.data
                        )
                    )
    # For central config only
    else:
        entities.append(
            ActivateBoilerThresholdNumber(hass, unique_id, name, entry.data)
        )
        for preset in CONF_PRESETS_VALUES:
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, False, False, entry.data
                )
            )
        for preset in CONF_PRESETS_WITH_AC_VALUES:
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, True, False, entry.data
                )
            )

        for preset in CONF_PRESETS_AWAY_VALUES:
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, False, True, entry.data
                )
            )

        for preset in CONF_PRESETS_AWAY_WITH_AC_VALUES:
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, True, True, entry.data
                )
            )

    async_add_entities(entities, True)


class ActivateBoilerThresholdNumber(
    NumberEntity, RestoreEntity
):  # pylint: disable=abstract-method
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


class CentralConfigTemperatureNumber(
    NumberEntity, RestoreEntity
):  # pylint: disable=abstract-method
    """Representation of one temperature number"""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        preset_name,
        is_ac,
        is_away,
        entry_infos,
    ) -> None:
        """Initialize the temperature with entry_infos if available. Else
        the restoration will do the trick."""

        self._config_id = unique_id
        self._device_name = name
        # self._attr_name = name

        self._attr_translation_key = preset_name
        self.entity_id = f"{NUMBER_DOMAIN}.{slugify(name)}_preset_{preset_name}"
        self._attr_unique_id = f"central_configuration_preset_{preset_name}"
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

        self._attr_native_step = entry_infos.get(CONF_STEP_TEMPERATURE, 0.5)
        self._attr_native_min_value = entry_infos.get(CONF_TEMP_MIN)
        self._attr_native_max_value = entry_infos.get(CONF_TEMP_MAX)

        # Initialize the values if included into the entry_infos. This will do
        # the temperature migration. Else the temperature will be restored from
        # previous value
        # TODO remove this after the next major release and just keep the init min/max
        temp = None
        if (temp := entry_infos.get(preset_name, None)) is not None:
            self._attr_value = self._attr_native_value = temp
        else:
            if entry_infos.get(CONF_AC_MODE) is True:
                self._attr_native_value = self._attr_native_max_value
            else:
                self._attr_native_value = self._attr_native_min_value

        self._attr_mode = NumberMode.BOX
        self._preset_name = preset_name
        self._is_away = is_away
        self._is_ac = is_ac

    @property
    def icon(self) -> str | None:
        return PRESET_ICON_MAPPING[self._preset_name]

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

        # register the temp entity for this device and preset
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        api.register_temperature_number(self._config_id, self._preset_name, self)

        # Restore value from previous one if exists
        old_state: CoreState = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        try:
            if old_state is not None and ((value := float(old_state.state)) > 0):
                self._attr_value = self._attr_native_value = value
        except ValueError:
            pass

    @overrides
    async def async_set_native_value(self, value: float) -> None:
        """The value have change from the Number Entity in UI"""
        float_value = float(value)
        old_value = float(self._attr_native_value)
        if float_value == old_value:
            return

        self._attr_value = self._attr_native_value = float_value

        # persist the value
        self.async_write_ha_state()

        # We have to reload all VTherm for which uses the central configuration
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        # Update the VTherms which have temperature in central config
        self.hass.create_task(api.init_vtherm_links(only_use_central=True))

    def __str__(self):
        return f"VersatileThermostat-{self.name}"

    @property
    def native_unit_of_measurement(self) -> str | None:
        """The unit of measurement"""
        # TODO Kelvin ? It seems not because all internal values are stored in
        # ° Celsius but only the render in front can be in °K depending on the
        # user configuration.
        return UnitOfTemperature.CELSIUS


class TemperatureNumber(  # pylint: disable=abstract-method
    VersatileThermostatBaseEntity, NumberEntity, RestoreEntity
):
    """Representation of one temperature number"""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        preset_name,
        is_ac,
        is_away,
        entry_infos,
    ) -> None:
        """Initialize the temperature with entry_infos if available. Else
        the restoration will do the trick."""
        super().__init__(hass, unique_id, name)

        self._attr_translation_key = preset_name
        self.entity_id = f"{NUMBER_DOMAIN}.{slugify(name)}_preset_{preset_name}"

        self._attr_unique_id = f"{self._device_name}_preset_{preset_name}"
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

        self._attr_native_step = entry_infos.get(CONF_STEP_TEMPERATURE, 0.5)
        self._attr_native_min_value = entry_infos.get(CONF_TEMP_MIN)
        self._attr_native_max_value = entry_infos.get(CONF_TEMP_MAX)

        # Initialize the values if included into the entry_infos. This will do
        # the temperature migration.
        temp = None
        if (temp := entry_infos.get(preset_name, None)) is not None:
            self._attr_value = self._attr_native_value = temp
        else:
            if entry_infos.get(CONF_AC_MODE) is True:
                self._attr_native_value = self._attr_native_max_value
            else:
                self._attr_native_value = self._attr_native_min_value

        self._attr_mode = NumberMode.BOX
        self._preset_name = preset_name
        self._canonical_preset_name = preset_name.replace(
            PRESET_TEMP_SUFFIX, ""
        ).replace(PRESET_AWAY_SUFFIX, "")
        self._is_away = is_away
        self._is_ac = is_ac

    @property
    def icon(self) -> str | None:
        return PRESET_ICON_MAPPING[self._preset_name]

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # register the temp entity for this device and preset
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        api.register_temperature_number(self._config_id, self._preset_name, self)

        old_state: CoreState = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        try:
            if old_state is not None and ((value := float(old_state.state)) > 0):
                self._attr_value = self._attr_native_value = value
        except ValueError:
            pass

    @overrides
    def my_climate_is_initialized(self):
        """Called when the associated climate is initialized"""
        self._attr_native_step = self.my_climate.target_temperature_step
        self._attr_native_min_value = self.my_climate.min_temp
        self._attr_native_max_value = self.my_climate.max_temp
        return

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

        # Update the VTherm temp
        self.hass.create_task(
            self.my_climate.service_set_preset_temperature(
                self._canonical_preset_name,
                self._attr_native_value if not self._is_away else None,
                self._attr_native_value if self._is_away else None,
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
