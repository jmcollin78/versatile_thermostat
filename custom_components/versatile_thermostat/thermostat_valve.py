# pylint: disable=line-too-long, abstract-method
""" A climate over switch classe """
import logging
from datetime import timedelta, datetime

from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    async_call_later,
    EventStateChangedData,
)
from homeassistant.core import Event, HomeAssistant, callback

from .base_thermostat import BaseThermostat, ConfigData
from .thermostat_prop import ThermostatProp

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log

from .underlyings import UnderlyingValve

_LOGGER = logging.getLogger(__name__)

class ThermostatOverValve(ThermostatProp[UnderlyingValve]):  # pylint: disable=abstract-method
    """Representation of a class for a Versatile Thermostat over a Valve"""

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_valve",
                "vtherm_over_valve",
            }
        )
    )

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, config_entry: ConfigData
    ):
        """Initialize the thermostat over switch."""
        self._valve_open_percent: int = 0
        self._last_calculation_timestamp: datetime | None = None
        self._auto_regulation_dpercent: float | None = None
        self._auto_regulation_period_min: int | None = None

        # Call to super must be done after initialization because it calls post_init at the end
        super().__init__(hass, unique_id, name, config_entry)

    @property
    def is_over_valve(self) -> bool:
        """True if the Thermostat is over_valve"""
        return True

    @property
    def valve_open_percent(self) -> int:
        """Gives the percentage of valve needed"""
        if self.vtherm_hvac_mode is VThermHvacMode_OFF:
            return 0
        else:
            return self._valve_open_percent



    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat"""

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

        lst_valves = config_entry.get(CONF_UNDERLYING_LIST)

        for _, valve in enumerate(lst_valves):
            self._underlyings.append(
                UnderlyingValve(hass=self._hass, thermostat=self, valve_entity_id=valve)
            )

        self._should_relaunch_control_heating = False

    @overrides
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener to all underlying entities
        for valve in self._underlyings:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [valve.entity_id], self._async_valve_changed
                )
            )

        # Start the control_heating
        # starts a cycle
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self.async_control_heating,
                interval=timedelta(minutes=self._cycle_min),
            )
        )

    @callback
    async def _async_valve_changed(self, event: Event[EventStateChangedData]):
        """Handle unerdlying valve state changes.
        This method just log the change. It changes nothing to avoid loops.
        """
        new_state = event.data.get("new_state")
        self.calculate_hvac_action()
        self.update_custom_attributes()
        self.async_write_ha_state()
        write_event_log(_LOGGER, self, f"Underlying valve state changed to {new_state}")

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        self._attr_extra_state_attributes.update(
            {
                "is_over_valve": self.is_over_valve,
                "on_percent": self.safe_on_percent,
                "power_percent": self.power_percent,
                "valve_open_percent": self.valve_open_percent,
                "vtherm_over_valve": {
                    "valve_open_percent": self.valve_open_percent,
                    "underlying_entities": [underlying.entity_id for underlying in self._underlyings],
                    "on_percent": self.safe_on_percent,
                    "function": self._proportional_function,
                    "tpi_coef_int": self._tpi_coef_int,
                    "tpi_coef_ext": self._tpi_coef_ext,
                    "tpi_threshold_low": self._tpi_threshold_low,
                    "tpi_threshold_high": self._tpi_threshold_high,
                    "minimal_activation_delay": self._minimal_activation_delay,
                    "minimal_deactivation_delay": self._minimal_deactivation_delay,
                    "auto_regulation_dpercent": self._auto_regulation_dpercent,
                    "auto_regulation_period_min": self._auto_regulation_period_min,
                    "last_calculation_timestamp": (self._last_calculation_timestamp.astimezone(self._current_tz).isoformat() if self._last_calculation_timestamp else None),
                    "calculated_on_percent": (
                        self._prop_algorithm.calculated_on_percent
                        if self._prop_algorithm
                        else None
                    ),
                },
            }
        )

        _LOGGER.debug("%s - Calling update_custom_attributes: %s", self, self._attr_extra_state_attributes)

    @overrides
    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate the open percent", self)

        self.stop_recalculate_later()

        if self._auto_regulation_period_min is None or self._auto_regulation_dpercent is None:
            _LOGGER.warning(
                "%s - auto_regulation_period_min or auto_regulation_dpercent is not set. Stopping TPI calculation.",
                self,
            )
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

        if self._prop_algorithm:
            self._prop_algorithm.calculate(
                self.target_temperature,
                self._cur_temp,
                self._cur_ext_temp,
                self.last_temperature_slope,
                self.vtherm_hvac_mode or VThermHvacMode_OFF,
            )

        new_valve_percent = round(
            max(0, min(self.safe_on_percent, 1)) * 100
        )

        # Issue 533 - don't filter with dtemp if valve should be close. Else it will never close
        if new_valve_percent < self._auto_regulation_dpercent:
            new_valve_percent = 0

        dpercent = new_valve_percent - self.valve_open_percent
        if (
            new_valve_percent > 0
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

        if self._valve_open_percent == new_valve_percent:
            _LOGGER.debug("%s - no change in valve_open_percent.", self)
            return

        self._valve_open_percent = new_valve_percent

        # is in start_cycle now which is called by control_heating
        # for under in self._underlyings:
        #    under.set_valve_open_percent()

        self._last_calculation_timestamp = now

        # self.calculate_hvac_action()
        self.update_custom_attributes()
        self.async_write_ha_state()

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

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        if self.vtherm_hvac_mode == VThermHvacMode_OFF:
            return

        added_energy = 0
        if not self.is_over_climate and self.power_manager.mean_cycle_power is not None:
            added_energy = (
                self.power_manager.mean_cycle_power * float(self._cycle_min) / 60.0
            )

        if self._total_energy is None:
            self._total_energy = added_energy
            _LOGGER.debug(
                "%s - incremente_energy set energy is %s",
                self,
                self._total_energy,
            )
        else:
            self._total_energy += added_energy
            _LOGGER.debug(
                "%s - get_my_previous_state increment energy is %s",
                self,
                self._total_energy,
            )

        self.update_custom_attributes()
        self.async_write_ha_state()

        _LOGGER.debug(
            "%s - added energy is %.3f . Total energy is now: %.3f",
            self,
            added_energy,
            self._total_energy,
        )

    @property
    def vtherm_type(self) -> str | None:
        """Return the type of thermostat"""
        return "over_valve"
