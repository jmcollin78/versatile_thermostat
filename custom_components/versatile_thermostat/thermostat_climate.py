# pylint: disable=line-too-long
""" A climate over switch classe """
import logging
from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from homeassistant.components.climate import HVACAction, HVACMode

from .commons import NowClass, round_to_nearest
from .base_thermostat import BaseThermostat
from .pi_algorithm import PITemperatureRegulator

from .const import (
    overrides,
    DOMAIN,
    CONF_CLIMATE,
    CONF_CLIMATE_2,
    CONF_CLIMATE_3,
    CONF_CLIMATE_4,
    CONF_AUTO_REGULATION_MODE,
    CONF_AUTO_REGULATION_NONE,
    CONF_AUTO_REGULATION_SLOW,
    CONF_AUTO_REGULATION_LIGHT,
    CONF_AUTO_REGULATION_MEDIUM,
    CONF_AUTO_REGULATION_STRONG,
    CONF_AUTO_REGULATION_EXPERT,
    CONF_AUTO_REGULATION_DTEMP,
    CONF_AUTO_REGULATION_PERIOD_MIN,
    RegulationParamSlow,
    RegulationParamLight,
    RegulationParamMedium,
    RegulationParamStrong,
)

from .vtherm_api import VersatileThermostatAPI
from .underlyings import UnderlyingClimate

_LOGGER = logging.getLogger(__name__)


