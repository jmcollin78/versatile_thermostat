# pylint: disable=line-too-long
""" A climate over switch classe """
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.core import callback
from homeassistant.components.climate import HVACMode, HVACAction

from .base_thermostat import BaseThermostat

from .const import CONF_VALVE, CONF_VALVE_2, CONF_VALVE_3, CONF_VALVE_4

from .underlyings import UnderlyingValve

_LOGGER = logging.getLogger(__name__)

class ThermostatOverValve(BaseThermostat):
    """Representation of a class for a Versatile Thermostat over a Valve"""

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(frozenset(
        {
            "is_over_valve", "underlying_valve_0", "underlying_valve_1",
            "underlying_valve_2", "underlying_valve_3", "on_time_sec", "off_time_sec",
            "cycle_min", "function", "tpi_coef_int", "tpi_coef_ext"
        }))

    def __init__(self, hass: HomeAssistant, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat over switch."""
        super().__init__(hass, unique_id, name, entry_infos)

    @property
    def is_over_valve(self) -> bool:
        """ True if the Thermostat is over_valve"""
        return True

    @property
    def valve_open_percent(self) -> int:
        """ Gives the percentage of valve needed"""
        if self._hvac_mode == HVACMode.OFF:
            return 0
        else:
            return round(max(0, min(self.proportional_algorithm.on_percent, 1)) * 100)

    def post_init(self, entry_infos):
        """ Initialize the Thermostat"""

        super().post_init(entry_infos)
        lst_valves = [entry_infos.get(CONF_VALVE)]
        if entry_infos.get(CONF_VALVE_2):
            lst_valves.append(entry_infos.get(CONF_VALVE_2))
        if entry_infos.get(CONF_VALVE_3):
            lst_valves.append(entry_infos.get(CONF_VALVE_3))
        if entry_infos.get(CONF_VALVE_4):
            lst_valves.append(entry_infos.get(CONF_VALVE_4))

        for _, valve in enumerate(lst_valves):
            self._underlyings.append(
                UnderlyingValve(
                    hass=self._hass,
                    thermostat=self,
                    valve_entity_id=valve
                )
            )

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
    async def _async_valve_changed(self, event):
        """Handle unerdlying valve state changes.
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
                self.is_over_climate
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

    def update_custom_attributes(self):
        """ Custom attributes """
        super().update_custom_attributes()
        self._attr_extra_state_attributes["valve_open_percent"] = self.valve_open_percent
        self._attr_extra_state_attributes["is_over_valve"] = self.is_over_valve
        self._attr_extra_state_attributes["underlying_valve_0"] = (
                self._underlyings[0].entity_id)
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

        self.async_write_ha_state()
        _LOGGER.debug(
            "%s - Calling update_custom_attributes: %s",
            self,
            self._attr_extra_state_attributes,
        )

    def recalculate(self):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate all", self)
        self._prop_algorithm.calculate(
            self._target_temp,
            self._cur_temp,
            self._cur_ext_temp,
            self._hvac_mode == HVACMode.COOL,
        )

        for under in self._underlyings:
            under.set_valve_open_percent(
                self._prop_algorithm.on_percent
            )

        self.update_custom_attributes()
        self.async_write_ha_state()
