# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate with a direct valve regulation class """

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import HVACAction
from homeassistant.helpers.event import async_call_later


from .underlyings import UnderlyingValveRegulation

# from .commons import NowClass, round_to_nearest
from .base_thermostat import ConfigData
from .thermostat_climate import ThermostatOverClimate
from .prop_algorithm import PropAlgorithm

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log
from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF, VThermHvacMode_SLEEP

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverClimateValve(ThermostatOverClimate):
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
        # if mode sleep is activated, the valve is fully open but the hvac_mode is off
        self._is_sleeping: bool = False

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
            self._minimal_deactivation_delay,
            self.name,
            max_on_percent=self._max_on_percent,
            tpi_threshold_low=self._tpi_threshold_low,
            tpi_threshold_high=self._tpi_threshold_high,
        )

        offset_list = config_entry.get(CONF_OFFSET_CALIBRATION_LIST, [])
        opening_list = config_entry.get(CONF_OPENING_DEGREE_LIST)
        closing_list = config_entry.get(CONF_CLOSING_DEGREE_LIST, [])
        max_closing_degree = config_entry.get(CONF_MAX_CLOSING_DEGREE, 100)
        opening_threshold_degree = config_entry.get(CONF_OPENING_THRESHOLD_DEGREE, 0)
        regulation_threshold = config_entry.get(CONF_AUTO_REGULATION_DTEMP, 0)

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
            real_opening_threshold = max(opening_threshold_degree, regulation_threshold)

            under = UnderlyingValveRegulation(
                hass=self._hass,
                thermostat=self,
                offset_calibration_entity_id=offset,
                opening_degree_entity_id=opening,
                closing_degree_entity_id=closing,
                climate_underlying=self._underlyings[idx],
                min_opening_degree=(min_opening_degrees_list[idx] if idx < len(min_opening_degrees_list) else 0),
                max_closing_degree=max_closing_degree,
                opening_threshold=real_opening_threshold,
            )
            self._underlyings_valve_regulation.append(under)

    @overrides
    def restore_specific_previous_state(self, old_state: State):
        """Restore my specific attributes from previous state"""
        super().restore_specific_previous_state(old_state)

        self._is_sleeping = self.vtherm_hvac_mode == VThermHvacMode_OFF and old_state.attributes.get("is_sleeping", False)
        if self._is_sleeping:
            self.set_hvac_off_reason(HVAC_OFF_REASON_SLEEP_MODE)

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        self._attr_extra_state_attributes.update(
            {
                "vtherm_over_climate_valve": {
                    "have_valve_regulation": self.have_valve_regulation,
                    "valve_regulation": {
                        "underlyings_valve_regulation": [underlying.valve_entity_ids for underlying in self._underlyings_valve_regulation],
                        "on_percent": self._prop_algorithm.on_percent,
                        "power_percent": self.power_percent,
                        "function": self._proportional_function,
                        "tpi_coef_int": self._tpi_coef_int,
                        "tpi_coef_ext": self._tpi_coef_ext,
                        "min_opening_degrees": self._min_opening_degrees,
                        "valve_open_percent": self.valve_open_percent,
                        "auto_regulation_dpercent": self._auto_regulation_dpercent,
                        "auto_regulation_period_min": self._auto_regulation_period_min,
                        "last_calculation_timestamp": (self._last_calculation_timestamp.astimezone(self._current_tz).isoformat() if self._last_calculation_timestamp else None),
                    },
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

        # TODO this is exactly the same method as the thermostat_valve recalculate. Put that in common
        if self._is_sleeping:
            self._valve_open_percent = 100
            return

        if not self.is_on:
            # the 0 will be clamped to the min value
            self._valve_open_percent = 0
            return

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

        self._prop_algorithm.calculate(
            self.target_temperature,
            self._cur_temp,
            self._cur_ext_temp,
            self.last_temperature_slope,
            self.vtherm_hvac_mode or VThermHvacMode_OFF,
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

    def do_recalculate_later(self):
        """A utility function to set the valve open percent later on all underlyings"""
        _LOGGER.debug("%s - do_recalculate_later call", self)

        async def callback_recalculate(_):
            """Callback to set the valve percent"""
            self.recalculate()
            self.update_custom_attributes()
            self.async_write_ha_state()

        self.stop_recalculate_later()

        self._cancel_recalculate_later = async_call_later(self._hass, delay=20, action=callback_recalculate)

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""
        if self.vtherm_hvac_mode == VThermHvacMode_OFF and not self._is_sleeping:
            _LOGGER.debug("%s - don't send regulated temperature cause VTherm is off ", self)
            return

        if self.target_temperature is None:
            _LOGGER.warning(
                "%s - don't send regulated temperature cause VTherm target_temp (%s) is None. This should be a temporary warning message.",
                self,
                self.target_temperature,
            )
            return

        if not force and not self.check_auto_regulation_period_min(self.now):
            return

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
    async def async_set_hvac_mode(self, hvac_mode: VThermHvacMode, _=False):
        """Set new hvac mode"""

        write_event_log(_LOGGER, self, f"Setting hvac_mode to {hvac_mode}")
        if hvac_mode == VThermHvacMode_SLEEP:
            self._is_sleeping = True
            hvac_mode = VThermHvacMode_OFF
            self.set_hvac_off_reason(HVAC_OFF_REASON_SLEEP_MODE)
        else:
            self._is_sleeping = False
            if hvac_mode == VThermHvacMode_OFF:
                for under in self._underlyings_valve_regulation:
                    await under.turn_off()

        await super().async_set_hvac_mode(hvac_mode)

    @overrides
    def build_hvac_list(self) -> list[VThermHvacMode]:
        """Build the hvac list depending on ac_mode"""
        if self._ac_mode:
            return [VThermHvacMode_COOL, VThermHvacMode_SLEEP, VThermHvacMode_OFF]
        else:
            return [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]

    @property
    def have_valve_regulation(self) -> bool:
        """True if the Thermostat is regulated by valve"""
        return True

    @property
    def valve_open_percent(self) -> int:
        """Gives the percentage of valve needed"""
        if (self.vtherm_hvac_mode == VThermHvacMode_OFF and not self._is_sleeping) or self._valve_open_percent is None:
            return 0
        else:
            return self._valve_open_percent

    def calculate_hvac_action(self, under_list: list = None) -> HVACAction | None:
        """Returns the current hvac_action by checking all hvac_action of the _underlyings_valve_regulation"""

        if self._is_sleeping:
            self._attr_hvac_action = HVACAction.OFF
        else:
            super().calculate_hvac_action(self._underlyings_valve_regulation)

    @property
    def is_device_active(self) -> bool:
        """A hack to overrides the state from underlyings"""
        if self._is_sleeping:
            return False
        else:
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
    @property
    def is_sleeping(self) -> bool:
        """True if the thermostat is in sleep mode"""
        return self._is_sleeping

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
