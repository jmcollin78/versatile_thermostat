# pylint: disable=line-too-long, abstract-method

""" A climate over switch classe """
import logging
from datetime import timedelta
from homeassistant.core import Event, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    EventStateChangedData,
)
from homeassistant.core import HomeAssistant
from .vtherm_hvac_mode import VThermHvacMode_OFF

from .const import (
    CONF_UNDERLYING_LIST,
    CONF_HEATER_KEEP_ALIVE,
    CONF_INVERSE_SWITCH,
    CONF_VSWITCH_ON_CMD_LIST,
    CONF_VSWITCH_OFF_CMD_LIST,
    PROPORTIONAL_FUNCTION_TPI,
    overrides,
)

from .commons import write_event_log

from .base_thermostat import BaseThermostat, ConfigData
from .thermostat_prop import ThermostatProp
from .underlyings import UnderlyingSwitch

_LOGGER = logging.getLogger(__name__)

class ThermostatOverSwitch(ThermostatProp[UnderlyingSwitch]):
    """Representation of a base class for a Versatile Thermostat over a switch."""

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_switch",
                "vtherm_over_switch",
            }
        )
    )

    def __init__(self, hass: HomeAssistant, unique_id, name, config_entry) -> None:
        """Initialize the thermostat over switch."""
        self._is_inversed: bool | None = None
        self._lst_vswitch_on: list[str] = []
        self._lst_vswitch_off: list[str] = []
        super().__init__(hass, unique_id, name, config_entry)

    @property
    def is_over_switch(self) -> bool:
        """True if the Thermostat is over_switch"""
        return True

    @property
    def is_inversed(self) -> bool:
        """True if the switch is inversed (for pilot wire and diode)"""
        return self._is_inversed is True

    @overrides
    def post_init(self, config_entry: ConfigData):
        """Initialize the Thermostat"""

        super().post_init(config_entry)

        self._is_inversed = config_entry.get(CONF_INVERSE_SWITCH) is True

        lst_switches = config_entry.get(CONF_UNDERLYING_LIST)
        self._lst_vswitch_on = config_entry.get(CONF_VSWITCH_ON_CMD_LIST, [])
        self._lst_vswitch_off = config_entry.get(CONF_VSWITCH_OFF_CMD_LIST, [])

        delta_cycle = self._cycle_min * 60 / len(lst_switches)
        for idx, switch in enumerate(lst_switches):
            vswitch_on = self._lst_vswitch_on[idx] if idx < len(self._lst_vswitch_on) else None
            vswitch_off = self._lst_vswitch_off[idx] if idx < len(self._lst_vswitch_off) else None
            self._underlyings.append(
                UnderlyingSwitch(
                    hass=self._hass,
                    thermostat=self,
                    switch_entity_id=switch,
                    initial_delay_sec=idx * delta_cycle,
                    keep_alive_sec=config_entry.get(CONF_HEATER_KEEP_ALIVE, 0),
                    vswitch_on=vswitch_on,
                    vswitch_off=vswitch_off,
                )
            )

        self._should_relaunch_control_heating = False

    @overrides
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener to all underlying entities
        for switch in self._underlyings:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [switch.entity_id], self._async_switch_changed
                )
            )
            # done in BaseThermostat into async_startup
            # switch.startup()

        # self.hass.create_task(self.async_control_heating())
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
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        under0: UnderlyingSwitch = self._underlyings[0]

        # Standard attributes
        attributes = {
            "is_over_switch": self.is_over_switch,
            "on_percent": self.safe_on_percent,
            "power_percent": self.power_percent,
        }

        # Use pre-calculated on/off times from handler's control_heating
        on_time_sec = self._on_time_sec
        off_time_sec = self._off_time_sec

        # Underlying specific attributes
        vtherm_over_switch_attr = {
            "is_inversed": self.is_inversed,
            "keep_alive_sec": under0.keep_alive_sec,
            "underlying_entities": [underlying.entity_id for underlying in self._underlyings],
            "on_percent": self.safe_on_percent,
            "power_percent": self.power_percent,
            "on_time_sec": on_time_sec,
            "off_time_sec": off_time_sec,
            "function": self._proportional_function,
            "vswitch_on_commands": self._lst_vswitch_on,
            "vswitch_off_commands": self._lst_vswitch_off,
        }

        # Add TPI attributes if active
        if self._proportional_function == PROPORTIONAL_FUNCTION_TPI:
            vtherm_over_switch_attr.update({
                "tpi_coef_int": self._tpi_coef_int,
                "tpi_coef_ext": self._tpi_coef_ext,
                "tpi_threshold_low": self._tpi_threshold_low,
                "tpi_threshold_high": self._tpi_threshold_high,
                "minimal_activation_delay": self._minimal_activation_delay,
                "minimal_deactivation_delay": self._minimal_deactivation_delay,
            })

        attributes["vtherm_over_switch"] = vtherm_over_switch_attr
        self._attr_extra_state_attributes.update(attributes)

        # _LOGGER.debug("%s - Calling update_custom_attributes: %s", self, self._attr_extra_state_attributes)

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        if self.vtherm_hvac_mode == VThermHvacMode_OFF:
            return

        added_energy = 0
        if self.power_manager.mean_cycle_power is not None:
            # each underlying entity calculate its own energy. So we should divide by the number of underlying entities
            # see #877
            added_energy = self.power_manager.mean_cycle_power * float(self._cycle_min) / 60.0 / self.nb_underlying_entities

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
                "%s - incremente_energy increment energy is %s",
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

    @callback
    def _async_switch_changed(self, event: Event[EventStateChangedData]):
        """Handle heater switch state changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        write_event_log(_LOGGER, self, f"Underlying switch state changed from {old_state.state if old_state else None} to {new_state.state if new_state else None}")
        if new_state is None:
            return
        # #1654 - nno more needed now
        # if old_state is None:
        #     self.hass.create_task(self._check_initial_state())

        self.calculate_hvac_action()
        self.update_custom_attributes()
        self.async_write_ha_state()

    @property
    def vtherm_type(self) -> str | None:
        """Return the type of thermostat"""
        return "over_switch"
