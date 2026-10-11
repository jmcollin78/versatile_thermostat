# pylint: disable=unused-argument
""" Implements the VersatileThermostat sensors component """
import logging
from vtherm_api.log_collector import get_vtherm_logger
import math
from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback, Event, State, CoreState

from homeassistant.const import (
    UnitOfTime,
    PERCENTAGE,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
)


from .base_thermostat import BaseThermostat
from .vtherm_central_api import VersatileThermostatAPI
from .base_entity import VersatileThermostatBaseEntity
from .commons import cleanup_orphan_entity
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_UNDERLYING_LIST,
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
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_AUTO_TPI_MODE,
    overrides,
)

_LOGGER = get_vtherm_logger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat sensors with config flow."""
    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    _LOGGER.debug("%s - Calling async_setup_entry entry=%s, data=%s", name, entry.entry_id, entry.data)

    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)
    have_valve_regulation = (
        entry.data.get(CONF_AUTO_REGULATION_MODE) == CONF_AUTO_REGULATION_VALVE
    )

    entities = None

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        if entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            entities = [
                NbActiveDeviceForBoilerSensor(hass, unique_id, name, entry.data),
                TotalPowerActiveDeviceForBoilerSensor(hass, unique_id, name, entry.data),
            ]
    else:
        entities = [
            LastTemperatureSensor(hass, unique_id, name, entry.data),
            LastExtTemperatureSensor(hass, unique_id, name, entry.data),
            TemperatureSlopeSensor(hass, unique_id, name, entry.data),
            EMATemperatureSensor(hass, unique_id, name, entry.data),
        ]
        if vt_type == CONF_THERMOSTAT_CLIMATE:
            # Batteries of the underlying devices (TRV...), with or without valve regulation
            entities.append(UnderlyingBatterySensor(hass, unique_id, name, entry.data))

        if entry.data.get(CONF_DEVICE_POWER):
            entities.append(EnergySensor(hass, unique_id, name, entry.data))
            if have_valve_regulation or entry.data.get(CONF_THERMOSTAT_TYPE) in [
                CONF_THERMOSTAT_SWITCH,
                CONF_THERMOSTAT_VALVE,
            ]:
                entities.append(MeanPowerSensor(hass, unique_id, name, entry.data))

        is_tpi_capable = entry.data.get(CONF_THERMOSTAT_TYPE) in [
            CONF_THERMOSTAT_SWITCH,
            CONF_THERMOSTAT_VALVE,
        ] or (
            entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE
            and have_valve_regulation
        )
        has_proportional_algorithm = (
            is_tpi_capable and entry.data.get(CONF_PROP_FUNCTION) is not None
        )

        if has_proportional_algorithm:
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

        # Add Auto TPI Sensor only if:
        # 1. Thermostat is TPI-capable
        # 2. TPI algorithm is selected
        # 3. Auto TPI mode is enabled in configuration
        should_have_auto_tpi = (
            is_tpi_capable
            and entry.data.get(CONF_PROP_FUNCTION) == PROPORTIONAL_FUNCTION_TPI
            and entry.data.get(CONF_AUTO_TPI_MODE, False)
        )

        if should_have_auto_tpi:
            entities.append(AutoTpiSensor(hass, unique_id, name, entry.data))
        else:
            # Cleanup: Remove orphan Auto TPI sensor from registry if it exists
            await cleanup_orphan_entity(hass, entry, "sensor", name, "auto_tpi_learning")

    if entities:
        async_add_entities(entities, True)


def find_underlying_battery_entities(hass: HomeAssistant, underlying_entity_ids: list[str]) -> list[str]:
    """Return the entity_ids of the battery sensors belonging to the devices of the given underlying entities.
    The result is deduplicated and keeps the discovery order."""
    ent_reg = er.async_get(hass)
    battery_entities: list[str] = []
    for underlying_id in underlying_entity_ids or []:
        underlying_entry = ent_reg.async_get(underlying_id)
        if underlying_entry is None or underlying_entry.device_id is None:
            continue
        for device_entry in er.async_entries_for_device(ent_reg, underlying_entry.device_id):
            if device_entry.domain != "sensor":
                continue
            if SensorDeviceClass.BATTERY not in (device_entry.device_class, device_entry.original_device_class):
                continue
            if device_entry.entity_id not in battery_entities:
                battery_entities.append(device_entry.entity_id)
    return battery_entities


class UnderlyingBatterySensor(VersatileThermostatBaseEntity, SensorEntity):
    """Exposes the lowest battery level among the devices of the underlying climates"""

    _attr_translation_key = "underlying_battery"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the underlying battery sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_underlying_battery"
        self._underlying_ids: list[str] = list(entry_infos.get(CONF_UNDERLYING_LIST) or [])
        self._battery_entities: list[str] = []
        self._levels: dict[str, float | None] = {}
        self._unsub_battery_listener = None
        self._unsub_started_listener = None

    async def async_added_to_hass(self):
        """Discover the battery entities once HA is started (the registry of the underlying
        integrations may not be populated before)"""
        await super().async_added_to_hass()

        @callback
        def _discover(*_):
            self._unsub_started_listener = None
            self._discover_battery_entities()

        @callback
        def _registry_updated(event: Event):
            """A sensor entity was added, removed or got a new device/device class: rediscover (late integrations)"""
            if not str(event.data.get("entity_id", "")).startswith("sensor."):
                return
            action = event.data.get("action")
            if action in ("create", "remove") or (action == "update" and {"device_id", "device_class"} & set(event.data.get("changes", {}))):
                self._discover_battery_entities()

        self.async_on_remove(self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _registry_updated))
        self.async_on_remove(self._cancel_battery_listener)

        if self.hass.state == CoreState.running:
            _discover()
        else:
            self._unsub_started_listener = self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _discover)

            @callback
            def _cancel_started_listener():
                if self._unsub_started_listener:
                    self._unsub_started_listener()
                    self._unsub_started_listener = None

            self.async_on_remove(_cancel_started_listener)

    @callback
    def _cancel_battery_listener(self):
        """Stop listening to the battery entities"""
        if self._unsub_battery_listener:
            self._unsub_battery_listener()
            self._unsub_battery_listener = None

    @callback
    def _discover_battery_entities(self):
        """Find the battery entities and (re)subscribe to their state changes"""
        found = find_underlying_battery_entities(self.hass, self._underlying_ids)
        if found != self._battery_entities or self._unsub_battery_listener is None:
            self._cancel_battery_listener()
            self._battery_entities = found
            if found:
                self._unsub_battery_listener = async_track_state_change_event(self.hass, found, self._battery_state_changed)
        self._recompute()

    @callback
    def _battery_state_changed(self, event: Event):
        """A battery entity state has changed"""
        self._recompute()

    @callback
    def _recompute(self):
        """Compute the lowest valid level and publish the state"""
        levels: dict[str, float | None] = {}
        for entity_id in self._battery_entities:
            level = None
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    level = float(state.state)
                    if math.isnan(level) or math.isinf(level):
                        level = None
                except (ValueError, TypeError):
                    level = None
            levels[entity_id] = level

        valid = [lvl for lvl in levels.values() if lvl is not None]
        new_value = min(valid) if valid else None
        if new_value != self._attr_native_value or levels != self._levels:
            self._levels = levels
            self._attr_native_value = new_value
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Unavailable when no battery entity is found or none has a valid value"""
        return self._attr_native_value is not None

    @property
    def extra_state_attributes(self) -> dict:
        """The battery entities with their level"""
        return {"battery_entities": dict(self._levels)}

    @property
    def icon(self) -> str | None:
        return "mdi:battery-alert-variant-outline"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return PERCENTAGE


class EnergySensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a Energy sensor which exposes the energy"""

    _attr_translation_key = "energy"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_energy"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        energy_wh = self.my_climate.total_energy
        if energy_wh is None:
            return

        if math.isnan(energy_wh) or math.isinf(energy_wh):
            raise ValueError(f"Sensor has illegal state {self.my_climate.total_energy}")

        # Convert from internal Wh to display unit (Wh or kWh)
        displayed_energy = self.my_climate.power_manager.from_watts(energy_wh, self.my_climate.power_manager.power_unit)

        old_state = self._attr_native_value
        self._attr_native_value = round(displayed_energy, self.suggested_display_precision)
        if old_state != self._attr_native_value:
            self.async_write_ha_state()
        return

    @property
    def icon(self) -> str | None:
        return "mdi:lightning-bolt"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if not self.my_climate:
            return None
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> SensorStateClass | None:
        if not self.my_climate:
            return None
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str | None:
        if not self.my_climate:
            return None

        return self.my_climate.power_manager.energy_unit

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 3


class MeanPowerSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a power sensor which exposes the mean power in a cycle"""

    _attr_translation_key = "mean_power_cycle"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_mean_power_cycle"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        mean_cycle_power = self.my_climate.power_manager.mean_cycle_power
        if mean_cycle_power is None:
            return

        if math.isnan(float(mean_cycle_power)) or math.isinf(float(mean_cycle_power)):
            raise ValueError(f"Sensor has illegal state {mean_cycle_power}")

        mean_cycle_power = float(mean_cycle_power)
        # Convert from internal Watts to display unit
        displayed_power = self.my_climate.power_manager.from_watts(mean_cycle_power, self.my_climate.power_manager.power_unit)

        old_state = self._attr_native_value
        if displayed_power is None:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(
                displayed_power,
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

        return self.my_climate.power_manager.power_unit

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested number of decimal digits for display."""
        return 3


class OnPercentSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on percent sensor which exposes the on_percent in a cycle"""

    _attr_translation_key = "power_percent"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_power_percent"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        raw_on_percent = (
            self.my_climate.proportional_algorithm.on_percent
            if self.my_climate
            and self.my_climate.has_prop
            and self.my_climate.proportional_algorithm is not None
            else None
        )
        if raw_on_percent is None:
            return
        on_percent = float(raw_on_percent)

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


class AutoTpiSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of the Auto TPI Learning state"""

    _attr_translation_key = "auto_tpi_learning"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the Auto TPI sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_auto_tpi_learning"
        self._attr_icon = "mdi:brain"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""

        # Verify has_prop and proportional_algorithm
        # proportional_algorithm can be None during initialization even if has_prop is True
        if not self.my_climate or not self.my_climate.has_prop:
            self._attr_native_value = "disabled"
            self.async_write_ha_state()
            return

        if not hasattr(self.my_climate, "auto_tpi_manager") or not self.my_climate.auto_tpi_manager:
            self._attr_native_value = "disabled"
            self.async_write_ha_state()
            return

        manager = self.my_climate.auto_tpi_manager

        # Determine state
        if manager.learning_active:
            if manager.is_in_bootstrap:
                self._attr_native_value = "bootstrap"
            else:
                self._attr_native_value = "active"
        else:
            self._attr_native_value = "off" # Or "Completed" / "Idle" depending on context, but "Off" implies not learning.

        # Update attributes
        # Update attributes
        self._attr_extra_state_attributes = {
            "coeff_int_cycles": manager.int_cycles,
            "coeff_ext_cycles": manager.ext_cycles,
            "heating_cycles_count": manager.heating_cycles_count,  # Total heating cycles
            "thermal_time_constant_hours": manager.time_constant,  # Building's thermal time constant τ
            "model_confidence": manager.confidence,  # Model confidence (R² or percentage)
            "last_learning_status": manager.state.last_learning_status,  # Reason for last learning outcome
            "learning_start_dt": manager.state.learning_start_date,
            "allow_kint_boost_on_stagnation": manager.state.allow_kint_boost,
            "allow_kext_compensation_on_overshoot": manager.state.allow_kext_overshoot,
            "bootstrap_failure_count": manager.state.bootstrap_failure_count,
        }

        # Add mode-specific attributes
        if manager._current_hvac_mode == "cool":
            self._attr_extra_state_attributes.update({
                "max_capacity_cool": manager.state.max_capacity_cool,
            })
        else:
            self._attr_extra_state_attributes.update({
                "max_capacity_heat": manager.state.max_capacity_heat,
                "capacity_heat_status": "learning" if manager.is_in_bootstrap else "learned",
                "capacity_heat_value": manager.state.max_capacity_heat,
                "capacity_heat_count": manager.state.capacity_heat_learn_count,
            })

        # Add calculated TPI coefficients
        calculated = manager.get_calculated_params()
        self._attr_extra_state_attributes.update({
            "calculated_coef_int": calculated.get(CONF_TPI_COEF_INT),
            "calculated_coef_ext": calculated.get(CONF_TPI_COEF_EXT),
        })

        self.async_write_ha_state()


class ValveOpenPercentSensor(VersatileThermostatBaseEntity, SensorEntity):
    """Representation of a on percent sensor which exposes the on_percent in a cycle"""

    _attr_translation_key = "valve_open_percent"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_valve_open_percent"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        if not self.my_climate or not hasattr(self.my_climate, "valve_open_percent"):
            _LOGGER.warning("%s - my_climate not found or no valve_open_percent property found. This could be normal at startup. Ignore the underlying device change.", self)
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

    _attr_translation_key = "on_time"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_on_time"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        on_time = (
            float(self.my_climate.on_time_sec)
            if self.my_climate and hasattr(self.my_climate, "on_time_sec")
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

    _attr_translation_key = "off_time"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_unique_id = f"{self._device_name}_off_time"

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        off_time = (
            float(self.my_climate.off_time_sec)
            if self.my_climate and hasattr(self.my_climate, "off_time_sec")
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

    _attr_translation_key = "last_temperature_date"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the last temperature datetime sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_entity_registry_enabled_default = False
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

    _attr_translation_key = "last_external_temperature_date"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the last temperature datetime sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_entity_registry_enabled_default = False
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

    _attr_translation_key = "temperature_slope"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the slope sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
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
        if (
            self._attr_native_value is None
            or not isinstance(self._attr_native_value, (int, float))
            or self._attr_native_value == 0
        ):
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

    _attr_translation_key = "regulated_temperature"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the regulated temperature sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
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

    _attr_translation_key = "ema_temperature"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the regulated temperature sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
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
    """Representation of the  number of VTherm
    which are active and configured to activate the boiler"""


    _attr_has_entity_name = True
    _attr_translation_key = "nb_device_active_boiler"

    # TODO remove all listener mecanisms
    _entity_component_unrecorded_attributes = SensorEntity._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset({"active_device_ids"})
    )

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        self._hass = hass
        self._config_id = unique_id
        self._device_name = entry_infos.get(CONF_NAME)
        self._attr_unique_id = "nb_device_active_boiler"
        self._attr_value = self._attr_native_value = None  # default value
        self._entities = []
        self._attr_active_device_ids = []  # Holds the entity ids of active devices``
        self._cancel_listener_nb_active: Callable | None = None

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
            entry_type=None,
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
        api.central_boiler_manager.register_nb_device_active_boiler(self)

    async def listen_vtherms_entities(self):
        """Initialize the listening of state change of VTherms"""

        # Listen to all VTherm underlying state change
        self._entities = []
        # underlying_entities_id = []

        component: EntityComponent[ClimateEntity] = self.hass.data.get(CLIMATE_DOMAIN)
        if component is None:
            _LOGGER.warning("%s - No climate component found in hass.data", self)
            return

        self.cancel_listening_nb_active()

        for entity in list(component.entities):
            if isinstance(entity, BaseThermostat) and entity.is_used_by_central_boiler:
                self._entities.append(entity)
                # for under in entity.activable_underlying_entities:
                #    underlying_entities_id.append(under.entity_id)
        # if len(underlying_entities_id) > 0:
        # Arme l'écoute de la première entité
        # self._cancel_listener_nb_active = async_track_state_change_event(
        #     self._hass,
        #     underlying_entities_id,
        #     self.calculate_nb_active_devices,
        # )
        #    _LOGGER.info(
        #        "%s - the underlyings that could control the central boiler are %s",
        #        self,
        #        underlying_entities_id,
        #     )
        # Fix 1406
        # self.async_on_remove(self._cancel_listener_nb_active)
        # else:
        #    _LOGGER.debug("%s - no VTherm could control the central boiler", self)

        await self.calculate_nb_active_devices(None)

    async def calculate_nb_active_devices(self, event: Event):
        """Calculate the number of active VTherm and the total active power that have an
        influence on the central boiler and update the list of active device names."""

        # _LOGGER.debug("%s- calculate_nb_active_devices_or_power - the event is %s ", self, event)

        if event is not None:
            new_state: State = event.data.get("new_state")
            # _LOGGER.debug(
            #     "%s - calculate_nb_active_devices_or_power new_state is %s", self, new_state
            # )
            if not new_state:
                return

            old_state: State = event.data.get("old_state")

            # For underlying climate, we need to observe also the hvac_action if available
            new_hvac_action = new_state.attributes.get("hvac_action")
            old_hvac_action = old_state.attributes.get("hvac_action") if old_state is not None else None

            # Filter events that are not interesting for us
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
                "%s - After examining the device_actives, device_actives is %s",
                entity.name,
                device_actives,
            )

            nb_active += len(device_actives)
            active_device_ids.extend(device_actives)

        self._attr_native_value = nb_active
        self._attr_active_device_ids = active_device_ids

        self.async_write_ha_state()
        await VersatileThermostatAPI.get_vtherm_api(self._hass).central_boiler_manager.refresh_central_boiler_custom_attributes()

    @property
    def active_device_ids(self) -> list:
        """Get the list of active device id"""
        return self._attr_active_device_ids

    def __str__(self):
        return f"{self.name}"

    def cancel_listening_nb_active(self):
        """Cancel the listening of underlying VTherm state changes"""
        if self._cancel_listener_nb_active is not None:
            try:
                self._cancel_listener_nb_active()  # pylint: disable=not-callable
            except (ValueError, TypeError):  # the listener could be already cancelled
                pass
            self._cancel_listener_nb_active = None

    @overrides
    async def async_will_remove_from_hass(self) -> None:
        """Called when entity is about to be removed from hass"""
        self.cancel_listening_nb_active()


class TotalPowerActiveDeviceForBoilerSensor(NbActiveDeviceForBoilerSensor):
    """Representation of the total power of VTherm
    which are active and configured to activate the boiler"""

    _attr_translation_key = "total_power_active_boiler"

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the energy sensor"""
        super().__init__(hass, unique_id, name, entry_infos)
        self._attr_unique_id = "total_power_active_boiler"
        self._attr_value = self._attr_native_value = None  # default value
        self._cancel_listener_power: callable | None = None

    @property
    def icon(self) -> str | None:
        return "mdi:flash-auto"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.POWER

    @property
    def native_unit_of_measurement(self) -> str | None:
        return VersatileThermostatAPI.get_vtherm_api(self._hass).central_power_manager.power_unit

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 2

    @overrides
    async def async_added_to_hass(self) -> None:
        # do not ! await super().async_added_to_hass()

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.central_boiler_manager.register_total_power_active_boiler(self)

    async def listen_vtherms_entities(self):
        """Initialize the listening of state change of VTherms"""

        # Listen to all VTherm state change
        self._entities = []
        entities_id = []

        component: EntityComponent[ClimateEntity] = self.hass.data.get(CLIMATE_DOMAIN)
        if component is None:
            _LOGGER.warning("%s - No climate component found in hass.data", self)
            return

        self.cancel_listening_power()

        for entity in list(component.entities):
            if isinstance(entity, BaseThermostat) and entity.is_used_by_central_boiler:
                self._entities.append(entity)
                entities_id.append(entity.entity_id)

        if len(self._entities) > 0:
            # Arme l'écoute de la première entité
            self._cancel_listener_power = async_track_state_change_event(
                self._hass,
                entities_id,
                self.calculate_total_power,
            )
            _LOGGER.info(
                "%s - the VTherm that could control the central boiler are %s",
                self,
                entities_id,
            )
            # Fix 1406
            # self.async_on_remove(self._cancel_listener_power)
        else:
            _LOGGER.debug("%s - no VTherm could control the central boiler", self)

        await self.calculate_total_power(None)

    async def calculate_total_power(self, event: Event):
        """Calculate the total active power that have an
        influence on the central boiler and update the list of active device names."""

        # _LOGGER.debug("%s- calculate_nb_active_devices_or_power - the event is %s ", self, event)

        if event is not None:
            new_state: State = event.data.get("new_state")
            # _LOGGER.debug(
            #     "%s - calculate_nb_active_devices_or_power new_state is %s", self, new_state
            # )
            if not new_state:
                return

            old_state: State = event.data.get("old_state")

            # For underlying climate, we need to observe also the hvac_action if available
            new_mean_cycle_power = new_state.attributes.get("power_manager", {}).get("mean_cycle_power")
            old_mean_cycle_power = old_state.attributes.get("power_manager", {}).get("mean_cycle_power") if old_state is not None else None

            # Filter events that are not interesting for us
            if old_state is not None and new_mean_cycle_power == old_mean_cycle_power:
                # A false state change
                return

            _LOGGER.debug(
                "%s - calculating the total power of active underlying device for boiler activation. mean_power_cycle change from %s to %s",
                self,
                old_mean_cycle_power,
                new_mean_cycle_power,
            )
        else:
            _LOGGER.debug(
                "%s - calculating the total power of active underlying device for boiler activation. First time calculation",
                self,
            )

        total_active_power = 0
        active_device_ids = []

        for entity in self._entities:
            if getattr(entity, "is_sleeping", False) is True:
                continue

            mean_cycle_power = entity.power_manager.mean_cycle_power
            if mean_cycle_power is None or mean_cycle_power <= 0:
                continue

            _LOGGER.debug(
                "%s - After examining the mean_cycle_power, mean_cycle_power is %s",
                entity.name,
                mean_cycle_power,
            )

            active_device_ids.extend([under.entity_id for under in entity.activable_underlying_entities])

            total_active_power += mean_cycle_power

        central_power_manager = VersatileThermostatAPI.get_vtherm_api(self._hass).central_power_manager
        self._attr_native_value = central_power_manager.from_watts(
            total_active_power,
            central_power_manager.power_unit,
        )
        self._attr_active_device_ids = active_device_ids

        self.async_write_ha_state()
        await VersatileThermostatAPI.get_vtherm_api(self._hass).central_boiler_manager.refresh_central_boiler_custom_attributes()

    @property
    def active_device_ids(self) -> list:
        """Get the list of active device id"""
        return self._attr_active_device_ids

    def __str__(self):
        return f"{self.name}"

    @overrides
    async def async_will_remove_from_hass(self) -> None:
        """Called when entity is about to be removed from hass"""
        self.cancel_listening_power()

    def cancel_listening_power(self):
        """Cancel the listening of underlying VTherm state changes"""
        if self._cancel_listener_power is not None:
            self._cancel_listener_power()
            self._cancel_listener_power = None
