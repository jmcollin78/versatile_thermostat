# pylint: disable=line-too-long, abstract-method
"""A climate over switch classe"""

from vtherm_api.log_collector import get_vtherm_logger
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
from .cycle_scheduler import CycleScheduler
from .vtherm_central_api import VersatileThermostatAPI
from .vtherm_hvac_mode import (
    VThermHvacMode_OFF,
    VThermHvacMode_HEAT,
    VThermHvacMode_COOL,
    VThermHvacMode_SLEEP,
)
from homeassistant.components.climate import HVACAction
from homeassistant.core import State

_LOGGER = get_vtherm_logger(__name__)

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
        self._opening_threshold_degree: int = 0
        self._max_closing_degree: int = 100
        self._min_opening_degrees: list[int] = []
        self._max_opening_degrees: list[int] = []
        self._have_valve_control = False

        # Call to super must be done after initialization because it calls post_init at the end
        super().__init__(hass, unique_id, name, config_entry)

    @property
    def is_over_valve(self) -> bool:
        """True if the Thermostat is over_valve"""
        return True

    @overrides
    def build_hvac_list(self) -> list[VThermHvacMode]:
        """Build the hvac list depending on ac_mode"""
        if self._ac_mode:
            return [VThermHvacMode_COOL, VThermHvacMode_SLEEP, VThermHvacMode_OFF]
        else:
            return [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]

    @overrides
    @property
    def is_sleeping(self) -> bool:
        """True if the thermostat is in sleep mode"""
        return self.vtherm_hvac_mode == VThermHvacMode_SLEEP

    @overrides
    async def service_set_hvac_mode_sleep(self):
        """Set the hvac_mode to SLEEP mode (valid for over_valve and over_climate with valve regulation):
        service: versatile_thermostat.set_hvac_mode_sleep
        target:
            entity_id: climate.thermostat_1
        """
        if self.lock_manager.check_is_locked("service_set_hvac_mode_sleep"):
            return
        write_event_log(_LOGGER, self, "Calling SERVICE_SET_HVAC_MODE_SLEEP")
        # Pre-inject the 100% raw demand to avoid a transitory window
        # displaying the previous valve position (issue 1938 - design Q2)
        self._valve_open_percent = 100
        await self.async_set_hvac_mode(hvac_mode=VThermHvacMode_SLEEP)

    @overrides
    async def async_set_hvac_mode(self, hvac_mode: VThermHvacMode):
        """Refresh central boiler accounting when entering or leaving sleep."""
        was_sleeping = self.is_sleeping
        await super().async_set_hvac_mode(hvac_mode)

        if was_sleeping == self.is_sleeping or not self.is_used_by_central_boiler:
            return

        central_boiler_manager = VersatileThermostatAPI.get_vtherm_api(self._hass).central_boiler_manager
        if central_boiler_manager is not None:
            await central_boiler_manager.refresh_active_devices()

    @overrides
    def calculate_hvac_action(self, _: list = None) -> HVACAction | None:
        """Calculate the HVAC action. Force OFF if sleeping (BR-009)."""
        if self.is_sleeping:
            self._attr_hvac_action = HVACAction.OFF
        else:
            super().calculate_hvac_action(None)

    @overrides
    @property
    def should_device_be_active(self) -> bool:
        """A sleeping VTherm never requires its devices to be active"""
        if self.is_sleeping:
            return False
        return super().should_device_be_active

    @overrides
    @property
    def is_device_active(self) -> bool:
        """A sleeping VTherm is never active"""
        if self.is_sleeping:
            return False
        return super().is_device_active

    @overrides
    @property
    def device_actives(self) -> list[str]:
        """Calculate the active devices.
        A sleeping over_valve VTherm must never trigger the central boiler,
        whatever the physical valve opening or the #1348 opening-parameter
        profile (invariant BR-009 / FR-007).
        """
        if self.is_sleeping:
            return []
        return super().device_actives

    @overrides
    def restore_specific_previous_state(self, old_state: State):
        """Restore my specific attributes from previous state"""
        super().restore_specific_previous_state(old_state)

        if self.is_sleeping:
            self.set_hvac_off_reason(HVAC_OFF_REASON_SLEEP_MODE)

    @property
    def valve_open_percent(self) -> int:
        """Gives the percentage of valve needed"""
        if (self.vtherm_hvac_mode is VThermHvacMode_OFF and not self.is_sleeping) or self._valve_open_percent is None:
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

        self._opening_threshold_degree = config_entry.get(
            CONF_OPENING_THRESHOLD_DEGREE, 0
        )
        self._max_closing_degree = config_entry.get(CONF_MAX_CLOSING_DEGREE, 100)
        min_opening_degrees = config_entry.get(CONF_MIN_OPENING_DEGREES, "")
        max_opening_degrees = config_entry.get(CONF_MAX_OPENING_DEGREES, "")
        self._min_opening_degrees = (
            [int(value.strip()) for value in min_opening_degrees.split(",")]
            if min_opening_degrees
            else []
        )
        self._max_opening_degrees = (
            [int(value.strip()) for value in max_opening_degrees.split(",")]
            if max_opening_degrees
            else []
        )
        self._have_valve_control = (
            self._opening_threshold_degree != 0
            or self._max_closing_degree != 100
            or bool(self._min_opening_degrees)
            or bool(self._max_opening_degrees)
        )

        lst_valves = config_entry.get(CONF_UNDERLYING_LIST)

        for index, valve in enumerate(lst_valves):
            valve_state = self._hass.states.get(valve)
            default_max = (
                valve_state.attributes.get("max", 100) if valve_state else 100
            )
            self._underlyings.append(
                UnderlyingValve(
                    hass=self._hass,
                    thermostat=self,
                    valve_entity_id=valve,
                    min_opening_degree=(
                        self._min_opening_degrees[index]
                        if index < len(self._min_opening_degrees)
                        else 0
                    ),
                    max_opening_degree=(
                        self._max_opening_degrees[index]
                        if index < len(self._max_opening_degrees)
                        else default_max
                    ),
                    max_closing_degree=self._max_closing_degree,
                    opening_threshold=self._opening_threshold_degree,
                )
            )

        self._bind_scheduler(CycleScheduler(
            hass=self._hass,
            thermostat=self,
            underlyings=self._underlyings,
            cycle_duration_sec=self._cycle_min * 60,
            min_activation_delay=self.minimal_activation_delay,
            min_deactivation_delay=self.minimal_deactivation_delay,
        ))

        self._should_relaunch_control_heating = False

    @overrides
    async def async_added_to_hass(self):
        """Run when entity about to be added."""

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

        attributes = {
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
        if self._have_valve_control:
            commands = [underlying.command_percent for underlying in self._underlyings]
            attributes["vtherm_over_valve"].update(
                {
                    "have_valve_control": True,
                    "opening_threshold_degree": self._opening_threshold_degree,
                    "max_closing_degree": self._max_closing_degree,
                    "min_opening_degrees": self._min_opening_degrees,
                    "max_opening_degrees": self._max_opening_degrees,
                    "underlying_valves": [
                        {
                            "entity_id": underlying.entity_id,
                            "command_percent": underlying.command_percent,
                            "last_sent_opening_value": underlying.last_sent_opening_value,
                        }
                        for underlying in self._underlyings
                    ],
                }
            )
            if len(commands) == 1:
                attributes["valve_command_percent"] = commands[0]
            else:
                attributes["valve_command_by_valve"] = commands

        self._attr_extra_state_attributes.update(attributes)

        # _LOGGER.debug("%s - Calling update_custom_attributes: %s", self, self._attr_extra_state_attributes)

    @overrides
    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate the open percent", self)

        self.stop_recalculate_later()

        # Issue 1938 - during sleep the raw 100% demand must not be
        # recomputed by the TPI algorithm (FR-008 / BR-004)
        if self.is_sleeping:
            self.apply_valve_command_percent(1.0, force=True)
            return

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

        current_on_percent = self.safe_on_percent
        if current_on_percent is None:
            # Temperature not yet available; preserve the current valve position.
            return

        self.apply_valve_command_percent(current_on_percent, force=True)

    def apply_valve_command_percent(
        self,
        on_percent: float,
        force: bool = False,
    ) -> float:
        """Accept a requested valve command and return the retained ratio.

        This is the single conversion point between a proportional algorithm's
        continuous output and the integer command exposed by the thermostat.
        """
        self.stop_recalculate_later()

        # Issue 1938 - during sleep, the raw 100% demand is injected directly,
        # bypassing the dpercent / period_min filters which could otherwise
        # retain the previous TPI position (design decision D1/D2)
        if self.is_sleeping:
            self._valve_open_percent = 100
            self._last_calculation_timestamp = self.now
            self.update_custom_attributes()
            self.async_write_ha_state()
            return 1.0

        if self._auto_regulation_period_min is None or self._auto_regulation_dpercent is None:
            _LOGGER.warning(
                "%s - auto_regulation_period_min or auto_regulation_dpercent is not set. Keeping current valve command.",
                self,
            )
            return self.valve_open_percent / 100.0

        new_valve_percent = round(
            max(0, min(on_percent, 1)) * 100
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

            return self.valve_open_percent / 100.0

        if self._valve_open_percent == new_valve_percent:
            _LOGGER.debug("%s - no change in valve_open_percent.", self)
            return self.valve_open_percent / 100.0

        now = self.now
        if self._last_calculation_timestamp is not None:
            period = (now - self._last_calculation_timestamp).total_seconds() / 60
            if not force and period < self._auto_regulation_period_min:
                _LOGGER.info(
                    "%s - do not apply valve command because regulation_period (%d) is not exceeded",
                    self,
                    period,
                )
                self.do_recalculate_later()
                return self.valve_open_percent / 100.0

        self._valve_open_percent = new_valve_percent

        # Valve open percent is sent to underlyings by CycleScheduler
        # in start_cycle (called from control_heating)

        self._last_calculation_timestamp = now

        # self.calculate_hvac_action()
        self.update_custom_attributes()
        self.async_write_ha_state()
        return self.valve_open_percent / 100.0

    def do_recalculate_later(self):
        """A utility function to set the valve open percent later on all underlyings"""
        _LOGGER.debug("%s - do_recalculate_later call", self)

        async def callback_recalculate(_):
            """Callback to set the valve percent"""
            self.recalculate()
            current_on_percent = self.safe_on_percent
            if self._cycle_scheduler and current_on_percent is not None:
                await self._cycle_scheduler.apply_valve_update(
                    self.vtherm_hvac_mode or VThermHvacMode_OFF,
                    current_on_percent,
                )
            self.update_custom_attributes()
            self.async_write_ha_state()

        self.stop_recalculate_later()

        self._cancel_recalculate_later = async_call_later(self._hass, delay=20, action=callback_recalculate)

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        # Issue 1938 - no energy is counted while sleeping: no device is
        # considered active (H-004)
        if self.is_sleeping:
            return
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
