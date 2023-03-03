""" Implements the VersatileThermostat sensors component """
import logging
import math

from homeassistant.core import HomeAssistant, callback, Event

from homeassistant.const import UnitOfTime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commons import VersatileThermostatBaseEntity
from .const import (
    CONF_NAME,
    CONF_DEVICE_POWER,
    CONF_PROP_FUNCTION,
    PROPORTIONAL_FUNCTION_TPI,
    CONF_THERMOSTAT_SWITCH,
    CONF_THERMOSTAT_TYPE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat sensors with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)

    entities = [
        LastTemperatureSensor(hass, unique_id, name, entry.data),
        LastExtTemperatureSensor(hass, unique_id, name, entry.data),
    ]
    if entry.data.get(CONF_DEVICE_POWER):
        entities.append(EnergySensor(hass, unique_id, name, entry.data))
        if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_SWITCH:
            entities.append(MeanPowerSensor(hass, unique_id, name, entry.data))

    if entry.data.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI:
        entities.append(OnPercentSensor(hass, unique_id, name, entry.data))
        entities.append(OnTimeSensor(hass, unique_id, name, entry.data))
        entities.append(OffTimeSensor(hass, unique_id, name, entry.data))

    async_add_entities(entities, True)


class EnergySensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a Energy sensor which exposes the energy"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Energy"
        self._attr_unique_id = f"{self._device_name}_energy"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        if math.isnan(self.my_climate.total_energy) or math.isinf(
            self.my_climate.total_energy
        ):
            raise ValueError(f"Sensor has illegal state {self.my_climate.total_energy}")

        old_state = self._attr_native_value
        self._attr_native_value = round(
            self.my_climate.total_energy, self.suggested_display_precision
        )
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:lightning-bolt"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "kWh"

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 3


class MeanPowerSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a power sensor which exposes the mean power in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Mean power cycle"
        self._attr_unique_id = f"{self._device_name}_mean_power_cycle"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        if math.isnan(float(self.my_climate.mean_cycle_power)) or math.isinf(
            self.my_climate.mean_cycle_power
        ):
            raise ValueError(
                f"Sensor has illegal state {self.my_climate.mean_cycle_power}"
            )

        old_state = self._attr_native_value
        self._attr_native_value = round(
            self.my_climate.mean_cycle_power, self.suggested_display_precision
        )
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:flash-outline"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "kW"

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 3


class OnPercentSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on percent sensor which exposes the on_percent in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Power percent"
        self._attr_unique_id = f"{self._device_name}_power_percent"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        on_percent = (
            float(self.my_climate.proportional_algorithm.on_percent)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )
        if math.isnan(on_percent) or math.isinf(on_percent):
            raise ValueError(f"Sensor has illegal state {on_percent}")

        old_state = self._attr_native_value
        self._attr_native_value = round(
            on_percent * 100.0, self.suggested_display_precision
        )
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:meter-electric-outline"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.POWER_FACTOR

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 1


class OnTimeSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on time sensor which exposes the on_time_sec in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "On time"
        self._attr_unique_id = f"{self._device_name}_on_time"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        on_time = (
            float(self.my_climate.proportional_algorithm.on_time_sec)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )
        if math.isnan(on_time) or math.isinf(on_time):
            raise ValueError(f"Sensor has illegal state {on_time}")

        old_state = self._attr_native_value
        self._attr_native_value = round(on_time)
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfTime.SECONDS


class OffTimeSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on time sensor which exposes the off_time_sec in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Off time"
        self._attr_unique_id = f"{self._device_name}_off_time"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        off_time = (
            float(self.my_climate.proportional_algorithm.off_time_sec)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )
        if math.isnan(off_time) or math.isinf(off_time):
            raise ValueError(f"Sensor has illegal state {off_time}")

        old_state = self._attr_native_value
        self._attr_native_value = round(off_time)
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:timer-off-outline"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfTime.SECONDS


class LastTemperatureSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a last temperature datetime sensor"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the last temperature datetime sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Last temperature date"
        self._attr_unique_id = f"{self._device_name}_last_temp_datetime"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        old_state = self._attr_native_value
        self._attr_native_value = self.my_climate.last_temperature_mesure
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:home-clock"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.TIMESTAMP


class LastExtTemperatureSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a last external temperature datetime sensor"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the last temperature datetime sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Last external temperature date"
        self._attr_unique_id = f"{self._device_name}_last_ext_temp_datetime"

    @callback
    async def async_my_climate_changed(self, event: Event):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", event.origin.name)

        old_state = self._attr_native_value
        self._attr_native_value = self.my_climate.last_ext_temperature_mesure
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:sun-clock"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.TIMESTAMP
