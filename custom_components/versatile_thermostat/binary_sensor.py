""" Implements the VersatileThermostat binary sensors component """
# pylint: disable=unused-argument, line-too-long

import logging

from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    # CoreState,
)

from homeassistant.const import STATE_ON, STATE_OFF

from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .vtherm_api import VersatileThermostatAPI
from .base_entity import VersatileThermostatBaseEntity
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
    CONF_USE_CENTRAL_BOILER_FEATURE,
    overrides,
    EventType,
    gen_attr_uniq_id,
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

    entities = None

    if vt_type == CONF_THERMOSTAT_CENTRAL_CONFIG:
        if entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE):
            # we capture here the configuration for central boiler feature
            api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
            api.central_boiler_manager.post_init(entry.data)
            entities = [
                CentralBoilerBinarySensor(hass, unique_id, name, entry.data),
            ]
    else:
        entities = [
            SafetyBinarySensor(hass, unique_id, name, entry.data),
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

    if entities:
        async_add_entities(entities, True)


class SafetyBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the security state"""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,  # pylint: disable=unused-argument
        entry_infos,
    ) -> None:
        """Initialize the SafetyState Binary sensor"""
        super().__init__(hass, unique_id, name)
        self._attr_name = "Safety state"
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "safety_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_is_on
        self._attr_is_on = self.my_climate.safety_manager.is_safety_detected
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
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "overpowering_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

        old_state = self._attr_is_on
        self._attr_is_on = self.my_climate.overpowering_state is STATE_ON
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
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "window_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)

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
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "motion_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)
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
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "presence_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""

        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)
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
        self._attr_unique_id = gen_attr_uniq_id(unique_id, entry_infos, "window_bypass_state")
        self._attr_is_on = False

    @callback
    async def async_my_climate_changed(self, event: Event = None):
        """Called when my climate have change"""
        # _LOGGER.debug("%s - climate state change", self._attr_unique_id)
        old_state = self._attr_is_on
        if self.my_climate.is_window_bypass in [True, False]:
            self._attr_is_on = self.my_climate.is_window_bypass
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

    _entity_component_unrecorded_attributes = BinarySensorEntity._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset({"is_central_boiler_configured", "is_central_boiler_ready", "central_boiler_manager"})
    )

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
        self._entry_infos = entry_infos
        self._hass = hass

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

        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        api.central_boiler_manager.register_central_boiler(self)

        # Listen to central boiler events
        self.async_on_remove(
            self._hass.bus.async_listen(
                EventType.CENTRAL_BOILER_EVENT.value,
                self._handle_central_boiler_event,
            )
        )

        self.update_custom_attributes()
        self.async_write_ha_state()

    @callback
    def _handle_central_boiler_event(self, event):
        """Handle central boiler event to update internal state."""
        _LOGGER.debug("%s - Received central boiler event: %s", self, event.data)
        if "central_boiler" in event.data:
            new_state = event.data["central_boiler"]
            if self._attr_is_on != new_state:
                self._attr_is_on = new_state
                self.refresh_custom_attributes()

    def refresh_custom_attributes(self):
        """Refresh the custom attributes"""
        self.update_custom_attributes()
        self.async_write_ha_state()

    def update_custom_attributes(self):
        """Update the custom extra attributes for the entity"""
        self._attr_extra_state_attributes = {"central_boiler_state": STATE_ON if self._attr_is_on else STATE_OFF}
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api()
        cb_manager = api.central_boiler_manager
        cb_manager.add_custom_attributes(self._attr_extra_state_attributes)

    def __str__(self):
        return f"VersatileThermostat-{self.name}"
