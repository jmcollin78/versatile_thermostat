""" Some usefull commons class """

# pylint: disable=line-too-long

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
from .const import DOMAIN, DEVICE_MANUFACTURER, ServiceConfigurationError

_LOGGER = logging.getLogger(__name__)


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


class NowClass:
    """For testing purpose only"""

    @staticmethod
    def get_now(hass: HomeAssistant) -> datetime:
        """A test function to get the now.
        For testing purpose this method can be overriden to get a specific
        timestamp.
        """
        return datetime.now(get_tz(hass))


def round_to_nearest(n: float, x: float) -> float:
    """Round a number to the nearest x (which should be decimal but not null)
    Example:
        nombre1 = 3.2
        nombre2 = 4.7
        x = 0.3

        nombre_arrondi1 = round_to_nearest(nombre1, x)
        nombre_arrondi2 = round_to_nearest(nombre2, x)

        print(nombre_arrondi1)  # Output: 3.3
        print(nombre_arrondi2)  # Output: 4.6
    """
    assert x > 0
    return round(n * (1 / x)) / (1 / x)


def check_and_extract_service_configuration(service_config) -> dict:
    """Raise a ServiceConfigurationError. In return you have a dict formatted like follows.
    Example if you call with 'climate.central_boiler/climate.set_temperature/temperature:10':
    {
        "service_domain": "climate",
        "service_name": "set_temperature",
        "entity_id": "climate.central_boiler",
        "entity_domain": "climate",
        "entity_name": "central_boiler",
        "data": {
            "temperature": "10"
        },
        "attribute_name": "temperature",
        "attribute_value: "10"
    }

    For this example 'switch.central_boiler/switch.turn_off' you will have this:
    {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_id": "switch.central_boiler",
        "entity_domain": "switch",
        "entity_name": "central_boiler",
        "data": { },
    }

    All values are striped (white space are removed) and are string
    """

    ret = {}

    if service_config is None:
        return ret

    parties = service_config.split("/")
    if len(parties) < 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. Service {service_config} should be formatted with: 'entity_name/service_name[/data]'. See README for more information."
        )
    entity_id = parties[0]
    service_name = parties[1]

    service_infos = service_name.split(".")
    if len(service_infos) != 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. The service {service_config} should be formatted like: 'domain.service_name' (ex: 'switch.turn_on'). See README for more information."
        )

    ret.update(
        {
            "service_domain": service_infos[0].strip(),
            "service_name": service_infos[1].strip(),
        }
    )

    entity_infos = entity_id.split(".")
    if len(entity_infos) != 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. The entity_id {entity_id} should be formatted like: 'domain.entity_name' (ex: 'switch.central_boiler_switch'). See README for more information."
        )

    ret.update(
        {
            "entity_domain": entity_infos[0].strip(),
            "entity_name": entity_infos[1].strip(),
            "entity_id": entity_id.strip(),
        }
    )

    if len(parties) == 3:
        data = parties[2]
        if len(data) > 0:
            data_infos = None
            data_infos = data.split(":")
            if (
                len(data_infos) != 2
                or len(data_infos[0]) <= 0
                or len(data_infos[1]) <= 0
            ):
                raise ServiceConfigurationError(
                    f"Incorrect service configuration. The data {data} should be formatted like: 'attribute:value' (ex: 'value:25'). See README for more information."
                )

            ret.update(
                {
                    "attribute_name": data_infos[0].strip(),
                    "attribute_value": data_infos[1].strip(),
                    "data": {data_infos[0].strip(): data_infos[1].strip()},
                }
            )
        else:
            raise ServiceConfigurationError(
                f"Incorrect service configuration. The data {data} should be formatted like: 'attribute:value' (ex: 'value:25'). See README for more information."
            )
    else:
        ret.update({"data": {}})

    _LOGGER.debug(
        "check_and_extract_service_configuration(%s) gives '%s'", service_config, ret
    )
    return ret


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
            if self._my_climate:
                # Only the first time
                self.my_climate_is_initialized()
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
    def my_climate_is_initialized(self):
        """Called when the associated climate is initialized"""
        return

    @callback
    async def async_my_climate_changed(
        self, event: Event
    ):  # pylint: disable=unused-argument
        """Called when my climate have change
        This method aims to be overriden to take the status change
        """
        return
