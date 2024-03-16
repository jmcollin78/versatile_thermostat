# pylint: disable=line-too-long
""" A climate over switch classe """
import logging
from datetime import timedelta, datetime

from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    EventStateChangedData,
)
from homeassistant.helpers.typing import EventType as HASSEventType
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.climate import HVACMode

from .base_thermostat import BaseThermostat, ConfigData
from .prop_algorithm import PropAlgorithm

from .const import (
    CONF_VALVE,
    CONF_VALVE_2,
    CONF_VALVE_3,
    CONF_VALVE_4,
    # This is not really self-regulation but regulation here
    CONF_AUTO_REGULATION_DTEMP,
    CONF_AUTO_REGULATION_PERIOD_MIN,
    overrides,
)

from .underlyings import UnderlyingValve

_LOGGER = logging.getLogger(__name__)


class ThermostatOverValve(BaseThermostat):  # pylint: disable=abstract-method
    """Representation of a class for a Versatile Thermostat over a Valve"""

    _entity_component_unrecorded_attributes = (
        BaseThermostat._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "is_over_valve",
                    "underlying_valve_0",
                    "underlying_valve_1",
                    "underlying_valve_2",
                    "underlying_valve_3",
                    "on_time_sec",
                    "off_time_sec",
                    "cycle_min",
                    "function",
                    "tpi_coef_int",
                    "tpi_coef_ext",
                    "auto_regulation_dpercent",
                    "auto_regulation_period_min",
                    "last_calculation_timestamp",
                }
            )
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
        if self._hvac_mode == HVACMode.OFF:
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

        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
        )

        lst_valves = [config_entry.get(CONF_VALVE)]
        if config_entry.get(CONF_VALVE_2):
            lst_valves.append(config_entry.get(CONF_VALVE_2))
        if config_entry.get(CONF_VALVE_3):
            lst_valves.append(config_entry.get(CONF_VALVE_3))
        if config_entry.get(CONF_VALVE_4):
            lst_valves.append(config_entry.get(CONF_VALVE_4))

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
    async def _async_valve_changed(self, event: HASSEventType[EventStateChangedData]):
        """Handle unerdlying valve state changes.
        This method just log the change. It changes nothing to avoid loops.
        """
        new_state = event.data.get("new_state")
        _LOGGER.debug(
            "%s - _async_valve_changed new_state is %s", self, new_state.state
        )

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()
        self._attr_extra_state_attributes[
            "valve_open_percent"
        ] = self.valve_open_percent
        self._attr_extra_state_attributes["is_over_valve"] = self.is_over_valve
        self._attr_extra_state_attributes["underlying_valve_0"] = self._underlyings[
            0
        ].entity_id
        self._attr_extra_state_attributes["underlying_valve_1"] = (
            self._underlyings[1].entity_id if len(self._underlyings) > 1 else None
        )
        self._attr_extra_state_attributes["underlying_valve_2"] = (
            self._underlyings[2].entity_id if len(self._underlyings) > 2 else None
        )
        self._attr_extra_state_attributes["underlying_valve_3"] = (
            self._underlyings[3].entity_id if len(self._underlyings) > 3 else None
        )

        self._attr_extra_state_attributes[
            "on_percent"
        ] = self._prop_algorithm.on_percent
        self._attr_extra_state_attributes[
            "on_time_sec"
        ] = self._prop_algorithm.on_time_sec
        self._attr_extra_state_attributes[
            "off_time_sec"
        ] = self._prop_algorithm.off_time_sec
        self._attr_extra_state_attributes["cycle_min"] = self._cycle_min
        self._attr_extra_state_attributes["function"] = self._proportional_function
        self._attr_extra_state_attributes["tpi_coef_int"] = self._tpi_coef_int
        self._attr_extra_state_attributes["tpi_coef_ext"] = self._tpi_coef_ext
        self._attr_extra_state_attributes[
            "auto_regulation_dpercent"
        ] = self._auto_regulation_dpercent
        self._attr_extra_state_attributes[
            "auto_regulation_period_min"
        ] = self._auto_regulation_period_min
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

        dpercent = new_valve_percent - self.valve_open_percent
        if (
            dpercent >= -1 * self._auto_regulation_dpercent
            and dpercent < self._auto_regulation_dpercent
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

        for under in self._underlyings:
            under.set_valve_open_percent()

        self._last_calculation_timestamp = now

        self.update_custom_attributes()
        self.async_write_ha_state()

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        if self.hvac_mode == HVACMode.OFF:
            return

        added_energy = 0
        if not self.is_over_climate and self.mean_cycle_power is not None:
            added_energy = self.mean_cycle_power * float(self._cycle_min) / 60.0

        self._total_energy += added_energy
        _LOGGER.debug(
            "%s - added energy is %.3f . Total energy is now: %.3f",
            self,
            added_energy,
            self._total_energy,
        )
