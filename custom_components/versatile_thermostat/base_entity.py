""" A base class for all VTherm entities"""

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event, async_call_later


from .const import DOMAIN, DEVICE_MANUFACTURER

from .base_thermostat import BaseThermostat

_LOGGER = logging.getLogger(__name__)


class VersatileThermostatBaseEntity(Entity):
    """A base class for all entities"""

    _my_climate: BaseThermostat
    hass: HomeAssistant
    _config_id: str
    _device_name: str

    def __init__(self, hass: HomeAssistant, config_id, device_name) -> None:
        """The CTOR"""
        self.hass = hass
        self._config_id = config_id
        self._device_name = device_name
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._my_climate = None
        self._cancel_call = None
        self._attr_has_entity_name = True

    @property
    def should_poll(self) -> bool:
        """Do not poll for those entities"""
        return False

    @property
    def my_climate(self) -> BaseThermostat | None:
        """Returns my climate if found"""
        if not self._my_climate:
            self._my_climate = self.find_my_versatile_thermostat()
            if self._my_climate:
                # Only the first time
                self.my_climate_is_initialized()
        return self._my_climate

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

    def find_my_versatile_thermostat(self) -> BaseThermostat:
        """Find the underlying climate entity"""
        try:
            component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                # _LOGGER.debug("Device_info is %s", entity.device_info)
                if entity.device_info == self.device_info:
                    _LOGGER.debug("Found %s!", entity)
                    return entity
        except KeyError:
            pass

        return None

    @callback
    async def async_added_to_hass(self):
        """Listen to my climate state change"""

        # Check delay condition
        async def try_find_climate(_):
            _LOGGER.debug(
                "%s - Calling VersatileThermostatBaseEntity.async_added_to_hass", self
            )
            mcl = self.my_climate
            if mcl:
                if self._cancel_call:
                    self._cancel_call()
                    self._cancel_call = None
                self.async_on_remove(
                    async_track_state_change_event(
                        self.hass,
                        [mcl.entity_id],
                        self.async_my_climate_changed,
                    )
                )
            else:
                _LOGGER.debug("%s - no entity to listen. Try later", self)
                self._cancel_call = async_call_later(
                    self.hass, timedelta(seconds=1), try_find_climate
                )

        await try_find_climate(None)

    @callback
    def my_climate_is_initialized(self):
        """Called when the associated climate is initialized"""
        return

    @callback
    async def async_my_climate_changed(
        self, event: Event
    ):  # pylint: disable=unused-argument
        """Called when my climate have change
        This method aims to be overridden to take the status change
        """
        return
