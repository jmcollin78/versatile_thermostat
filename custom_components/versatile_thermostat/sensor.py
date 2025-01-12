# pylint: disable=unused-argument
""" Implements the VersatileThermostat sensors component """
import logging
import math

from homeassistant.core import HomeAssistant, callback, Event, CoreState, State

from homeassistant.const import (
    UnitOfTime,
    UnitOfPower,
    UnitOfEnergy,
    PERCENTAGE,
    EVENT_HOMEASSISTANT_START,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
)


from .base_thermostat import BaseThermostat
from .vtherm_api import VersatileThermostatAPI
from .base_entity import VersatileThermostatBaseEntity
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_DEVICE_POWER,
    CONF_PROP_FUNCTION,
    PROPORTIONAL_FUNCTION_TPI,
    CONF_THERMOSTAT_SWITCH,
    CONF_THERMOSTAT_VALVE,
    CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_USE_CENTRAL_BOILER_FEATURE,
    CONF_AUTO_REGULATION_VALVE,
    CONF_AUTO_REGULATION_MODE,
    overrides,
)

THRESHOLD_WATT_KILO = 100

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
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)
    have_valve_regulation = (
        entry.data.get(CONF_AUTO_REGULATION_MODE) == CONF_AUTO_REGULATION_VALVE
    )

    entities = None

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        if entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            entities = [
                NbActiveDeviceForBoilerSensor(hass, unique_id, name, entry.data)
            ]
    else:
        entities = [
            LastTemperatureSensor(hass, unique_id, name, entry.data),
            LastExtTemperatureSensor(hass, unique_id, name, entry.data),
            TemperatureSlopeSensor(hass, unique_id, name, entry.data),
            EMATemperatureSensor(hass, unique_id, name, entry.data),
        ]
        if entry.data.get(CONF_DEVICE_POWER):
            entities.append(EnergySensor(hass, unique_id, name, entry.data))
            if entry.data.get(CONF_THERMOSTAT_TYPE) in [
                CONF_THERMOSTAT_SWITCH,
                CONF_THERMOSTAT_VALVE,
            ]:
                entities.append(MeanPowerSensor(hass, unique_id, name, entry.data))

        if entry.data.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI:
            entities.append(OnPercentSensor(hass, unique_id, name, entry.data))
            entities.append(OnTimeSensor(hass, unique_id, name, entry.data))
            entities.append(OffTimeSensor(hass, unique_id, name, entry.data))

        if (
            entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_VALVE
            or have_valve_regulation
        ):
            entities.append(ValveOpenPercentSensor(hass, unique_id, name, entry.data))

        if (
            entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE
            and not have_valve_regulation
        ):
            entities.append(
                RegulatedTemperatureSensor(hass, unique_id, name, entry.data)
            )

    if entities:
        async_add_entities(entities, True)


class EnergySensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a Energy sensor which exposes the energy"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Energy"
        self._attr_unique_id = f"{self._device_name}_energy"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        energy = self.my_climate.total_energy
        if energy is None:
            return

        if math.isnan(energy) or math.isinf(energy):
            raise ValueError(f"Sensor has illegal state {self.my_climate.total_energy}")

        old_state = self._attr_native_value
        self._attr_native_value = round(energy, self.suggested_display_precision)
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
        if not self.my_climate:
            return None

        if self.my_climate.power_manager.device_power > THRESHOLD_WATT_KILO:
            return UnitOfEnergy.WATT_HOUR
        else:
            return UnitOfEnergy.KILO_WATT_HOUR

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
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        if math.isnan(
            float(self.my_climate.power_manager.mean_cycle_power)
        ) or math.isinf(self.my_climate.power_manager.mean_cycle_power):
            raise ValueError(
                f"Sensor has illegal state {self.my_climate.power_manager.mean_cycle_power}"
            )

        old_state = self._attr_native_value
        self._attr_native_value = round(
            self.my_climate.power_manager.mean_cycle_power,
            self.suggested_display_precision,
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
        if not self.my_climate:
            return None

        if self.my_climate.power_manager.device_power > THRESHOLD_WATT_KILO:
            return UnitOfPower.WATT
        else:
            return UnitOfPower.KILO_WATT

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
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        on_percent = (
            float(self.my_climate.proportional_algorithm.on_percent)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )
        if on_percent is None:
            return

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
        return PERCENTAGE

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 1


class ValveOpenPercentSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on percent sensor which exposes the on_percent in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Valve open percent"
        self._attr_unique_id = f"{self._device_name}_valve_open_percent"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        if not self.my_climate or not hasattr(self.my_climate, "valve_open_percent"):
            _LOGGER.warning("%s - my_climate not found or no valve_open_percent property found. This could be normal at startup. Ignore the underlying device change.")
            return

        old_state = self._attr_native_value
        self._attr_native_value = self.my_climate.valve_open_percent
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:pipe-valve"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.POWER_FACTOR

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return PERCENTAGE

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 0


class OnTimeSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on time sensor which exposes the on_time_sec in a cycle"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "On time"
        self._attr_unique_id = f"{self._device_name}_on_time"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        on_time = (
            float(self.my_climate.proportional_algorithm.on_time_sec)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )

        if on_time is None:
            return

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
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        off_time = (
            float(self.my_climate.proportional_algorithm.off_time_sec)
            if self.my_climate and self.my_climate.proportional_algorithm
            else None
        )
        if off_time is None:
            return

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
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_native_value
        self._attr_native_value = self.my_climate.last_temperature_measure
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
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_native_value
        self._attr_native_value = self.my_climate.last_ext_temperature_measure
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:sun-clock"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.TIMESTAMP


class TemperatureSlopeSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a sensor which exposes the temperature slope curve"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the slope sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Temperature slope"
        self._attr_unique_id = f"{self._device_name}_temperature_slope"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        last_slope = self.my_climate.last_temperature_slope
        if last_slope is None:
            return

        if math.isnan(last_slope) or math.isinf(last_slope):
            raise ValueError(f"Sensor has illegal state {last_slope}")

        old_state = self._attr_native_value
        self._attr_native_value = round(last_slope, self.suggested_display_precision)
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        if self._attr_native_value is None or self._attr_native_value == 0:
            return "mdi:thermometer"
        elif self._attr_native_value > 0:
            return "mdi:thermometer-chevron-up"
        else:
            return "mdi:thermometer-chevron-down"

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        if not self.my_climate:
            return None

        return self.my_climate.temperature_unit + "/hour"

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 2


class RegulatedTemperatureSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a Energy sensor which exposes the energy"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the regulated temperature sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Regulated temperature"
        self._attr_unique_id = f"{self._device_name}_regulated_temperature"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        new_temp = self.my_climate.regulated_target_temp
        if new_temp is None:
            return

        if math.isnan(new_temp) or math.isinf(new_temp):
            raise ValueError(f"Sensor has illegal state {new_temp}")

        old_state = self._attr_native_value
        self._attr_native_value = round(new_temp, self.suggested_display_precision)
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:thermometer-auto"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        if not self.my_climate:
            return self.hass.config.units.temperature_unit
        return self.my_climate.temperature_unit

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 1


class EMATemperatureSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a Exponential Moving Average temp"""

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the regulated temperature sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "EMA temperature"
        self._attr_unique_id = f"{self._device_name}_ema_temperature"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        new_ema = self.my_climate.ema_temperature
        if new_ema is None:
            return

        if math.isnan(new_ema) or math.isinf(new_ema):
            raise ValueError(f"Sensor has illegal state {new_ema}")

        old_state = self._attr_native_value
        self._attr_native_value = new_ema
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:thermometer-lines"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        if not self.my_climate:
            return self.hass.config.units.temperature_unit
        return self.my_climate.temperature_unit

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 2


class NbActiveDeviceForBoilerSensor(SensorEntity):
    """Representation of the threshold of the number of VTherm
    which should be active to activate the boiler"""

    _entity_component_unrecorded_attributes = SensorEntity._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset({"active_device_ids"})
    )

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        self._hass = hass
        self._config_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)
        self._attr_name = "Nb device active for boiler"
        self._attr_unique_id = "nb_device_active_boiler"
        self._attr_value = self._attr_native_value = None  # default value
        self._entities = []
        self._attr_active_device_ids = []  # Holds the entity ids of active devices

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes for the sensor."""
        return {
            "active_device_ids": self._attr_active_device_ids,
        }

    @property
    def icon(self) -> str | None:
        return "mdi:heat-wave"

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

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 0

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.register_nb_device_active_boiler(self)

        @callback
        async def _async_startup_internal(*_):
            _LOGGER.debug("%s - Calling async_startup_internal", self)
            await self.listen_vtherms_entities()

        if self.hass.state == CoreState.running:
            await _async_startup_internal()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, _async_startup_internal
            )

    async def listen_vtherms_entities(self):
        """Initialize the listening of state change of VTherms"""

        # Listen to all VTherm state change
        self._entities = []
        underlying_entities_id = []

        component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
        for entity in component.entities:
            if isinstance(entity, BaseThermostat) and entity.is_used_by_central_boiler:
                self._entities.append(entity)
                for under in entity.activable_underlying_entities:
                    underlying_entities_id.append(under.entity_id)
        if len(underlying_entities_id) > 0:
            # Arme l'écoute de la première entité
            listener_cancel = async_track_state_change_event(
                self._hass,
                underlying_entities_id,
                self.calculate_nb_active_devices,
            )
            _LOGGER.info(
                "%s - the underlyings that could control the central boiler are %s",
                self,
                underlying_entities_id,
            )
            self.async_on_remove(listener_cancel)
        else:
            _LOGGER.debug("%s - no VTherm could control the central boiler", self)

        await self.calculate_nb_active_devices(None)

    async def calculate_nb_active_devices(self, event: Event):
        """Calculate the number of active VTherm that have an
        influence on the central boiler and update the list of active device names."""

        # _LOGGER.debug("%s- calculate_nb_active_devices - the event is %s ", self, event)

        if event is not None:
            new_state: State = event.data.get("new_state")
            # _LOGGER.debug(
            #     "%s - calculate_nb_active_devices new_state is %s", self, new_state
            # )
            if not new_state:
                return

            old_state: State = event.data.get("old_state")

            # For underlying climate, we need to observe also the hvac_action if available
            new_hvac_action = new_state.attributes.get("hvac_action")
            old_hvac_action = (
                old_state.attributes.get("hvac_action")
                if old_state is not None
                else None
            )

            # Filter events that are not interested for us
            if (
                old_state is not None
                and new_state.state == old_state.state
                and new_hvac_action == old_hvac_action
                # issue 698 - force recalculation when underlying climate doesn't have any hvac_action
                and new_hvac_action is not None
            ):
                # A false state change
                return

            _LOGGER.debug(
                "%s - calculating the number of active underlying device for boiler activation. change change from %s to %s",
                self,
                old_state,
                new_state,
            )
        else:
            _LOGGER.debug(
                "%s - calculating the number of active underlying device for boiler activation. First time calculation",
                self,
            )

        nb_active = 0
        active_device_ids = []

        for entity in self._entities:
            device_actives = entity.device_actives
            _LOGGER.debug(
                "After examining the hvac_action of %s, device_actives is %s",
                entity.name,
                device_actives,
            )

            nb_active += len(device_actives)
            active_device_ids.extend(device_actives)

        self._attr_native_value = nb_active
        self._attr_active_device_ids = active_device_ids

        self.async_write_ha_state()

    @property
    def active_device_ids(self) -> list:
        """Get the list of active device id"""
        return self._attr_active_device_ids

    def __str__(self):
        return f"VersatileThermostat-{self.name}"
