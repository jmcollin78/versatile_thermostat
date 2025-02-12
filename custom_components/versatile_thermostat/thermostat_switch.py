# pylint: disable=line-too-long, abstract-method

""" A climate over switch classe """
import logging
from homeassistant.core import Event, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from .const import (
    CONF_UNDERLYING_LIST,
    CONF_HEATER_KEEP_ALIVE,
    CONF_INVERSE_SWITCH,
    CONF_VSWITCH_ON_CMD_LIST,
    CONF_VSWITCH_OFF_CMD_LIST,
    overrides,
)

from .base_thermostat import BaseThermostat, ConfigData
from .underlyings import UnderlyingSwitch
from .prop_algorithm import PropAlgorithm

_LOGGER = logging.getLogger(__name__)

class ThermostatOverSwitch(BaseThermostat[UnderlyingSwitch]):
    """Representation of a base class for a Versatile Thermostat over a switch."""

    _entity_component_unrecorded_attributes = BaseThermostat._entity_component_unrecorded_attributes.union(  # pylint: disable=protected-access
        frozenset(
            {
                "is_over_switch",
                "is_inversed",
                "underlying_entities",
                "on_time_sec",
                "off_time_sec",
                "cycle_min",
                "function",
                "tpi_coef_int",
                "tpi_coef_ext",
                "power_percent",
                "calculated_on_percent",
                "vswitch_on_commands",
                "vswitch_off_commands",
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

        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
            self._minimal_deactivation_delay,
            self.name,
            max_on_percent=self._max_on_percent,
        )

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
            switch.startup()

        self.hass.create_task(self.async_control_heating())

    @overrides
    def update_custom_attributes(self):
        """Custom attributes"""
        super().update_custom_attributes()

        under0: UnderlyingSwitch = self._underlyings[0]
        self._attr_extra_state_attributes["is_over_switch"] = self.is_over_switch
        self._attr_extra_state_attributes["is_inversed"] = self.is_inversed
        self._attr_extra_state_attributes["keep_alive_sec"] = under0.keep_alive_sec

        self._attr_extra_state_attributes["underlying_entities"] = [
           underlying.entity_id for underlying in self._underlyings
        ]

        self._attr_extra_state_attributes[
            "on_percent"
        ] = self._prop_algorithm.on_percent
        self._attr_extra_state_attributes["power_percent"] = self.power_percent
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
            "calculated_on_percent"
        ] = self._prop_algorithm.calculated_on_percent

        self._attr_extra_state_attributes["vswitch_on_commands"] = self._lst_vswitch_on
        self._attr_extra_state_attributes["vswitch_off_commands"] = self._lst_vswitch_off

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
        self._prop_algorithm.calculate(
            self._target_temp,
            self._cur_temp,
            self._cur_ext_temp,
            self._hvac_mode or HVACMode.OFF,
        )
        self.update_custom_attributes()
        # already done bu update_custom_attributes
        # self.async_write_ha_state()

    @overrides
    def incremente_energy(self):
        """increment the energy counter if device is active"""
        if self.hvac_mode == HVACMode.OFF:
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
                "%s - incremente_energy increment energy is %s",
                self,
                self._total_energy,
            )

        self.update_custom_attributes()

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
        if new_state is None:
            return
        if old_state is None:
            self.hass.create_task(self._check_initial_state())

        self.async_write_ha_state()
        self.update_custom_attributes()
