# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate with a direct valve regulation class """

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode, HVACAction

from .underlyings import UnderlyingValveRegulation

# from .commons import NowClass, round_to_nearest
from .base_thermostat import ConfigData
from .thermostat_climate import ThermostatOverClimate
from .prop_algorithm import PropAlgorithm

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverClimateValve(ThermostatOverClimate):
    """This class represent a VTherm over a climate with a direct valve regulation"""

    _entity_component_unrecorded_attributes = ThermostatOverClimate._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_climate",
                "have_valve_regulation",
                "underlying_entities",
                "on_time_sec",
                "off_time_sec",
                "cycle_min",
                "function",
                "tpi_coef_int",
                "tpi_coef_ext",
                "power_percent",
                "min_opening_degrees",
            }
        )
    )

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the ThermostatOverClimateValve class"""
        _LOGGER.debug("%s - creating a ThermostatOverClimateValve VTherm", name)
        self._underlyings_valve_regulation: list[UnderlyingValveRegulation] = []
        self._valve_open_percent: int | None = None
        self._last_calculation_timestamp: datetime | None = None
        self._auto_regulation_dpercent: float | None = None
        self._auto_regulation_period_min: int | None = None
        self._min_opening_degress: list[int] = []

        super().__init__(hass, unique_id, name, entry_infos)

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat and underlyings
        Beware that the underlyings list contains the climate which represent the TRV
        but also the UnderlyingValveRegulation which reprensent the valve"""

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

        offset_list = config_entry.get(CONF_OFFSET_CALIBRATION_LIST, [])
        opening_list = config_entry.get(CONF_OPENING_DEGREE_LIST)
        closing_list = config_entry.get(CONF_CLOSING_DEGREE_LIST, [])

        self._min_opening_degrees = config_entry.get(CONF_MIN_OPENING_DEGREES, None)
        min_opening_degrees_list = []
        if self._min_opening_degrees:
            min_opening_degrees_list = [
                int(x.strip()) for x in self._min_opening_degrees.split(",")
            ]

        for idx, _ in enumerate(config_entry.get(CONF_UNDERLYING_LIST)):
            offset = offset_list[idx] if idx < len(offset_list) else None
            # number of opening should equal number of underlying
            opening = opening_list[idx]
            closing = closing_list[idx] if idx < len(closing_list) else None
            under = UnderlyingValveRegulation(
                hass=self._hass,
                thermostat=self,
                offset_calibration_entity_id=offset,
                opening_degree_entity_id=opening,
                closing_degree_entity_id=closing,
                climate_underlying=self._underlyings[idx],
                min_opening_degree=(
                    min_opening_degrees_list[idx]
                    if idx < len(min_opening_degrees_list)
                    else 0
                ),
            )
            self._underlyings_valve_regulation.append(under)

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        self._attr_extra_state_attributes["have_valve_regulation"] = (
            self.have_valve_regulation
        )

        self._attr_extra_state_attributes["underlyings_valve_regulation"] = [
            underlying.valve_entity_ids
            for underlying in self._underlyings_valve_regulation
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

        self._attr_extra_state_attributes["min_opening_degrees"] = (
            self._min_opening_degrees
        )

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

        self._last_calculation_timestamp = now

        super().recalculate()

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""
        if self.target_temperature is None:
            return

        for under in self._underlyings:
            if self.target_temperature != under.last_sent_temperature:
                await under.set_temperature(
                    self.target_temperature,
                    self._attr_max_temp,
                    self._attr_min_temp,
                )

        for under in self._underlyings_valve_regulation:
            await under.set_valve_open_percent()

    @property
    def have_valve_regulation(self) -> bool:
        """True if the Thermostat is regulated by valve"""
        return True

    @overrides
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
        """Returns the current hvac_action by checking all hvac_action of the _underlyings_valve_regulation"""

        return self.calculate_hvac_action(self._underlyings_valve_regulation)

    @property
    def is_device_active(self) -> bool:
        """A hack to overrides the state from underlyings"""
        return self.valve_open_percent > 0

    @property
    def device_actives(self) -> int:
        """Calculate the number of active devices"""
        if self.is_device_active:
            return [
                under.opening_degree_entity_id
                for under in self._underlyings_valve_regulation
            ]
        else:
            return []

    @property
    def activable_underlying_entities(self) -> list | None:
        """Returns the activable underlying entities for controling the central boiler"""
        return self._underlyings_valve_regulation

    @overrides
    async def service_set_auto_regulation_mode(self, auto_regulation_mode: str):
        """This should not be possible in valve regulation mode"""
        return
