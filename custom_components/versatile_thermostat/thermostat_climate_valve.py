# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate with a direct valve regulation class """

import logging
import asyncio
from datetime import datetime

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import HVACAction
from homeassistant.helpers.event import async_call_later


from .underlyings import UnderlyingValveRegulation, UnderlyingClimate

from .base_thermostat import ConfigData
from .thermostat_climate import ThermostatOverClimate
from .thermostat_prop import ThermostatProp

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log
from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF, VThermHvacMode_SLEEP
from homeassistant.exceptions import ServiceValidationError

# from .vtherm_api import VersatileThermostatAPI

_LOGGER = logging.getLogger(__name__)


class ThermostatOverClimateValve(ThermostatProp[UnderlyingClimate], ThermostatOverClimate):
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

        self._max_opening_degrees = config_entry.get(CONF_MAX_OPENING_DEGREES, None)
        max_opening_degrees_list = []
        if self._max_opening_degrees:
            max_opening_degrees_list = [
                int(x.strip()) for x in self._max_opening_degrees.split(",")
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
                max_opening_degree=(max_opening_degrees_list[idx] if idx < len(max_opening_degrees_list) else 100),
                max_closing_degree=self._max_closing_degree,
                opening_threshold=self._opening_threshold_degree,
            )
            self._underlyings_valve_regulation.append(under)

        # Guard to prevent concurrent recalibration tasks per thermostat entity
        self._recalibrate_lock: asyncio.Lock | None = None

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
                        "max_opening_degrees": self._max_opening_degrees,
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

    async def service_recalibrate_valves(self, delay_seconds: int):
        """Start recalibration of valve opening/closing degrees for each underlying valve in background.

        Steps:
        1) memorize requested state
        2) set VTherm hvac mode to OFF
        3) for each valve: open to 100% (opening_degree=100, closing_degree=0), wait,
           close to fully (opening_degree=0, closing_degree=100), wait
        4) restore requested state

        During this operation opening_threshold/min/max are ignored by sending
        direct commands to the underlying number entities.
        """
        if self.lock_manager.check_is_locked("service_recalibrate_valves"):
            return {"message": "thermostat locked"}

        write_event_log(_LOGGER, self, f"Calling SERVICE_RECALIBRATE_VALVES delay_seconds={delay_seconds}")

        # Validate underlyings synchronously before launching background task
        if not self._underlyings_valve_regulation:
            raise ServiceValidationError(f"{self} - No valve regulation underlyings available")

        # Build a short validation list and capture entity min/max per underlying
        valves_config = []
        for under in self._underlyings_valve_regulation:
            opening = under.opening_degree_entity_id
            closing = under.closing_degree_entity_id
            if not opening or not closing:
                raise ServiceValidationError(f"{self} - Underlying {under} must have opening and closing degree entities configured")

            opening_state = self._hass.states.get(opening)
            closing_state = self._hass.states.get(closing)
            if opening_state is None or closing_state is None:
                raise ServiceValidationError(f"{self} - Opening/closing entities {opening}/{closing} not found for underlying {under}")

            opening_min = opening_state.attributes.get("min", 0)
            opening_max = opening_state.attributes.get("max", 100)
            closing_min = closing_state.attributes.get("min", 0)
            closing_max = closing_state.attributes.get("max", 100)

            valves_config.append(
                {
                    "under": under,
                    "opening": opening,
                    "closing": closing,
                    "opening_min": opening_min,
                    "opening_max": opening_max,
                    "closing_min": closing_min,
                    "closing_max": closing_max,
                }
            )

        # Memorize expected/requested state
        expected_state = self.requested_state.to_dict() if self.requested_state is not None else None

        # If a recalibration is already running, return immediately and do not schedule
        if self._recalibrate_lock is None:
            self._recalibrate_lock = asyncio.Lock()

        if self._recalibrate_lock.locked():
            _LOGGER.warning("Recalibration request refused: already running for %s", self.entity_id)
            return {"message": "recalibrage en cours"}

        def pct_to_entity_value(pct: int, ent_min: float, ent_max: float) -> int:
            val = round(ent_min + (pct / 100.0) * (ent_max - ent_min))
            return int(val)

        # Define the background coroutine
        async def _recalibrate_task():
            # Initialize lock if needed
            if self._recalibrate_lock is None:
                self._recalibrate_lock = asyncio.Lock()

            # If already running, log and exit
            if self._recalibrate_lock.locked():
                _LOGGER.warning("Recalibration already in progress for %s", self.entity_id)
                return

            async with self._recalibrate_lock:
                try:
                    # Turn off vtherm
                    _LOGGER.info("%s - Recalibration - Stopping VTherm and waiting for %s seconds", self, delay_seconds)
                    await self.async_set_hvac_mode(VThermHvacMode_OFF)
                    await asyncio.sleep(delay_seconds)

                    _LOGGER.info("%s - Recalibration - Full opening of the valves and waiting for %s seconds", self, delay_seconds)
                    for cfg in valves_config:
                        under = cfg["under"]
                        opening = cfg["opening"]
                        closing = cfg["closing"]

                        open_val = pct_to_entity_value(100, cfg["opening_min"], cfg["opening_max"])
                        close_val = pct_to_entity_value(0, cfg["closing_min"], cfg["closing_max"])

                        _LOGGER.info("%s - Forcing opening=%s to %s and closing=%s to %s", self, opening, open_val, closing, close_val)
                        await under.send_value_to_number(opening, open_val)
                        await under.send_value_to_number(closing, close_val)

                    await asyncio.sleep(delay_seconds)

                    _LOGGER.info("%s - Recalibration - Full closing of the valves and waiting for %s seconds", self, delay_seconds)
                    for cfg in valves_config:
                        under = cfg["under"]
                        opening = cfg["opening"]
                        closing = cfg["closing"]

                        open_val2 = pct_to_entity_value(0, cfg["opening_min"], cfg["opening_max"])
                        close_val2 = pct_to_entity_value(100, cfg["closing_min"], cfg["closing_max"])

                        _LOGGER.info("%s - Forcing opening=%s to %s and closing=%s to %s", self, opening, open_val2, closing, close_val2)
                        await under.send_value_to_number(opening, open_val2)
                        await under.send_value_to_number(closing, close_val2)

                    await asyncio.sleep(delay_seconds)

                    # Restore requested state
                    _LOGGER.info("%s - Recalibration - Restoring requested state", self)
                    if expected_state:
                        try:
                            self.requested_state.set_state(
                                hvac_mode=expected_state.get("hvac_mode"),
                                target_temperature=expected_state.get("target_temperature"),
                                preset=expected_state.get("preset"),
                            )
                            self.requested_state.force_changed()
                            await self.update_states(force=True)
                        except Exception as ex:  # pylint: disable=broad-except
                            _LOGGER.error("%s - Cannot restore requested state after recalibration: %s", self, ex)
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.error("%s - Error during recalibration: %s", self, exc)

        # Launch background task and return immediately
        try:
            self.hass.async_create_task(_recalibrate_task())
        except Exception:
            # fallback
            self._hass.create_task(_recalibrate_task())

        return {"message": "calibrage en cours"}
