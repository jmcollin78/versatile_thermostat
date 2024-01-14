""" Implements the VersatileThermostat binary sensors component """
# pylint: disable=unused-argument

import logging

from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    CoreState,
    HomeAssistantError,
)

from homeassistant.const import STATE_ON, STATE_OFF, EVENT_HOMEASSISTANT_START

from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    HVACAction,
    DOMAIN as CLIMATE_DOMAIN,
)

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .vtherm_api import VersatileThermostatAPI
from .commons import (
    VersatileThermostatBaseEntity,
    check_and_extract_service_configuration,
)
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    CONF_USE_POWER_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_WINDOW_FEATURE,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
    CONF_CENTRAL_BOILER_ACTIVATION_SRV,
    CONF_CENTRAL_BOILER_DEACTIVATION_SRV,
    overrides,
    EventType,
    send_vtherm_event,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat binary sensors with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)
    vt_type = entry.data.get(CONF_THERMOSTAT_TYPE)

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        entities = [
            CentralBoilerBinarySensor(hass, unique_id, name, entry.data),
        ]
    else:
        entities = [
            SecurityBinarySensor(hass, unique_id, name, entry.data),
            WindowByPassBinarySensor(hass, unique_id, name, entry.data),
        ]
        if entry.data.get(CONF_USE_MOTION_FEATURE):
            entities.append(MotionBinarySensor(hass, unique_id, name, entry.data))
        if entry.data.get(CONF_USE_WINDOW_FEATURE):
            entities.append(WindowBinarySensor(hass, unique_id, name, entry.data))
        if entry.data.get(CONF_USE_PRESENCE_FEATURE):
            entities.append(PresenceBinarySensor(hass, unique_id, name, entry.data))
        if entry.data.get(CONF_USE_POWER_FEATURE):
            entities.append(OverpoweringBinarySensor(hass, unique_id, name, entry.data))

    async_add_entities(entities, True)


class SecurityBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the security state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the SecurityState Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Security state"
        self._attr_unique_id = f"{self._device_name}_security_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_is_on
        self._attr_is_on = self.my_climate.security_state is True
        if old_state != self._attr_is_on:
            self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.SAFETY

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:shield-alert"
        else:
            return "mdi:shield-check-outline"


class OverpoweringBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the overpowering state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the OverpoweringState Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Overpowering state"
        self._attr_unique_id = f"{self._device_name}_overpowering_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_is_on
        self._attr_is_on = self.my_climate.overpowering_state is True
        if old_state != self._attr_is_on:
            self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.POWER

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:flash-alert-outline"
        else:
            return "mdi:flash-outline"


class WindowBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the window state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the WindowState Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Window state"
        self._attr_unique_id = f"{self._device_name}_window_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_is_on
        # Issue 120 - only take defined presence value
        if self.my_climate.window_state in [
            STATE_ON,
            STATE_OFF,
        ] or self.my_climate.window_auto_state in [STATE_ON, STATE_OFF]:
            self._attr_is_on = (
                self.my_climate.window_state == STATE_ON
                or self.my_climate.window_auto_state == STATE_ON
            )
            if old_state != self._attr_is_on:
                self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.WINDOW

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            if self.my_climate.window_state == STATE_ON:
                return "mdi:window-open-variant"
            else:
                return "mdi:window-open"
        else:
            return "mdi:window-closed-variant"


class MotionBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the motion state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the MotionState Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Motion state"
        self._attr_unique_id = f"{self._device_name}_motion_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", self._attr_unique_id)
        old_state = self._attr_is_on
        # Issue 120 - only take defined presence value
        if self.my_climate.motion_state in [STATE_ON, STATE_OFF]:
            self._attr_is_on = self.my_climate.motion_state == STATE_ON
            if old_state != self._attr_is_on:
                self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.MOTION

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:motion-sensor"
        else:
            return "mdi:motion-sensor-off"


class PresenceBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the presence state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the PresenceState Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Presence state"
        self._attr_unique_id = f"{self._device_name}_presence_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""

        _LOGGER.debug("%s - climate state change", self._attr_unique_id)
        old_state = self._attr_is_on
        # Issue 120 - only take defined presence value
        if self.my_climate.presence_state in [STATE_ON, STATE_OFF]:
            self._attr_is_on = self.my_climate.presence_state == STATE_ON
            if old_state != self._attr_is_on:
                self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.PRESENCE

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:home-account"
        else:
            return "mdi:nature-people"


class WindowByPassBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the Window ByPass state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the WindowByPass Binary sensor"""
        super().__init__(hass, unique_id, entry_infos.get(CONF_NAME))
        self._attr_name = "Window bypass"
        self._attr_unique_id = f"{self._device_name}_window_bypass_state"
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        _LOGGER.debug("%s - climate state change", self._attr_unique_id)
        old_state = self._attr_is_on
        if self.my_climate.window_bypass_state in [True, False]:
            self._attr_is_on = self.my_climate.window_bypass_state
            if old_state != self._attr_is_on:
                self.async_write_ha_state()
        return

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.RUNNING

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:window-shutter-cog"
        else:
            return "mdi:window-shutter-auto"


class CentralBoilerBinarySensor(BinarySensorEntity):
    """Representation of a BinarySensor which exposes the Central Boiler state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the CentralBoiler Binary sensor"""
        self._config_id = unique_id
        self._attr_name = "Central boiler"
        self._attr_unique_id = "central_boiler_state"
        self._attr_is_on = False
        self._device_name = entry_infos.get(CONF_NAME)
        self._entities = []
        self._hass = hass
        self._service_activate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV)
        )
        self._service_deactivate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV)
        )

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
    def device_class(self) -> BinarySensorDeviceClass | None:
        return BinarySensorDeviceClass.RUNNING

    @property
    def icon(self) -> str | None:
        if self._attr_is_on:
            return "mdi:water-boiler"
        else:
            return "mdi:water-boiler-off"

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        async def _async_startup_internal(*_):
            _LOGGER.debug("%s - Calling async_startup_internal", self)
            api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(
                self._hass
            )
            api.register_central_boiler(self)
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
        entities_id = []

        component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
        for entity in component.entities:
            if isinstance(entity, BaseThermostat) and entity.is_used_by_central_boiler:
                self._entities.append(entity)
                entities_id.append(entity.entity_id)
        if len(self._entities) > 0:
            # Arme l'écoute de la première entité
            listener_cancel = async_track_state_change_event(
                self._hass,
                entities_id,
                self.calculate_central_boiler_state,
            )
            _LOGGER.info(
                "%s - VTherm that could controls the central boiler are %s",
                self,
                entities_id,
            )
            self.async_on_remove(listener_cancel)
        else:
            _LOGGER.debug("%s - no VTherm could controls the central boiler", self)

        await self.calculate_central_boiler_state(None)

    async def calculate_central_boiler_state(self, _):
        """Calculate the central boiler state depending on all VTherm that
        controls this central boiler"""

        _LOGGER.debug("%s - calculating the new central boiler state", self)
        active = False
        for entity in self._entities:
            _LOGGER.debug(
                "Examining the hvac_action of %s",
                entity.name,
            )
            if (
                entity.hvac_mode == HVACMode.HEAT
                and entity.hvac_action == HVACAction.HEATING
            ):
                active = True
                break

        if self._attr_is_on != active:
            try:
                if active:
                    await self.call_service(self._service_activate)
                    _LOGGER.info("%s - central boiler have been turned on", self)
                else:
                    await self.call_service(self._service_deactivate)
                    _LOGGER.info("%s - central boiler have been turned off", self)
                self._attr_is_on = active
                send_vtherm_event(
                    hass=self._hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=self,
                    data={"central_boiler": active},
                )
                self.async_write_ha_state()
            except HomeAssistantError as err:
                _LOGGER.error(
                    "%s - Impossible to activate/deactivat boiler due to error %s."
                    "Central boiler will not being controled by VTherm."
                    "Please check your service configuration. Cf. README.",
                    self,
                    err,
                )

    async def call_service(self, service_config: dict):
        """Make a call to a service if correctly configured"""
        if not service_config:
            return

        await self._hass.services.async_call(
            service_config["service_domain"],
            service_config["service_name"],
            service_data=service_config["data"],
            target={
                "entity_id": service_config["entity_id"],
            },
        )

    def __str__(self):
        return f"VersatileThermostat-{self.name}"
