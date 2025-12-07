# pylint: disable=unused-argument

""" Implements the VersatileThermostat select component """
import logging

# from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, CoreState  # , callback

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
    NumberDeviceClass,
    DOMAIN as NUMBER_DOMAIN,
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .vtherm_api import VersatileThermostatAPI
from .base_entity import VersatileThermostatBaseEntity

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
    CONF_PRESETS_VALUES,
    CONF_PRESETS_WITH_AC_VALUES,
    CONF_PRESETS_AWAY_VALUES,
    CONF_PRESETS_AWAY_WITH_AC_VALUES,
    CONF_USE_PRESETS_CENTRAL_CONFIG,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_CENTRAL_BOILER_FEATURE,
    overrides,
    gen_attr_uniq_id,
    CONF_USE_MAIN_CENTRAL_CONFIG,
)

from .vtherm_preset import VThermPreset, VThermPresetWithAC, VThermPresetWithAway, VThermPresetWithACAway, PRESET_TEMP_SUFFIX, PRESET_AWAY_SUFFIX

PRESET_ICON_MAPPING = {
    VThermPreset.FROST + PRESET_TEMP_SUFFIX: "mdi:snowflake-thermometer",
    VThermPreset.ECO + PRESET_TEMP_SUFFIX: "mdi:leaf",
    VThermPreset.COMFORT + PRESET_TEMP_SUFFIX: "mdi:sofa",
    VThermPreset.BOOST + PRESET_TEMP_SUFFIX: "mdi:rocket-launch",
    VThermPresetWithAC.ECO + PRESET_TEMP_SUFFIX: "mdi:leaf-circle-outline",
    VThermPresetWithAC.COMFORT + PRESET_TEMP_SUFFIX: "mdi:sofa-outline",
    VThermPresetWithAC.BOOST + PRESET_TEMP_SUFFIX: "mdi:rocket-launch-outline",
    VThermPresetWithAway.FROST + PRESET_TEMP_SUFFIX: "mdi:snowflake-thermometer",
    VThermPresetWithAway.ECO + PRESET_TEMP_SUFFIX: "mdi:leaf",
    VThermPresetWithAway.COMFORT + PRESET_TEMP_SUFFIX: "mdi:sofa",
    VThermPresetWithAway.BOOST + PRESET_TEMP_SUFFIX: "mdi:rocket-launch",
    VThermPresetWithACAway.ECO + PRESET_TEMP_SUFFIX: "mdi:leaf-circle-outline",
    VThermPresetWithACAway.COMFORT + PRESET_TEMP_SUFFIX: "mdi:sofa-outline",
    VThermPresetWithACAway.BOOST + PRESET_TEMP_SUFFIX: "mdi:rocket-launch-outline",
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
            if entry.data.get(CONF_AC_MODE, False):
                for preset in CONF_PRESETS_WITH_AC_VALUES:
                    _LOGGER.debug(
                        "%s - configuring Number non central, AC, non AWAY for preset %s",
                        name,
                        preset,
                    )
                    entities.append(
                        TemperatureNumber(
                            hass, unique_id, name, preset, True, False, entry.data
                        )
                    )
            else:
                for preset in CONF_PRESETS_VALUES:
                    _LOGGER.debug(
                        "%s - configuring Number non central, non AC, non AWAY for preset %s",
                        name,
                        preset,
                    )
                    entities.append(
                        TemperatureNumber(
                            hass, unique_id, name, preset, False, False, entry.data
                        )
                    )

            if entry.data.get(CONF_USE_PRESENCE_FEATURE, False) is True:
                if entry.data.get(CONF_AC_MODE, False):
                    for preset in CONF_PRESETS_AWAY_WITH_AC_VALUES:
                        _LOGGER.debug(
                            "%s - configuring Number non central, AC, AWAY for preset %s",
                            name,
                            preset,
                        )
                        entities.append(TemperatureNumber(hass, unique_id, name, preset, True, True, entry.data))
                else:
                    for preset in CONF_PRESETS_AWAY_VALUES:
                        _LOGGER.debug(
                            "%s - configuring Number non central, non AC, AWAY for preset %s",
                            name,
                            preset,
                        )
                        entities.append(TemperatureNumber(hass, unique_id, name, preset, False, True, entry.data))

    # For central config only
    else:
        if entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            entities.append(ActivateBoilerThresholdNumber(hass, unique_id, name, entry.data))
            entities.append(ActivateBoilerPowerThresholdNumber(hass, unique_id, name, entry.data))

        for preset in CONF_PRESETS_WITH_AC_VALUES:
            _LOGGER.debug(
                "%s - configuring Number central, AC, non AWAY for preset %s",
                name,
                preset,
            )
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, True, False, entry.data
                )
            )

        for preset in CONF_PRESETS_AWAY_WITH_AC_VALUES:
            _LOGGER.debug(
                "%s - configuring Number central, AC, AWAY for preset %s", name, preset
            )
            entities.append(
                CentralConfigTemperatureNumber(
                    hass, unique_id, name, preset, True, True, entry.data
                )
            )

    if len(entities) > 0:
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
        self._attr_name = "Number activation threshold"
        self._attr_unique_id = "boiler_activation_threshold"
        self._attr_value = self._attr_native_value = 0  # default value
        self._attr_native_min_value = 0
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
            entry_type=None,
            identifiers={(DOMAIN, self._config_id)},
            name=self._device_name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.central_boiler_manager.register_central_boiler_activation_number_threshold(self)

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
        self.hass.create_task(VersatileThermostatAPI.get_vtherm_api(self._hass).central_boiler_manager.refresh_central_boiler_custom_attributes())

    def __str__(self):
        return f"VersatileThermostat-{self.name}"


