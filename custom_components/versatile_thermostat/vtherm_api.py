""" The API of Versatile Thermostat"""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_AUTO_REGULATION_EXPERT,
)

VTHERM_API_NAME = "vtherm_api"

_LOGGER = logging.getLogger(__name__)


class VersatileThermostatAPI(dict):
    """The VersatileThermostatAPI"""

    _hass: HomeAssistant
    # _entries: Dict(str, ConfigEntry)

    @classmethod
    def get_vtherm_api(cls, hass: HomeAssistant):
        """Get the eventual VTherm API class instance"""
        ret = hass.data.get(DOMAIN).get(VTHERM_API_NAME)
        if ret is None:
            ret = VersatileThermostatAPI(hass)
            hass.data[DOMAIN][VTHERM_API_NAME] = ret
        return ret

    def __init__(self, hass: HomeAssistant) -> None:
        _LOGGER.debug("building a VersatileThermostatAPI")
        super().__init__()
        self._hass = hass
        self._expert_params = None

    def add_entry(self, entry: ConfigEntry):
        """Add a new entry"""
        _LOGGER.debug("Add the entry %s", entry.entry_id)
        # self._entries[entry.entry_id] = entry
        # Add the entry in hass.data
        self._hass.data[DOMAIN][entry.entry_id] = entry

    def remove_entry(self, entry: ConfigEntry):
        """Remove an entry"""
        _LOGGER.debug("Remove the entry %s", entry.entry_id)
        # self._entries.pop(entry.entry_id)
        self._hass.data[DOMAIN].pop(entry.entry_id)
        # If not more entries are preset, remove the API
        if len(self) == 0:
            _LOGGER.debug("No more entries-> Remove the API from DOMAIN")
            self._hass.data.pop(DOMAIN)

    def set_global_config(self, config):
        """Read the global configuration from configuration.yaml file"""
        _LOGGER.info("Read global config from configuration.yaml")

        self._expert_params = config.get(CONF_AUTO_REGULATION_EXPERT)
        if self._expert_params:
            _LOGGER.debug("We have found expert params %s", self._expert_params)

    @property
    def self_regulation_expert(self):
        """Get the self regulation params"""
        return self._expert_params

    @property
    def hass(self):
        """Get the HomeAssistant object"""
        return self._hass
