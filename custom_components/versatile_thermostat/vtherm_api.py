""" The API of Versatile Thermostat"""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_AUTO_REGULATION_EXPERT,
    CONF_SHORT_EMA_PARAMS,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_CENTRAL_CONFIG,
)

VTHERM_API_NAME = "vtherm_api"

_LOGGER = logging.getLogger(__name__)


class VersatileThermostatAPI(dict):
    """The VersatileThermostatAPI"""

    _hass: HomeAssistant = None

    @classmethod
    def get_vtherm_api(cls, hass=None):
        """Get the eventual VTherm API class instance or
        instantiate it if it doesn't exists"""
        if hass is not None:
            VersatileThermostatAPI._hass = hass

        if VersatileThermostatAPI._hass is None:
            return None

        domain = VersatileThermostatAPI._hass.data.get(DOMAIN)
        if not domain:
            VersatileThermostatAPI._hass.data.setdefault(DOMAIN, {})

        ret = VersatileThermostatAPI._hass.data.get(DOMAIN).get(VTHERM_API_NAME)
        if ret is None:
            ret = VersatileThermostatAPI()
            VersatileThermostatAPI._hass.data[DOMAIN][VTHERM_API_NAME] = ret
        return ret

    def __init__(self) -> None:
        _LOGGER.debug("building a VersatileThermostatAPI")
        super().__init__()
        self._expert_params = None
        self._short_ema_params = None
        self._central_boiler_entity = None

    def find_central_configuration(self):
        """Search for a central configuration"""
        for config_entry in VersatileThermostatAPI._hass.config_entries.async_entries(
            DOMAIN
        ):
            if (
                config_entry.data.get(CONF_THERMOSTAT_TYPE)
                == CONF_THERMOSTAT_CENTRAL_CONFIG
            ):
                central_config = config_entry
                return central_config
        return None

    def add_entry(self, entry: ConfigEntry):
        """Add a new entry"""
        _LOGGER.debug("Add the entry %s", entry.entry_id)
        # Add the entry in hass.data
        VersatileThermostatAPI._hass.data[DOMAIN][entry.entry_id] = entry

    def remove_entry(self, entry: ConfigEntry):
        """Remove an entry"""
        _LOGGER.debug("Remove the entry %s", entry.entry_id)
        VersatileThermostatAPI._hass.data[DOMAIN].pop(entry.entry_id)
        # If not more entries are preset, remove the API
        if len(self) == 0:
            _LOGGER.debug("No more entries-> Remove the API from DOMAIN")
            VersatileThermostatAPI._hass.data.pop(DOMAIN)

    def set_global_config(self, config):
        """Read the global configuration from configuration.yaml file"""
        _LOGGER.info("Read global config from configuration.yaml")

        self._expert_params = config.get(CONF_AUTO_REGULATION_EXPERT)
        if self._expert_params:
            _LOGGER.debug("We have found expert params %s", self._expert_params)

        self._short_ema_params = config.get(CONF_SHORT_EMA_PARAMS)
        if self._short_ema_params:
            _LOGGER.debug("We have found short ema params %s", self._short_ema_params)

    def register_central_boiler(self, central_boiler_entity):
        """Register the central boiler entity. This is used by the CentralBoilerBinarySensor
        class to register itself at creation"""
        self._central_boiler_entity = central_boiler_entity

    async def reload_central_boiler_entities_list(self):
        """Reload the central boiler list of entities if a central boiler is used"""
        if self._central_boiler_entity is not None:
            await self._central_boiler_entity.listen_vtherms_entities()

    @property
    def self_regulation_expert(self):
        """Get the self regulation params"""
        return self._expert_params

    @property
    def short_ema_params(self):
        """Get the self regulation params"""
        return self._short_ema_params

    @property
    def hass(self):
        """Get the HomeAssistant object"""
        return VersatileThermostatAPI._hass
