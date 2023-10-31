""" Some usefull commons class """
import logging
from datetime import timedelta, datetime
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.util import dt as dt_util

from .base_thermostat import BaseThermostat
from .const import DOMAIN, DEVICE_MANUFACTURER

_LOGGER = logging.getLogger(__name__)

def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)

class NowClass:
    """ For testing purpose only"""

    @staticmethod
    def get_now(hass: HomeAssistant) -> datetime:
        """ A test function to get the now.
            For testing purpose this method can be overriden to get a specific
            timestamp
        """
        return datetime.now( get_tz(hass))

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
        return self._my_climate

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
                _LOGGER.warning("%s - no entity to listen. Try later", self)
                self._cancel_call = async_call_later(
                    self.hass, timedelta(seconds=1), try_find_climate
                )

        await try_find_climate(None)

    @callback
    async def async_my_climate_changed(self, event: Event):         # pylint: disable=unused-argument
        """Called when my climate have change
        This method aims to be overriden to take the status change
        """
        return
