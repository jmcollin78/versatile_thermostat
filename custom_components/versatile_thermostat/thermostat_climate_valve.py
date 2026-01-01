# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate with a direct valve regulation class """

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import HVACAction
from homeassistant.helpers.event import async_call_later


from .underlyings import UnderlyingValveRegulation, UnderlyingClimate

from .base_thermostat import ConfigData
from .thermostat_climate import ThermostatOverClimate
from .thermostat_tpi import ThermostatTPI

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log
from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF, VThermHvacMode_SLEEP

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverClimateValve(ThermostatTPI[UnderlyingClimate], ThermostatOverClimate):
    """This class represent a VTherm over a climate with a direct valve regulation"""

    _entity_component_unrecorded_attributes = ThermostatOverClimate._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_climate",
                "vtherm_over_climate",
                "vtherm_over_climate_valve",
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
        self._max_closing_degree: int = 100
        self._opening_threshold_degree: int = 0

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

        opening_list = config_entry.get(CONF_OPENING_DEGREE_LIST)
        closing_list = config_entry.get(CONF_CLOSING_DEGREE_LIST, [])
        self._max_closing_degree = config_entry.get(CONF_MAX_CLOSING_DEGREE, 100)
        self._opening_threshold_degree = config_entry.get(CONF_OPENING_THRESHOLD_DEGREE, 0)
        regulation_threshold = config_entry.get(CONF_AUTO_REGULATION_DTEMP, 0)

        self._min_opening_degrees = config_entry.get(CONF_MIN_OPENING_DEGREES, None)
        min_opening_degrees_list = []
        if self._min_opening_degrees:
            min_opening_degrees_list = [
                int(x.strip()) for x in self._min_opening_degrees.split(",")
            ]

        for idx, _ in enumerate(config_entry.get(CONF_UNDERLYING_LIST)):
            # number of opening should equal number of underlying
            opening = opening_list[idx]
            closing = closing_list[idx] if idx < len(closing_list) else None
            self._opening_threshold_degree = max(self._opening_threshold_degree, regulation_threshold)

            under = UnderlyingValveRegulation(
                hass=self._hass,
                thermostat=self,
                opening_degree_entity_id=opening,
                closing_degree_entity_id=closing,
                climate_underlying=self._underlyings[idx],
                min_opening_degree=(min_opening_degrees_list[idx] if idx < len(min_opening_degrees_list) else 0),
                max_closing_degree=self._max_closing_degree,
                opening_threshold=self._opening_threshold_degree,
            )
            self._underlyings_valve_regulation.append(under)

    @overrides
    def restore_specific_previous_state(self, old_state: State):
        """Restore my specific attributes from previous state"""
        super().restore_specific_previous_state(old_state)

        if self.is_sleeping:
            self.set_hvac_off_reason(HVAC_OFF_REASON_SLEEP_MODE)

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        valve_attributes = {}
        for under in self._underlyings_valve_regulation:
            valve_attributes.update(
                {
                    under.entity_id: {
                        "hvac_action": under.hvac_action,
                        "percent_open": under.percent_open,
                        "last_sent_opening_value": under.last_sent_opening_value,
                        "min_opening_degree": under._min_opening_degree,  # pylint: disable=protected-access
                        "max_opening_degree": under._max_opening_degree,  # pylint: disable=protected-access
                        "min_sync_entity": under._min_sync_entity,  # pylint: disable=protected-access
                        "max_sync_entity": under._max_sync_entity,  # pylint: disable=protected-access
                        "step_calibration": under._step_sync_entity,  # pylint: disable=protected-access
                    }
                }
            )

        self._attr_extra_state_attributes["valve_open_percent"] = self.valve_open_percent
        self._attr_extra_state_attributes["power_percent"] = self.power_percent
        self._attr_extra_state_attributes["on_percent"] = self.safe_on_percent
        self._attr_extra_state_attributes.update(
            {
                "vtherm_over_climate_valve": {
                    "have_valve_regulation": self.have_valve_regulation,
                    "valve_regulation": {
                        "underlyings_valve_regulation": [underlying.valve_entity_ids for underlying in self._underlyings_valve_regulation],
                        "on_percent": self.safe_on_percent,
                        "power_percent": self.power_percent,
                        "function": self._proportional_function,
                        "tpi_coef_int": self._tpi_coef_int,
                        "tpi_coef_ext": self._tpi_coef_ext,
                        "tpi_threshold_low": self._tpi_threshold_low,
                        "tpi_threshold_high": self._tpi_threshold_high,
                        "minimal_activation_delay": self._minimal_activation_delay,
                        "minimal_deactivation_delay": self._minimal_deactivation_delay,
                        "min_opening_degrees": self._min_opening_degrees,
                        "opening_threshold_degree": self._opening_threshold_degree,
                        "max_closing_degree": self._max_closing_degree,
                        "valve_open_percent": self.valve_open_percent,
                        "auto_regulation_dpercent": self._auto_regulation_dpercent,
                        "auto_regulation_period_min": self._auto_regulation_period_min,
                        "last_calculation_timestamp": (self._last_calculation_timestamp.astimezone(self._current_tz).isoformat() if self._last_calculation_timestamp else None),
                    },
                    "underlying_valves": valve_attributes,
                }
            }
        )

        self.async_write_ha_state()
        _LOGGER.debug("%s - Calling update_custom_attributes: %s", self, self._attr_extra_state_attributes)

    @overrides
    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate the open percent", self)

        self.stop_recalculate_later()

        # For testing purpose. Should call _set_now() before
        now = self.now

        if self._last_calculation_timestamp is not None:
            period = (now - self._last_calculation_timestamp).total_seconds() / 60
            if not force and period < self._auto_regulation_period_min:
                _LOGGER.info(
                    "%s - do not calculate TPI because regulation_period (%d) is not exceeded",
                    self,
                    period,
                )
                self.do_recalculate_later()
                return

        # Call parent TPI recalculate to perform the TPI algorithm calculation
        super().recalculate(force)

        if self.is_sleeping:
            new_valve_percent = 100
        else:
            on_percent = self.safe_on_percent
            new_valve_percent = round(max(0, min(on_percent, 1)) * 100)

            # Issue 533 - don't filter with dtemp if valve should be close. Else it will never close
            if new_valve_percent < self._auto_regulation_dpercent:
                new_valve_percent = 0

            dpercent = new_valve_percent - self._valve_open_percent if self._valve_open_percent is not None else 0
            if self._last_calculation_timestamp is not None and new_valve_percent > 0 and -1 * self._auto_regulation_dpercent <= dpercent < self._auto_regulation_dpercent:
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

    def do_recalculate_later(self):
        """A utility function to set the valve open percent later on all underlyings"""
        _LOGGER.debug("%s - do_recalculate_later call", self)

        async def callback_recalculate(_):
            """Callback to set the valve percent"""
            self.recalculate()
            await self.async_control_heating(force=False)
            self.update_custom_attributes()
            self.async_write_ha_state()

        self.stop_recalculate_later()

        self._cancel_recalculate_later = async_call_later(self._hass, delay=20, action=callback_recalculate)

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""
        # if self.vtherm_hvac_mode == VThermHvacMode_OFF and not self._is_sleeping:
        #    _LOGGER.debug("%s - don't send regulated temperature cause VTherm is off ", self)
        #    return

        if self.target_temperature is None:
            _LOGGER.warning(
                "%s - don't send regulated temperature cause VTherm target_temp (%s) is None. This should be a temporary warning message.",
                self,
                self.target_temperature,
            )
            return

        if not force and not self.check_auto_regulation_period_min(self.now):
            return

        # Don't send temperature if hvac_mode is off
        if self.vtherm_hvac_mode != VThermHvacMode_OFF:
            for under in self._underlyings:
                if self.target_temperature != under.last_sent_temperature:
                    await under.set_temperature(
                        self.target_temperature,
                        self._attr_max_temp,
                        self._attr_min_temp,
                    )

            self._last_regulation_change = self.now
            self.reset_last_change_time_from_vtherm()

        _LOGGER.debug(
            "%s - last_regulation_change is now: %s and last_change_from_vtherm is now: %s", self, self._last_regulation_change, self._last_change_time_from_vtherm
        )  # pylint: disable=protected-access

        for under in self._underlyings_valve_regulation:
            await under.set_valve_open_percent()

    @overrides
    def build_hvac_list(self) -> list[VThermHvacMode]:
        """Build the hvac list depending on ac_mode"""
        if self._ac_mode:
            return [VThermHvacMode_COOL, VThermHvacMode_SLEEP, VThermHvacMode_OFF]
        else:
            return [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        if self._underlying_climate_start_hvac_action_date:
            stop_power_date = self.now
            delta = stop_power_date - self._underlying_climate_start_hvac_action_date
            self._underlying_climate_delta_t = delta.total_seconds() / 3600.0
            _LOGGER.debug("%s - underlying_climate_delta_t: %.4f hours", self, self._underlying_climate_delta_t)
            # increment energy at the end of the cycle
            super().incremente_energy()
            self._underlying_climate_start_hvac_action_date = self.now
            self._underlying_climate_mean_power_cycle = self.power_manager.mean_cycle_power
        else:
            _LOGGER.debug("%s - no underlying_climate_start_hvac_action_date to calculate energy", self)

    @property
    def have_valve_regulation(self) -> bool:
        """True if the Thermostat is regulated by valve"""
        return True

    @property
    def valve_open_percent(self) -> int:
        """Gives the percentage of valve needed"""
        if (self.vtherm_hvac_mode == VThermHvacMode_OFF and not self.is_sleeping) or self._valve_open_percent is None:
            return 0
        else:
            return self._valve_open_percent

    def calculate_hvac_action(self, under_list: list = None) -> HVACAction | None:
        """Returns the current hvac_action by checking all hvac_action of the _underlyings_valve_regulation"""

        if self.is_sleeping:
            self._attr_hvac_action = HVACAction.OFF
        else:
            super().calculate_hvac_action(self._underlyings_valve_regulation)

    @property
    def is_device_active(self) -> bool:
        """A hack to overrides the state from underlyings"""
        if self.is_sleeping:
            return False

        for under in self._underlyings_valve_regulation:
            if under.is_device_active:
                return True
        return False

    @property
    def device_actives(self) -> int:
        """Calculate the number of active devices"""
        if self.is_sleeping:
            return []

        return [under.opening_degree_entity_id for under in self._underlyings_valve_regulation if under.is_device_active]

    @property
    def activable_underlying_entities(self) -> list | None:
        """Returns the activable underlying entities for controling the central boiler"""
        return self._underlyings_valve_regulation

    @overrides
    @property
    def is_sleeping(self) -> bool:
        """True if the thermostat is in sleep mode"""
        return self.vtherm_hvac_mode == VThermHvacMode_SLEEP

    @overrides
    async def service_set_auto_regulation_mode(self, auto_regulation_mode: str):
        """This should not be possible in valve regulation mode"""
        return

    @overrides
    async def service_set_hvac_mode_sleep(self):
        """Set the hvac_mode to SLEEP mode (valid only for over_climate with valve regulation):
        service: versatile_thermostat.set_hvac_mode_sleep
        target:
            entity_id: climate.thermostat_1
        """
        write_event_log(_LOGGER, self, "Calling SERVICE_SET_HVAC_MODE_SLEEP")
        await self.async_set_hvac_mode(hvac_mode=VThermHvacMode_SLEEP)

    @overrides
    async def _check_initial_state(self):
        """Check the initial state of the thermostat and its underlyings"""
        await super()._check_initial_state()
        for under in self._underlyings_valve_regulation:
            await under.check_initial_state(self.vtherm_hvac_mode)

    @overrides
    def choose_auto_fan_mode(self, auto_fan_mode: str):
        """Force no auto_fan for climate with valve regulation"""
        self._current_auto_fan_mode = CONF_AUTO_FAN_NONE
        self._auto_activated_fan_mode = self._auto_deactivated_fan_mode = None

    @property
    def vtherm_type(self) -> str | None:
        """Return the type of thermostat"""
        return "over_climate_valve"
