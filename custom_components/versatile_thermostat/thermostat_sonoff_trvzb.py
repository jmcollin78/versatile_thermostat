# pylint: disable=line-too-long, too-many-lines
""" A climate over Sonoff TRVZB classe """

import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from .underlyings import UnderlyingSonoffTRVZB

# from .commons import NowClass, round_to_nearest
from .base_thermostat import BaseThermostat, ConfigData
from .prop_algorithm import PropAlgorithm

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverSonoffTRVZB(BaseThermostat[UnderlyingSonoffTRVZB]):
    """This class represent a VTherm over a Sonoff TRVZB climate"""

    _entity_component_unrecorded_attributes = (
        BaseThermostat._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "is_over_climate",
                    "is_over_sonoff_trvzb",
                    "underlying_entities",
                    "on_time_sec",
                    "off_time_sec",
                    "cycle_min",
                    "function",
                    "tpi_coef_int",
                    "tpi_coef_ext",
                    "power_percent",
                }
            )
        )
    )

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the ThermostatOverSonoffTRVZB class"""
        _LOGGER.debug("%s - creating a ThermostatOverSonoffTRVZB VTherm", name)
        super().__init__(hass, unique_id, name, entry_infos)

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat"""

        super().post_init(config_entry)

        for idx, _ in enumerate(config_entry.get(CONF_UNDERLYING_LIST)):
            offset = config_entry.get(CONF_OFFSET_CALIBRATION_LIST)[idx]
            opening = config_entry.get(CONF_OPENING_DEGREE_LIST)[idx]
            closing = config_entry.get(CONF_CLOSING_DEGREE_LIST)[idx]
            under = UnderlyingSonoffTRVZB(
                hass=self._hass,
                thermostat=self,
                offset_calibration_entity_id=offset,
                opening_degree_entity_id=opening,
                closing_degree_entity_id=closing,
            )
            self._underlyings.append(under)

        # Initialization of the TPI algo
        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
            self.name,
        )

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        under0: UnderlyingSonoffTRVZB = self._underlyings[0]
        self._attr_extra_state_attributes["is_over_sonoff_trvzb"] = (
            self.is_over_sonoff_trvzb
        )
        self._attr_extra_state_attributes["keep_alive_sec"] = under0.keep_alive_sec

        self._attr_extra_state_attributes["underlying_entities"] = [
            underlying.entity_id for underlying in self._underlyings
        ]

        self._attr_extra_state_attributes["on_percent"] = (
            self._prop_algorithm.on_percent
        )
        self._attr_extra_state_attributes["power_percent"] = self.power_percent
        self._attr_extra_state_attributes["on_time_sec"] = (
            self._prop_algorithm.on_time_sec
        )
        self._attr_extra_state_attributes["off_time_sec"] = (
            self._prop_algorithm.off_time_sec
        )
        self._attr_extra_state_attributes["cycle_min"] = self._cycle_min
        self._attr_extra_state_attributes["function"] = self._proportional_function
        self._attr_extra_state_attributes["tpi_coef_int"] = self._tpi_coef_int
        self._attr_extra_state_attributes["tpi_coef_ext"] = self._tpi_coef_ext

        self.async_write_ha_state()
        _LOGGER.debug(
            "%s - Calling update_custom_attributes: %s",
            self,
            self._attr_extra_state_attributes,
        )

    @overrides
    def recalculate(self):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate all", self)
        self._prop_algorithm.calculate(
            self._target_temp,
            self._cur_temp,
            self._cur_ext_temp,
            self._hvac_mode or HVACMode.OFF,
        )
        self.update_custom_attributes()

    @property
    def is_over_sonoff_trvzb(self) -> bool:
        """True if the Thermostat is over_sonoff_trvzb"""
        return True

    @property
    def power_percent(self) -> float | None:
        """Get the current on_percent value"""
        if self._prop_algorithm:
            return round(self._prop_algorithm.on_percent * 100, 0)
        else:
            return None
