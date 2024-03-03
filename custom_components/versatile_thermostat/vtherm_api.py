""" The API of Versatile Thermostat"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.number import NumberEntity, DOMAIN as NUMBER_DOMAIN

from .const import (
    DOMAIN,
    CONF_AUTO_REGULATION_EXPERT,
    CONF_SHORT_EMA_PARAMS,
    CONF_SAFETY_MODE,
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
        self._safety_mode = None
        self._central_boiler_entity = None
        self._threshold_number_entity = None
        self._nb_active_number_entity = None
        self._central_configuration = None
        # A dict that will store all Number entities which holds the temperature
        self._number_temperatures = dict()

    def find_central_configuration(self):
        """Search for a central configuration"""
        if not self._central_configuration:
            for (
                config_entry
            ) in VersatileThermostatAPI._hass.config_entries.async_entries(DOMAIN):
                if (
                    config_entry.data.get(CONF_THERMOSTAT_TYPE)
                    == CONF_THERMOSTAT_CENTRAL_CONFIG
                ):
                    self._central_configuration = config_entry
                    break
                    # return self._central_configuration
        return self._central_configuration

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

        self._safety_mode = config.get(CONF_SAFETY_MODE)
        if self._safety_mode:
            _LOGGER.debug("We have found safet_mode params %s", self._safety_mode)

    def register_central_boiler(self, central_boiler_entity):
        """Register the central boiler entity. This is used by the CentralBoilerBinarySensor
        class to register itself at creation"""
        self._central_boiler_entity = central_boiler_entity

    def register_central_boiler_activation_number_threshold(
        self, threshold_number_entity
    ):
        """register the two number entities needed for boiler activation"""
        self._threshold_number_entity = threshold_number_entity
        # If sensor and threshold number are initialized, reload the listener
        # if self._nb_active_number_entity and self._central_boiler_entity:
        #     self._hass.async_add_job(self.reload_central_boiler_binary_listener)

    def register_nb_device_active_boiler(self, nb_active_number_entity):
        """register the two number entities needed for boiler activation"""
        self._nb_active_number_entity = nb_active_number_entity
        # if self._threshold_number_entity and self._central_boiler_entity:
        #     self._hass.async_add_job(self.reload_central_boiler_binary_listener)

    def register_temperature_number(
        self,
        config_id: str,
        preset_name: str,
        number_entity: NumberEntity,
    ):
        """Register the NumberEntity for a particular device / preset."""
        # Search for device_name into the _number_temperatures dict
        if not self._number_temperatures.get(config_id):
            self._number_temperatures[config_id] = dict()

        self._number_temperatures.get(config_id)[preset_name] = number_entity

    def get_temperature_number_value(self, config_id, preset_name) -> float | None:
        """Returns the value of a previously registred NumberEntity which represent
        a temperature. If no NumberEntity was previously registred, then returns None"""
        entities = self._number_temperatures.get(config_id, None)
        if entities:
            entity = entities.get(preset_name, None)
            if entity:
                return entity.state
        return None

    async def init_vtherm_links(self):
        """INitialize all VTherms entities links
        This method is called when HA is fully started (and all entities should be initialized)
        """
        await self.reload_central_boiler_binary_listener()
        await self.reload_central_boiler_entities_list()
        # Initialization of all preset for all VTherm
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None
        )
        if component:
            for entity in component.entities:
                await entity.init_presets(self.find_central_configuration())

    async def reload_central_boiler_binary_listener(self):
        """Reloads the BinarySensor entity which listen to the number of
        active devices and the thresholds entities"""
        if self._central_boiler_entity:
            await self._central_boiler_entity.listen_nb_active_vtherm_entity()

    async def reload_central_boiler_entities_list(self):
        """Reload the central boiler list of entities if a central boiler is used"""
        if self._nb_active_number_entity is not None:
            await self._nb_active_number_entity.listen_vtherms_entities()

    @property
    def self_regulation_expert(self):
        """Get the self regulation params"""
        return self._expert_params

    @property
    def short_ema_params(self):
        """Get the short EMA params in expert mode"""
        return self._short_ema_params

    @property
    def safety_mode(self):
        """Get the safety_mode params"""
        return self._safety_mode

    @property
    def central_boiler_entity(self):
        """Get the central boiler binary_sensor entity"""
        return self._central_boiler_entity

    @property
    def nb_active_device_for_boiler(self):
        """Returns the number of active VTherm which have an
        influence on boiler"""
        if self._nb_active_number_entity is None:
            return None
        else:
            return self._nb_active_number_entity.native_value

    @property
    def nb_active_device_for_boiler_entity(self):
        """Returns the number of active VTherm entity which have an
        influence on boiler"""
        return self._nb_active_number_entity

    @property
    def nb_active_device_for_boiler_threshold_entity(self):
        """Returns the number of active VTherm entity which have an
        influence on boiler"""
        return self._threshold_number_entity

    @property
    def nb_active_device_for_boiler_threshold(self):
        """Returns the number of active VTherm entity which have an
        influence on boiler"""
        if self._threshold_number_entity is None:
            return None
        return int(self._threshold_number_entity.native_value)

    @property
    def hass(self):
        """Get the HomeAssistant object"""
        return VersatileThermostatAPI._hass
