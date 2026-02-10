# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate over climate classe """
import logging
from typing import Optional

from datetime import timedelta, datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval, EventStateChangedData, async_call_later
from homeassistant.components.climate import (
    HVACAction,
    ClimateEntityFeature,
)

from .commons import round_to_nearest, write_event_log
from .base_thermostat import BaseThermostat, ConfigData
from .pi_algorithm import PITemperatureRegulator

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingClimate
from .feature_auto_start_stop_manager import FeatureAutoStartStopManager
from .vtherm_hvac_mode import VThermHvacMode

_LOGGER = logging.getLogger(__name__)

HVAC_ACTION_ON = [  # pylint: disable=invalid-name
    HVACAction.COOLING,
    HVACAction.DRYING,
    HVACAction.FAN,
    HVACAction.HEATING,
]

class ThermostatOverClimate(BaseThermostat[UnderlyingClimate]):
    """Representation of a base class for a Versatile Thermostat over a climate"""

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_climate",
                "vtherm_over_climate",
            }
        ).union(FeatureAutoStartStopManager.unrecorded_attributes)
    )

    def __init__(
        self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData
    ):
        """Initialize the thermostat over switch."""
        self._auto_regulation_mode: str | None = None
        self._regulation_algo = None
        self._regulated_target_temp: float | None = None
        self._auto_regulation_dtemp: float | None = None
        self._auto_regulation_period_min: int | None = None
        self._last_regulation_change: datetime | None = None
        # The fan mode configured in configEntry
        self._auto_fan_mode: str | None = None
        # The current fan mode (could be change by service call)
        self._current_auto_fan_mode: str | None = None
        # The fan_mode name depending of the current_mode
        self._auto_activated_fan_mode: str | None = None
        self._auto_deactivated_fan_mode: str | None = None
        self._follow_underlying_temp_change: bool = False
        self._last_regulation_change = None  # NowClass.get_now(hass)
        self._sync_entity_list: list[str] = []
        self._sync_with_calibration: bool = False

        # super.__init__ calls post_init at the end. So it must be called after regulation initialization
        super().__init__(hass, unique_id, name, entry_infos)
        self._regulated_target_temp = self.target_temperature

        self._last_hvac_mode = None

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat"""

        self._auto_start_stop_manager: FeatureAutoStartStopManager = (
            FeatureAutoStartStopManager(self, self._hass)
        )

        self.register_manager(self._auto_start_stop_manager)

        super().post_init(config_entry)

        for climate in config_entry.get(CONF_UNDERLYING_LIST, []):
            under = UnderlyingClimate(
                hass=self._hass,
                thermostat=self,
                climate_entity_id=climate,
            )
            self._underlyings.append(under)

        self._sync_entity_list = config_entry.get(CONF_SYNC_ENTITY_LIST, [])
        self._sync_with_calibration = config_entry.get(CONF_SYNC_WITH_CALIBRATION, False)

        self.choose_auto_regulation_mode(
            config_entry.get(CONF_AUTO_REGULATION_MODE)
            if config_entry.get(CONF_AUTO_REGULATION_MODE) is not None
            else CONF_AUTO_REGULATION_NONE
        )

        self._auto_regulation_dtemp = (
            config_entry.get(CONF_AUTO_REGULATION_DTEMP)
            if config_entry.get(CONF_AUTO_REGULATION_DTEMP) is not None
            else 0.5
        )
        self._auto_regulation_period_min = (
            config_entry.get(CONF_AUTO_REGULATION_PERIOD_MIN)
            if config_entry.get(CONF_AUTO_REGULATION_PERIOD_MIN) is not None
            else 5
        )

        self._auto_fan_mode = (
            config_entry.get(CONF_AUTO_FAN_MODE)
            if config_entry.get(CONF_AUTO_FAN_MODE) is not None
            else CONF_AUTO_FAN_NONE
        )

        self._auto_regulation_use_device_temp = config_entry.get(
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP, False
        )

    @property
    def is_over_climate(self) -> bool:
        """True if the Thermostat is over_climate"""
        return True

    @overrides
    def calculate_hvac_action(self, under_list: list = None) -> HVACAction | None:
        """Calculate an hvac action based on the hvac_action of the list in argument"""
        # if one not IDLE or OFF -> return it
        # else if one IDLE -> IDLE
        # else OFF
        if under_list is None:
            under_list = self._underlyings

        one_idle = False
        for under in under_list:
            if (action := under.hvac_action) not in [
                HVACAction.IDLE,
                HVACAction.OFF,
            ]:
                self._attr_hvac_action = action
                return
            if under.hvac_action == HVACAction.IDLE:
                one_idle = True
        if one_idle:
            self._attr_hvac_action = HVACAction.IDLE
        else:
            self._attr_hvac_action = HVACAction.OFF

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""

        self.stop_recalculate_later()

        if self.vtherm_hvac_mode == VThermHvacMode_OFF:
            _LOGGER.debug(
                "%s - don't send regulated temperature cause VTherm is off ", self
            )
            # In this case, reset the timer of last regulation change to avoid time delta too high
            self._last_regulation_change = self.now
            return

        if self.target_temperature is None:
            _LOGGER.warning(
                "%s - don't send regulated temperature cause VTherm target_temp (%s) is None. This should be a temporary warning message.",
                self,
                self.target_temperature,
            )
            return

        _LOGGER.info(
            "%s - Calling ThermostatClimate._send_regulated_temperature force=%s",
            self,
            force,
        )

        if not force and not self.check_auto_regulation_period_min(self.now):
            self.do_send_regulated_temp_later()
            return

        self._regulation_algo.set_target_temp(self.target_temperature)

        if not self._regulated_target_temp:
            self._regulated_target_temp = self.target_temperature

        _LOGGER.info("%s - regulation calculation will be done", self)

        # use _attr_target_temperature_step to round value if _auto_regulation_dtemp is equal to 0
        regulation_step = self._auto_regulation_dtemp if self._auto_regulation_dtemp else self._attr_target_temperature_step
        _LOGGER.debug("%s - usage regulation_step: %.2f ", self, regulation_step)

        # Find time delta since last regulation change
        time_delta: float = (
            (self.now - self._last_regulation_change).total_seconds() / 60.0 / self._auto_regulation_period_min
            if self._last_regulation_change and self._auto_regulation_period_min
            else 1.0
        )
        _LOGGER.debug("%s - usage time_delta: %.2f ", self, time_delta)

        if self.current_temperature is not None:
            new_regulated_temp = round_to_nearest(
                self._regulation_algo.calculate_regulated_temperature(self.current_temperature, self._cur_ext_temp, time_delta),
                regulation_step,
            )
        else:
            new_regulated_temp = self.target_temperature

        _LOGGER.info(
            "%s - Regulated temp have changed to %.1f. Resend it to underlyings",
            self,
            new_regulated_temp,
        )

        self._last_regulation_change = self.now
        for under in self._underlyings:
            # issue 348 - use device temperature if configured as offset
            offset_temp = 0
            device_temp = 0
            if (
                # current_temperature is set
                self.current_temperature is not None
                # regulation can use the device_temp
                and self.auto_regulation_use_device_temp
                # and we have access to the device temp
                and (device_temp := under.underlying_current_temperature) is not None
            ):
                offset_temp = device_temp - self.current_temperature

            target_temp = round_to_nearest(new_regulated_temp + offset_temp, regulation_step)

            # The dtemp is the difference between the new target temp and the last sent temperature to the underlying. 
            # If the dtemp is too low, we consider that there is no need to send a new temperature to the underlying because it
            # will not have any effect on the device. This avoid to send too many temperature changes to the underlying.
            dtemp = target_temp - (under.last_sent_temperature if under.last_sent_temperature else 0)

            if not force and abs(dtemp) < (self._auto_regulation_dtemp or 0):
                _LOGGER.info(
                    "%s - dtemp (%.1f) is < %.1f -> forget the regulation send for %s",
                    self,
                    dtemp,
                    self._auto_regulation_dtemp,
                    under.entity_id,
                )
                continue

            _LOGGER.debug(
                "%s - The device offset temp for regulation is %.2f - internal temp is %.2f. New target is %.2f",
                self,
                offset_temp,
                device_temp,
                target_temp,
            )

            await under.set_temperature(
                target_temp,
                self._attr_max_temp,
                self._attr_min_temp,
            )

        # Update regulated_target_temp after the loop to avoid affecting dtemp calculation for other underlyings
        self._regulated_target_temp = new_regulated_temp

    def do_send_regulated_temp_later(self):
        """A utility function to set the temperature later on an underlying"""
        # For over climate we do nothing because the temperature is set in the main loop
        _LOGGER.debug("%s - do_set_temperature_later call", self)

        async def callback_send_regulated_temp(_):
            """Callback to send the regulated temperature"""
            await self._send_regulated_temperature()
            self.update_custom_attributes()
            self.async_write_ha_state()

        self.stop_recalculate_later()

        self._cancel_recalculate_later = async_call_later(self._hass, 20, callback_send_regulated_temp)

    def check_auto_regulation_period_min(self, now):
        """Check if minimal auto_regulation period is exceeded
        Returns true if it is not exceeded (so auto regulation can continue)"""
        if self._last_regulation_change is None:
            return True

        period = float((now - self._last_regulation_change).total_seconds()) / 60.0
        if period < (self._auto_regulation_period_min or 0):
            _LOGGER.info(
                "%s - period (%.1f) min is < %.0f min -> forget the auto-regulation send",
                self,
                period,
                self._auto_regulation_period_min,
            )
            return False

        _LOGGER.debug(
            "%s - period (%.1f) min is >= %.0f min -> auto-regulation is available",
            self,
            period,
            self._auto_regulation_period_min,
        )
        return True

    async def _send_auto_fan_mode(self):
        """Send the fan mode if auto_fan_mode and temperature gap is > threshold"""
        if not self._auto_fan_mode or not self._auto_activated_fan_mode:
            return

        dtemp = (
            self.regulated_target_temp if self.is_regulated else self.target_temperature
        )
        if dtemp is None or self.current_temperature is None:
            return

        dtemp = dtemp - self.current_temperature
        should_activate_auto_fan = (
            dtemp >= AUTO_FAN_DTEMP_THRESHOLD or dtemp <= -AUTO_FAN_DTEMP_THRESHOLD
        )

        # deal with ac / non ac mode
        hvac_mode = self.vtherm_hvac_mode
        if (hvac_mode == VThermHvacMode_COOL and dtemp > 0) or (hvac_mode == VThermHvacMode_HEAT and dtemp < 0) or (hvac_mode == VThermHvacMode_OFF):
            should_activate_auto_fan = False

        if should_activate_auto_fan and self.fan_mode != self._auto_activated_fan_mode:
            _LOGGER.info(
                "%s - Activate the auto fan mode with %s because delta temp is %.2f",
                self,
                self._auto_fan_mode,
                dtemp,
            )
            await self.async_set_fan_mode(self._auto_activated_fan_mode)
        if (
            not should_activate_auto_fan
            and self.fan_mode not in AUTO_FAN_DEACTIVATED_MODES
        ):
            _LOGGER.info(
                "%s - DeActivate the auto fan mode with %s because delta temp is %.2f",
                self,
                self._auto_deactivated_fan_mode,
                dtemp,
            )
            await self.async_set_fan_mode(self._auto_deactivated_fan_mode)

    def choose_auto_regulation_mode(self, auto_regulation_mode: str):
        """Choose or change the regulation mode"""
        self._auto_regulation_mode = auto_regulation_mode
        if self._auto_regulation_mode == CONF_AUTO_REGULATION_LIGHT:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamLight.kp,
                RegulationParamLight.ki,
                RegulationParamLight.k_ext,
                RegulationParamLight.offset_max,
                RegulationParamLight.accumulated_error_threshold,
                RegulationParamLight.overheat_protection,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_MEDIUM:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamMedium.kp,
                RegulationParamMedium.ki,
                RegulationParamMedium.k_ext,
                RegulationParamMedium.offset_max,
                RegulationParamMedium.accumulated_error_threshold,
                RegulationParamMedium.overheat_protection,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_STRONG:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamStrong.kp,
                RegulationParamStrong.ki,
                RegulationParamStrong.k_ext,
                RegulationParamStrong.offset_max,
                RegulationParamStrong.accumulated_error_threshold,
                RegulationParamStrong.overheat_protection,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_SLOW:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamSlow.kp,
                RegulationParamSlow.ki,
                RegulationParamSlow.k_ext,
                RegulationParamSlow.offset_max,
                RegulationParamSlow.accumulated_error_threshold,
                RegulationParamSlow.overheat_protection,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_EXPERT:
            api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(
                self._hass
            )
            if api:
                if (expert_param := api.self_regulation_expert) is not None:
                    self._regulation_algo = PITemperatureRegulator(
                        self.target_temperature,
                        expert_param.get("kp"),
                        expert_param.get("ki"),
                        expert_param.get("k_ext"),
                        expert_param.get("offset_max"),
                        expert_param.get("accumulated_error_threshold"),
                        expert_param.get("overheat_protection", True),
                    )
                else:
                    _LOGGER.error(
                        "%s - Cannot initialize Expert self-regulation mode due to VTherm API doesn't exists. Please contact the publisher of the integration",
                        self,
                    )
            else:
                _LOGGER.error(
                    "%s - Cannot initialize Expert self-regulation mode cause the configuration in configuration.yaml have not been found. Please see readme documentation for %s",
                    self,
                    DOMAIN,
                )

        if not self._regulation_algo:
            # A default empty algo (which does nothing)
            self._regulation_algo = PITemperatureRegulator(self.target_temperature, 0, 0, 0, 0, 0, True)

    def choose_auto_fan_mode(self, auto_fan_mode: str):
        """Choose the correct fan mode depending of the underlying capacities and the configuration"""

        self._current_auto_fan_mode = auto_fan_mode

        # Get the supported feature of the first underlying. We suppose each underlying have the same fan attributes
        fan_supported = (self.supported_features or 0) & ClimateEntityFeature.FAN_MODE > 0

        if auto_fan_mode == CONF_AUTO_FAN_NONE or not fan_supported:
            self._auto_activated_fan_mode = self._auto_deactivated_fan_mode = None
            return

        def find_fan_mode(fan_modes: list[str], fan_mode: str) -> str | None:
            """Return the fan_mode if it exist of None if not"""
            try:
                return fan_mode if fan_modes.index(fan_mode) >= 0 else None
            except ValueError:
                return None

        def determine_fan_mode_contains_speed(fan_modes: list[str]) -> bool:
            """Determine if the fan_modes contains speed modes by searching for the keywords "low"/"1"."""
            for val in ["low", "1"]:
                if find_fan_mode(fan_modes, val):
                    return True
            return False

        def fix_order_speed_modes(speed_modes: list) -> list:
            """Determine if speed_modes list is ordered from high to low speed and reverse it"""
            index = -1
            if "low" in speed_modes:
                index = speed_modes.index("low")
            elif "1" in speed_modes:
                index = speed_modes.index("1")

            if index > -1 and index >= len(speed_modes) / 2:
                speed_modes.reverse()

            return speed_modes

        # Remove special modes like "auto"
        fan_modes = self.fan_modes or []
        speed_modes = [
            mode for mode in fan_modes
            if mode not in ["auto"]
        ]

        num_speeds = len(speed_modes)
        if num_speeds == 0:
            self._auto_activated_fan_mode = None
            return

        # We suppose speed_modes are ordered from low to high speed
        speed_modes = fix_order_speed_modes(speed_modes)

        # We suppose that the speed modes contains at least 3 values
        # fan_modes = low, medium, high :
        #    |CONF_AUTO_FAN_LOW     |low    |
        #    |CONF_AUTO_FAN_MEDIUM  |medium |
        #    |CONF_AUTO_FAN_HIGH    |high   |
        #    |CONF_AUTO_FAN_TURBO   |high   |
        # fan_modes =  low, medium, high, turbo :
        #    |CONF_AUTO_FAN_LOW     |low  |
        #    |CONF_AUTO_FAN_MEDIUM  |medium    |
        #    |CONF_AUTO_FAN_HIGH    |high |
        #    |CONF_AUTO_FAN_TURBO   |turbo   |
        # fan_modes = low, medium_low, medium, medium_high, high :
        #    |CONF_AUTO_FAN_LOW     |medium_low  |
        #    |CONF_AUTO_FAN_MEDIUM  |medium      |
        #    |CONF_AUTO_FAN_HIGH    |medium_high |
        #    |CONF_AUTO_FAN_TURBO   |high        |
        target_index = -1

        if determine_fan_mode_contains_speed(fan_modes) is False:
            self._auto_activated_fan_mode = None
            _LOGGER.warning(
                "%s - #1419 - choose_auto_fan_mode cannot define value because fan_modes=%s doesn't contains speed values",
                self,
                self.fan_modes,
            )

            return

        if auto_fan_mode == CONF_AUTO_FAN_LOW:
            if num_speeds >= 4:
                target_index = num_speeds - 4
            else:
                target_index = 0
        elif auto_fan_mode == CONF_AUTO_FAN_MEDIUM:
            if num_speeds >= 4:
                target_index = num_speeds - 3
            else:
                target_index = 1
        elif auto_fan_mode == CONF_AUTO_FAN_HIGH:
            if num_speeds >= 4:
                target_index = num_speeds - 2
            else:
                target_index = 2
        elif auto_fan_mode == CONF_AUTO_FAN_TURBO:
            target_index = num_speeds - 1

        if target_index >= 0:
            self._auto_activated_fan_mode = speed_modes[target_index]
        else:
            self._auto_activated_fan_mode = None

        for val in AUTO_FAN_DEACTIVATED_MODES:
            if find_fan_mode(fan_modes, val):
                self._auto_deactivated_fan_mode = val
                break

        _LOGGER.info(
            "%s - choose_auto_fan_mode founds current_auto_fan_mode=%s auto_activated_fan_mode=%s and auto_deactivated_fan_mode=%s",
            self,
            self._current_auto_fan_mode,
            self._auto_activated_fan_mode,
            self._auto_deactivated_fan_mode,
        )

    @overrides
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener to all underlying entities
        # TODO should be triggered by Underlying class ? -> yes
        # for climate in self._underlyings:
        #     self.async_on_remove(
        #         async_track_state_change_event(
        #             self.hass, [climate.entity_id], self._async_climate_changed
        #         )
        #     )

        # Start the control_heating
        # starts a cycle
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self.async_control_heating,
                interval=timedelta(minutes=self._cycle_min),
            )
        )

        # Synchronize temperature if activated
        await self.synchronize_device_temperature()

    @overrides
    def restore_specific_previous_state(self, old_state: State):
        """Restore my specific attributes from previous state"""
        old_error = old_state.attributes.get("regulation_accumulated_error")
        if old_error:
            self._regulation_algo.set_accumulated_error(old_error)
            _LOGGER.debug(
                "%s - Old regulation accumulated_error have been restored to %f",
                self,
                old_error,
            )

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        self._attr_extra_state_attributes["fan_mode"] = self.fan_mode
        self._attr_extra_state_attributes["fan_modes"] = self.fan_modes
        self._attr_extra_state_attributes["is_over_climate"] = self.is_over_climate
        # the attr is 2 times in custom_attributes, because it need to be restored, so it must be at root
        self._attr_extra_state_attributes["regulation_accumulated_error"] = self._regulation_algo.accumulated_error
        self._attr_extra_state_attributes["regulated_target_temperature"] = self.regulated_target_temp
        vtherm_over_climate_data = {
            "start_hvac_action_date": self._underlying_climate_start_hvac_action_date,
            "last_mean_power_cycle": self._underlying_climate_mean_power_cycle,
            "underlying_entities": [underlying.entity_id for underlying in self._underlyings],
            "is_regulated": self.is_regulated,
            "auto_fan_mode": self.auto_fan_mode,
            "current_auto_fan_mode": self._current_auto_fan_mode,
            "auto_activated_fan_mode": self._auto_activated_fan_mode,
            "auto_deactivated_fan_mode": self._auto_deactivated_fan_mode,
            "follow_underlying_temp_change": self._follow_underlying_temp_change,
            "auto_regulation_use_device_temp": self.auto_regulation_use_device_temp,
        }

        if self.is_regulated:
            vtherm_over_climate_data["regulation"] = {
                "regulated_target_temperature": self._regulated_target_temp,
                "auto_regulation_mode": self._auto_regulation_mode,
                "regulation_accumulated_error": self._regulation_algo.accumulated_error,
            }

        if self.has_sync_entities:
            under_attributes = {}
            for idx, under in enumerate(self._underlyings):
                try:
                    state = self.hass.states.get(self._sync_entity_list[idx])
                    value = float(state.state) if state is not None else None
                except (ValueError, AttributeError, TypeError):
                    value = None

                under_attributes[self._sync_entity_list[idx]] = {
                    "value": value,
                    "min_sync_entity": under.min_sync_entity,
                    "max_sync_entity": under.max_sync_entity,
                    "step_sync_entity": under.step_sync_entity,
                }
            vtherm_over_climate_data["temp_synchronisation"] = {
                "sync_entity_ids": self._sync_entity_list,
                "sync_with_calibration": self._sync_with_calibration,
                "sync_attributes": under_attributes,
            }

        self._attr_extra_state_attributes.update({"vtherm_over_climate": vtherm_over_climate_data})

        _LOGGER.debug("%s - Calling update_custom_attributes: %s", self, self._attr_extra_state_attributes)

    @overrides
    def recalculate(self, force=False):
        """A utility function to force the calculation of a the algo. For over_climate there is nothing to
        recalculate but we need it cause the base function throw not implemented error
        """

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""

        # if self.vtherm_hvac_mode == VThermHvacMode_OFF:
        #     return

        device_power = self._underlying_climate_mean_power_cycle

        added_energy = 0
        self._underlying_climate_delta_t = 0
        if self._underlying_climate_start_hvac_action_date:
            delta = self.now - self._underlying_climate_start_hvac_action_date
            self._underlying_climate_delta_t = delta.total_seconds() / 3600.0

        if self.is_over_climate and self._underlying_climate_delta_t > 0 and device_power is not None and device_power > 0:
            added_energy = device_power * self._underlying_climate_delta_t

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
                "%s - incremente_energy incremented energy is %s",
                self,
                self._total_energy,
            )

        self._underlying_climate_start_hvac_action_date = self.now if self.should_device_be_active else None

        _LOGGER.debug(
            "%s - added energy is %.3f . Total energy is now: %.3f",
            self,
            added_energy,
            self._total_energy,
        )

    @callback
    async def underlying_changed(  # pylint: disable=too-many-arguments
        self,
        under: UnderlyingClimate,
        new_hvac_mode: VThermHvacMode | None,
        new_hvac_action: HVACAction | None,
        new_target_temp: float | None,
        new_fan_mode: str | None,
        new_state: State,
        old_state: State,
    ):
        """Handle underlying changes. This is called by the UnderlyingClimate class when the entity changes. The UnderlyingClimate does some checks to ensure that the change is relevant. When an attribute is not changed, the corresponding parameter is None."""

        write_event_log(_LOGGER, self, f"Underlying climate {under.entity_id}state changed from {old_state} to new_state {new_state}")

        async def end_climate_changed(changes: bool):
            """To end the event management"""
            if changes:
                self.requested_state.force_changed()
                await self.update_states()

        changes = False

        # A real changes have to be managed
        _LOGGER.debug(
            "%s - Underlying climate %s have changed. new_hvac_mode is %s (vs %s), new_hvac_action=%s (vs %s), new_target_temp=%s (vs %s), new_fan_mode=%s (vs %s)",
            self,
            under.entity_id,
            new_hvac_mode,
            self.vtherm_hvac_mode,
            new_hvac_action,
            self.hvac_action,
            new_target_temp,
            self.target_temperature,
            new_fan_mode,
            self.fan_mode,
        )

        # Check that the state is defined
        if new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            _LOGGER.info(
                "%s - Underlying climate %s is in state %s. We consider that there is no change to do",
                self,
                under.entity_id,
                new_state.state,
            )
            await end_climate_changed(changes)
            # TODO add a specific attribute to know that the underlying is unavailable and manage it in the error messages
            return

        # Interpretation of hvac action
        if new_hvac_action:
            old_hvac_action = old_state.attributes.get("hvac_action") if old_state and old_state.attributes else None
            if old_hvac_action not in HVAC_ACTION_ON and new_hvac_action in HVAC_ACTION_ON:
                self._underlying_climate_start_hvac_action_date = self.now  # self.get_last_updated_date_or_now(new_state) the event has the system date
                self._underlying_climate_mean_power_cycle = self.power_manager.mean_cycle_power
                _LOGGER.info(
                    "%s - underlying just switch ON. Set power and energy start date %s",
                    self,
                    self._underlying_climate_start_hvac_action_date.isoformat(),
                )
                changes = True

            if old_hvac_action in HVAC_ACTION_ON and new_hvac_action not in HVAC_ACTION_ON:
                self.incremente_energy()
                changes = True

        # Filter new state when received just after a change from VTherm
        # Issue #120 - Some TRV are changing target temperature a very long time (6 sec) after the change.
        # In that case a loop is possible if a user change multiple times during this 6 sec.
        new_state_date_updated = new_state.last_updated if new_state.last_updated else None
        if new_state_date_updated and self._last_change_time_from_vtherm:
            delta = (new_state_date_updated - self._last_change_time_from_vtherm).total_seconds()
            if delta < 10:
                _LOGGER.info(
                    "%s - underlying event is received less than 10 sec after command. Forget it to avoid loop",
                    self,
                )
                await end_climate_changed(changes)
                return

        # Update all underlyings hvac_mode state if it has change
        if new_hvac_mode:
            # Issue #334 - if all underlyings are not aligned with the same hvac_mode don't change the underlying and wait they are aligned
            if self.is_over_climate:
                for under in self._underlyings:
                    if under.entity_id != new_state.entity_id and under.hvac_mode != self.vtherm_hvac_mode:
                        _LOGGER.info(
                            "%s - the underlying's hvac_mode %s is not aligned with VTherm hvac_mode %s. So we don't diffuse the change to all other underlyings to avoid loops",
                            under,
                            under.hvac_mode,
                            self.vtherm_hvac_mode,
                        )
                        return

                _LOGGER.debug(
                    "%s - All underlyings have the same hvac_mode, so VTherm will send the new hvac mode %s",
                    self,
                    new_hvac_mode,
                )
            changes = True
            # We follow the underlying hvac_mode change
            if self._follow_underlying_temp_change:
                self.requested_state.set_hvac_mode(new_hvac_mode)

        # A quick win to known if it has change by using the self._attr_fan_mode and not only underlying[0].fan_mode
        if new_fan_mode:
            self._attr_fan_mode = new_fan_mode
            changes = True

        # Manage new target temperature set if state if no other changes have been found
        # and if a target temperature have already been sent and if the VTherm is on
        if new_target_temp and self._follow_underlying_temp_change and not changes:
            if under.last_sent_temperature is not None and self.vtherm_hvac_mode != VThermHvacMode_OFF:
                _LOGGER.debug(
                    "%s - Do temperature check. under.last_sent_temperature is %s, new_target_temp is %s",
                    self,
                    under.last_sent_temperature,
                    new_target_temp,
                )
                _LOGGER.info(
                    "%s - Target temp in underlying have change to %s (vs %s)",
                    self,
                    new_target_temp,
                    under.last_sent_temperature,
                )
                await self.async_set_temperature(temperature=new_target_temp)
                changes = True

        await end_climate_changed(changes)

    @overrides
    async def async_control_heating(self, timestamp=None, force=False) -> bool:
        """The main function used to run the calculation at each cycle"""

        if not self.is_ready:
            _LOGGER.debug("%s - async_control_heating is called but the entity is not initialized yet. Skip the cycle", self)
            return False

        # Check if we need to auto start/stop the Vtherm
        old_stop = self.auto_start_stop_manager.is_auto_stop_detected
        new_stop = await self.auto_start_stop_manager.refresh_state()
        if old_stop != new_stop:
            _LOGGER.info("%s - Auto stop state changed from %s to %s", self, old_stop, new_stop)
            self.requested_state.force_changed()
            await self.update_states(force=True)
            return True

        # Continue the normal async_control_heating

        # Send the regulated temperature to the underlyings
        await self._send_regulated_temperature(force=force)

        if self._auto_fan_mode and self._auto_fan_mode != CONF_AUTO_FAN_NONE:
            await self._send_auto_fan_mode()

        ret = await super().async_control_heating(timestamp=timestamp, force=force)

        self.incremente_energy()

        return ret

    def set_follow_underlying_temp_change(self, follow: bool):
        """Set the flaf follow the underlying temperature changes"""
        self._follow_underlying_temp_change = follow
        self.update_custom_attributes()
        self.async_write_ha_state()

    @overrides
    async def _async_temperature_changed(self, event: Event) -> callable:
        """Handle temperature of the temperature sensor changes.
        Return the function to dearm (clear) the window auto check"""

        ret = await super()._async_temperature_changed(event)

        # Synchronize the device temperature if needed
        await self.synchronize_device_temperature()

        return ret

    async def synchronize_device_temperature(self):
        """Synchronize the device temperature by sending the offset calibration"""

        if not self.has_sync_entities:
            return

        for idx, sync_entity_id in enumerate(self._sync_entity_list):
            sync_entity_state = self._hass.states.get(sync_entity_id)
            if not sync_entity_state:
                _LOGGER.warning(
                    "%s - Cannot synchronize device temperature because sync entity %s not found",
                    self,
                    sync_entity_id,
                )
                continue

            under = self.underlying_entity(idx)
            if not under:
                _LOGGER.warning(
                    "%s - Cannot synchronize device temperature because underlying index %d not found",
                    self,
                    idx,
                )
                continue

            if (
                (min_sync_entity := under.min_sync_entity) is not None
                and (max_sync_entity := under.max_sync_entity) is not None
                and (step_sync_entity := under.step_sync_entity) is not None
            ):
                pass
            else:
                # get min, max, step from sync entity attributes
                min_sync_entity = sync_entity_state.attributes.get("min")
                max_sync_entity = sync_entity_state.attributes.get("max")
                step_sync_entity = sync_entity_state.attributes.get("step") or 0.1  # default step is 0.1

                # save the min, max and step
                under.set_min_max_step_sync_entity(
                    min_sync_entity,
                    max_sync_entity,
                    step_sync_entity,
                )

            room_temp = self.current_temperature
            if self._sync_with_calibration:
                # send offset_calibration to the difference between target temp and local temp
                offset = None
                local_temp = under.underlying_current_temperature
                current_offset = get_safe_float(self._hass, sync_entity_id)
                if local_temp is not None and room_temp is not None and current_offset is not None:
                    val = round_to_nearest(room_temp - (local_temp - current_offset), step_sync_entity)
                    offset = min(max_sync_entity, max(min_sync_entity, val))

                    _LOGGER.debug(
                        "%s - Synchronize device temperature for entity %s: local_temp=%.2f, room_temp=%.2f, current_offset=%.2f -> new offset=%.2f",
                        self,
                        sync_entity_id,
                        local_temp,
                        room_temp,
                        current_offset,
                        offset,
                    )
                    await under.send_value_to_number(sync_entity_id, offset)
            elif room_temp is not None:
                # Send the new temperature directly
                val = round_to_nearest(room_temp, step_sync_entity)
                val = min(max_sync_entity, max(min_sync_entity, val))
                _LOGGER.debug(
                    "%s - Synchronize device temperature for entity %s: room_temp=%.2f -> new temp=%.2f",
                    self,
                    sync_entity_id,
                    room_temp,
                    val,
                )
                await under.send_value_to_number(sync_entity_id, val)

    @property
    def has_sync_entities(self) -> bool:
        """Return True if the underlying have a sync entity"""
        return self._sync_entity_list is not None and len(self._sync_entity_list) > 0

    @property
    def is_sync_with_calibration(self) -> bool:
        """Return True if the underlying is synchronized with calibration (or with temperature copying)"""
        return self._sync_with_calibration

    @property
    def sync_entity_ids(self) -> list[str] | None:
        """Get the sync entity ids"""
        return self._sync_entity_list

    @property
    def auto_regulation_mode(self) -> str | None:
        """Get the regulation mode"""
        return self._auto_regulation_mode

    @property
    def auto_fan_mode(self) -> str | None:
        """Get the auto fan mode"""
        return self._auto_fan_mode

    @property
    def auto_regulation_use_device_temp(self) -> bool | None:
        """Returns the value of parameter auto_regulation_use_device_temp"""
        return self._auto_regulation_use_device_temp

    @property
    def regulated_target_temp(self) -> float | None:
        """Get the regulated target temperature"""
        return self._regulated_target_temp

    @property
    def is_regulated(self) -> bool:
        """Check if the ThermostatOverClimate is regulated"""
        return self.auto_regulation_mode != CONF_AUTO_REGULATION_NONE

    @overrides
    def build_hvac_list(self) -> list[VThermHvacMode]:
        """Build the hvac list depending on ac_mode"""
        if self.underlying_entity(0):
            # replace HEAT_COOL by heat and cool
            result = under_hvac_modes = self.underlying_entity(0).hvac_modes
            if VThermHvacMode_HEAT_COOL in under_hvac_modes:
                result = [mode for mode in under_hvac_modes if mode != VThermHvacMode_HEAT_COOL]
                if VThermHvacMode_HEAT not in under_hvac_modes:
                    result.extend([VThermHvacMode_HEAT])
                if VThermHvacMode_COOL not in under_hvac_modes:
                    result.extend([VThermHvacMode_COOL])

            return result

        if self._ac_mode:
            return [VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF]

        return [VThermHvacMode_HEAT, VThermHvacMode_OFF]

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting.

        Requires ClimateEntityFeature.FAN_MODE.
        """
        if self.underlying_entity(0):
            self._attr_fan_mode = self.underlying_entity(0).fan_mode
            return self._attr_fan_mode

        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes.

        Requires ClimateEntityFeature.FAN_MODE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).fan_modes

        return []

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).swing_mode

        return None

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).swing_modes

        return None

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the swing horizontal setting.

        Requires ClimateEntityFeature.SWING_HORIZONTAL_MODE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).swing_horizontal_mode

        return None

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the list of available swing horizontal modes.

        Requires ClimateEntityFeature.SWING_HORIZONTAL_MODE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).swing_horizontal_modes

        return None

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self.hass.config.units.temperature_unit

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self.underlying_entity(0) and self.underlying_entity(0).supported_features:
            return self.underlying_entity(0).supported_features | self._support_flags

        return self._support_flags

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach.

        Requires ClimateEntityFeature.TARGET_TEMPERATURE_RANGE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).target_temperature_high

        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach.

        Requires ClimateEntityFeature.TARGET_TEMPERATURE_RANGE.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).target_temperature_low

        return None

    @property
    def current_humidity(self) -> float | None:
        """Return the humidity."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).current_humidity

        return None

    @property
    def is_aux_heat(self) -> bool | None:
        """Return true if aux heater.

        Requires ClimateEntityFeature.AUX_HEAT.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).is_aux_heat

        return None

    @property
    def follow_underlying_temp_change(self) -> bool:
        """Get the follow underlying temp change flag"""
        return self._follow_underlying_temp_change

    @overrides
    async def init_underlyings_completed(self, under_entity_id: Optional[str] = None):
        """Called when all entities of an underlying are initialized. Then we can complete the startup with the underlying info"""
        if not self.is_ready:
            return

        # Reinitialize the hvac list because we have one underlying at least now
        self.set_hvac_list()
        await super().init_underlyings_completed(under_entity_id)

        self.choose_auto_fan_mode(self._auto_fan_mode)

    @overrides
    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).turn_aux_heat_on()

        raise NotImplementedError()

    @overrides
    async def async_turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        for under in self._underlyings:
            await under.async_turn_aux_heat_on()

    @overrides
    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        for under in self._underlyings:
            return under.turn_aux_heat_off()

    @overrides
    async def async_turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        for under in self._underlyings:
            await under.async_turn_aux_heat_off()

    @overrides
    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        _LOGGER.info("%s - Set fan mode: %s", self, fan_mode)
        if fan_mode is None:
            return

        for under in self._underlyings:
            await under.set_fan_mode(fan_mode)
        self._fan_mode = fan_mode
        self.async_write_ha_state()

    @overrides
    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set humidity: %s", self, humidity)
        if humidity is None:
            return
        for under in self._underlyings:
            await under.set_humidity(humidity)
        self._humidity = humidity
        self.async_write_ha_state()

    @overrides
    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set swing mode: %s", self, swing_mode)
        if swing_mode is None:
            return
        for under in self._underlyings:
            await under.set_swing_mode(swing_mode)
        self._swing_mode = swing_mode
        self.async_write_ha_state()

    @overrides
    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode):
        """Set new target swing horizontal operation."""
        _LOGGER.info("%s - Set swing horizontal mode: %s", self, swing_horizontal_mode)
        if swing_horizontal_mode is None:
            return
        for under in self._underlyings:
            await under.set_swing_horizontal_mode(swing_horizontal_mode)
        self._swing_horizontal_mode = swing_horizontal_mode
        self.async_write_ha_state()

    async def service_set_auto_regulation_mode(self, auto_regulation_mode: str):
        """Called by a service call:
        service: versatile_thermostat.set_auto_regulation_mode
        data:
            auto_regulation_mode: [None | Light | Medium | Strong]
        target:
            entity_id: climate.thermostat_1
        """
        _LOGGER.info(
            "%s - Calling service_set_auto_regulation_mode, auto_regulation_mode: %s",
            self,
            auto_regulation_mode,
        )
        if auto_regulation_mode == "None":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_NONE)
        elif auto_regulation_mode == "Light":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_LIGHT)
        elif auto_regulation_mode == "Medium":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_MEDIUM)
        elif auto_regulation_mode == "Strong":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_STRONG)
        elif auto_regulation_mode == "Slow":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_SLOW)
        elif auto_regulation_mode == "Expert":
            self.choose_auto_regulation_mode(CONF_AUTO_REGULATION_EXPERT)
        else:
            _LOGGER.warning(
                "%s - auto_regulation_mode %s is not supported",
                self,
                auto_regulation_mode,
            )
            return

        await self._send_regulated_temperature()
        self.update_custom_attributes()
        self.async_write_ha_state()

    async def service_set_auto_fan_mode(self, auto_fan_mode: str):
        """Called by a service call:
        service: versatile_thermostat.set_auto_fan_mode
        data:
            auto_fan_mode: [None | Low | Medium | High | Turbo]
        target:
            entity_id: climate.thermostat_1
        """
        _LOGGER.info(
            "%s - Calling service_set_auto_fan_mode, auto_fan_mode: %s",
            self,
            auto_fan_mode,
        )
        if auto_fan_mode == "None":
            self.choose_auto_fan_mode(CONF_AUTO_FAN_NONE)
        elif auto_fan_mode == "Low":
            self.choose_auto_fan_mode(CONF_AUTO_FAN_LOW)
        elif auto_fan_mode == "Medium":
            self.choose_auto_fan_mode(CONF_AUTO_FAN_MEDIUM)
        elif auto_fan_mode == "High":
            self.choose_auto_fan_mode(CONF_AUTO_FAN_HIGH)
        elif auto_fan_mode == "Turbo":
            self.choose_auto_fan_mode(CONF_AUTO_FAN_TURBO)

        self.update_custom_attributes()
        self.async_write_ha_state()

    @overrides
    async def async_turn_off(self) -> None:
        """Turn off the climate entity."""
        self._last_hvac_mode = self.requested_state.hvac_mode
        await self.async_set_hvac_mode(VThermHvacMode_OFF)

    @overrides
    async def async_turn_on(self) -> None:
        """Turn on the climate entity. If multiple modes are available, choose the most appropriate one."""
        if self._last_hvac_mode:
            await self.async_set_hvac_mode(self._last_hvac_mode)
        elif self._ac_mode:
            await self.async_set_hvac_mode(VThermHvacMode_COOL)
        else:
            await self.async_set_hvac_mode(VThermHvacMode_HEAT)

    @property
    def vtherm_type(self) -> str | None:
        """Return the type of thermostat"""
        return "over_climate"
