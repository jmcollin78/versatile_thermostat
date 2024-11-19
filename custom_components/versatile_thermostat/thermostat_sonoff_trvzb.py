# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate over Sonoff TRVZB classe """

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode, HVACAction

from .underlyings import UnderlyingSonoffTRVZB

# from .commons import NowClass, round_to_nearest
from .base_thermostat import ConfigData
from .thermostat_climate import ThermostatOverClimate
from .prop_algorithm import PropAlgorithm

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverSonoffTRVZB(ThermostatOverClimate):
    """This class represent a VTherm over a Sonoff TRVZB climate"""

    _entity_component_unrecorded_attributes = ThermostatOverClimate._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
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
    _underlyings_sonoff_trvzb: list[UnderlyingSonoffTRVZB] = []
    _valve_open_percent: int | None = None
    _last_calculation_timestamp: datetime | None = None
    _auto_regulation_dpercent: float | None = None
    _auto_regulation_period_min: int | None = None

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the ThermostatOverSonoffTRVZB class"""
        _LOGGER.debug("%s - creating a ThermostatOverSonoffTRVZB VTherm", name)
        super().__init__(hass, unique_id, name, entry_infos)
        # self._valve_open_percent: int = 0
        # self._last_calculation_timestamp: datetime | None = None
        # self._auto_regulation_dpercent: float | None = None
        # self._auto_regulation_period_min: int | None = None

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat and underlyings
        Beware that the underlyings list contains the climate which represent the Sonoff TRVZB
        but also the UnderlyingSonoff which reprensent the valve"""

        super().post_init(config_entry)

        self._auto_regulation_dpercent = (
            config_entry.get(CONF_AUTO_REGULATION_DTEMP)
            if config_entry.get(CONF_AUTO_REGULATION_DTEMP) is not None
            else 0.0
        )
        self._auto_regulation_period_min = (
            config_entry.get(CONF_AUTO_REGULATION_PERIOD_MIN)
            if config_entry.get(CONF_AUTO_REGULATION_PERIOD_MIN) is not None
            else 0
        )

        # Initialization of the TPI algo
        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
            self.name,
        )

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
                climate_underlying=self._underlyings[idx],
            )
            self._underlyings_sonoff_trvzb.append(under)

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        self._attr_extra_state_attributes["is_over_sonoff_trvzb"] = (
            self.is_over_sonoff_trvzb
        )

        self._attr_extra_state_attributes["underlying_sonoff_trvzb_entities"] = [
            underlying.entity_id for underlying in self._underlyings_sonoff_trvzb
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

        self._attr_extra_state_attributes["valve_open_percent"] = (
            self.valve_open_percent
        )

        self._attr_extra_state_attributes["auto_regulation_dpercent"] = (
            self._auto_regulation_dpercent
        )
        self._attr_extra_state_attributes["auto_regulation_period_min"] = (
            self._auto_regulation_period_min
        )
        self._attr_extra_state_attributes["last_calculation_timestamp"] = (
            self._last_calculation_timestamp.astimezone(self._current_tz).isoformat()
            if self._last_calculation_timestamp
            else None
        )

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
        _LOGGER.debug("%s - recalculate the open percent", self)

        # TODO this is exactly the same method as the thermostat_valve recalculate. Put that in common

        # For testing purpose. Should call _set_now() before
        now = self.now

        if self._last_calculation_timestamp is not None:
            period = (now - self._last_calculation_timestamp).total_seconds() / 60
            if period < self._auto_regulation_period_min:
                _LOGGER.info(
                    "%s - do not calculate TPI because regulation_period (%d) is not exceeded",
                    self,
                    period,
                )
                return

        self._prop_algorithm.calculate(
            self._target_temp,
            self._cur_temp,
            self._cur_ext_temp,
            self._hvac_mode or HVACMode.OFF,
        )

        new_valve_percent = round(
            max(0, min(self.proportional_algorithm.on_percent, 1)) * 100
        )

        # Issue 533 - don't filter with dtemp if valve should be close. Else it will never close
        if new_valve_percent < self._auto_regulation_dpercent:
            new_valve_percent = 0

        dpercent = (
            new_valve_percent - self._valve_open_percent
            if self._valve_open_percent is not None
            else 0
        )
        if (
            self._last_calculation_timestamp is not None
            and new_valve_percent > 0
            and -1 * self._auto_regulation_dpercent
            <= dpercent
            < self._auto_regulation_dpercent
        ):
            _LOGGER.debug(
                "%s - do not calculate TPI because regulation_dpercent (%.1f) is not exceeded",
                self,
                dpercent,
            )

            return

        if (
            self._last_calculation_timestamp is not None
            and self._valve_open_percent == new_valve_percent
        ):
            _LOGGER.debug("%s - no change in valve_open_percent.", self)
            return

        self._valve_open_percent = new_valve_percent

        for under in self._underlyings_sonoff_trvzb:
            under.set_valve_open_percent()

        self._last_calculation_timestamp = now

        self.update_custom_attributes()

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""
        self.recalculate()

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

    # @property
    # def hvac_modes(self) -> list[HVACMode]:
    #    """Get the hvac_modes"""
    #    return self._hvac_list

    @property
    def valve_open_percent(self) -> int:
        """Gives the percentage of valve needed"""
        if self._hvac_mode == HVACMode.OFF or self._valve_open_percent is None:
            return 0
        else:
            return self._valve_open_percent

    @property
    def hvac_action(self) -> HVACAction | None:
        """Returns the current hvac_action by checking all hvac_action of the _underlyings_sonoff_trvzb"""

        return self.calculate_hvac_action(self._underlyings_sonoff_trvzb)