class ActivateBoilerPowerThresholdNumber(NumberEntity, RestoreEntity):  # pylint: disable=abstract-method
    """Representation of the threshold of the total power of VTherm
    which should be active to activate the boiler"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        self._hass = hass
        self._config_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)
        self._attr_name = "Power activation threshold"
        self._attr_unique_id = "boiler_power_activation_threshold"
        self._attr_value = self._attr_native_value = 0  # default value
        self._attr_native_min_value = 0
        self._attr_native_max_value = 10000  # for people who works in Watts
        self._attr_step = 1  # default value
        self._attr_mode = NumberMode.AUTO

    @property
    def icon(self) -> str | None:
        return "mdi:water-boiler-auto"

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

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.central_boiler_manager.register_central_boiler_power_activation_threshold(self)

        old_state: CoreState = await self.async_get_last_state()
        _LOGGER.debug("%s - Calling async_added_to_hass old_state is %s", self, old_state)
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
        self.hass.create_task(VersatileThermostatAPI.get_vtherm_api(self._hass).central_boiler_manager.refresh_central_boiler_custom_attributes())

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
        self._attr_native_unit_of_measurement = hass.config.units.temperature_unit

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
            entry_type=None,
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
        old_value = (
            None if self._attr_native_value is None else float(self._attr_native_value)
        )

        if float_value == old_value:
            return

        self._attr_value = self._attr_native_value = float_value

        # persist the value
        self.async_write_ha_state()

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self.hass)
        api.register_temperature_number(self._config_id, self._preset_name, self)

        # We have to reload all VTherm for which uses the central configuration
        # Update the VTherms which have temperature in central config
        self.hass.create_task(api.init_vtherm_preset_with_central())

    def __str__(self):
        return f"VersatileThermostat-{self.name}"

    @property
    def native_unit_of_measurement(self) -> str | None:
        """The unit of measurement"""
        return self.hass.config.units.temperature_unit


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

        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, f"_preset_{preset_name}")
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = hass.config.units.temperature_unit

        self._has_central_main_attributes = entry_infos.get(
            CONF_USE_MAIN_CENTRAL_CONFIG, False
        )

        self.init_min_max_step(entry_infos)

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
        old_value = (
            None if self._attr_native_value is None else float(self._attr_native_value)
        )

        if float_value == old_value:
            return

        self._attr_value = self._attr_native_value = float_value
        self.async_write_ha_state()

        # Update the VTherm temp
        self.hass.create_task(
            self.my_climate.set_preset_temperature(
                self._canonical_preset_name,
                self._attr_native_value if not self._is_away else None,
                self._attr_native_value if self._is_away else None,
            )
        )

        # We set the min, max and step from central config if relevant because it is possible
        # that central config was not loaded at startup
        self.init_min_max_step()

    def __str__(self):
        return f"VersatileThermostat-{self.name}"

    @property
    def native_unit_of_measurement(self) -> str | None:
        """The unit of measurement"""
        if not self.my_climate:
            return self.hass.config.units.temperature_unit
        return self.my_climate.temperature_unit

    def init_min_max_step(self, entry_infos=None):
        """Initialize min, max and step value from config or from central config"""
        if self._has_central_main_attributes:
            vthermapi: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()
            central_config = vthermapi.find_central_configuration()
            if central_config:
                self._attr_native_step = central_config.data.get(CONF_STEP_TEMPERATURE)
                self._attr_native_min_value = central_config.data.get(CONF_TEMP_MIN)
                self._attr_native_max_value = central_config.data.get(CONF_TEMP_MAX)

                return

        if entry_infos:
            self._attr_native_step = entry_infos.get(
                CONF_STEP_TEMPERATURE, DEFAULT_STEP
            )
            self._attr_native_min_value = entry_infos.get(
                CONF_TEMP_MIN, DEFAULT_MIN_VALUE
            )
            self._attr_native_max_value = entry_infos.get(
                CONF_TEMP_MAX, DEFAULT_MAX_VALUE
            )
