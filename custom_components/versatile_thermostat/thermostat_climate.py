# pylint: disable=line-too-long, too-many-lines, abstract-method
""" A climate over climate classe """
import logging
from datetime import timedelta, datetime

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    EventStateChangedData,
)
from homeassistant.components.climate import (
    HVACAction,
    HVACMode,
    ClimateEntityFeature,
)

from .commons import round_to_nearest
from .base_thermostat import BaseThermostat, ConfigData
from .pi_algorithm import PITemperatureRegulator

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingClimate
from .feature_auto_start_stop_manager import FeatureAutoStartStopManager

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
                "start_hvac_action_date",
                "underlying_entities",
                "regulation_accumulated_error",
                "auto_regulation_mode",
                "auto_fan_mode",
                "current_auto_fan_mode",
                "auto_activated_fan_mode",
                "auto_deactivated_fan_mode",
                "auto_regulation_use_device_temp",
                "follow_underlying_temp_change",
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

        # super.__init__ calls post_init at the end. So it must be called after regulation initialization
        super().__init__(hass, unique_id, name, entry_infos)
        self._regulated_target_temp = self.target_temperature

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat"""

        self._auto_start_stop_manager: FeatureAutoStartStopManager = (
            FeatureAutoStartStopManager(self, self._hass)
        )

        self.register_manager(self._auto_start_stop_manager)

        super().post_init(config_entry)

        for climate in config_entry.get(CONF_UNDERLYING_LIST):
            under = UnderlyingClimate(
                hass=self._hass,
                thermostat=self,
                climate_entity_id=climate,
            )
            self._underlyings.append(under)

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

    def calculate_hvac_action(self, under_list: list) -> HVACAction | None:
        """Calculate an hvac action based on the hvac_action of the list in argument"""
        # if one not IDLE or OFF -> return it
        # else if one IDLE -> IDLE
        # else OFF
        one_idle = False
        for under in under_list:
            if (action := under.hvac_action) not in [
                HVACAction.IDLE,
                HVACAction.OFF,
            ]:
                return action
            if under.hvac_action == HVACAction.IDLE:
                one_idle = True
        if one_idle:
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Returns the current hvac_action by checking all hvac_action of the underlyings"""
        return self.calculate_hvac_action(self._underlyings)

    @overrides
    async def change_target_temperature(self, temperature: float, force=False):
        """Set the target temperature and the target temperature of underlying climate if any"""
        await super().change_target_temperature(temperature, force=force)

        self._regulation_algo.set_target_temp(self.target_temperature)
        # Is necessary cause control_heating method will not force the update.
        await self._send_regulated_temperature(force=True)

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""

        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.debug(
                "%s - don't send regulated temperature cause VTherm is off ", self
            )
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

        if self._last_regulation_change is not None:
            period = (
                float((self.now - self._last_regulation_change).total_seconds()) / 60.0
            )
            if not force and period < self._auto_regulation_period_min:
                _LOGGER.info(
                    "%s - period (%.1f) min is < %.0f min -> forget the regulation send",
                    self,
                    period,
                    self._auto_regulation_period_min,
                )
                return

        if not self._regulated_target_temp:
            self._regulated_target_temp = self.target_temperature

        _LOGGER.info("%s - regulation calculation will be done", self)

        # use _attr_target_temperature_step to round value if _auto_regulation_dtemp is equal to 0
        regulation_step = self._auto_regulation_dtemp if self._auto_regulation_dtemp else self._attr_target_temperature_step
        _LOGGER.debug("%s - usage regulation_step: %.2f ", self, regulation_step)

        if self.current_temperature is not None:
            new_regulated_temp = round_to_nearest(
                self._regulation_algo.calculate_regulated_temperature(
                    self.current_temperature, self._cur_ext_temp
                ),
                regulation_step,
            )
        else:
            new_regulated_temp = self.target_temperature
        dtemp = new_regulated_temp - self._regulated_target_temp

        if not force and abs(dtemp) < self._auto_regulation_dtemp:
            _LOGGER.info(
                "%s - dtemp (%.1f) is < %.1f -> forget the regulation send",
                self,
                dtemp,
                self._auto_regulation_dtemp,
            )
            return

        self._regulated_target_temp = new_regulated_temp
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

            target_temp = round_to_nearest(self.regulated_target_temp + offset_temp, regulation_step)

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
        hvac_mode = self.hvac_mode
        if (
            (hvac_mode == HVACMode.COOL and dtemp > 0)
            or (hvac_mode == HVACMode.HEAT and dtemp < 0)
            or (hvac_mode == HVACMode.OFF)
        ):
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
                RegulationParamLight.stabilization_threshold,
                RegulationParamLight.accumulated_error_threshold,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_MEDIUM:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamMedium.kp,
                RegulationParamMedium.ki,
                RegulationParamMedium.k_ext,
                RegulationParamMedium.offset_max,
                RegulationParamMedium.stabilization_threshold,
                RegulationParamMedium.accumulated_error_threshold,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_STRONG:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamStrong.kp,
                RegulationParamStrong.ki,
                RegulationParamStrong.k_ext,
                RegulationParamStrong.offset_max,
                RegulationParamStrong.stabilization_threshold,
                RegulationParamStrong.accumulated_error_threshold,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_SLOW:
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature,
                RegulationParamSlow.kp,
                RegulationParamSlow.ki,
                RegulationParamSlow.k_ext,
                RegulationParamSlow.offset_max,
                RegulationParamSlow.stabilization_threshold,
                RegulationParamSlow.accumulated_error_threshold,
            )
        elif self._auto_regulation_mode == CONF_AUTO_REGULATION_EXPERT:
            api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(
                self._hass
            )
            if api is not None:
                if (expert_param := api.self_regulation_expert) is not None:
                    self._regulation_algo = PITemperatureRegulator(
                        self.target_temperature,
                        expert_param.get("kp"),
                        expert_param.get("ki"),
                        expert_param.get("k_ext"),
                        expert_param.get("offset_max"),
                        expert_param.get("stabilization_threshold"),
                        expert_param.get("accumulated_error_threshold"),
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
            self._regulation_algo = PITemperatureRegulator(
                self.target_temperature, 0, 0, 0, 0, 0.1, 0
            )

    def choose_auto_fan_mode(self, auto_fan_mode: str):
        """Choose the correct fan mode depending of the underlying capacities and the configuration"""

        self._current_auto_fan_mode = auto_fan_mode

        # Get the supported feature of the first underlying. We suppose each underlying have the same fan attributes
        fan_supported = self.supported_features & ClimateEntityFeature.FAN_MODE > 0

        if auto_fan_mode == CONF_AUTO_FAN_NONE or not fan_supported:
            self._auto_activated_fan_mode = self._auto_deactivated_fan_mode = None
            return

        def find_fan_mode(fan_modes: list[str], fan_mode: str) -> str | None:
            """Return the fan_mode if it exist of None if not"""
            try:
                return fan_mode if fan_modes.index(fan_mode) >= 0 else None
            except ValueError:
                return None

        fan_modes = self.fan_modes
        if auto_fan_mode == CONF_AUTO_FAN_LOW:
            self._auto_activated_fan_mode = find_fan_mode(fan_modes, "low")
        elif auto_fan_mode == CONF_AUTO_FAN_MEDIUM:
            self._auto_activated_fan_mode = find_fan_mode(fan_modes, "mid")
        elif auto_fan_mode == CONF_AUTO_FAN_HIGH:
            self._auto_activated_fan_mode = find_fan_mode(fan_modes, "high")
        elif auto_fan_mode == CONF_AUTO_FAN_TURBO:
            self._auto_activated_fan_mode = find_fan_mode(
                fan_modes, "turbo"
            ) or find_fan_mode(fan_modes, "high")

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
        for climate in self._underlyings:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [climate.entity_id], self._async_climate_changed
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

        # init auto_regulation_mode
        # Issue 325 - do only once (in post_init and not here)
        # self.choose_auto_regulation_mode(self._auto_regulation_mode)

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

        self._attr_extra_state_attributes["is_over_climate"] = self.is_over_climate
        self._attr_extra_state_attributes["start_hvac_action_date"] = (
            self._underlying_climate_start_hvac_action_date
        )

        self._attr_extra_state_attributes["underlying_entities"] = [
            underlying.entity_id for underlying in self._underlyings
        ]

        if self.is_regulated:
            self._attr_extra_state_attributes["is_regulated"] = self.is_regulated
            self._attr_extra_state_attributes["regulated_target_temperature"] = (
                self._regulated_target_temp
            )
            self._attr_extra_state_attributes["auto_regulation_mode"] = (
                self.auto_regulation_mode
            )
            self._attr_extra_state_attributes["regulation_accumulated_error"] = (
                self._regulation_algo.accumulated_error
            )

        self._attr_extra_state_attributes["auto_fan_mode"] = self.auto_fan_mode
        self._attr_extra_state_attributes["current_auto_fan_mode"] = (
            self._current_auto_fan_mode
        )

        self._attr_extra_state_attributes["auto_activated_fan_mode"] = (
            self._auto_activated_fan_mode
        )

        self._attr_extra_state_attributes["auto_deactivated_fan_mode"] = (
            self._auto_deactivated_fan_mode
        )

        self._attr_extra_state_attributes["auto_regulation_use_device_temp"] = (
            self.auto_regulation_use_device_temp
        )

        self._attr_extra_state_attributes["follow_underlying_temp_change"] = (
            self._follow_underlying_temp_change
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
        _LOGGER.debug("%s - recalculate all", self)
        self.update_custom_attributes()
        self.async_write_ha_state()

    @overrides
    async def restore_hvac_mode(self, need_control_heating=False):
        """Restore a previous hvac_mod"""
        old_hvac_mode = self.hvac_mode

        await super().restore_hvac_mode(need_control_heating=need_control_heating)

        # Issue 133 - force the temperature in over_climate mode if unerlying are turned on
        if old_hvac_mode == HVACMode.OFF and self.hvac_mode != HVACMode.OFF:
            _LOGGER.info(
                "%s - Force resent target temp cause we turn on some over climate"
            )
            await self.change_target_temperature(self._target_temp)

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""

        if self.hvac_mode == HVACMode.OFF:
            return

        device_power = self.power_manager.device_power
        added_energy = 0
        if (
            self.is_over_climate
            and self._underlying_climate_delta_t is not None
            and device_power
        ):
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

        _LOGGER.debug(
            "%s - added energy is %.3f . Total energy is now: %.3f",
            self,
            added_energy,
            self._total_energy,
        )

    @callback
    async def _async_climate_changed(self, event: Event[EventStateChangedData]):
        """Handle unerdlying climate state changes.
        This method takes the underlying values and update the VTherm with them.
        To avoid loops (issues #121 #101 #95 #99), we discard the event if it is received
        less than 10 sec after the last command. What we want here is to take the values
        from underlyings ONLY if someone have change directly on the underlying and not
        as a return of the command. The only thing we take all the time is the HVACAction
        which is important for feedaback and which cannot generates loops.
        """

        async def end_climate_changed(changes: bool):
            """To end the event management"""
            if changes:
                # already done by update_custom_attribute
                # self.async_write_ha_state()
                self.update_custom_attributes()
                await self.async_control_heating()

        new_state = event.data.get("new_state")
        _LOGGER.debug("%s - _async_climate_changed new_state is %s", self, new_state)
        if not new_state:
            return

        # Find the underlying which have change
        under: UnderlyingClimate = self.find_underlying_by_entity_id(new_state.entity_id)

        if not under:
            _LOGGER.warning(
                "We have a receive an event from entity %s which is NOT one of our underlying entities. This is not normal and should be reported to the developper of the integration"
            )
            return

        changes = False
        new_hvac_mode = new_state.state

        old_state = event.data.get("old_state")

        # Issue #829 - refresh underlying command if it comes back to life
        if old_state is not None and new_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) and old_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.warning("%s - underlying %s come back to life. New state=%s, old_state=%s. Will refresh its status", self, under.entity_id, new_state.state, old_state.state)
            # Force hvac_mode and target temperature
            await under.set_hvac_mode(self.hvac_mode)
            await self._send_regulated_temperature(force=True)

            return

        old_hvac_action = (
            old_state.attributes.get("hvac_action")
            if old_state and old_state.attributes
            else None
        )
        new_hvac_action = (
            new_state.attributes.get("hvac_action")
            if new_state and new_state.attributes
            else None
        )

        new_fan_mode = (
            new_state.attributes.get("fan_mode")
            if new_state and new_state.attributes
            else None
        )

        old_state_date_changed = (
            old_state.last_changed if old_state and old_state.last_changed else None
        )
        old_state_date_updated = (
            old_state.last_updated if old_state and old_state.last_updated else None
        )
        new_state_date_changed = (
            new_state.last_changed if new_state and new_state.last_changed else None
        )
        new_state_date_updated = (
            new_state.last_updated if new_state and new_state.last_updated else None
        )

        new_target_temp = (
            new_state.attributes.get("temperature")
            if new_state and new_state.attributes
            else None
        )

        last_sent_temperature = under.last_sent_temperature or 0
        under_temp_diff = (
            (new_target_temp - last_sent_temperature) if new_target_temp else 0
        )

        step = self.target_temperature_step or 1
        if -step < under_temp_diff < step:
            under_temp_diff = 0

        # Issue 99 - some AC turn hvac_mode=cool and hvac_action=idle when sending a HVACMode_OFF command
        # Issue 114 - Remove this because hvac_mode is now managed by local _hvac_mode and use idle action as is
        # if self._hvac_mode == HVACMode.OFF and new_hvac_action == HVACAction.IDLE:
        #    _LOGGER.debug("The underlying switch to idle instead of OFF. We will consider it as OFF")
        #    new_hvac_mode = HVACMode.OFF

        # Forget event when the event holds no real changes
        if (
            new_hvac_mode == self._hvac_mode
            and new_hvac_action == old_hvac_action
            and under_temp_diff == 0
            and (new_fan_mode is None or new_fan_mode == self._attr_fan_mode)
        ):
            _LOGGER.debug(
                "%s - a underlying state change event is received but no real change have been found. Forget the event",
                self,
            )
            return

        # Ignore new target temperature when out of range
        if (
            not new_target_temp is None
            and not self._attr_min_temp is None
            and not self._attr_max_temp is None
            and not (self._attr_min_temp <= new_target_temp <= self._attr_max_temp)
        ):
            _LOGGER.debug(
                "%s - underlying sent a target temperature (%s) which is out of configured min/max range (%s / %s). The value will be ignored",
                self,
                new_target_temp,
                self._attr_min_temp,
                self._attr_max_temp,
            )
            new_target_temp = None
            under_temp_diff = 0

        # A real changes have to be managed
        _LOGGER.info(
            "%s - Underlying climate %s have changed. new_hvac_mode is %s (vs %s), new_hvac_action=%s (vs %s), new_target_temp=%s (vs %s), new_fan_mode=%s (vs %s)",
            self,
            under.entity_id,
            new_hvac_mode,
            self._hvac_mode,
            new_hvac_action,
            old_hvac_action,
            new_target_temp,
            self.target_temperature,
            new_fan_mode,
            self._attr_fan_mode,
        )

        _LOGGER.debug(
            "%s - last_change_time=%s old_state_date_changed=%s old_state_date_updated=%s new_state_date_changed=%s new_state_date_updated=%s",
            self,
            self._last_change_time_from_vtherm,
            old_state_date_changed,
            old_state_date_updated,
            new_state_date_changed,
            new_state_date_updated,
        )

        # Interpretation of hvac action
        if old_hvac_action not in HVAC_ACTION_ON and new_hvac_action in HVAC_ACTION_ON:
            self._underlying_climate_start_hvac_action_date = (
                self.get_last_updated_date_or_now(new_state)
            )
            _LOGGER.info(
                "%s - underlying just switch ON. Set power and energy start date %s",
                self,
                self._underlying_climate_start_hvac_action_date.isoformat(),
            )
            changes = True

        if old_hvac_action in HVAC_ACTION_ON and new_hvac_action not in HVAC_ACTION_ON:
            stop_power_date = self.get_last_updated_date_or_now(new_state)
            if self._underlying_climate_start_hvac_action_date:
                delta = (
                    stop_power_date - self._underlying_climate_start_hvac_action_date
                )
                self._underlying_climate_delta_t = delta.total_seconds() / 3600.0

                # increment energy at the end of the cycle
                self.incremente_energy()

                self._underlying_climate_start_hvac_action_date = None

            _LOGGER.info(
                "%s - underlying just switch OFF at %s. delta_h=%.3f h",
                self,
                stop_power_date.isoformat(),
                self._underlying_climate_delta_t,
            )
            changes = True

        # Filter new state when received just after a change from VTherm
        # Issue #120 - Some TRV are changing target temperature a very long time (6 sec) after the change.
        # In that case a loop is possible if a user change multiple times during this 6 sec.
        if new_state_date_updated and self._last_change_time_from_vtherm:
            delta = (
                new_state_date_updated - self._last_change_time_from_vtherm
            ).total_seconds()
            if delta < 10:
                _LOGGER.info(
                    "%s - underlying event is received less than 10 sec after command. Forget it to avoid loop",
                    self,
                )
                await end_climate_changed(changes)
                return

        # Update all underlyings hvac_mode state if it has change
        if (
            new_hvac_mode
            in [
                HVACMode.OFF,
                HVACMode.HEAT,
                HVACMode.COOL,
                HVACMode.HEAT_COOL,
                HVACMode.DRY,
                HVACMode.AUTO,
                HVACMode.FAN_ONLY,
                None,
            ]
            and self._hvac_mode != new_hvac_mode
        ):
            # Issue #334 - if all underlyings are not aligned with the same hvac_mode don't change the underlying and wait they are aligned
            if self.is_over_climate:
                for under in self._underlyings:
                    if (
                        under.entity_id != new_state.entity_id
                        and under.hvac_mode != self._hvac_mode
                    ):
                        _LOGGER.info(
                            "%s - the underlying's hvac_mode %s is not aligned with VTherm hvac_mode %s. So we don't diffuse the change to all other underlyings to avoid loops",
                            under,
                            under.hvac_mode,
                            self._hvac_mode,
                        )
                        return

                _LOGGER.debug(
                    "%s - All underlyings have the same hvac_mode, so VTherm will send the new hvac mode %s",
                    self,
                    new_hvac_mode,
                )
                for under in self._underlyings:
                    await under.set_hvac_mode(new_hvac_mode)
            changes = True
            self._hvac_mode = new_hvac_mode

        # A quick win to known if it has change by using the self._attr_fan_mode and not only underlying[0].fan_mode
        if new_fan_mode != self._attr_fan_mode:
            self._attr_fan_mode = new_fan_mode
            changes = True

        # try to manage new target temperature set if state if no other changes have been found
        # and if a target temperature have already been sent
        if (
            self._follow_underlying_temp_change
            and not changes
            and under.last_sent_temperature is not None
        ):
            _LOGGER.debug(
                "%s - Do temperature check. under.last_sent_temperature is %s, new_target_temp is %s",
                self,
                under.last_sent_temperature,
                new_target_temp,
            )
            # if the underlying have change its target temperature
            if under_temp_diff != 0:
                _LOGGER.info(
                    "%s - Target temp in underlying have change to %s (vs %s)",
                    self,
                    new_target_temp,
                    under.last_sent_temperature,
                )
                await self.async_set_temperature(temperature=new_target_temp)
                changes = True
            else:
                _LOGGER.debug(
                    "%s - Forget the eventual underlying temperature change there is no real change",
                    self,
                )

        await end_climate_changed(changes)

    @overrides
    async def async_control_heating(self, force=False, _=None) -> bool:
        """The main function used to run the calculation at each cycle"""
        ret = await super().async_control_heating(force, _)

        # Check if we need to auto start/stop the Vtherm
        continu = await self.auto_start_stop_manager.refresh_state()
        if not continu:
            return ret

        # Continue the normal async_control_heating

        # Send the regulated temperature to the underlyings
        await self._send_regulated_temperature()

        if self._auto_fan_mode and self._auto_fan_mode != CONF_AUTO_FAN_NONE:
            await self._send_auto_fan_mode()

        return ret

    def set_follow_underlying_temp_change(self, follow: bool):
        """Set the flaf follow the underlying temperature changes"""
        self._follow_underlying_temp_change = follow
        self.update_custom_attributes()

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

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """List of available operation modes."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).hvac_modes
        else:
            return super.hvac_modes

    @property
    def mean_cycle_power(self) -> float | None:
        """Returns the mean power consumption during the cycle"""
        return None

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
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self.hass.config.units.temperature_unit

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self.underlying_entity(0):
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
    def is_initialized(self) -> bool:
        """Check if all underlyings are initialized"""
        for under in self._underlyings:
            if not under.is_initialized:
                return False
        return True

    @property
    def follow_underlying_temp_change(self) -> bool:
        """Get the follow underlying temp change flag"""
        return self._follow_underlying_temp_change

    @property
    def auto_start_stop_manager(self) -> FeatureAutoStartStopManager:
        """Return the auto-start-stop Manager"""
        return self._auto_start_stop_manager

    @overrides
    def init_underlyings(self):
        """Init the underlyings if not already done"""
        for under in self._underlyings:
            if not under.is_initialized:
                _LOGGER.info(
                    "%s - Underlying %s is not initialized. Try to initialize it",
                    self,
                    under.entity_id,
                )
                try:
                    under.startup()
                except UnknownEntity:
                    # still not found, we an stop here
                    return False
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

    @overrides
    async def async_turn_off(self) -> None:
        # if window is open, don't overwrite the saved_hvac_mode
        if self.window_state != STATE_ON:
            self.save_hvac_mode()
        await self.async_set_hvac_mode(HVACMode.OFF)

    @overrides
    async def async_turn_on(self) -> None:

        # don't turn_on if window is open
        if self.window_state == STATE_ON:
            _LOGGER.info(
                "%s - refuse to turn on because window is open. We keep the save_hvac_mode",
                self,
            )
            return

        if self._saved_hvac_mode is not None:  # pylint: disable=protected-access
            await self.restore_hvac_mode(True)
        else:
            if self._ac_mode:
                await self.async_set_hvac_mode(HVACMode.COOL)
            else:
                await self.async_set_hvac_mode(HVACMode.HEAT)