class ThermostatOverClimate(BaseThermostat):
    """Representation of a base class for a Versatile Thermostat over a climate"""

    _auto_regulation_mode: str = None
    _regulation_algo = None
    _regulated_target_temp: float = None
    _auto_regulation_dtemp: float = None
    _auto_regulation_period_min: int = None
    _last_regulation_change: datetime = None

    _entity_component_unrecorded_attributes = (
        BaseThermostat._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "is_over_climate",
                    "start_hvac_action_date",
                    "underlying_climate_0",
                    "underlying_climate_1",
                    "underlying_climate_2",
                    "underlying_climate_3",
                    "regulation_accumulated_error",
                    "auto_regulation_mode",
                }
            )
        )
    )

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat over switch."""
        # super.__init__ calls post_init at the end. So it must be called after regulation initialization
        super().__init__(hass, unique_id, name, entry_infos)
        self._regulated_target_temp = self.target_temperature
        self._last_regulation_change = NowClass.get_now(hass)

    @property
    def is_over_climate(self) -> bool:
        """True if the Thermostat is over_climate"""
        return True

    @property
    def hvac_action(self) -> HVACAction | None:
        """Returns the current hvac_action by checking all hvac_action of the underlyings"""

        # if one not IDLE or OFF -> return it
        # else if one IDLE -> IDLE
        # else OFF
        one_idle = False
        for under in self._underlyings:
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

    @overrides
    async def _async_internal_set_temperature(self, temperature):
        """Set the target temperature and the target temperature of underlying climate if any"""
        await super()._async_internal_set_temperature(temperature)

        self._regulation_algo.set_target_temp(self.target_temperature)
        await self._send_regulated_temperature(force=True)

    async def _send_regulated_temperature(self, force=False):
        """Sends the regulated temperature to all underlying"""
        _LOGGER.info(
            "%s - Calling ThermostatClimate._send_regulated_temperature force=%s",
            self,
            force,
        )

        now: datetime = NowClass.get_now(self._hass)
        period = float((now - self._last_regulation_change).total_seconds()) / 60.0
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
        self._last_regulation_change = now

        new_regulated_temp = round_to_nearest(
            self._regulation_algo.calculate_regulated_temperature(
                self.current_temperature, self._cur_ext_temp
            ),
            self._auto_regulation_dtemp,
        )
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

        for under in self._underlyings:
            await under.set_temperature(
                self.regulated_target_temp, self._attr_max_temp, self._attr_min_temp
            )

    @overrides
    def post_init(self, entry_infos):
        """Initialize the Thermostat"""

        super().post_init(entry_infos)
        for climate in [
            CONF_CLIMATE,
            CONF_CLIMATE_2,
            CONF_CLIMATE_3,
            CONF_CLIMATE_4,
        ]:
            if entry_infos.get(climate):
                self._underlyings.append(
                    UnderlyingClimate(
                        hass=self._hass,
                        thermostat=self,
                        climate_entity_id=entry_infos.get(climate),
                    )
                )

        self.choose_auto_regulation_mode(
            entry_infos.get(CONF_AUTO_REGULATION_MODE)
            if entry_infos.get(CONF_AUTO_REGULATION_MODE) is not None
            else CONF_AUTO_REGULATION_NONE
        )

        self._auto_regulation_dtemp = (
            entry_infos.get(CONF_AUTO_REGULATION_DTEMP)
            if entry_infos.get(CONF_AUTO_REGULATION_DTEMP) is not None
            else 0.5
        )
        self._auto_regulation_period_min = (
            entry_infos.get(CONF_AUTO_REGULATION_PERIOD_MIN)
            if entry_infos.get(CONF_AUTO_REGULATION_PERIOD_MIN) is not None
            else 5
        )

    def choose_auto_regulation_mode(self, auto_regulation_mode):
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

    @overrides
    def restore_specific_previous_state(self, old_state):
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
        self._attr_extra_state_attributes[
            "start_hvac_action_date"
        ] = self._underlying_climate_start_hvac_action_date
        self._attr_extra_state_attributes["underlying_climate_0"] = self._underlyings[
            0
        ].entity_id
        self._attr_extra_state_attributes["underlying_climate_1"] = (
            self._underlyings[1].entity_id if len(self._underlyings) > 1 else None
        )
        self._attr_extra_state_attributes["underlying_climate_2"] = (
            self._underlyings[2].entity_id if len(self._underlyings) > 2 else None
        )
        self._attr_extra_state_attributes["underlying_climate_3"] = (
            self._underlyings[3].entity_id if len(self._underlyings) > 3 else None
        )

        if self.is_regulated:
            self._attr_extra_state_attributes["is_regulated"] = self.is_regulated
            self._attr_extra_state_attributes[
                "regulated_target_temperature"
            ] = self._regulated_target_temp
            self._attr_extra_state_attributes[
                "auto_regulation_mode"
            ] = self.auto_regulation_mode
            self._attr_extra_state_attributes[
                "regulation_accumulated_error"
            ] = self._regulation_algo.accumulated_error

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
            await self._async_internal_set_temperature(self._target_temp)

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""

        if self.hvac_mode == HVACMode.OFF:
            return

        added_energy = 0
        if self.is_over_climate and self._underlying_climate_delta_t is not None:
            added_energy = self._device_power * self._underlying_climate_delta_t

        self._total_energy += added_energy
        _LOGGER.debug(
            "%s - added energy is %.3f . Total energy is now: %.3f",
            self,
            added_energy,
            self._total_energy,
        )

    @callback
    async def _async_climate_changed(self, event):
        """Handle unerdlying climate state changes.
        This method takes the underlying values and update the VTherm with them.
        To avoid loops (issues #121 #101 #95 #99), we discard the event if it is received
        less than 10 sec after the last command. What we want here is to take the values
        from underlyings ONLY if someone have change directly on the underlying and not
        as a return of the command. The only thing we take all the time is the HVACAction
        which is important for feedaback and which cannot generates loops.
        """

        async def end_climate_changed(changes):
            """To end the event management"""
            if changes:
                self.async_write_ha_state()
                self.update_custom_attributes()
                await self.async_control_heating()

        new_state = event.data.get("new_state")
        _LOGGER.debug("%s - _async_climate_changed new_state is %s", self, new_state)
        if not new_state:
            return

        changes = False
        new_hvac_mode = new_state.state

        old_state = event.data.get("old_state")
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

        # Issue 99 - some AC turn hvac_mode=cool and hvac_action=idle when sending a HVACMode_OFF command
        # Issue 114 - Remove this because hvac_mode is now managed by local _hvac_mode and use idle action as is
        # if self._hvac_mode == HVACMode.OFF and new_hvac_action == HVACAction.IDLE:
        #    _LOGGER.debug("The underlying switch to idle instead of OFF. We will consider it as OFF")
        #    new_hvac_mode = HVACMode.OFF

        _LOGGER.info(
            "%s - Underlying climate changed. Event.new_hvac_mode is %s, current_hvac_mode=%s, new_hvac_action=%s, old_hvac_action=%s",
            self,
            new_hvac_mode,
            self._hvac_mode,
            new_hvac_action,
            old_hvac_action,
        )

        _LOGGER.debug(
            "%s - last_change_time=%s old_state_date_changed=%s old_state_date_updated=%s new_state_date_changed=%s new_state_date_updated=%s",
            self,
            self._last_change_time,
            old_state_date_changed,
            old_state_date_updated,
            new_state_date_changed,
            new_state_date_updated,
        )

        # Interpretation of hvac action
        HVAC_ACTION_ON = [  # pylint: disable=invalid-name
            HVACAction.COOLING,
            HVACAction.DRYING,
            HVACAction.FAN,
            HVACAction.HEATING,
        ]
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

        # Issue #120 - Some TRV are chaning target temperature a very long time (6 sec) after the change.
        # In that case a loop is possible if a user change multiple times during this 6 sec.
        if new_state_date_updated and self._last_change_time:
            delta = (new_state_date_updated - self._last_change_time).total_seconds()
            if delta < 10:
                _LOGGER.info(
                    "%s - underlying event is received less than 10 sec after command. Forget it to avoid loop",
                    self,
                )
                await end_climate_changed(changes)
                return

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
            changes = True
            self._hvac_mode = new_hvac_mode
            # Update all underlyings state
            if self.is_over_climate:
                for under in self._underlyings:
                    await under.set_hvac_mode(new_hvac_mode)

        if not changes:
            # try to manage new target temperature set if state
            _LOGGER.debug(
                "Do temperature check. temperature is %s, new_state.attributes is %s",
                self.target_temperature,
                new_state.attributes,
            )
            if (
                # we do not change target temperature on regulated VTherm
                not self.is_regulated
                and new_state.attributes
                and (new_target_temp := new_state.attributes.get("temperature"))
                and new_target_temp != self.target_temperature
            ):
                _LOGGER.info(
                    "%s - Target temp in underlying have change to %s",
                    self,
                    new_target_temp,
                )
                await self.async_set_temperature(temperature=new_target_temp)
                changes = True

        await end_climate_changed(changes)

    @overrides
    async def async_control_heating(self, force=False, _=None):
        """The main function used to run the calculation at each cycle"""
        ret = await super().async_control_heating(force, _)

        await self._send_regulated_temperature()

        return ret

    @property
    def auto_regulation_mode(self):
        """Get the regulation mode"""
        return self._auto_regulation_mode

    @property
    def regulated_target_temp(self):
        """Get the regulated target temperature"""
        return self._regulated_target_temp

    @property
    def is_regulated(self):
        """Check if the ThermostatOverClimate is regulated"""
        return self.auto_regulation_mode != CONF_AUTO_REGULATION_NONE

    @property
    def hvac_modes(self):
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
            return self.underlying_entity(0).fan_mode

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
        if self.underlying_entity(0):
            return self.underlying_entity(0).temperature_unit

        return self._unit

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).supported_features | self._support_flags

        return self._support_flags

    @property
    def target_temperature_step(self) -> float | None:
        """Return the supported step of target temperature."""
        if self.underlying_entity(0):
            return self.underlying_entity(0).target_temperature_step

        return None

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
    def is_aux_heat(self) -> bool | None:
        """Return true if aux heater.

        Requires ClimateEntityFeature.AUX_HEAT.
        """
        if self.underlying_entity(0):
            return self.underlying_entity(0).is_aux_heat

        return None

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
    async def async_set_fan_mode(self, fan_mode):
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
        _LOGGER.info("%s - Set fan mode: %s", self, humidity)
        if humidity is None:
            return
        for under in self._underlyings:
            await under.set_humidity(humidity)
        self._humidity = humidity
        self.async_write_ha_state()

    @overrides
    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set fan mode: %s", self, swing_mode)
        if swing_mode is None:
            return
        for under in self._underlyings:
            await under.set_swing_mode(swing_mode)
        self._swing_mode = swing_mode
        self.async_write_ha_state()

    async def service_set_auto_regulation_mode(self, auto_regulation_mode):
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

        await self._send_regulated_temperature()
        self.update_custom_attributes()
