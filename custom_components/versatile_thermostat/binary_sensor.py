""" Implements the VersatileThermostat binary sensors component """
import logging

from homeassistant.core import HomeAssistant, callback, Event

from homeassistant.const import STATE_ON, STATE_OFF

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commons import VersatileThermostatBaseEntity
from .const import (
    CONF_NAME,
    CONF_USE_POWER_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_WINDOW_FEATURE,
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

    entities = [SecurityBinarySensor(hass, unique_id, name, entry.data),WindowByPassBinarySensor(hass, unique_id, name, entry.data)]
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
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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

#PR - Adding Window ByPass
class WindowByPassBinarySensor(VersatileThermostatBaseEntity, BinarySensorEntity):
    """Representation of a BinarySensor which exposes the Window ByPass state"""

    def __init__(
        self, hass: HomeAssistant, unique_id, name, entry_infos
    ) -> None:  # pylint: disable=unused-argument
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
            return "mdi:check-circle-outline"
        else:
            return "mdi:alpha-b-circle-outline"